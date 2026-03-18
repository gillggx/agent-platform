"""
Unit Tests for AgentOrchestrator — agent session management and coordination.

Test Cases:
- Agent session creation and state transitions
- Role definition validation
- Agent memory management
- Session lifecycle (create → run → complete)
- Knowledge pack passing
- Session querying and filtering
"""

import pytest
from datetime import datetime
from app.core import (
    AgentOrchestrator,
    AgentSession,
    AgentSessionStatus,
    AgentRole,
    RoleDefinition,
    KnowledgePack,
    AgentMemory,
    AgentOutput,
    create_agent_orchestrator,
    create_pm_role,
    create_architect_role,
    create_qa_role,
)


class TestAgentSessionCreation:
    """Test agent session creation and initialization."""

    @pytest.mark.asyncio
    async def test_create_session(self):
        """Test creating an agent session."""
        orchestrator = create_agent_orchestrator()
        role = create_pm_role()
        context = {"workflow_id": "wf1", "project_id": "p1"}
        
        session = await orchestrator.create_agent_session(role, context)
        
        assert session is not None
        assert session.role == role
        assert session.context == context
        assert session.status == AgentSessionStatus.CREATED
        assert session.is_active()

    @pytest.mark.asyncio
    async def test_multiple_sessions(self):
        """Test creating multiple sessions."""
        orchestrator = create_agent_orchestrator()
        pm_role = create_pm_role()
        arch_role = create_architect_role()
        
        session1 = await orchestrator.create_agent_session(pm_role, {})
        session2 = await orchestrator.create_agent_session(arch_role, {})
        
        assert session1.id != session2.id
        assert session1.role.role == AgentRole.PM.value
        assert session2.role.role == AgentRole.ARCHITECT.value

    @pytest.mark.asyncio
    async def test_get_session(self):
        """Test retrieving a session by ID."""
        orchestrator = create_agent_orchestrator()
        role = create_pm_role()
        
        session = await orchestrator.create_agent_session(role, {})
        retrieved = await orchestrator.get_session(session.id)
        
        assert retrieved == session
        assert retrieved.id == session.id

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self):
        """Test retrieving a nonexistent session."""
        orchestrator = create_agent_orchestrator()
        
        retrieved = await orchestrator.get_session("nonexistent")
        
        assert retrieved is None


class TestAgentMemory:
    """Test agent memory management."""

    def test_memory_creation(self):
        """Test creating agent memory."""
        memory = AgentMemory()
        
        assert memory.short_term == {}
        assert memory.long_term == {}
        assert memory.interaction_history == []

    def test_add_interaction(self):
        """Test adding interactions to memory."""
        memory = AgentMemory()
        
        memory.add_interaction("pm", "Create a specification")
        memory.add_interaction("architect", "Design the system")
        
        assert len(memory.interaction_history) == 2
        assert memory.interaction_history[0]["role"] == "pm"
        assert memory.interaction_history[1]["role"] == "architect"

    def test_interaction_history_limit(self):
        """Test that interaction history has a size limit."""
        memory = AgentMemory()
        
        # Add more than the limit (100)
        for i in range(150):
            memory.add_interaction(f"role_{i}", f"interaction_{i}")
        
        # Should keep only last 100
        assert len(memory.interaction_history) == 100

    def test_memory_serialization(self):
        """Test memory can be serialized."""
        memory = AgentMemory()
        memory.short_term["key"] = "value"
        memory.add_interaction("pm", "test")
        
        serialized = memory.to_dict()
        
        assert serialized["short_term"]["key"] == "value"
        assert len(serialized["interaction_history"]) == 1


class TestRoleDefinition:
    """Test role definition and capabilities."""

    def test_pm_role(self):
        """Test PM role definition."""
        role = create_pm_role()
        
        assert role.role == AgentRole.PM.value
        assert role.display_name == "Product Manager"
        assert role.can_perform("specification")
        assert role.can_perform("analysis")

    def test_architect_role(self):
        """Test Architect role definition."""
        role = create_architect_role()
        
        assert role.role == AgentRole.ARCHITECT.value
        assert role.can_perform("design")
        assert role.can_perform("architecture")

    def test_custom_role(self):
        """Test creating a custom role."""
        custom_role = RoleDefinition(
            role="custom",
            display_name="Custom Agent",
            description="A custom agent",
            system_prompt="You are a custom agent",
            capabilities=["custom_task"],
        )
        
        assert custom_role.role == "custom"
        assert custom_role.can_perform("custom_task")
        assert not custom_role.can_perform("other_task")

    def test_role_serialization(self):
        """Test role can be serialized."""
        role = create_pm_role()
        serialized = role.to_dict()
        
        assert serialized["role"] == AgentRole.PM.value
        assert serialized["display_name"] == "Product Manager"


class TestKnowledgePack:
    """Test knowledge pack creation and passing."""

    def test_knowledge_pack_creation(self):
        """Test creating a knowledge pack."""
        pack = KnowledgePack(
            context_data={"workflow_id": "wf1"},
            upstream_artifacts=[{"id": "a1", "type": "spec"}],
        )
        
        assert pack.context_data["workflow_id"] == "wf1"
        assert len(pack.upstream_artifacts) == 1

    def test_knowledge_pack_serialization(self):
        """Test knowledge pack serialization."""
        pack = KnowledgePack(
            context_data={"key": "value"},
            upstream_artifacts=[{"id": "a1"}],
        )
        
        serialized = pack.to_dict()
        
        assert serialized["context_data"]["key"] == "value"
        assert len(serialized["upstream_artifacts"]) == 1


class TestAgentSessionStateTransitions:
    """Test agent session lifecycle."""

    @pytest.mark.asyncio
    async def test_pause_session(self):
        """Test pausing a session."""
        orchestrator = create_agent_orchestrator()
        role = create_pm_role()
        session = await orchestrator.create_agent_session(role, {})
        
        success = await orchestrator.pause_session(session.id)
        
        assert success
        assert session.status == AgentSessionStatus.PAUSED

    @pytest.mark.asyncio
    async def test_resume_session(self):
        """Test resuming a paused session."""
        orchestrator = create_agent_orchestrator()
        role = create_pm_role()
        session = await orchestrator.create_agent_session(role, {})
        
        await orchestrator.pause_session(session.id)
        success = await orchestrator.resume_session(session.id)
        
        assert success
        assert session.status == AgentSessionStatus.RUNNING

    @pytest.mark.asyncio
    async def test_pause_nonexistent_session(self):
        """Test pausing a nonexistent session."""
        orchestrator = create_agent_orchestrator()
        
        success = await orchestrator.pause_session("nonexistent")
        
        assert not success


class TestAgentSessionFiltering:
    """Test querying and filtering sessions."""

    @pytest.mark.asyncio
    async def test_list_all_sessions(self):
        """Test listing all sessions."""
        orchestrator = create_agent_orchestrator()
        pm_role = create_pm_role()
        arch_role = create_architect_role()
        
        await orchestrator.create_agent_session(pm_role, {})
        await orchestrator.create_agent_session(arch_role, {})
        
        sessions = await orchestrator.list_sessions()
        
        assert len(sessions) == 2

    @pytest.mark.asyncio
    async def test_list_sessions_by_role(self):
        """Test filtering sessions by role."""
        orchestrator = create_agent_orchestrator()
        pm_role = create_pm_role()
        arch_role = create_architect_role()
        
        await orchestrator.create_agent_session(pm_role, {})
        await orchestrator.create_agent_session(pm_role, {})
        await orchestrator.create_agent_session(arch_role, {})
        
        pm_sessions = await orchestrator.list_sessions(role=AgentRole.PM.value)
        arch_sessions = await orchestrator.list_sessions(role=AgentRole.ARCHITECT.value)
        
        assert len(pm_sessions) == 2
        assert len(arch_sessions) == 1


class TestAgentExecution:
    """Test agent step execution."""

    @pytest.mark.asyncio
    async def test_execute_step_without_executor(self):
        """Test that execution fails without executor."""
        orchestrator = create_agent_orchestrator()
        role = create_pm_role()
        session = await orchestrator.create_agent_session(role, {})
        
        with pytest.raises(RuntimeError, match="Step executor not registered"):
            await orchestrator.execute_step(
                session,
                {},
                KnowledgePack(),
            )

    @pytest.mark.asyncio
    async def test_execute_step_with_executor(self):
        """Test executing a step with registered executor."""
        orchestrator = create_agent_orchestrator()
        role = create_pm_role()
        session = await orchestrator.create_agent_session(role, {})
        
        # Register dummy executor
        async def dummy_executor(session, inputs, knowledge_pack):
            return AgentOutput(
                session_id=session.id,
                role=session.role.role,
                output_type="text",
                content="test output",
            )
        
        orchestrator.register_step_executor(dummy_executor)
        
        # Execute
        output = await orchestrator.execute_step(
            session,
            {"task": "test"},
            KnowledgePack(),
        )
        
        # Verify
        assert output.session_id == session.id
        assert output.role == AgentRole.PM.value
        assert output.content == "test output"
        assert session.status == AgentSessionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_step_updates_memory(self):
        """Test that execution updates session memory."""
        orchestrator = create_agent_orchestrator()
        role = create_pm_role()
        session = await orchestrator.create_agent_session(role, {})
        
        async def dummy_executor(session, inputs, knowledge_pack):
            return AgentOutput(
                session_id=session.id,
                role=session.role.role,
                output_type="text",
                content="output",
            )
        
        orchestrator.register_step_executor(dummy_executor)
        
        await orchestrator.execute_step(
            session,
            {"task": "test_task"},
            KnowledgePack(),
        )
        
        # Verify memory was updated
        assert session.memory.short_term["last_step"] == "test_task"
        assert len(session.memory.interaction_history) > 0


class TestAgentOutput:
    """Test agent output format."""

    def test_agent_output_creation(self):
        """Test creating agent output."""
        output = AgentOutput(
            session_id="sess1",
            role="pm",
            output_type="text",
            content="test content",
        )
        
        assert output.session_id == "sess1"
        assert output.role == "pm"
        assert output.content == "test content"

    def test_agent_output_serialization(self):
        """Test agent output serialization."""
        output = AgentOutput(
            session_id="sess1",
            role="pm",
            output_type="text",
            content="test",
            execution_time_ms=100.5,
        )
        
        serialized = output.to_dict()
        
        assert serialized["session_id"] == "sess1"
        assert serialized["execution_time_ms"] == 100.5


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
