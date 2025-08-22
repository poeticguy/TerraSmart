"""Main CLI interface for TerraSmart."""

import click
from pathlib import Path
from typing import Optional

from .config import load_config, prompt_for_config
from .utils import success_message, error_exit, info_message, warning_message
from .llm import to_dsl
from .dsl import validate_dsl
from .render import render_terraform
from .tfexec import TerraformExecutor


@click.group()
@click.version_option(version="0.1.0")
def main():
    """ts - Natural language to Terraform CLI for Cloudflare."""
    pass


@main.command()
def init():
    """Initialize ts configuration."""
    info_message("Initializing ts configuration...")
    
    # Prompt for configuration
    config = prompt_for_config()
    
    # Save configuration
    config.save()
    
    success_message("Configuration saved successfully!")
    info_message(f"Configuration file: {config.config_file}")
    
    if not config.has_cloudflare_config():
        warning_message(
            "Cloudflare configuration is incomplete. "
            "You can run 'ts init' again to update it, "
            "or set CLOUDFLARE_API_TOKEN environment variable."
        )
    
    info_message("Run 'ts doctor' to verify your setup.")


@main.command()
@click.argument('prompt', required=True)
@click.option('--dir', 'output_dir', help='Output directory for generated files')
def plan(prompt: str, output_dir: Optional[str]):
    """Generate and plan Terraform configuration from natural language."""
    config = load_config()
    config.validate_required()
    
    info_message(f"Processing: {prompt}")
    
    # Convert natural language to DSL
    try:
        dsl_data = to_dsl(prompt, config)
        info_message("✓ Natural language converted to DSL")
    except Exception as e:
        error_exit(f"Failed to convert prompt to DSL: {e}")
    
    # Validate DSL
    try:
        validate_dsl(dsl_data)
        info_message("✓ DSL validation passed")
    except Exception as e:
        error_exit(f"DSL validation failed: {e}")
    
    # Render Terraform files
    try:
        work_dir = render_terraform(dsl_data, config, output_dir)
        info_message(f"✓ Terraform files generated in: {work_dir}")
    except Exception as e:
        error_exit(f"Failed to render Terraform files: {e}")
    
    # Execute terraform plan
    try:
        executor = TerraformExecutor(work_dir)
        executor.init()
        info_message("✓ Terraform initialized")
        
        plan_output = executor.plan()
        info_message("✓ Terraform plan completed")
        
        print("\n" + "="*50)
        print("TERRAFORM PLAN OUTPUT")
        print("="*50)
        print(plan_output)
        
        success_message(f"Plan completed successfully! Files in: {work_dir}")
        
    except Exception as e:
        error_exit(f"Terraform plan failed: {e}")


@main.command()
@click.option('--approve', is_flag=True, help='Auto-approve the apply')
@click.option('--dir', 'work_dir', help='Working directory (uses latest if not specified)')
def apply(approve: bool, work_dir: Optional[str]):
    """Apply the Terraform configuration."""
    config = load_config()
    config.validate_required()
    
    if not work_dir:
        # Find the latest terraform directory in current working directory
        terraform_dir = Path.cwd() / "terraform"
        if not terraform_dir.exists():
            error_exit("No terraform directory found. Run 'ts plan' first.")
        
        run_dirs = [d for d in terraform_dir.glob("*") if d.is_dir()]
        if not run_dirs:
            error_exit("No previous runs found. Run 'ts plan' first.")
        work_dir = str(max(run_dirs, key=lambda x: x.stat().st_mtime))
        info_message(f"Using latest run directory: {work_dir}")
    
    work_path = Path(work_dir)
    if not work_path.exists():
        error_exit(f"Working directory does not exist: {work_dir}")
    
    try:
        executor = TerraformExecutor(work_path)
        
        # Check if there are any destroys in the plan
        if not approve:
            plan_output = executor.plan()
            if "destroy" in plan_output.lower() or "delete" in plan_output.lower():
                if not click.confirm("⚠️  This plan contains destructive changes. Continue?"):
                    info_message("Apply cancelled.")
                    return
        
        apply_output = executor.apply(auto_approve=approve)
        info_message("✓ Terraform apply completed")
        
        print("\n" + "="*50)
        print("TERRAFORM APPLY OUTPUT")
        print("="*50)
        print(apply_output)
        
        success_message("Apply completed successfully!")
        
    except Exception as e:
        error_exit(f"Terraform apply failed: {e}")


@main.command()
@click.argument('prompt', required=True)
@click.option('--dir', 'output_dir', help='Output directory for generated files')
def dryrun(prompt: str, output_dir: Optional[str]):
    """Generate Terraform configuration without executing it."""
    config = load_config()
    config.validate_required()
    
    info_message(f"Dry run for: {prompt}")
    
    # Convert natural language to DSL
    try:
        dsl_data = to_dsl(prompt, config)
        info_message("✓ Natural language converted to DSL")
    except Exception as e:
        error_exit(f"Failed to convert prompt to DSL: {e}")
    
    # Validate DSL
    try:
        validate_dsl(dsl_data)
        info_message("✓ DSL validation passed")
    except Exception as e:
        error_exit(f"DSL validation failed: {e}")
    
    # Render Terraform files
    try:
        work_dir = render_terraform(dsl_data, config, output_dir)
        info_message(f"✓ Terraform files generated in: {work_dir}")
    except Exception as e:
        error_exit(f"Failed to render Terraform files: {e}")
    
    success_message(f"Dry run completed! Files generated in: {work_dir}")
    info_message("Run 'ts plan' with the same prompt to execute terraform plan.")


@main.command()
def doctor():
    """Check system requirements and configuration."""
    from .utils import check_binary_exists, get_terraform_version
    
    info_message("Running ts diagnostics...")
    
    issues = []
    
    # Check Python version
    import sys
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    if sys.version_info >= (3, 10):
        success_message(f"Python {python_version} ✓")
    else:
        issues.append(f"Python 3.10+ required, found {python_version}")
    
    # Check Terraform
    if check_binary_exists("terraform"):
        tf_version = get_terraform_version()
        success_message(f"Terraform {tf_version} ✓")
    else:
        issues.append("Terraform not found in PATH")
    
    # Check configuration
    config = load_config()
    
    if config.openai_api_key:
        success_message("OpenAI API key configured ✓")
    else:
        issues.append("OpenAI API key not configured (run 'ts init')")
    
    if config.cloudflare_api_token:
        success_message("Cloudflare API token configured ✓")
    else:
        issues.append("Cloudflare API token not configured")
    
    if config.account_id:
        success_message("Cloudflare account ID configured ✓")
    else:
        issues.append("Cloudflare account ID not configured")
    
    # Test OpenAI connectivity
    if config.openai_api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=config.openai_api_key)
            # Test with a simple completion
            response = client.chat.completions.create(
                model=config.model_id,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            success_message("OpenAI API connectivity ✓")
        except Exception as e:
            issues.append(f"OpenAI API test failed: {str(e)[:100]}...")
    
    # Summary
    if issues:
        print("\n❌ Issues found:")
        for issue in issues:
            print(f"  • {issue}")
        print("\nRecommendations:")
        if "OpenAI API key not configured" in str(issues):
            print("  • Run 'ts init' to configure API keys")
        if "Terraform not found" in str(issues):
            print("  • Install Terraform: https://terraform.io/downloads")
        if "Cloudflare" in str(issues):
            print("  • Get Cloudflare API token: https://dash.cloudflare.com/profile/api-tokens")
    else:
        success_message("All checks passed! ts is ready to use.")


if __name__ == "__main__":
    main()
