"""
LLM Schemas — Pydantic models for LLM requests, responses, and configurations.

Provides:
- LLMRequestSchema: Standardized LLM call requests
- LLMResponseSchema: Standardized LLM responses with usage tracking
- LLMConfigSchema: Global LLM configuration
- ModelSelectionSchema: Model selection decision data

Type annotations: 100%
Docstrings: 100%
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"


class ComplexityLevel(str, Enum):
    """Task complexity levels for model selection."""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


class LLMUsageSchema(BaseModel):
    """
    LLM API usage statistics.
    
    Attributes:
        prompt_tokens: Number of prompt tokens used
        completion_tokens: Number of completion tokens used
        total_tokens: Total tokens used
        model: Model identifier used
        provider: Provider name
        cost_usd: Estimated cost in USD
    """
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    model: str = Field(..., min_length=1)
    provider: str = Field(default="unknown")
    cost_usd: float = Field(default=0.0, ge=0.0)


class LLMRequestSchema(BaseModel):
    """
    Standardized LLM request.
    
    Attributes:
        prompt: The main prompt text
        system_prompt: System context/instructions
        temperature: Response randomness (0.0-2.0)
        max_tokens: Maximum tokens to generate
        role: Agent role making the request (for routing)
        complexity: Task complexity level
        context: Additional context for the LLM
        metadata: Request metadata
    """
    prompt: str = Field(..., min_length=1)
    system_prompt: Optional[str] = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, gt=0, le=32000)
    role: Optional[str] = None
    complexity: ComplexityLevel = Field(default=ComplexityLevel.MEDIUM)
    context: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LLMResponseSchema(BaseModel):
    """
    Standardized LLM response.
    
    Attributes:
        content: Generated text content
        usage: Token usage statistics
        model: Model that generated this response
        provider: Provider that generated this response
        completion_time_ms: Time to complete request in milliseconds
        cached: Whether response was cached
        metadata: Additional response metadata
    """
    content: str = Field(..., min_length=1)
    usage: LLMUsageSchema
    model: str = Field(..., min_length=1)
    provider: str = Field(default="unknown")
    completion_time_ms: Optional[float] = None
    cached: bool = Field(default=False)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ModelConfigSchema(BaseModel):
    """
    Configuration for a specific LLM model.
    
    Attributes:
        model_id: Model identifier
        provider: Provider (openai, anthropic, etc.)
        complexity_level: Suitable complexity level
        max_tokens: Maximum tokens for this model
        cost_per_1k_tokens: Cost per 1000 tokens
        latency_p95_ms: 95th percentile latency
        enabled: Whether this model is enabled
    """
    model_id: str = Field(..., min_length=1)
    provider: LLMProvider
    complexity_level: ComplexityLevel
    max_tokens: int = Field(default=2048, gt=0)
    cost_per_1k_tokens: float = Field(default=0.0, ge=0.0)
    latency_p95_ms: Optional[float] = None
    enabled: bool = Field(default=True)


class LLMConfigSchema(BaseModel):
    """
    Global LLM configuration.
    
    Attributes:
        default_provider: Default LLM provider
        default_model: Default model to use
        api_keys: API keys by provider
        models: Configuration for each available model
        rate_limit_rpm: Requests per minute limit
        timeout_seconds: Request timeout
        max_retries: Maximum retry attempts
        fallback_strategy: Fallback strategy when primary fails
        enable_caching: Cache LLM responses
    """
    default_provider: LLMProvider = Field(default=LLMProvider.OPENAI)
    default_model: str = Field(default="gpt-4o-mini")
    api_keys: Dict[str, str] = Field(default_factory=dict)
    models: List[ModelConfigSchema] = Field(default_factory=list)
    rate_limit_rpm: int = Field(default=100, gt=0)
    timeout_seconds: int = Field(default=90, gt=0)
    max_retries: int = Field(default=3, ge=0, le=10)
    fallback_strategy: str = Field(default="timeout_rate_limit_error")
    enable_caching: bool = Field(default=False)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ModelSelectionSchema(BaseModel):
    """
    Result of model selection decision.
    
    Attributes:
        selected_model: Selected model ID
        provider: Selected provider
        reason: Reasoning for this selection
        alternatives: Alternative models considered
        confidence: Confidence level (0.0-1.0)
    """
    selected_model: str = Field(..., min_length=1)
    provider: LLMProvider
    reason: str = Field(default="")
    alternatives: List[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class FallbackDecisionSchema(BaseModel):
    """
    Fallback strategy decision when LLM call fails.
    
    Attributes:
        error_type: Type of error (timeout, rate_limit, error)
        fallback_model: Model to fallback to
        should_retry: Whether to retry
        retry_delay_seconds: How long to wait before retry
        metadata: Additional fallback metadata
    """
    error_type: str = Field(...)
    fallback_model: Optional[str] = None
    should_retry: bool = Field(default=True)
    retry_delay_seconds: float = Field(default=5.0, ge=0.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
