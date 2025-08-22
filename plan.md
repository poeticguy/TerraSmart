# TerraSmart — Plan de ejecución (MVP con **ChatGPT GPT-5 nano**)

> **Objetivo:** construir un **CLI para Ubuntu/macOS** que convierte **lenguaje natural → DSL YAML → Terraform (Cloudflare provider v5)** y ejecuta **plan/apply**.  
> **Requisito clave:** el **CLI debe pedir y guardar la API key de ChatGPT antes de continuar** (ningún comando distinto a `init` puede ejecutarse si falta).
> **Requisito clave:** no  olvides el autor es Fernando Reyes y su cuenta de GitHub es @poeticguy, cuando necesites declararlo. Va ser un repositorio para publicar en Githib al mundo.

---

## 1) Alcance del MVP (v0.1)

- **CLI `ts`** con subcomandos: `init`, `plan`, `apply`, `dryrun`, `doctor`.
- **Integración IA**: uso de **ChatGPT** con modelo por defecto **`gpt-5-nano`** para traducir texto humano → **DSL** (YAML/JSON) con esquema fijo.
- **Validación estricta** del DSL con **JSON Schema** (rechazar salida inválida).
- **Render** de plantillas **Jinja2** → `providers.tf`, `main.tf`, `src/worker.js`.
- **Terraform local** (init/plan/apply) con **Cloudflare provider v5**.
- **Seguridad**: almacenar credenciales en `~/.config/terrasmart/config.toml` con permisos `0600`.
- **Packaging**: paquete `.deb` (Ubuntu) y alternativa **`pip install`** (Mac/Linux).

> **No incluido en v0.1:** runs remotos en Terraform Cloud, import masivo de recursos existentes, cobertura total de productos Cloudflare (se ampliará por versiones).

---

## 2) Requisitos y dependencias

- **SO:** Ubuntu 22.04+/Debian bookworm; macOS 13+ (para desarrollo/uso sin `.deb`).
- **Terraform/OpenTofu:** `terraform >= 1.5` (o `opentofu` equivalente).
- **Python 3.10+** con: `click`, `jinja2`, `jsonschema`, `pyyaml` o `toml`, `requests`, `openai`.
- **Credenciales necesarias:**
  - `OPENAI_API_KEY` (**obligatoria**; se solicitará por CLI en `init`).
  - `CLOUDFLARE_API_TOKEN` y `account_id`.
  - (Opcional) `default_zone` para atajos.

---

## 3) UX/Flujo del CLI

1. **`ts init`**  
   - Pide **API key de ChatGPT (obligatoria)** antes de continuar.  
   - Pide `CLOUDFLARE_API_TOKEN`, `account_id`, `default_zone`.  
   - Guarda `~/.config/terrasmart/config.toml` (`0600`).  
   - Si falta la API key, **termina con error** y no permite otros comandos.

2. **`ts plan "Crea un Worker y conéctalo a test.lattecompany.com"`**  
   - IA (`gpt-5-nano`) → **DSL** → **validación JSON Schema**.  
   - Render **Terraform** a `~/.local/share/terrasmart/run/<timestamp>/`.  
   - Ejecuta `terraform init -upgrade && terraform plan`.  
   - Muestra resumen de diff (+/~/-) y ruta a los archivos generados.

3. **`ts apply [--approve]`**  
   - Ejecuta `terraform apply` en la última carpeta de run (o `--dir`).  
   - Confirma si hay destrucciones (sin `--approve`).

4. **`ts dryrun "…"`**  
   - Genera DSL y archivos **sin** ejecutar Terraform.

5. **`ts doctor`**  
   - Verifica binarios, versiones y presencia de tokens con mensajes accionables.

---

## 4) Estructura del repositorio

```
terrasmart/
├─ apps/
│  └─ cli/
│     ├─ terrasmartrun/
│     │  ├─ __init__.py
│     │  ├─ cli.py          # entrypoint click
│     │  ├─ config.py       # lee/escribe config TOML (0600)
│     │  ├─ llm.py          # ChatGPT (gpt-5-nano) → DSL
│     │  ├─ dsl.py          # validación JSON Schema, fallback parser
│     │  ├─ render.py       # Jinja2 → TF files
│     │  ├─ tfexec.py       # init/plan/apply
│     │  └─ utils.py
│     └─ pyproject.toml
├─ templates/
│  ├─ providers.tf.j2
│  ├─ main.tf.j2
│  └─ worker.js
├─ schema/
│  └─ dsl.schema.json
├─ deb/
│  ├─ build.sh
│  └─ postinst.sh
├─ .github/workflows/
│  ├─ test.yml
│  └─ release.yml
└─ README.md
```

---

## 5) DSL (mini-contrato)

**`schema/dsl.schema.json`**
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["intent", "zone_name", "hostname"],
  "properties": {
    "intent": {
      "enum": [
        "create_worker_and_bind_domain",
        "create_dns_record",
        "create_kv_namespace",
        "create_d1_database"
      ]
    },
    "zone_name": { "type": "string", "pattern": "^[a-z0-9.-]+$" },
    "hostname":  { "type": "string", "pattern": "^[a-z0-9.-]+$" },
    "routing":   { "type": "object", "properties": { "mode": { "enum": ["custom_domain", "route"] } } },
    "worker": {
      "type": "object",
      "required": ["name", "module", "compatibility_date"],
      "properties": {
        "name": { "type": "string", "pattern": "^[a-z0-9-]{3,}$" },
        "module": { "type": "boolean" },
        "compatibility_date": { "type": "string" }
      }
    },
    "bindings": {
      "type": "object",
      "properties": {
        "kv": { "type": "array", "items": { "type": "string" } },
        "d1": { "type": "array", "items": { "type": "string" } }
      },
      "additionalProperties": false
    }
  },
  "additionalProperties": false
}
```

**Notas:**
- `routing.mode = "custom_domain"` por defecto; `"route"` usa DNS CNAME proxied + `worker_route`.
- `worker` es requerido solo para `create_worker_and_bind_domain`.

---

## 6) Integración **ChatGPT (GPT-5 nano)**

**Objetivo:** convertir texto → **DSL** válido y minimalista.

### 6.1 Configuración

- `ts init` **siempre** pide `OPENAI_API_KEY` y la guarda en `config.toml`:
```toml
[auth]
openai_api_key = "sk-..."
[defaults]
account_id = ""
zone_name  = ""
model_id   = "gpt-5-nano"
```
- El modelo se puede cambiar vía `model_id` (default: `"gpt-5-nano"`).

### 6.2 `apps/cli/terrasmartrun/llm.py`

**System prompt (sugerido):**
```
Eres un traductor de intención a un DSL de infraestructura para Cloudflare.
Devuelve SOLO JSON válido, sin texto extra ni markdown.
Esquema del DSL:
- intent: uno de ["create_worker_and_bind_domain","create_dns_record","create_kv_namespace","create_d1_database"]
- zone_name: dominio base, ej. "lattecompany.com"
- hostname: FQDN, ej. "api.lattecompany.com"
- routing.mode: "custom_domain" o "route" (por defecto custom_domain)
- worker: { name, module:boolean, compatibility_date: "YYYY-MM-DD" }
- bindings: { kv:[], d1:[] }
No inventes campos fuera del esquema. Usa defaults sensatos.
```

**Pseudocódigo de llamada:**
```python
def to_dsl(prompt_text: str, cfg: Config) -> dict:
    # Construir mensajes con system + user
    # Llamar al cliente OpenAI con model=cfg.model_id ("gpt-5-nano")
    # Parsear respuesta JSON -> dict
    # Validar contra schema (dsl.validate())
    # Si falla o no hay API key -> fallback a dsl.parse_rules()
```

### 6.3 Reglas de seguridad

- Timeout y reintentos limitados.
- Rechazar campos no permitidos por schema.
- **Nunca** imprimir la API key.
- Si la IA falla 2 veces → fallback parser (RegEx) que extrae `hostname`, deriva `zone_name`, y setea defaults.

---

## 7) Plantillas Terraform (Cloudflare v5)

**`templates/providers.tf.j2`**
```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    cloudflare = { source = "cloudflare/cloudflare", version = "~> 5" }
  }
}

variable "zone_name"  { type = string }
variable "hostname"   { type = string }
variable "worker_name"{ type = string }
variable "account_id" { type = string }

provider "cloudflare" {}

data "cloudflare_zones" "zone" { name = var.zone_name }
locals { zone_id = data.cloudflare_zones.zone.result[0].id }
```

**`templates/main.tf.j2`** (modo `custom_domain` por defecto; conmutar a `route` si se indica)
```hcl
{% if intent == "create_worker_and_bind_domain" %}
resource "cloudflare_workers_script" "app" {
  account_id         = var.account_id
  name               = var.worker_name
  module             = {{ "true" if worker.module else "false" }}
  compatibility_date = "{{ worker.compatibility_date }}"
  content            = file("${path.module}/src/worker.js")
  {% for ns in (bindings.kv or []) %}
  kv_namespace_binding {
    name         = "{{ ns | upper }}"
    namespace_id = cloudflare_workers_kv_namespace.{{ ns }}.id
  }
  {% endfor %}
  {% for db in (bindings.d1 or []) %}
  d1_database_binding {
    name        = "{{ db | upper }}"
    database_id = cloudflare_d1_database.{{ db }}.id
  }
  {% endfor %}
}

{% for ns in (bindings.kv or []) %}
resource "cloudflare_workers_kv_namespace" "{{ ns }}" {
  account_id = var.account_id
  title      = "{{ ns }}"
}
{% endfor %}

{% for db in (bindings.d1 or []) %}
resource "cloudflare_d1_database" "{{ db }}" {
  account_id = var.account_id
  name       = "{{ db }}"
}
{% endfor %}

{% if (routing.mode or "custom_domain") == "custom_domain" %}
resource "cloudflare_workers_custom_domain" "host" {
  account_id = var.account_id
  script_name = cloudflare_workers_script.app.name
  zone_id    = local.zone_id
  hostname   = var.hostname
}
{% else %}
resource "cloudflare_dns_record" "host" {
  zone_id = local.zone_id
  name    = replace(var.hostname, ".{{ zone_name }}", "")
  type    = "CNAME"
  content = "{{ zone_name }}"
  proxied = true
  ttl     = 300
}
resource "cloudflare_worker_route" "route" {
  zone_id     = local.zone_id
  pattern     = "${var.hostname}/*"
  script_name = cloudflare_workers_script.app.name
}
{% endif %}

{% elif intent == "create_dns_record" %}
resource "cloudflare_dns_record" "record" {
  zone_id = local.zone_id
  name    = replace(var.hostname, ".{{ zone_name }}", "")
  type    = "TXT"
  content = "managed-by-terrasmart"
  ttl     = 300
  proxied = false
}
{% endif %}
```

**`templates/worker.js`**
```js
export default {
  async fetch() {
    return new Response("Hola desde TerraSmart 👋\n", {
      headers: { "content-type": "text/plain; charset=utf-8" },
    });
  }
}
```

---

## 8) Implementación del CLI

### 8.1 `init` (API key bloqueante)
- Flujo:
  1) Solicitar `OPENAI_API_KEY` (**obligatoria**). Si vacía → abortar con error claro.
  2) Solicitar `CLOUDFLARE_API_TOKEN`, `account_id`, `default_zone` (opcionales; advertir si faltan).
  3) Guardar `config.toml` y aplicar `chmod 600`.

### 8.2 `plan`
- `llm.to_dsl(texto, cfg)` (modelo `gpt-5-nano` por defecto).
- Validar el DSL; si falla, fallback reglas.
- Render TF; generar `terraform.tfvars` con `zone_name`, `hostname`, `worker_name`, `account_id`.
- `terraform init -upgrade && terraform plan`.
- Mostrar diff resumido y ruta de trabajo.

### 8.3 `apply`
- Requiere carpeta de run (última por defecto).
- Confirmación si hay destrucciones (sin `--approve`).

### 8.4 `dryrun`
- Igual que `plan` pero **sin** ejecutar Terraform.

### 8.5 `doctor`
- Verifica: Python, Terraform en `PATH`, `OPENAI_API_KEY`, `CLOUDFLARE_API_TOKEN`, conectividad simple.

---

## 9) Packaging y CI

### 9.1 `.deb` (Ubuntu)
- `deb/build.sh` usando **fpm** o `dpkg-deb`:
  - Instalar binario `ts` en `/usr/bin/`.
  - Plantillas en `/usr/share/terrasmart/templates/`.
  - `postinst.sh`: mensaje final (“ejecuta `terrasmart init`”).

### 9.2 `pip install` (Mac/Linux)
- `pyproject.toml` con entrypoint `ts`.
- Publicación opcional en PyPI en v0.1.1.

### 9.3 GitHub Actions
- `test.yml`: lint + tests unitarios (parser/validator/render).
- `release.yml`: on tag → build `.deb` y adjuntar a Releases.

---

## 10) Criterios de aceptación (v0.1)

- **Init bloqueante por API key:** si el usuario no ingresa `OPENAI_API_KEY`, **ningún** otro comando corre.
- `ts plan "Crea un Worker y conéctalo a test.lattecompany.com"`:
  - IA devuelve DSL válido; se renderiza TF sin error.
  - `terraform plan` corre y muestra cambios a aplicar.
- `ts apply --approve` crea:
  - `cloudflare_workers_script` + `workers_custom_domain` (o `route+dns` si se elige).
  - El host responde al `worker.js`.
- `doctor` reporta claramente problemas de binarios/tokens.

---

## 11) Roadmap siguiente

- **v0.2:** Terraform Cloud (runs remotos) + `imports.tf` para adopción sin CLI local.  
- **v0.3:** más recursos Cloudflare (R2, reglas de seguridad comunes), multi-intención en una sola orden (“crea KV + bindea + CNAME”).

---

## 12) Tareas para Windsurf (pasos concretos)

1. **Proyecto y CLI base**
   - Crear `apps/cli/terrasmartrun` con `click` y comandos: `init`, `plan`, `apply`, `dryrun`, `doctor`.
   - `init` pide **OPENAI_API_KEY** primero; si falta, aborta.

2. **Integración ChatGPT (`gpt-5-nano`)**
   - Implementar `llm.py` con `to_dsl(text, cfg)` usando `model_id` (default `"gpt-5-nano"`).
   - System prompt que describa el DSL; output **JSON** estricto.
   - Manejar errores y fallback a `dsl.parse_rules()`.

3. **Validación DSL**
   - `dsl.py` con `validate(dsl)` usando `schema/dsl.schema.json`.
   - Fallback parser: extraer `hostname`, derivar `zone_name`, defaults de `worker`.

4. **Render TF y ejecución**
   - `render.py` (Jinja2) → `providers.tf`, `main.tf`, `src/worker.js`.
   - `tfexec.py` → `terraform init/plan/apply`; crear `terraform.tfvars`.

5. **Templates y schema**
   - Añadir `templates/` y `schema/` como arriba.
   - Asegurar `data.cloudflare_zones...result[0].id`.

6. **Packaging y CI**
   - `deb/build.sh` + `postinst.sh`.
   - Workflows `test.yml`, `release.yml`.

7. **Documentación**
   - `README.md` con Quickstart y Troubleshooting (auth v5, tokens, permisos).

---

## 13) Quickstart de desarrollo (para el equipo)

```bash
# Ubuntu/macOS
python3 -m venv .venv && source .venv/bin/activate
pip install -e apps/cli  # (usar pyproject.toml)
# Terraform
brew install hashicorp/tap/terraform || sudo apt-get install terraform

# Primera vez
ts init  # pide OPENAI_API_KEY (obligatoria), CLOUDFLARE_API_TOKEN, etc.

# Prueba (solo genera)
ts dryrun "Crea un Worker y conéctalo a test.lattecompany.com"

# Plan y apply
ts plan "Crea un Worker y conéctalo a test.lattecompany.com"
ts apply --approve
```
