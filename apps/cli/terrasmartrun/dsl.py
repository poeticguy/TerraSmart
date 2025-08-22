"""DSL validation and parsing for TerraSmart."""

import json
from pathlib import Path
from typing import Dict, Any
import jsonschema

from .utils import error_exit


def get_schema() -> Dict[str, Any]:
    """Load the DSL JSON schema."""
    # Try multiple possible locations for the schema file
    possible_paths = [
        Path(__file__).parent.parent.parent.parent / "schema" / "dsl.schema.json",  # From installed package
        Path(__file__).parent.parent.parent / "schema" / "dsl.schema.json",        # From development
        Path(__file__).parent / "schema" / "dsl.schema.json",                      # Alternative location
    ]
    
    schema_path = None
    for path in possible_paths:
        if path.exists():
            schema_path = path
            break
    
    if not schema_path:
        error_exit(f"Schema file not found in any of these locations: {[str(p) for p in possible_paths]}")
    
    try:
        with open(schema_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        error_exit(f"Failed to load schema: {e}")


def validate_dsl(dsl_data: Dict[str, Any]) -> None:
    """Validate DSL data against the JSON schema."""
    schema = get_schema()
    
    try:
        jsonschema.validate(dsl_data, schema)
    except jsonschema.ValidationError as e:
        raise ValueError(f"DSL validation failed: {e.message}")
    except Exception as e:
        raise ValueError(f"Schema validation error: {e}")
    
    # Additional custom validations
    _validate_custom_rules(dsl_data)


def _validate_custom_rules(dsl_data: Dict[str, Any]) -> None:
    """Apply custom validation rules beyond JSON schema."""
    intent = dsl_data.get("intent")
    
    # Worker is required for create_worker_and_bind_domain
    if intent == "create_worker_and_bind_domain":
        if "worker" not in dsl_data:
            raise ValueError("Worker configuration is required for create_worker_and_bind_domain intent")
        
        worker = dsl_data["worker"]
        
        # Validate worker name length (Cloudflare limits)
        if len(worker.get("name", "")) > 63:
            raise ValueError("Worker name must be 63 characters or less")
        
        # Validate compatibility date format
        compat_date = worker.get("compatibility_date", "")
        if not _is_valid_date_format(compat_date):
            raise ValueError("Worker compatibility_date must be in YYYY-MM-DD format")
    
    # Validate hostname is a valid FQDN
    hostname = dsl_data.get("hostname", "")
    if not _is_valid_hostname(hostname):
        raise ValueError(f"Invalid hostname format: {hostname}")
    
    # Validate zone_name is a valid domain
    zone_name = dsl_data.get("zone_name", "")
    if not _is_valid_domain(zone_name):
        raise ValueError(f"Invalid zone_name format: {zone_name}")


def _is_valid_date_format(date_str: str) -> bool:
    """Check if date string is in YYYY-MM-DD format."""
    import re
    pattern = r'^\d{4}-\d{2}-\d{2}$'
    return bool(re.match(pattern, date_str))


def _is_valid_hostname(hostname: str) -> bool:
    """Check if hostname is a valid FQDN."""
    import re
    # Basic hostname validation
    pattern = r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)*$'
    return bool(re.match(pattern, hostname.lower()))


def _is_valid_domain(domain: str) -> bool:
    """Check if domain is valid."""
    import re
    # Basic domain validation
    pattern = r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)*$'
    return bool(re.match(pattern, domain.lower())) and '.' in domain
