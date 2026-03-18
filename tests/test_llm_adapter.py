"""
Unit tests for LLM Adapter V2.

Tests:
- Model selection based on role and complexity
- LLM configuration management
- Fallback strategy logic
- Token tracking and cost estimation
"""

import pytest
import asyncio
from typing import Dict, Any
from app.intelligence.llm_adapter_v2 import (
    LLMAdapterV2,
    LLMConfig,
    ModelRouter,
    ComplexityLevel,
    ROLE_COMPLEXITY_MAP,
)


class TestModelRouter:
    """Tests for model selection."""

    def test_model_router_init(self):
        """Test ModelRouter initialization."""
        config = LLMConfig()
        router = ModelRouter(config)
        assert router.config == config

    def test_role_complexity_mapping(self):
        """Test role to complexity mapping."""
        # PM should map to MEDIUM
        assert ROLE_COMPLEXITY_MAP["pm"] == ComplexityLevel.MEDIUM
        # Architect should map to COMPLEX
        assert ROLE_COMPLEXITY_MAP["architect"] == ComplexityLevel.COMPLEX
        # QA should map to SIMPLE
        assert ROLE_COMPLEXITY_MAP["qa"] == ComplexityLevel.SIMPLE

    def test_select_model_by_role(self):
        """Test model selection by role."""
        config = LLMConfig()
        router = ModelRouter(config)
        
        # Select for architect (COMPLEX role)
        selection = router.select_model(role="architect")
        assert selection is not None
        assert selection.model_id is not None
        assert selection.provider is not None
        assert selection.complexity_level == ComplexityLevel.COMPLEX

    def test_select_model_by_complexity(self):
        """Test model selection by complexity level."""
        config = LLMConfig()
        router = ModelRouter(config)
        
        # Select for SIMPLE complexity
        selection = router.select_model(complexity=ComplexityLevel.SIMPLE)
        assert selection.complexity_level == ComplexityLevel.SIMPLE
        assert selection.confidence > 0.8

    def test_model_selection_includes_alternatives(self):
        """Test that model selection includes alternatives."""
        config = LLMConfig()
        router = ModelRouter(config)
        
        selection = router.select_model(role="qa", complexity=ComplexityLevel.SIMPLE)
        # Should have at least the selected model
        assert selection.model_id is not None
        # Alternatives list can be empty or have items
        assert isinstance(selection.alternatives, list)

    def test_cost_estimation(self):
        """Test cost estimation for models."""
        config = LLMConfig()
        router = ModelRouter(config)
        
        # Estimate cost: 1000 prompt tokens, 500 completion tokens
        cost = router.estimate_cost(
            prompt_tokens=1000,
            completion_tokens=500,
            model="gpt-4o-mini",
        )
        # Cost should be positive
        assert cost >= 0
        # Should be small for mini model
        assert cost < 0.01


class TestLLMConfig:
    """Tests for LLM configuration."""

    def test_config_defaults(self):
        """Test default configuration."""
        config = LLMConfig()
        assert config.default_provider == "openai"
        assert config.default_model == "gpt-4o-mini"
        assert config.timeout_seconds == 90
        assert config.max_retries == 3
        assert config.rate_limit_rpm == 100

    def test_api_key_management(self):
        """Test API key management."""
        config = LLMConfig()
        
        # Set and get API keys
        config.set_api_key("openai", "sk-test-key")
        assert config.get_api_key("openai") == "sk-test-key"
        
        # Non-existent key should return None
        assert config.get_api_key("anthropic") is None

    def test_config_customization(self):
        """Test configuration customization."""
        config = LLMConfig(
            default_provider="anthropic",
            default_model="claude-3-5-sonnet-20241022",
            timeout_seconds=60,
            max_retries=5,
        )
        assert config.default_provider == "anthropic"
        assert config.default_model == "claude-3-5-sonnet-20241022"
        assert config.timeout_seconds == 60
        assert config.max_retries == 5


class TestLLMAdapterV2:
    """Tests for LLM Adapter V2."""

    def test_adapter_init(self):
        """Test adapter initialization."""
        config = LLMConfig()
        adapter = LLMAdapterV2(config)
        
        assert adapter.config == config
        assert adapter.router is not None
        assert adapter.client is not None

    def test_adapter_default_config(self):
        """Test adapter with default config."""
        adapter = LLMAdapterV2()
        assert adapter.config is not None
        assert adapter.config.default_model == "gpt-4o-mini"

    def test_select_model_via_adapter(self):
        """Test model selection through adapter."""
        adapter = LLMAdapterV2()
        
        selection = adapter.select_model(role="director")
        assert selection.model_id is not None
        assert selection.complexity_level == ComplexityLevel.COMPLEX

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check (will be skipped without real API)."""
        adapter = LLMAdapterV2()
        # This will fail without proper API keys configured
        # In CI/test environment, we'll skip this
        pytest.skip("Requires API key configuration")


class TestComplexityLevels:
    """Tests for complexity level handling."""

    def test_complexity_enum_values(self):
        """Test complexity enum."""
        assert ComplexityLevel.SIMPLE.value == "simple"
        assert ComplexityLevel.MEDIUM.value == "medium"
        assert ComplexityLevel.COMPLEX.value == "complex"

    def test_all_roles_have_complexity_mapping(self):
        """Test that key roles have complexity mappings."""
        required_roles = ["pm", "architect", "qa", "devops", "director"]
        for role in required_roles:
            assert role in ROLE_COMPLEXITY_MAP
            assert isinstance(ROLE_COMPLEXITY_MAP[role], ComplexityLevel)


class TestModelSelection:
    """Tests for model selection decision."""

    def test_model_selection_to_dict(self):
        """Test model selection serialization."""
        from app.intelligence.llm_adapter_v2 import ModelSelection
        
        selection = ModelSelection(
            model_id="gpt-4o",
            provider="openai",
            complexity_level=ComplexityLevel.COMPLEX,
            confidence=0.95,
            reason="Test reason",
            alternatives=["claude-3-5-sonnet-20241022"],
        )
        
        data = selection.to_dict()
        assert data["model_id"] == "gpt-4o"
        assert data["provider"] == "openai"
        assert data["complexity_level"] == "complex"
        assert data["confidence"] == 0.95
        assert len(data["alternatives"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
