"""Configuration management for TerraSmart CLI."""

import os
import toml
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

from .utils import get_config_dir, secure_file_permissions, error_exit


@dataclass
class Config:
    """Configuration class for TerraSmart."""
    openai_api_key: Optional[str] = None
    cloudflare_api_token: Optional[str] = None
    account_id: Optional[str] = None
    default_zone: Optional[str] = None
    model_id: str = "gpt-4o-mini"  # Using available model instead of gpt-5-nano
    
    @property
    def config_file(self) -> Path:
        """Get the configuration file path."""
        if hasattr(self, '_config_file_override'):
            return self._config_file_override
        return get_config_dir() / "config.toml"
    
    def load(self) -> None:
        """Load configuration from file."""
        if not self.config_file.exists():
            return
        
        try:
            data = toml.load(self.config_file)
            
            # Load auth section
            auth = data.get("auth", {})
            self.openai_api_key = auth.get("openai_api_key")
            self.cloudflare_api_token = auth.get("cloudflare_api_token")
            
            # Load defaults section
            defaults = data.get("defaults", {})
            self.account_id = defaults.get("account_id")
            self.default_zone = defaults.get("zone_name")
            self.model_id = defaults.get("model_id", self.model_id)
            
        except Exception as e:
            error_exit(f"Failed to load configuration: {e}")
    
    def save(self) -> None:
        """Save configuration to file."""
        config_data = {
            "auth": {
                "openai_api_key": self.openai_api_key,
                "cloudflare_api_token": self.cloudflare_api_token,
            },
            "defaults": {
                "account_id": self.account_id,
                "zone_name": self.default_zone,
                "model_id": self.model_id,
            }
        }
        
        # Remove None values
        config_data["auth"] = {k: v for k, v in config_data["auth"].items() if v is not None}
        config_data["defaults"] = {k: v for k, v in config_data["defaults"].items() if v is not None}
        
        try:
            # Ensure config directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write configuration
            with open(self.config_file, 'w') as f:
                toml.dump(config_data, f)
            
            # Set secure permissions
            secure_file_permissions(self.config_file)
            
        except Exception as e:
            error_exit(f"Failed to save configuration: {e}")
    
    def validate_required(self) -> None:
        """Validate that required configuration is present."""
        if not self.openai_api_key:
            error_exit(
                "OpenAI API key is required but not configured.\n"
                "Please run 'terrasmart init' to set up your configuration."
            )
    
    def has_cloudflare_config(self) -> bool:
        """Check if Cloudflare configuration is present."""
        return bool(self.cloudflare_api_token and self.account_id)


def load_config() -> Config:
    """Load configuration from file."""
    config = Config()
    config.load()
    return config


def prompt_for_config() -> Config:
    """Prompt user for configuration values."""
    import getpass
    
    config = Config()
    
    # OpenAI API Key (required)
    while not config.openai_api_key:
        api_key = getpass.getpass("Enter your OpenAI API key (required): ").strip()
        if not api_key:
            print("❌ OpenAI API key is required to continue.")
            continue
        config.openai_api_key = api_key
    
    # Cloudflare API Token
    cloudflare_token = getpass.getpass("Enter your Cloudflare API token (optional, press Enter to skip): ").strip()
    if cloudflare_token:
        config.cloudflare_api_token = cloudflare_token
    
    # Account ID
    if config.cloudflare_api_token:
        account_id = input("Enter your Cloudflare account ID (optional): ").strip()
        if account_id:
            config.account_id = account_id
    
    # Default zone
    if config.cloudflare_api_token:
        default_zone = input("Enter your default zone/domain (optional): ").strip()
        if default_zone:
            config.default_zone = default_zone
    
    # Use default model without asking
    # config.model_id already defaults to "gpt-4o-mini"
    
    return config
