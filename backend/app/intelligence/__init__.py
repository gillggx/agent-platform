"""
Intelligence Module — LLM integration and conversation engine.

Exports:
- LLMAdapterV2: Unified LLM interface with intelligent routing
- ModelRouter: Model selection based on complexity/cost
- LLMClient: Raw LLM API calls with retry logic
- LLMConfig: Global LLM configuration
- AgentConversation: Multi-agent conversation engine
- ConversationContext: Conversation state management
- Message: Inter-agent message format
- MessageType: Message type enumeration
"""

from .llm_adapter_v2 import (
    LLMAdapterV2,
    LLMClient,
    ModelRouter,
    LLMConfig,
    LLMResponse,
    LLMUsage,
    ModelSelection,
    FallbackDecision,
    ComplexityLevel,
    ROLE_COMPLEXITY_MAP,
)

from .agent_conversation import (
    AgentConversation,
    ConversationContext,
    ConversationManager,
    Message,
    MessageType,
    ConversationState,
    MessageBroadcaster,
)

__all__ = [
    # LLM Adapter
    "LLMAdapterV2",
    "LLMClient",
    "ModelRouter",
    "LLMConfig",
    "LLMResponse",
    "LLMUsage",
    "ModelSelection",
    "FallbackDecision",
    "ComplexityLevel",
    "ROLE_COMPLEXITY_MAP",
    # Conversation
    "AgentConversation",
    "ConversationContext",
    "ConversationManager",
    "Message",
    "MessageType",
    "ConversationState",
    "MessageBroadcaster",
]
