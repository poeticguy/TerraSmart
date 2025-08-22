"""Terraform template rendering for TerraSmart."""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader

from .config import Config
from .utils import get_data_dir, error_exit


def render_terraform(dsl_data: Dict[str, Any], config: Config, output_dir: Optional[str] = None) -> Path:
    """Render Terraform files from DSL data."""
    # Determine output directory
    if output_dir:
        work_dir = Path(output_dir)
    else:
        # Generate in current working directory instead of hidden system directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        work_dir = Path.cwd() / "terraform" / timestamp
    
    work_dir.mkdir(parents=True, exist_ok=True)
    
    # Setup Jinja2 environment - try multiple possible locations
    possible_template_dirs = [
        Path(__file__).parent.parent.parent.parent / "templates",  # From installed package
        Path(__file__).parent.parent.parent / "templates",        # From development
        Path(__file__).parent / "templates",                      # Alternative location
    ]
    
    template_dir = None
    for path in possible_template_dirs:
        if path.exists():
            template_dir = path
            break
    
    if not template_dir:
        error_exit(f"Templates directory not found in any of these locations: {[str(p) for p in possible_template_dirs]}")
    
    env = Environment(loader=FileSystemLoader(template_dir))
    
    # Prepare template variables
    template_vars = {
        **dsl_data,
        "config": config
    }
    
    # Render providers.tf
    providers_template = env.get_template("providers.tf.j2")
    providers_content = providers_template.render(**template_vars)
    
    providers_file = work_dir / "providers.tf"
    with open(providers_file, 'w') as f:
        f.write(providers_content)
    
    # Render main.tf
    main_template = env.get_template("main.tf.j2")
    main_content = main_template.render(**template_vars)
    
    main_file = work_dir / "main.tf"
    with open(main_file, 'w') as f:
        f.write(main_content)
    
    # Create src directory and copy worker.js if needed
    if dsl_data.get("intent") == "create_worker_and_bind_domain":
        src_dir = work_dir / "src"
        src_dir.mkdir(exist_ok=True)
        
        worker_template_file = template_dir / "worker.js"
        worker_file = src_dir / "worker.js"
        
        if worker_template_file.exists():
            with open(worker_template_file, 'r') as f:
                worker_content = f.read()
            with open(worker_file, 'w') as f:
                f.write(worker_content)
    
    # Generate terraform.tfvars
    tfvars_content = _generate_tfvars(dsl_data, config)
    tfvars_file = work_dir / "terraform.tfvars"
    with open(tfvars_file, 'w') as f:
        f.write(tfvars_content)
    
    return work_dir


def _generate_tfvars(dsl_data: Dict[str, Any], config: Config) -> str:
    """Generate terraform.tfvars content."""
    lines = []
    
    # Required variables
    lines.append(f'zone_name = "{dsl_data["zone_name"]}"')
    lines.append(f'hostname = "{dsl_data["hostname"]}"')
    
    # Worker name
    if dsl_data.get("intent") == "create_worker_and_bind_domain":
        worker_name = dsl_data["worker"]["name"]
    else:
        # Generate a default worker name
        worker_name = dsl_data["hostname"].replace('.', '-').replace('_', '-')
        if len(worker_name) > 63:
            worker_name = worker_name[:63]
    
    lines.append(f'worker_name = "{worker_name}"')
    
    # Account ID
    account_id = config.account_id or os.environ.get('CLOUDFLARE_ACCOUNT_ID', '')
    if not account_id:
        error_exit(
            "Cloudflare account ID is required but not configured.\n"
            "Set it in 'terrasmart init' or via CLOUDFLARE_ACCOUNT_ID environment variable."
        )
    
    lines.append(f'account_id = "{account_id}"')
    
    return '\n'.join(lines) + '\n'
