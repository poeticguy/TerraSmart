"""Terraform execution wrapper for TerraSmart."""

import os
import subprocess
from pathlib import Path
from typing import Optional

from .utils import error_exit


class TerraformExecutor:
    """Wrapper for executing Terraform commands."""
    
    def __init__(self, work_dir: Path):
        """Initialize with working directory."""
        self.work_dir = Path(work_dir)
        if not self.work_dir.exists():
            error_exit(f"Working directory does not exist: {work_dir}")
    
    def init(self) -> str:
        """Run terraform init."""
        return self._run_terraform(["init", "-upgrade"])
    
    def plan(self) -> str:
        """Run terraform plan."""
        return self._run_terraform(["plan", "-detailed-exitcode"])
    
    def apply(self, auto_approve: bool = False) -> str:
        """Run terraform apply."""
        cmd = ["apply"]
        if auto_approve:
            cmd.append("-auto-approve")
        return self._run_terraform(cmd)
    
    def destroy(self, auto_approve: bool = False) -> str:
        """Run terraform destroy."""
        cmd = ["destroy"]
        if auto_approve:
            cmd.append("-auto-approve")
        return self._run_terraform(cmd)
    
    def _run_terraform(self, args: list) -> str:
        """Run terraform command with given arguments."""
        cmd = ["terraform"] + args
        
        # Set environment variables
        env = os.environ.copy()
        
        # Ensure Cloudflare provider can find credentials
        if not env.get('CLOUDFLARE_API_TOKEN'):
            # Try to get from config
            from .config import load_config
            config = load_config()
            if config.cloudflare_api_token:
                env['CLOUDFLARE_API_TOKEN'] = config.cloudflare_api_token
        
        try:
            # For interactive commands (apply/destroy without auto-approve), don't capture input
            interactive = (args[0] in ["apply", "destroy"] and "-auto-approve" not in args)
            
            if interactive:
                result = subprocess.run(
                    cmd,
                    cwd=self.work_dir,
                    env=env,
                    capture_output=False,  # Allow interactive input
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                return ""  # No output to capture for interactive commands
            else:
                result = subprocess.run(
                    cmd,
                    cwd=self.work_dir,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
            
            # For plan command, exit code 2 means changes are present (not an error)
            if args[0] == "plan" and result.returncode == 2:
                return result.stdout
            
            if result.returncode != 0:
                error_msg = f"Terraform {args[0]} failed (exit code {result.returncode})"
                if result.stderr:
                    error_msg += f":\n{result.stderr}"
                if result.stdout:
                    error_msg += f"\nOutput:\n{result.stdout}"
                raise Exception(error_msg)
            
            return result.stdout
            
        except subprocess.TimeoutExpired:
            raise Exception(f"Terraform {args[0]} timed out after 5 minutes")
        except FileNotFoundError:
            raise Exception(
                "Terraform not found in PATH. Please install Terraform:\n"
                "https://terraform.io/downloads"
            )
        except Exception as e:
            raise Exception(f"Failed to run terraform {args[0]}: {e}")
