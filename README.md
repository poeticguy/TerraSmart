# TerraSmart

**Natural language to Terraform CLI for Cloudflare infrastructure**

TerraSmart converts your natural language descriptions into production-ready Terraform configurations for Cloudflare resources. Simply describe what you want in plain English (or Spanish), and TerraSmart will generate, plan, and apply the infrastructure for you.

[![Test](https://github.com/poeticguy/terrasmart/actions/workflows/test.yml/badge.svg)](https://github.com/poeticguy/terrasmart/actions/workflows/test.yml)
[![Release](https://github.com/poeticguy/terrasmart/actions/workflows/release.yml/badge.svg)](https://github.com/poeticguy/terrasmart/actions/workflows/release.yml)

## Features

- **AI-Powered**: Uses OpenAI GPT models to understand natural language
- **Secure**: Stores credentials safely with proper file permissions
- **Fast**: Direct Terraform execution with automatic initialization
- **Easy Install**: Available as `.deb` package or via pip
- **Comprehensive**: Supports Workers, DNS, KV namespaces, D1 databases
- **Validated**: JSON Schema validation with intelligent fallbacks

## Quick Start

### Installation

**Ubuntu/Debian:**
```bash
# Download the latest .deb package from releases
sudo dpkg -i terrasmart_0.1.0.deb
```

**macOS/Linux (pip):**
```bash
pip install terrasmart
```

### Setup

1. **Initialize configuration:**
```bash
ts init
```
This will prompt for:
- OpenAI API key (required)
- Cloudflare API token
- Cloudflare Account ID
- Default zone/domain

2. **Verify setup:**
```bash
ts doctor
```

### Usage Examples

**Create a Cloudflare Worker:**
```bash
ts plan "Create a Worker and connect it to api.mycompany.com"
ts apply --approve
```

**Create DNS records:**
```bash
ts plan "Add a DNS record for blog.mycompany.com"
ts apply
```

**Dry run (generate files only):**
```bash
ts dryrun "Create a Worker with KV storage for cache.mycompany.com"
```

## Requirements

- **Python 3.10+**
- **Terraform >= 1.5** ([Install Terraform](https://terraform.io/downloads))
- **OpenAI API key** ([Get API key](https://platform.openai.com/api-keys))
- **Cloudflare API token** ([Create token](https://dash.cloudflare.com/profile/api-tokens))

## Commands

### `ts init`
Initialize configuration with API keys and settings.

### `ts plan "<description>"`
Convert natural language to Terraform and run `terraform plan`.

### `ts apply [--approve]`
Apply the last generated Terraform configuration.

### `ts dryrun "<description>"`
Generate Terraform files without executing them.

### `ts doctor`
Check system requirements and configuration.

## Supported Infrastructure

### Cloudflare Workers
- Worker script deployment
- Custom domain binding
- Route-based deployment
- KV namespace binding
- D1 database binding

### DNS Management
- DNS record creation
- Proxied/non-proxied records
- Multiple record types

### Storage
- KV namespaces
- D1 databases

## Security

- API keys stored in `~/.config/terrasmart/config.toml` with `0600` permissions
- No credentials logged or exposed
- Secure environment variable handling
- Terraform state managed locally

## Configuration

Configuration is stored in `~/.config/terrasmart/config.toml`:

```toml
[auth]
openai_api_key = "sk-..."
cloudflare_api_token = "..."

[defaults]
account_id = "..."
zone_name = "mycompany.com"
model_id = "gpt-4o-mini"
```

## Development

### Setup Development Environment

```bash
git clone https://github.com/poeticguy/terrasmart.git
cd terrasmart
python3 -m venv .venv
source .venv/bin/activate
pip install -e apps/cli/
```

### Run Tests

```bash
pytest apps/cli/tests/ -v
```

### Build Package

```bash
cd deb
./build.sh
```

## Examples

### Worker with Custom Domain
```bash
ts plan "Deploy a Worker to handle API requests at api.example.com"
```

### Worker with KV Storage
```bash
ts plan "Create a Worker with KV storage for caching at cache.example.com"
```

### DNS Record
```bash
ts plan "Add a CNAME record for www.example.com"
```

### Multiple Resources
```bash
ts plan "Create a Worker with D1 database and KV namespace for app.example.com"
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Author

**Fernando Reyes** ([@poeticguy](https://github.com/poeticguy))

## Issues & Support

- [Report Issues](https://github.com/poeticguy/terrasmart/issues)
- [Feature Requests](https://github.com/poeticguy/terrasmart/issues/new?template=feature_request.md)

## Roadmap

- **v0.2**: Terraform Cloud integration, remote state management
- **v0.3**: Additional Cloudflare resources (R2, security rules)
- **v0.4**: Multi-cloud support (AWS, Azure, GCP)

---

**Made for the DevOps community**
