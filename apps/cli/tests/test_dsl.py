"""Tests for DSL validation and parsing."""

import pytest
from terrasmartrun.dsl import validate_dsl
from terrasmartrun.llm import _fallback_parser
from terrasmartrun.config import Config


def test_validate_worker_dsl():
    """Test DSL validation for worker creation."""
    valid_dsl = {
        "intent": "create_worker_and_bind_domain",
        "zone_name": "example.com",
        "hostname": "api.example.com",
        "routing": {"mode": "custom_domain"},
        "worker": {
            "name": "api-example-com",
            "module": True,
            "compatibility_date": "2024-01-01"
        },
        "bindings": {"kv": [], "d1": []}
    }
    
    # Should not raise any exception
    validate_dsl(valid_dsl)


def test_validate_dns_dsl():
    """Test DSL validation for DNS record creation."""
    valid_dsl = {
        "intent": "create_dns_record",
        "zone_name": "example.com",
        "hostname": "blog.example.com"
    }
    
    # Should not raise any exception
    validate_dsl(valid_dsl)


def test_invalid_dsl_missing_required():
    """Test DSL validation with missing required fields."""
    invalid_dsl = {
        "intent": "create_worker_and_bind_domain",
        # Missing zone_name and hostname
    }
    
    with pytest.raises(ValueError):
        validate_dsl(invalid_dsl)


def test_invalid_worker_name():
    """Test DSL validation with invalid worker name."""
    invalid_dsl = {
        "intent": "create_worker_and_bind_domain",
        "zone_name": "example.com",
        "hostname": "api.example.com",
        "worker": {
            "name": "a" * 70,  # Too long
            "module": True,
            "compatibility_date": "2024-01-01"
        }
    }
    
    with pytest.raises(ValueError):
        validate_dsl(invalid_dsl)


def test_fallback_parser():
    """Test the fallback parser functionality."""
    config = Config()
    config.account_id = "test-account"
    
    # Test worker creation
    result = _fallback_parser("Create a Worker and connect it to api.example.com", config)
    
    assert result["intent"] == "create_worker_and_bind_domain"
    assert result["zone_name"] == "example.com"
    assert result["hostname"] == "api.example.com"
    assert "worker" in result
    
    # Test DNS record creation
    result = _fallback_parser("Create DNS record for blog.example.com", config)
    
    assert result["intent"] == "create_dns_record"
    assert result["zone_name"] == "example.com"
    assert result["hostname"] == "blog.example.com"


def test_fallback_parser_kv():
    """Test fallback parser for KV namespace."""
    config = Config()
    
    result = _fallback_parser("Add KV storage for cache.example.com", config)
    
    assert result["intent"] == "create_kv_namespace"
    assert result["zone_name"] == "example.com"
    assert result["hostname"] == "cache.example.com"
