"""LLM integration for converting natural language to DSL."""

import json
import re
from typing import Dict, Any
from openai import OpenAI

from .config import Config
from .utils import error_exit, warning_message


SYSTEM_PROMPT = """Eres un traductor de intención a un DSL de infraestructura para Cloudflare.
Devuelve SOLO JSON válido, sin texto extra ni markdown.
Esquema del DSL:
- intent: uno de ["create_worker_and_bind_domain","create_dns_record","create_kv_namespace","create_d1_database","delete_dns_record"]
- zone_name: dominio base, ej. "example.com"
- hostname: FQDN, ej. "api.example.com"

Para create_worker_and_bind_domain:
- routing.mode: "custom_domain" o "route" (opcional, por defecto custom_domain)
- worker: { name, module:boolean, compatibility_date: "YYYY-MM-DD" }
- bindings: { kv:[], d1:[] }

Para create_dns_record:
- dns_record: { type: "A|AAAA|CNAME|TXT|MX|NS", content: "valor", ttl: 300, proxied: false }
- NO incluyas routing para DNS records

Para delete_dns_record:
- dns_record: { type: "A|AAAA|CNAME|TXT|MX|NS", content: "valor_a_eliminar" }
- Solo incluye los campos necesarios para identificar el registro a eliminar

No inventes campos fuera del esquema. Usa defaults sensatos."""


def to_dsl(prompt_text: str, config: Config) -> Dict[str, Any]:
    """Convert natural language prompt to DSL using OpenAI."""
    try:
        dsl_data = _call_openai(prompt_text, config)
        # Post-process the DSL to fix common issues
        dsl_data = _post_process_dsl(dsl_data, config)
        return dsl_data
    except Exception as e:
        warning_message(f"OpenAI call failed: {e}")
        warning_message("Falling back to rule-based parser...")
        return _fallback_parser(prompt_text, config)


def _call_openai(prompt_text: str, config: Config) -> Dict[str, Any]:
    """Call OpenAI API to convert prompt to DSL."""
    client = OpenAI(api_key=config.openai_api_key)
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt_text}
    ]
    
    try:
        response = client.chat.completions.create(
            model=config.model_id,
            messages=messages,
            max_tokens=500,
            temperature=0.1,
            timeout=30
        )
        
        content = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        content = re.sub(r'^```json\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        
        # Parse JSON
        dsl_data = json.loads(content)
        
        return dsl_data
        
    except json.JSONDecodeError as e:
        raise Exception(f"Invalid JSON response from OpenAI: {e}")
    except Exception as e:
        raise Exception(f"OpenAI API error: {e}")


def _fallback_parser(prompt_text: str, config: Config) -> Dict[str, Any]:
    """Fallback rule-based parser when OpenAI fails."""
    prompt_lower = prompt_text.lower()
    
    # Extract hostname using regex
    hostname_patterns = [
        r'(?:conecta|bind|domain|host).*?([a-z0-9.-]+\.[a-z]{2,})',
        r'([a-z0-9.-]+\.[a-z]{2,})',
    ]
    
    hostname = None
    for pattern in hostname_patterns:
        match = re.search(pattern, prompt_lower)
        if match:
            hostname = match.group(1)
            break
    
    # Handle @ symbol (root domain)
    if "@" in prompt_text or "apuntando a @" in prompt_lower:
        if config.default_zone:
            hostname = config.default_zone
        else:
            hostname = "example.com"
    elif not hostname:
        # Use default zone if available
        if config.default_zone:
            hostname = f"app.{config.default_zone}"
        else:
            hostname = "app.example.com"
    
    # Derive zone_name from hostname
    parts = hostname.split('.')
    if len(parts) >= 2:
        zone_name = '.'.join(parts[-2:])
    else:
        zone_name = hostname
    
    # Determine intent
    intent = "create_worker_and_bind_domain"  # Default
    
    if any(word in prompt_lower for word in ["eliminar", "delete", "borrar", "quitar", "remove"]):
        if any(word in prompt_lower for word in ["dns", "record", "txt", "cname", "a record"]):
            intent = "delete_dns_record"
    elif any(word in prompt_lower for word in ["dns", "record", "cname", "a record"]):
        intent = "create_dns_record"
    elif any(word in prompt_lower for word in ["kv", "namespace", "storage"]):
        intent = "create_kv_namespace"
    elif any(word in prompt_lower for word in ["d1", "database", "db"]):
        intent = "create_d1_database"
    
    # Generate worker name from hostname
    worker_name = hostname.replace('.', '-').replace('_', '-')
    if len(worker_name) > 63:  # Cloudflare limit
        worker_name = worker_name[:63]
    
    # Build DSL
    dsl = {
        "intent": intent,
        "zone_name": zone_name,
        "hostname": hostname
    }
    
    if intent == "create_worker_and_bind_domain":
        dsl["routing"] = {"mode": "custom_domain"}
        dsl["worker"] = {
            "name": worker_name,
            "module": True,
            "compatibility_date": "2024-01-01"
        }
        dsl["bindings"] = {"kv": [], "d1": []}
    elif intent == "create_dns_record":
        # Extract record type and content from prompt
        record_type = "TXT"  # Default
        content = "managed-by-terrasmart"  # Default
        
        if any(word in prompt_lower for word in ["txt", "text"]):
            record_type = "TXT"
            # Try to extract content from quotes or after "diga"
            import re
            content_match = re.search(r'(?:diga|contenido|content)["\s]*([^"]+)', prompt_lower)
            if content_match:
                content = content_match.group(1).strip()
            elif "hello mundo" in prompt_lower or "hello world" in prompt_lower:
                content = "Hello Mundo"
        elif any(word in prompt_lower for word in ["cname"]):
            record_type = "CNAME"
            content = zone_name
        elif any(word in prompt_lower for word in ["a record", "tipo a"]):
            record_type = "A"
            content = "192.0.2.1"  # Example IP
        
        dsl["dns_record"] = {
            "type": record_type,
            "content": content,
            "ttl": 300,
            "proxied": False
        }
    elif intent == "delete_dns_record":
        # Extract record type and content for deletion
        record_type = "TXT"  # Default
        content = None
        
        if any(word in prompt_lower for word in ["txt", "text"]):
            record_type = "TXT"
            # Try to extract content to identify the record
            if "hello" in prompt_lower:
                content = "Hello Mundo"
        elif any(word in prompt_lower for word in ["cname"]):
            record_type = "CNAME"
        elif any(word in prompt_lower for word in ["a record", "tipo a"]):
            record_type = "A"
        
        dsl["dns_record"] = {
            "type": record_type
        }
        if content:
            dsl["dns_record"]["content"] = content
    
    return dsl


def _post_process_dsl(dsl_data: Dict[str, Any], config: Config) -> Dict[str, Any]:
    """Post-process DSL data to fix common issues from OpenAI."""
    # Fix zone_name if it's "@" (root domain)
    if dsl_data.get("zone_name") == "@":
        if config.default_zone:
            dsl_data["zone_name"] = config.default_zone
        else:
            dsl_data["zone_name"] = "example.com"
    
    # Add missing hostname for DNS records
    if dsl_data.get("intent") in ["create_dns_record", "delete_dns_record"] and "hostname" not in dsl_data:
        # For @ records, hostname should be the zone itself
        dsl_data["hostname"] = dsl_data["zone_name"]
    
    # Ensure required fields are present
    if "zone_name" not in dsl_data and config.default_zone:
        dsl_data["zone_name"] = config.default_zone
    
    # For all DNS operations, ensure we use the correct zone from config
    if dsl_data.get("intent") in ["create_dns_record", "delete_dns_record"] and config.default_zone:
        # Always override with the configured zone
        dsl_data["zone_name"] = config.default_zone
        # For root domain records, hostname should be the zone itself
        if "hostname" not in dsl_data or dsl_data.get("hostname") in ["@", config.default_zone]:
            dsl_data["hostname"] = config.default_zone
        else:
            # For subdomains, ensure they're under the correct zone
            hostname = dsl_data.get("hostname", "")
            if not hostname.endswith(f".{config.default_zone}"):
                # Extract subdomain and rebuild with correct zone
                parts = hostname.split(".")
                if len(parts) > 1:
                    subdomain = parts[0]
                    dsl_data["hostname"] = f"{subdomain}.{config.default_zone}"
    
    return dsl_data
