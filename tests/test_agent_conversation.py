"""
Unit tests for Agent Conversation Engine.

Tests:
- Message creation and serialization
- Conversation context management
- Message broadcasting and routing
- Conversation state lifecycle
- Message history tracking
"""

import pytest
from datetime import datetime
from app.intelligence.agent_conversation import (
    Message,
    MessageType,
    ConversationContext,
    ConversationState,
    AgentConversation,
    ConversationManager,
    MessageBroadcaster,
)


class TestMessage:
    """Tests for Message format."""

    def test_message_creation(self):
        """Test creating a message."""
        msg = Message(
            from_role="pm",
            to_roles=["architect", "qa"],
            message_type=MessageType.REQUEST,
            content="Design a new feature",
        )
        
        assert msg.from_role == "pm"
        assert "architect" in msg.to_roles
        assert msg.message_type == MessageType.REQUEST
        assert msg.content == "Design a new feature"

    def test_message_id_generation(self):
        """Test that message IDs are generated."""
        msg1 = Message(from_role="pm", content="Test")
        msg2 = Message(from_role="pm", content="Test")
        
        assert msg1.message_id is not None
        assert msg2.message_id is not None
        assert msg1.message_id != msg2.message_id

    def test_message_serialization(self):
        """Test message to_dict."""
        msg = Message(
            from_role="architect",
            message_type=MessageType.RESPONSE,
            content="Here's the design",
            context={"design": "..."},
        )
        
        data = msg.to_dict()
        assert data["from_role"] == "architect"
        assert data["message_type"] == "response"
        assert data["content"] == "Here's the design"
        assert data["context"]["design"] == "..."

    def test_message_deserialization(self):
        """Test message from_dict."""
        original = Message(
            from_role="qa",
            message_type=MessageType.FEEDBACK,
            content="Found a bug",
        )
        
        data = original.to_dict()
        restored = Message.from_dict(data)
        
        assert restored.from_role == "qa"
        assert restored.message_type == MessageType.FEEDBACK
        assert restored.content == "Found a bug"

    def test_message_types(self):
        """Test all message types."""
        types = [
            MessageType.REQUEST,
            MessageType.RESPONSE,
            MessageType.DECISION,
            MessageType.FEEDBACK,
            MessageType.UPDATE,
            MessageType.ERROR,
        ]
        
        for msg_type in types:
            msg = Message(from_role="test", message_type=msg_type, content="Test")
            assert msg.message_type == msg_type


class TestConversationContext:
    """Tests for conversation context management."""

    def test_context_creation(self):
        """Test creating conversation context."""
        ctx = ConversationContext(initiator_role="pm", current_agent_role="pm")
        
        assert ctx.conversation_id is not None
        assert ctx.initiator_role == "pm"
        assert ctx.current_agent_role == "pm"
        assert ctx.current_turn == 0
        assert ctx.conversation_state == ConversationState.CREATED

    def test_context_message_history(self):
        """Test message history in context."""
        ctx = ConversationContext(initiator_role="pm", current_agent_role="pm")
        
        msg1 = Message(from_role="pm", content="First message")
        msg2 = Message(from_role="architect", content="Second message")
        
        ctx.message_history.append(msg1)
        ctx.message_history.append(msg2)
        
        assert len(ctx.message_history) == 2
        assert ctx.message_history[0].from_role == "pm"

    def test_context_filtering_messages(self):
        """Test filtering messages from context."""
        ctx = ConversationContext(initiator_role="pm", current_agent_role="pm")
        
        # Add messages from different roles
        for i in range(3):
            ctx.message_history.append(
                Message(from_role="pm", content=f"PM message {i}")
            )
        for i in range(2):
            ctx.message_history.append(
                Message(from_role="architect", content=f"Architect message {i}")
            )
        
        # Filter by role
        pm_messages = ctx.get_messages_from("pm")
        assert len(pm_messages) == 3
        
        arch_messages = ctx.get_messages_from("architect")
        assert len(arch_messages) == 2

    def test_context_recent_messages(self):
        """Test getting recent messages."""
        ctx = ConversationContext(initiator_role="pm", current_agent_role="pm")
        
        for i in range(10):
            ctx.message_history.append(
                Message(from_role="pm", content=f"Message {i}")
            )
        
        recent = ctx.get_recent_messages(count=3)
        assert len(recent) == 3
        assert recent[-1].content == "Message 9"

    def test_context_serialization(self):
        """Test context to_dict."""
        ctx = ConversationContext(
            initiator_role="pm",
            current_agent_role="architect",
            current_turn=5,
        )
        ctx.shared_context["key"] = "value"
        
        data = ctx.to_dict()
        assert data["initiator_role"] == "pm"
        assert data["current_agent_role"] == "architect"
        assert data["current_turn"] == 5


class TestAgentConversation:
    """Tests for conversation coordination."""

    @pytest.mark.asyncio
    async def test_conversation_lifecycle(self):
        """Test conversation creation and start."""
        conv = AgentConversation(
            initiator_role="pm",
            agent_roles=["pm", "architect", "qa"],
        )
        
        # Before start
        assert conv.context.conversation_state == ConversationState.CREATED
        
        # Start conversation
        await conv.start()
        assert conv.context.conversation_state == ConversationState.ACTIVE

    @pytest.mark.asyncio
    async def test_agent_say(self):
        """Test agent sending a message."""
        conv = AgentConversation(initiator_role="pm", agent_roles=["pm", "architect"])
        await conv.start()
        
        msg = await conv.agent_say(
            role="pm",
            message="Design a cache layer",
            message_type=MessageType.REQUEST,
        )
        
        assert msg.from_role == "pm"
        assert msg.content == "Design a cache layer"
        assert len(conv.context.message_history) == 1
        assert conv.context.current_agent_role == "pm"

    @pytest.mark.asyncio
    async def test_message_broadcasting(self):
        """Test broadcasting messages to agents."""
        conv = AgentConversation(
            initiator_role="pm",
            agent_roles=["pm", "architect", "qa"],
        )
        await conv.start()
        
        # PM sends message
        msg = await conv.agent_say(
            role="pm",
            message="Requirements",
            message_type=MessageType.REQUEST,
        )
        
        # Mock handler that collects responses
        responses_collected = {}
        
        async def mock_handler(role, message):
            responses_collected[role] = f"Response from {role}"
            return f"Response from {role}"
        
        # Broadcast to other agents
        responses = await conv.broadcast_to_agents(
            message=msg,
            agent_roles=["architect", "qa"],
            handler=mock_handler,
        )
        
        assert "architect" in responses
        assert "qa" in responses

    @pytest.mark.asyncio
    async def test_shared_context_management(self):
        """Test shared context updates."""
        conv = AgentConversation(initiator_role="pm", agent_roles=["pm", "architect"])
        
        # Update shared context
        conv.update_shared_context("workflow_id", "wf_123")
        conv.update_shared_context("artifacts", ["design.doc"])
        
        ctx = conv.get_shared_context()
        assert ctx["workflow_id"] == "wf_123"
        assert "design.doc" in ctx["artifacts"]

    @pytest.mark.asyncio
    async def test_message_history_retrieval(self):
        """Test retrieving message history."""
        conv = AgentConversation(initiator_role="pm", agent_roles=["pm", "architect"])
        await conv.start()
        
        # Add messages
        await conv.agent_say("pm", "Requirement 1", MessageType.REQUEST)
        await conv.agent_say("architect", "Design 1", MessageType.RESPONSE)
        await conv.agent_say("pm", "Requirement 2", MessageType.REQUEST)
        
        # Get all messages
        all_msgs = conv.get_message_history()
        assert len(all_msgs) == 3
        
        # Get PM messages only
        pm_msgs = conv.get_message_history(role="pm")
        assert len(pm_msgs) == 2
        
        # Get requests only
        requests = conv.get_message_history(message_type=MessageType.REQUEST)
        assert len(requests) == 2

    @pytest.mark.asyncio
    async def test_conversation_state_snapshot(self):
        """Test getting conversation state snapshot."""
        conv = AgentConversation(initiator_role="pm", agent_roles=["pm", "architect"])
        await conv.start()
        
        await conv.agent_say("pm", "Test message", MessageType.REQUEST)
        
        state = conv.get_conversation_state()
        assert state["conversation_id"] == conv.context.conversation_id
        assert state["initiator_role"] == "pm"
        assert state["state"] == "active"
        assert state["current_turn"] > 0

    @pytest.mark.asyncio
    async def test_max_turns_check(self):
        """Test max turns limit."""
        conv = AgentConversation(
            initiator_role="pm",
            agent_roles=["pm"],
            max_turns=3,
        )
        await conv.start()
        
        # Add messages up to max
        for i in range(3):
            await conv.agent_say("pm", f"Message {i}", MessageType.UPDATE)
        
        # Check if max reached
        exceeded = await conv.check_max_turns()
        assert exceeded

    @pytest.mark.asyncio
    async def test_conversation_conclusion(self):
        """Test concluding a conversation."""
        conv = AgentConversation(initiator_role="pm")
        await conv.start()
        
        assert conv.context.conversation_state == ConversationState.ACTIVE
        
        await conv.conclude(reason="Requirements finalized")
        assert conv.context.conversation_state == ConversationState.CONCLUDED


class TestConversationManager:
    """Tests for managing multiple conversations."""

    def test_manager_creation(self):
        """Test conversation manager."""
        manager = ConversationManager()
        assert len(manager.conversations) == 0

    def test_create_conversation(self):
        """Test creating conversations through manager."""
        manager = ConversationManager()
        
        conv = manager.create_conversation(
            initiator_role="pm",
            agent_roles=["pm", "architect", "qa"],
        )
        
        assert conv is not None
        assert len(manager.conversations) == 1
        assert conv.context.conversation_id in manager.conversations

    def test_get_conversation(self):
        """Test retrieving conversation from manager."""
        manager = ConversationManager()
        
        conv1 = manager.create_conversation("pm", ["pm", "architect"])
        conv_id = conv1.context.conversation_id
        
        retrieved = manager.get_conversation(conv_id)
        assert retrieved == conv1

    def test_agent_conversations_tracking(self):
        """Test tracking agent participation."""
        manager = ConversationManager()
        
        conv1 = manager.create_conversation("pm", ["pm", "architect"])
        conv2 = manager.create_conversation("qa", ["qa", "devops"])
        
        # PM should be in conv1 only
        pm_convs = manager.get_agent_conversations("pm")
        assert len(pm_convs) >= 1
        
        # QA should be in conv2 only
        qa_convs = manager.get_agent_conversations("qa")
        assert len(qa_convs) >= 1

    def test_list_active_conversations(self):
        """Test listing active conversations."""
        import asyncio
        
        async def run():
            manager = ConversationManager()
            
            conv1 = manager.create_conversation("pm", ["pm"])
            conv2 = manager.create_conversation("qa", ["qa"])
            
            await conv1.start()
            await conv2.start()
            
            active = manager.list_active_conversations()
            assert len(active) == 2
        
        pytest.mark.asyncio(run)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
