"""
Agent Conversation Engine — Multi-agent dialogue with context management.

Features:
- Multi-round conversations (agent.say() → other agents listen)
- Shared context visible to all agents
- Message history tracking with timestamps
- Inter-agent messaging and broadcasting
- Conversation state management

Architecture:
- ConversationContext: Mutable conversation state
- Message: Standardized message format
- AgentConversation: Main conversation coordinator
- MessageBroadcaster: Handles message routing to agents

Type annotations: 100%
Docstrings: 100%
Async-first design.
"""

from __future__ import annotations

import asyncio
import logging
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Awaitable
from uuid import uuid4

logger = logging.getLogger(__name__)


# ============================================================================
# Enums & Constants
# ============================================================================

class MessageType(str, Enum):
    """Types of inter-agent messages."""
    REQUEST = "request"
    RESPONSE = "response"
    DECISION = "decision"
    FEEDBACK = "feedback"
    UPDATE = "update"
    ERROR = "error"


class ConversationState(str, Enum):
    """Conversation lifecycle states."""
    CREATED = "created"
    ACTIVE = "active"
    PAUSED = "paused"
    CONCLUDED = "concluded"
    FAILED = "failed"
    TIMEOUT = "timeout"


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class Message:
    """
    Standardized inter-agent message.
    
    Attributes:
        message_id: Unique identifier
        from_role: Sending agent role
        to_roles: List of recipient roles (empty = broadcast to all)
        message_type: Type of message
        content: Message text content
        context: Context data (workflow state, artifacts, etc.)
        metadata: Additional metadata
        timestamp: When message was created
        parent_message_id: ID of message this replies to
    """
    message_id: str = field(default_factory=lambda: str(uuid4()))
    from_role: str = ""
    to_roles: List[str] = field(default_factory=list)
    message_type: MessageType = MessageType.REQUEST
    content: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    parent_message_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "message_id": self.message_id,
            "from_role": self.from_role,
            "to_roles": self.to_roles,
            "message_type": self.message_type.value,
            "content": self.content,
            "context": self.context,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "parent_message_id": self.parent_message_id,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Message:
        """Create Message from dictionary."""
        return Message(
            message_id=data.get("message_id", str(uuid4())),
            from_role=data.get("from_role", ""),
            to_roles=data.get("to_roles", []),
            message_type=MessageType(data.get("message_type", "request")),
            content=data.get("content", ""),
            context=data.get("context", {}),
            metadata=data.get("metadata", {}),
            timestamp=datetime.fromisoformat(data["timestamp"]) 
                if "timestamp" in data else datetime.utcnow(),
            parent_message_id=data.get("parent_message_id"),
        )


@dataclass
class ConversationContext:
    """
    Active conversation state.
    
    Attributes:
        conversation_id: Unique conversation identifier
        initiator_role: Agent that started the conversation
        current_agent_role: Currently speaking agent
        current_turn: Current turn number
        message_history: All messages in this conversation
        shared_context: State visible to all agents (workflow context, artifacts)
        execution_context: Execution/workflow metadata
        conversation_state: Current state (active, paused, concluded, etc.)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        max_turns: Maximum allowed turns (None = unlimited)
    """
    conversation_id: str = field(default_factory=lambda: str(uuid4()))
    initiator_role: str = ""
    current_agent_role: str = ""
    current_turn: int = 0
    message_history: List[Message] = field(default_factory=list)
    shared_context: Dict[str, Any] = field(default_factory=dict)
    execution_context: Dict[str, Any] = field(default_factory=dict)
    conversation_state: ConversationState = ConversationState.CREATED
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    max_turns: Optional[int] = None

    def get_messages_from(self, role: str) -> List[Message]:
        """Get all messages from a specific role."""
        return [m for m in self.message_history if m.from_role == role]

    def get_messages_to(self, role: str) -> List[Message]:
        """Get all messages to a specific role."""
        return [m for m in self.message_history 
                if role in m.to_roles or len(m.to_roles) == 0]

    def get_recent_messages(self, count: int = 5) -> List[Message]:
        """Get last N messages."""
        return self.message_history[-count:] if self.message_history else []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "conversation_id": self.conversation_id,
            "initiator_role": self.initiator_role,
            "current_agent_role": self.current_agent_role,
            "current_turn": self.current_turn,
            "message_count": len(self.message_history),
            "shared_context": self.shared_context,
            "execution_context": self.execution_context,
            "conversation_state": self.conversation_state.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


# ============================================================================
# MessageBroadcaster — Message Routing
# ============================================================================

class MessageBroadcaster:
    """
    Routes messages between agents in a conversation.
    
    Handles:
    - Broadcasting to multiple recipients
    - Filtering messages by recipient
    - Tracking message delivery status
    """

    def __init__(self, context: ConversationContext):
        """
        Initialize broadcaster.
        
        Args:
            context: Conversation context
        """
        self.context = context

    async def broadcast(
        self,
        message: Message,
        agent_roles: List[str],
        handler: Optional[Callable[[str, Message], Awaitable[Optional[str]]]] = None,
    ) -> Dict[str, Optional[str]]:
        """
        Broadcast message to multiple agents.
        
        Args:
            message: Message to broadcast
            agent_roles: List of agent roles to send to
            handler: Async function to call for each agent
            
        Returns:
            Dict mapping agent role → response (if any)
        """
        logger.info(f"Broadcasting message {message.message_id} to {agent_roles}")
        
        responses: Dict[str, Optional[str]] = {}
        
        # If handler provided, call it for each agent
        if handler:
            tasks = []
            for role in agent_roles:
                if role != message.from_role:  # Don't send to self
                    tasks.append(self._call_handler(role, message, handler))
            
            responses = dict(await asyncio.gather(*tasks))
        else:
            # Just mark recipients
            for role in agent_roles:
                responses[role] = None
        
        return responses

    async def _call_handler(
        self,
        role: str,
        message: Message,
        handler: Callable[[str, Message], Awaitable[Optional[str]]],
    ) -> tuple[str, Optional[str]]:
        """Call handler for a single agent."""
        try:
            response = await handler(role, message)
            return (role, response)
        except Exception as e:
            logger.error(f"Handler error for {role}: {str(e)}")
            return (role, None)


# ============================================================================
# AgentConversation — Main Conversation Coordinator
# ============================================================================

class AgentConversation:
    """
    Multi-agent conversation engine.
    
    Design:
    1. Agent initiates conversation: start()
    2. Agent sends message: agent_say()
    3. Message broadcast to other agents
    4. Other agents respond (via handler callback)
    5. Responses added to message history
    6. Conversation continues until concluded or timeout
    
    Example:
        conv = AgentConversation(initiator_role="pm")
        await conv.start()
        
        # PM sends requirement
        await conv.agent_say(
            role="pm",
            message="Design a cache layer",
            message_type=MessageType.REQUEST,
            context={"priority": "high"},
        )
        
        # Broadcast to other agents (architect, qa, devops)
        responses = await conv.broadcast_to_agents(...)
    """

    def __init__(
        self,
        initiator_role: str,
        agent_roles: Optional[List[str]] = None,
        max_turns: Optional[int] = None,
    ):
        """
        Initialize conversation.
        
        Args:
            initiator_role: Role that starts the conversation
            agent_roles: List of agent roles in this conversation
            max_turns: Maximum conversation turns (None = unlimited)
        """
        self.context = ConversationContext(
            initiator_role=initiator_role,
            current_agent_role=initiator_role,
            max_turns=max_turns,
        )
        self.agent_roles = agent_roles or []
        self.broadcaster = MessageBroadcaster(self.context)

    async def start(self) -> None:
        """
        Start conversation.
        
        Sets state to ACTIVE and initializes context.
        """
        logger.info(
            f"Starting conversation {self.context.conversation_id} "
            f"initiated by {self.context.initiator_role}"
        )
        self.context.conversation_state = ConversationState.ACTIVE
        self.context.current_agent_role = self.context.initiator_role

    async def conclude(self, reason: str = "") -> None:
        """
        Conclude conversation.
        
        Args:
            reason: Reason for conclusion
        """
        logger.info(f"Concluding conversation: {reason}")
        self.context.conversation_state = ConversationState.CONCLUDED
        self.context.updated_at = datetime.utcnow()

    async def agent_say(
        self,
        role: str,
        message: str,
        message_type: MessageType = MessageType.REQUEST,
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        parent_message_id: Optional[str] = None,
    ) -> Message:
        """
        Agent sends a message in the conversation.
        
        Args:
            role: Agent role sending the message
            message: Message content
            message_type: Type of message
            context: Context data to include
            metadata: Additional metadata
            parent_message_id: ID of message this replies to
            
        Returns:
            Message object created
        """
        msg = Message(
            from_role=role,
            message_type=message_type,
            content=message,
            context=context or {},
            metadata=metadata or {},
            parent_message_id=parent_message_id,
        )
        
        # Add to history
        self.context.message_history.append(msg)
        self.context.current_agent_role = role
        self.context.current_turn += 1
        self.context.updated_at = datetime.utcnow()
        
        logger.info(
            f"Agent {role} says (turn {self.context.current_turn}): "
            f"{message[:100]}..."
        )
        
        return msg

    async def broadcast_to_agents(
        self,
        message: Message,
        agent_roles: Optional[List[str]] = None,
        handler: Optional[Callable[[str, Message], Awaitable[Optional[str]]]] = None,
    ) -> Dict[str, Optional[str]]:
        """
        Broadcast message to agents and collect responses.
        
        Args:
            message: Message to broadcast
            agent_roles: Agents to send to (defaults to all except sender)
            handler: Callback function for agent responses
            
        Returns:
            Dict mapping agent role → response text
        """
        if agent_roles is None:
            # Send to all agents except sender
            agent_roles = [r for r in self.agent_roles if r != message.from_role]

        message.to_roles = agent_roles
        
        responses = await self.broadcaster.broadcast(message, agent_roles, handler)
        
        # Add responses to history
        for role, response_text in responses.items():
            if response_text:
                response_msg = Message(
                    from_role=role,
                    to_roles=[message.from_role],
                    message_type=MessageType.RESPONSE,
                    content=response_text,
                    parent_message_id=message.message_id,
                )
                self.context.message_history.append(response_msg)
        
        return responses

    def get_shared_context(self) -> Dict[str, Any]:
        """
        Get shared context visible to all agents.
        
        Returns:
            Shared context dictionary
        """
        return self.context.shared_context.copy()

    def update_shared_context(self, key: str, value: Any) -> None:
        """
        Update shared context (visible to all agents).
        
        Args:
            key: Context key
            value: Context value
        """
        self.context.shared_context[key] = value
        self.context.updated_at = datetime.utcnow()
        logger.debug(f"Updated shared context: {key}")

    def get_message_history(
        self, 
        role: Optional[str] = None,
        message_type: Optional[MessageType] = None,
        limit: Optional[int] = None,
    ) -> List[Message]:
        """
        Get message history with optional filtering.
        
        Args:
            role: Filter by agent role (from_role)
            message_type: Filter by message type
            limit: Maximum number of messages to return
            
        Returns:
            List of messages
        """
        messages = self.context.message_history
        
        if role:
            messages = [m for m in messages if m.from_role == role]
        
        if message_type:
            messages = [m for m in messages if m.message_type == message_type]
        
        if limit:
            messages = messages[-limit:]
        
        return messages

    def get_conversation_state(self) -> Dict[str, Any]:
        """
        Get complete conversation state snapshot.
        
        Returns:
            Dictionary with conversation metadata and recent messages
        """
        return {
            "conversation_id": self.context.conversation_id,
            "initiator_role": self.context.initiator_role,
            "current_agent_role": self.context.current_agent_role,
            "current_turn": self.context.current_turn,
            "state": self.context.conversation_state.value,
            "message_count": len(self.context.message_history),
            "recent_messages": [m.to_dict() for m in self.context.get_recent_messages(3)],
            "shared_context_keys": list(self.context.shared_context.keys()),
            "created_at": self.context.created_at.isoformat(),
            "updated_at": self.context.updated_at.isoformat(),
        }

    async def check_max_turns(self) -> bool:
        """
        Check if conversation has reached max turns limit.
        
        Returns:
            True if limit exceeded
        """
        if self.context.max_turns is None:
            return False
        
        if self.context.current_turn >= self.context.max_turns:
            logger.warning(
                f"Conversation reached max turns: "
                f"{self.context.current_turn}/{self.context.max_turns}"
            )
            return True
        
        return False


# ============================================================================
# ConversationManager — Higher-level coordination
# ============================================================================

class ConversationManager:
    """
    Manages multiple concurrent conversations.
    
    Tracks:
    - Active conversations
    - Conversation history
    - Agent participation
    """

    def __init__(self):
        """Initialize conversation manager."""
        self.conversations: Dict[str, AgentConversation] = {}
        self.agent_conversations: Dict[str, List[str]] = {}  # agent_role → conv_ids

    def create_conversation(
        self,
        initiator_role: str,
        agent_roles: List[str],
        max_turns: Optional[int] = None,
    ) -> AgentConversation:
        """
        Create new conversation.
        
        Args:
            initiator_role: Role starting the conversation
            agent_roles: Agents participating
            max_turns: Maximum turns allowed
            
        Returns:
            New AgentConversation
        """
        conv = AgentConversation(initiator_role, agent_roles, max_turns)
        self.conversations[conv.context.conversation_id] = conv
        
        for role in agent_roles:
            if role not in self.agent_conversations:
                self.agent_conversations[role] = []
            self.agent_conversations[role].append(conv.context.conversation_id)
        
        logger.info(f"Created conversation {conv.context.conversation_id}")
        return conv

    def get_conversation(self, conversation_id: str) -> Optional[AgentConversation]:
        """Get conversation by ID."""
        return self.conversations.get(conversation_id)

    def get_agent_conversations(self, role: str) -> List[str]:
        """Get all conversation IDs for an agent."""
        return self.agent_conversations.get(role, [])

    def list_active_conversations(self) -> List[str]:
        """Get all active conversation IDs."""
        return [
            conv_id for conv_id, conv in self.conversations.items()
            if conv.context.conversation_state == ConversationState.ACTIVE
        ]
