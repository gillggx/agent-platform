"""
Integration Tests for Phase 2 - LLM Integration + Conversation Engine.

Tests:
- End-to-end multi-agent conversation flow
- LLM adapter integration with conversation
- Dynamic routing in workflow context
- Role manager with prompt factory
- Complete workflow from requirements to approval
"""

import pytest
from datetime import datetime
from app.intelligence import (
    LLMAdapterV2,
    LLMConfig,
    AgentConversation,
    MessageType,
)
from app.knowledge import (
    RoleRegistry,
    KnowledgeBase,
    KnowledgeDocument,
    PromptFactory,
)
from app.core.dynamic_routing import (
    DynamicRouter,
    RoutingContext,
)


class TestPhase2Integration:
    """Integration tests for Phase 2 components."""

    @pytest.fixture
    def llm_config(self):
        """Create LLM configuration."""
        return LLMConfig(
            default_provider="openai",
            default_model="gpt-4o-mini",
            timeout_seconds=60,
            max_retries=2,
        )

    @pytest.fixture
    def role_registry(self):
        """Create role registry."""
        return RoleRegistry()

    @pytest.fixture
    def knowledge_base(self):
        """Create knowledge base with sample documents."""
        kb = KnowledgeBase()
        
        # Add sample documents
        docs = [
            KnowledgeDocument(
                doc_id="arch_patterns",
                title="Architecture Patterns",
                content="Microservices, monolith, event-driven architectures",
                tags=["architecture", "design"],
                role_relevant=["architect"],
            ),
            KnowledgeDocument(
                doc_id="testing_strategies",
                title="Testing Strategies",
                content="Unit tests, integration tests, E2E tests",
                tags=["testing", "qa"],
                role_relevant=["qa"],
            ),
            KnowledgeDocument(
                doc_id="deployment_guide",
                title="Deployment Guide",
                content="CI/CD pipelines, containerization, orchestration",
                tags=["deployment", "devops"],
                role_relevant=["devops"],
            ),
        ]
        
        for doc in docs:
            kb.add_document(doc)
        
        return kb

    @pytest.mark.asyncio
    async def test_conversation_initialization(self, role_registry):
        """Test initializing a multi-agent conversation."""
        # Get roles
        pm_role = role_registry.get_role("pm")
        arch_role = role_registry.get_role("architect")
        qa_role = role_registry.get_role("qa")
        
        assert pm_role is not None
        assert arch_role is not None
        assert qa_role is not None
        
        # Create conversation
        conv = AgentConversation(
            initiator_role="pm",
            agent_roles=["pm", "architect", "qa"],
        )
        
        await conv.start()
        
        assert conv.context.conversation_state.value == "active"
        assert conv.context.current_agent_role == "pm"

    @pytest.mark.asyncio
    async def test_requirements_to_design_flow(self, role_registry, knowledge_base):
        """Test requirement gathering -> architecture design flow."""
        # Initialize conversation with PM, Architect, QA
        conv = AgentConversation(
            initiator_role="pm",
            agent_roles=["pm", "architect", "qa"],
        )
        await conv.start()
        
        # PM presents requirements
        pm_msg = await conv.agent_say(
            role="pm",
            message="Build a scalable caching layer for API responses",
            message_type=MessageType.REQUEST,
            context={
                "priority": "high",
                "timeline": "2 weeks",
                "expected_throughput": "10k RPS",
            },
        )
        
        assert pm_msg.from_role == "pm"
        assert len(conv.context.message_history) == 1
        
        # Architect responds with design
        arch_msg = await conv.agent_say(
            role="architect",
            message="I recommend Redis with distributed cluster setup",
            message_type=MessageType.RESPONSE,
            context={
                "design": "Redis cluster with 3 nodes",
                "rationale": "Proven, high-throughput, low-latency",
                "trade_offs": "Increased operational complexity",
            },
            parent_message_id=pm_msg.message_id,
        )
        
        assert arch_msg.from_role == "architect"
        assert arch_msg.parent_message_id == pm_msg.message_id
        
        # QA provides testing strategy
        qa_msg = await conv.agent_say(
            role="qa",
            message="Need tests for failover, data consistency, performance",
            message_type=MessageType.RESPONSE,
            context={
                "test_coverage": ["failover", "consistency", "performance", "concurrent_access"],
                "automation": "Yes, for CI/CD",
            },
            parent_message_id=pm_msg.message_id,
        )
        
        assert qa_msg.from_role == "qa"
        
        # Verify conversation state
        state = conv.get_conversation_state()
        assert state["current_turn"] == 3
        assert state["message_count"] == 3

    @pytest.mark.asyncio
    async def test_shared_context_workflow(self):
        """Test shared context management across agents."""
        conv = AgentConversation(
            initiator_role="pm",
            agent_roles=["pm", "architect", "devops"],
        )
        await conv.start()
        
        # Initialize shared context
        conv.update_shared_context("project_id", "proj_123")
        conv.update_shared_context("budget_constraint", "$50k")
        
        # Message 1: PM adds requirement
        pm_msg = await conv.agent_say(
            role="pm",
            message="Build microservices platform",
            message_type=MessageType.REQUEST,
        )
        
        # Add artifact to shared context
        conv.update_shared_context("artifacts", {
            "requirements_doc": "docs/requirements.md",
            "created_by": "pm",
        })
        
        # Message 2: Architect reads shared context
        shared_ctx = conv.get_shared_context()
        assert shared_ctx["project_id"] == "proj_123"
        assert shared_ctx["budget_constraint"] == "$50k"
        assert "requirements_doc" in shared_ctx["artifacts"]
        
        arch_msg = await conv.agent_say(
            role="architect",
            message="Design ready",
            message_type=MessageType.RESPONSE,
            context=shared_ctx,
        )
        
        # Message 3: DevOps reads shared context
        shared_ctx = conv.get_shared_context()
        
        devops_msg = await conv.agent_say(
            role="devops",
            message="Deployment plan ready",
            message_type=MessageType.RESPONSE,
            context=shared_ctx,
        )
        
        # Verify all agents accessed shared context
        assert len(conv.context.message_history) == 3

    @pytest.mark.asyncio
    async def test_prompt_factory_integration(self, knowledge_base):
        """Test prompt generation with knowledge base."""
        factory = PromptFactory(knowledge_base=knowledge_base)
        
        # Generate system prompt for architect
        system_prompt = factory.build_system_prompt("architect")
        assert "architect" in system_prompt.lower()
        
        # Generate task prompt with context
        task_prompt = factory.build_task_prompt(
            role="architect",
            task="Design a caching solution",
            context={
                "requirements": "10k RPS, < 100ms latency",
                "constraints": "Budget $50k",
            },
        )
        
        assert "caching" in task_prompt.lower() or "cache" in task_prompt.lower()
        assert "10k RPS" in task_prompt
        
        # Generate review prompt
        review_prompt = factory.build_review_prompt(
            role="director",
            artifact="architecture_document",
            context={
                "criteria": "Scalability, cost-effectiveness, maintainability",
            },
        )
        
        assert "architecture" in review_prompt.lower() or "artifact" in review_prompt.lower()

    @pytest.mark.asyncio
    async def test_dynamic_routing_workflow(self, role_registry):
        """Test dynamic routing through workflow."""
        router = DynamicRouter(llm_adapter=None)  # Use static rules only
        
        # Simulate workflow progression with routing decisions
        roles_and_decisions = [
            ("pm", ["architect"]),
            ("architect", ["qa", "devops"]),
            ("qa", ["devops", "director"]),
            ("devops", ["director"]),
            ("director", []),
        ]
        
        for current_role, available_next in roles_and_decisions:
            ctx = RoutingContext(
                current_role=current_role,
                step_id=f"step_{current_role}",
                workflow_id="wf_complete",
                available_next_roles=available_next,
                execution_state={"step_completed": True},
            )
            
            decision = await router.decide(ctx, use_llm=False)
            
            # Verify decision
            assert decision is not None
            if available_next:
                # Should route to next role
                assert decision.should_execute
            else:
                # Terminal role
                assert not decision.should_execute

    @pytest.mark.asyncio
    async def test_role_capabilities_in_conversation(self, role_registry):
        """Test that conversation respects role capabilities."""
        # Get roles and verify capabilities
        pm = role_registry.get_role("pm")
        architect = role_registry.get_role("architect")
        qa = role_registry.get_role("qa")
        
        # PM should handle requirements
        assert pm.can_perform("requirement_definition") or len(pm.capabilities) > 0
        
        # Architect should handle design
        assert architect.can_perform("system_design") or len(architect.capabilities) > 0
        
        # QA should handle testing
        assert qa.can_perform("test_planning") or len(qa.capabilities) > 0
        
        # Use in conversation
        conv = AgentConversation(
            initiator_role="pm",
            agent_roles=["pm", "architect", "qa"],
        )
        await conv.start()
        
        # PM should send requirement message
        pm_msg = await conv.agent_say(
            role="pm",
            message="Build feature X",
            message_type=MessageType.REQUEST,
        )
        assert pm_msg.from_role == "pm"

    @pytest.mark.asyncio
    async def test_message_history_analysis(self):
        """Test analyzing conversation history."""
        conv = AgentConversation(
            initiator_role="pm",
            agent_roles=["pm", "architect", "qa"],
        )
        await conv.start()
        
        # Create diverse messages
        await conv.agent_say("pm", "Requirements", MessageType.REQUEST)
        await conv.agent_say("architect", "Design", MessageType.RESPONSE)
        await conv.agent_say("qa", "Tests", MessageType.RESPONSE)
        await conv.agent_say("pm", "Approved", MessageType.DECISION)
        
        # Analyze history
        all_msgs = conv.get_message_history()
        assert len(all_msgs) == 4
        
        # By role
        pm_msgs = conv.get_message_history(role="pm")
        assert len(pm_msgs) == 2
        
        # By type
        requests = conv.get_message_history(message_type=MessageType.REQUEST)
        assert len(requests) == 1
        
        responses = conv.get_message_history(message_type=MessageType.RESPONSE)
        assert len(responses) == 2
        
        # Recent messages
        recent = conv.get_message_history(limit=2)
        assert len(recent) == 2
        assert recent[-1].message_type == MessageType.DECISION

    @pytest.mark.asyncio
    async def test_conversation_max_turns_protection(self):
        """Test max turns limit protection."""
        conv = AgentConversation(
            initiator_role="pm",
            agent_roles=["pm"],
            max_turns=3,
        )
        await conv.start()
        
        # Add messages up to limit
        await conv.agent_say("pm", "Msg 1", MessageType.UPDATE)
        await conv.agent_say("pm", "Msg 2", MessageType.UPDATE)
        await conv.agent_say("pm", "Msg 3", MessageType.UPDATE)
        
        # Check if limit exceeded
        exceeded = await conv.check_max_turns()
        assert exceeded
        
        # Should still be able to conclude
        await conv.conclude("Max turns reached")
        assert conv.context.conversation_state.value == "concluded"

    @pytest.mark.asyncio
    async def test_knowledge_retrieval_in_prompts(self, knowledge_base):
        """Test using knowledge base in prompt generation."""
        factory = PromptFactory(knowledge_base=knowledge_base)
        
        # Generate task prompt for QA (should include testing knowledge)
        task_prompt = factory.build_task_prompt(
            role="qa",
            task="Test the distributed cache",
            context={"system": "Redis cluster"},
        )
        
        # Prompt should be valid
        assert isinstance(task_prompt, str)
        assert len(task_prompt) > 0
        assert "Test" in task_prompt or "test" in task_prompt.lower()


class TestPhase2EndToEnd:
    """End-to-end tests for typical workflows."""

    @pytest.mark.asyncio
    async def test_complete_workflow(self):
        """Test complete workflow from requirements to approval."""
        # Setup
        registry = RoleRegistry()
        router = DynamicRouter()
        
        # Create conversation
        conv = AgentConversation(
            initiator_role="pm",
            agent_roles=["pm", "architect", "qa", "devops", "director"],
            max_turns=10,
        )
        await conv.start()
        
        # Step 1: PM defines requirements
        await conv.agent_say(
            role="pm",
            message="Build API rate limiting service",
            message_type=MessageType.REQUEST,
            context={"priority": "critical"},
        )
        
        conv.update_shared_context("status", "requirements_defined")
        
        # Step 2: Architect designs solution
        await conv.agent_say(
            role="architect",
            message="Use Token Bucket algorithm with Redis",
            message_type=MessageType.RESPONSE,
            context={"approach": "token_bucket"},
        )
        
        conv.update_shared_context("status", "design_complete")
        
        # Step 3: QA creates test plan
        await conv.agent_say(
            role="qa",
            message="Will test rate limiting accuracy and edge cases",
            message_type=MessageType.RESPONSE,
        )
        
        conv.update_shared_context("status", "testing_planned")
        
        # Step 4: DevOps plans deployment
        await conv.agent_say(
            role="devops",
            message="Will deploy to K8s cluster with auto-scaling",
            message_type=MessageType.RESPONSE,
        )
        
        conv.update_shared_context("status", "deployment_planned")
        
        # Step 5: Director approves
        await conv.agent_say(
            role="director",
            message="Approved - proceed with implementation",
            message_type=MessageType.DECISION,
        )
        
        await conv.conclude("Approved for implementation")
        
        # Verify workflow completion
        assert conv.context.conversation_state.value == "concluded"
        assert len(conv.context.message_history) == 5
        assert conv.context.current_turn == 5

    @pytest.mark.asyncio
    async def test_broadcast_and_responses(self):
        """Test broadcasting and collecting responses."""
        conv = AgentConversation(
            initiator_role="director",
            agent_roles=["director", "architect", "qa", "devops"],
        )
        await conv.start()
        
        # Director asks for status updates
        msg = await conv.agent_say(
            role="director",
            message="Status update: where are we?",
            message_type=MessageType.REQUEST,
        )
        
        # Simulate broadcast (in real system, this would call agent handlers)
        responses = {}
        
        async def mock_agent_response(role, message):
            status_map = {
                "architect": "Design 90% complete",
                "qa": "Tests written, running",
                "devops": "Infra ready for deployment",
            }
            return status_map.get(role, "OK")
        
        broadcast_responses = await conv.broadcast_to_agents(
            message=msg,
            agent_roles=["architect", "qa", "devops"],
            handler=mock_agent_response,
        )
        
        # Responses should be in history
        assert len(conv.context.message_history) > 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
