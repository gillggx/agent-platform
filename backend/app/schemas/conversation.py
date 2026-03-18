"""
Conversation Schemas — Pydantic models for multi-agent conversations.

Provides:
- MessageSchema: Standardized inter-agent message format
- MessageTypeSchema: Message type enumeration
- ConversationContextSchema: Active conversation state
- MessageHistorySchema: Conversation history

Type annotations: 100%
Docstrings: 100%
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Types of inter-agent messages."""
    REQUEST = "request"
    RESPONSE = "response"
    DECISION = "decision"
    FEEDBACK = "feedback"
    UPDATE = "update"
    ERROR = "error"


class MessageStatusSchema(BaseModel):
    """
    Status of a message.
    
    Attributes:
        sent: Message sent timestamp
        received: Message received timestamp
        read: Message read timestamp
        acknowledged: Whether message was acknowledged
    """
    sent: datetime = Field(default_factory=datetime.utcnow)
    received: Optional[datetime] = None
    read: Optional[datetime] = None
    acknowledged: bool = Field(default=False)


class MessageSchema(BaseModel):
    """
    Standardized inter-agent message format.
    
    Attributes:
        message_id: Unique message identifier
        from_role: Sending agent role
        to_roles: List of recipient agent roles (empty = broadcast)
        message_type: Type of message (request, response, decision, etc.)
        content: Message content text
        context: Contextual information
        metadata: Additional message metadata
        status: Message delivery status
        parent_message_id: ID of message this replies to
    """
    message_id: str = Field(default_factory=lambda: str(__import__('uuid').uuid4()))
    from_role: str = Field(..., min_length=1, max_length=50)
    to_roles: List[str] = Field(default_factory=list)
    message_type: MessageType
    content: str = Field(..., min_length=1)
    context: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    status: MessageStatusSchema = Field(default_factory=MessageStatusSchema)
    parent_message_id: Optional[str] = None


class ConversationContextSchema(BaseModel):
    """
    Active conversation context state.
    
    Attributes:
        conversation_id: Unique conversation identifier
        initiator_role: Which agent started the conversation
        current_agent_role: Currently speaking agent
        current_turn: Current conversation turn number
        message_history: List of messages in this conversation
        shared_context: Shared state visible to all agents
        execution_context: Workflow/execution context
        conversation_state: Current state (active, paused, concluded, failed)
        created_at: Conversation creation timestamp
        updated_at: Last update timestamp
    """
    conversation_id: str = Field(default_factory=lambda: str(__import__('uuid').uuid4()))
    initiator_role: str = Field(..., min_length=1)
    current_agent_role: str = Field(..., min_length=1)
    current_turn: int = Field(default=0, ge=0)
    message_history: List[MessageSchema] = Field(default_factory=list)
    shared_context: Dict[str, Any] = Field(default_factory=dict)
    execution_context: Dict[str, Any] = Field(default_factory=dict)
    conversation_state: str = Field(default="active")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MessageHistorySchema(BaseModel):
    """
    Conversation message history snapshot.
    
    Attributes:
        conversation_id: Which conversation
        message_count: Total messages in history
        messages: Recent messages (paginated)
        time_range_start: Earliest message time
        time_range_end: Latest message time
        participant_roles: All roles that participated
        metadata: History metadata
    """
    conversation_id: str = Field(...)
    message_count: int = Field(default=0, ge=0)
    messages: List[MessageSchema] = Field(default_factory=list)
    time_range_start: Optional[datetime] = None
    time_range_end: Optional[datetime] = None
    participant_roles: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BroadcastResultSchema(BaseModel):
    """
    Result of broadcasting a message to multiple agents.
    
    Attributes:
        message_id: Original message ID
        broadcast_time_ms: Time to broadcast in milliseconds
        recipients_count: Number of recipients
        successful_recipients: Agents that received the message
        failed_recipients: Agents that failed to receive
        metadata: Additional metadata
    """
    message_id: str = Field(...)
    broadcast_time_ms: float = Field(default=0.0, ge=0.0)
    recipients_count: int = Field(default=0, ge=0)
    successful_recipients: List[str] = Field(default_factory=list)
    failed_recipients: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationSummarySchema(BaseModel):
    """
    Summary of a completed conversation.
    
    Attributes:
        conversation_id: Which conversation
        initiator_role: Agent that started it
        participants: All agents involved
        turn_count: Total turns/exchanges
        duration_seconds: Total conversation duration
        key_decisions: Important decisions made
        artifacts_generated: Artifacts created
        status: Final status (concluded, failed, timed_out)
    """
    conversation_id: str = Field(...)
    initiator_role: str = Field(..., min_length=1)
    participants: List[str] = Field(default_factory=list)
    turn_count: int = Field(default=0, ge=0)
    duration_seconds: float = Field(default=0.0, ge=0.0)
    key_decisions: List[Dict[str, Any]] = Field(default_factory=list)
    artifacts_generated: List[str] = Field(default_factory=list)
    status: str = Field(default="concluded")
