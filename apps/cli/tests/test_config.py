"""Tests for configuration management."""

import tempfile
import os
from pathlib import Path
from terrasmartrun.config import Config


def test_config_save_and_load():
    """Test configuration save and load functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a config with test data
        config = Config()
        config.openai_api_key = "test-key"
        config.cloudflare_api_token = "test-token"
        config.account_id = "test-account"
        config.default_zone = "example.com"
        config.model_id = "gpt-4o-mini"
        
        # Override config file path for testing
        original_config_file = config.config_file
        config._config_file_override = Path(temp_dir) / "config.toml"
        
        # Save configuration
        config.save()
        
        # Verify file exists and has correct permissions
        assert config.config_file.exists()
        file_mode = oct(config.config_file.stat().st_mode)[-3:]
        assert file_mode == "600"
        
        # Load configuration into new instance
        new_config = Config()
        new_config._config_file_override = config.config_file
        new_config.load()
        
        # Verify all values loaded correctly
        assert new_config.openai_api_key == "test-key"
        assert new_config.cloudflare_api_token == "test-token"
        assert new_config.account_id == "test-account"
        assert new_config.default_zone == "example.com"
        assert new_config.model_id == "gpt-4o-mini"


def test_config_has_cloudflare_config():
    """Test Cloudflare configuration detection."""
    config = Config()
    
    # Initially should not have Cloudflare config
    assert not config.has_cloudflare_config()
    
    # Add token but not account ID
    config.cloudflare_api_token = "test-token"
    assert not config.has_cloudflare_config()
    
    # Add account ID
    config.account_id = "test-account"
    assert config.has_cloudflare_config()


def test_config_validate_required():
    """Test required configuration validation."""
    config = Config()
    
    # Should raise error without OpenAI key
    try:
        config.validate_required()
        assert False, "Should have raised error"
    except SystemExit:
        pass  # Expected
    
    # Should not raise error with OpenAI key
    config.openai_api_key = "test-key"
    config.validate_required()  # Should not raise
