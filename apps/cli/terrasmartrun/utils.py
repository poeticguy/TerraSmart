"""Utility functions for TerraSmart CLI."""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional


def get_config_dir() -> Path:
    """Get the configuration directory path."""
    config_dir = Path.home() / ".config" / "terrasmart"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_data_dir() -> Path:
    """Get the data directory path for runs."""
    data_dir = Path.home() / ".local" / "share" / "terrasmart"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def check_binary_exists(binary: str) -> bool:
    """Check if a binary exists in PATH."""
    try:
        subprocess.run([binary, "--version"], 
                      capture_output=True, 
                      check=True, 
                      timeout=10)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_terraform_version() -> Optional[str]:
    """Get Terraform version if available."""
    try:
        result = subprocess.run(["terraform", "--version"], 
                              capture_output=True, 
                              text=True, 
                              timeout=10)
        if result.returncode == 0:
            # Extract version from first line
            first_line = result.stdout.split('\n')[0]
            if 'Terraform v' in first_line:
                return first_line.split('v')[1].strip()
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def error_exit(message: str, code: int = 1) -> None:
    """Print error message and exit."""
    print(f"❌ Error: {message}", file=sys.stderr)
    sys.exit(code)


def success_message(message: str) -> None:
    """Print success message."""
    print(f"✅ {message}")


def warning_message(message: str) -> None:
    """Print warning message."""
    print(f"⚠️  {message}")


def info_message(message: str) -> None:
    """Print info message."""
    print(f"ℹ️  {message}")


def secure_file_permissions(file_path: Path) -> None:
    """Set secure file permissions (0600)."""
    os.chmod(file_path, 0o600)
