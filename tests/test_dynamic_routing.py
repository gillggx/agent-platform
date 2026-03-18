"""
Unit tests for Dynamic Routing.

Tests:
- Static routing rule application
- Dynamic routing via LLM
- Routing decision parsing
- Fallback strategies
- Confidence scoring
"""

import pytest
import json
from app.core.dynamic_routing import (
    DynamicRouter,
    RoutingDecision,
    RoutingContext,
    RoutingRuleSet,
)


class TestRoutingRuleSet:
    """Tests for static routing rules."""

    def test_default_sequence(self):
        """Test default workflow sequence."""
        seq = RoutingRuleSet.DEFAULT_SEQUENCE
        assert len(seq) > 0
        assert "pm" in seq
        assert "director" in seq

    def test_transition_rules(self):
        """Test role transition rules."""
        # PM can transition to architect or director
        pm_next = RoutingRuleSet.get_next_roles("pm")
        assert len(pm_next) > 0
        assert "architect" in pm_next or "director" in pm_next

    def test_sequence_position(self):
        """Test getting role position in sequence."""
        pm_pos = RoutingRuleSet.get_sequence_position("pm")
        director_pos = RoutingRuleSet.get_sequence_position("director")
        
        assert pm_pos is not None
        assert director_pos is not None
        assert pm_pos < director_pos

    def test_suggest_next_role(self):
        """Test suggesting next role."""
        next_role = RoutingRuleSet.suggest_next_role("pm")
        assert next_role is not None
        assert isinstance(next_role, str)

    def test_director_terminal(self):
        """Test that director is terminal role."""
        next_roles = RoutingRuleSet.get_next_roles("director")
        assert len(next_roles) == 0


class TestRoutingDecision:
    """Tests for routing decision data structure."""

    def test_decision_creation_success(self):
        """Test creating success decision."""
        decision = RoutingDecision(
            should_execute=True,
            next_role="architect",
            confidence=0.95,
            reasoning="PM -> Architect follows standard sequence",
        )
        
        assert decision.should_execute is True
        assert decision.next_role == "architect"
        assert decision.confidence == 0.95

    def test_decision_creation_stop(self):
        """Test creating stop decision."""
        decision = RoutingDecision(
            should_execute=False,
            reasoning="All steps completed",
            confidence=0.98,
        )
        
        assert decision.should_execute is False
        assert decision.next_role is None
        assert decision.confidence > 0.9

    def test_decision_serialization(self):
        """Test decision to_dict."""
        decision = RoutingDecision(
            should_execute=True,
            next_role="qa",
            confidence=0.85,
            reasoning="Test reason",
        )
        
        data = decision.to_dict()
        assert data["should_execute"] is True
        assert data["next_role"] == "qa"
        assert data["confidence"] == 0.85

    def test_decision_confidence_bounds(self):
        """Test confidence bounds."""
        # Valid confidence
        decision = RoutingDecision(
            should_execute=True,
            next_role="devops",
            confidence=0.5,
        )
        assert 0.0 <= decision.confidence <= 1.0


class TestRoutingContext:
    """Tests for routing context."""

    def test_context_creation(self):
        """Test creating routing context."""
        ctx = RoutingContext(
            current_role="architect",
            step_id="design",
            workflow_id="wf_123",
            available_next_roles=["qa", "devops"],
        )
        
        assert ctx.current_role == "architect"
        assert ctx.step_id == "design"
        assert ctx.workflow_id == "wf_123"
        assert len(ctx.available_next_roles) == 2

    def test_context_with_execution_state(self):
        """Test context with execution state."""
        ctx = RoutingContext(
            current_role="qa",
            step_id="testing",
            workflow_id="wf_456",
            available_next_roles=["devops", "director"],
            execution_state={
                "tests_passed": True,
                "coverage": 95.5,
                "bugs_found": 0,
            },
        )
        
        assert ctx.execution_state["tests_passed"] is True
        assert ctx.execution_state["coverage"] == 95.5


class TestDynamicRouter:
    """Tests for dynamic routing decisions."""

    def test_router_creation(self):
        """Test router initialization."""
        router = DynamicRouter()
        assert router.rules is not None
        assert router.llm_adapter is None  # No LLM provided

    def test_static_routing_single_option(self):
        """Test static routing with single option."""
        router = DynamicRouter()
        
        # PM has clear next options
        decision = router._try_static_routing(
            RoutingContext(
                current_role="pm",
                step_id="requirements",
                workflow_id="wf_1",
                available_next_roles=["architect"],  # Only one option
            )
        )
        
        # Should have high confidence
        assert decision is not None
        assert decision.confidence >= 0.9

    def test_static_routing_multiple_options(self):
        """Test static routing with multiple options (ambiguous)."""
        router = DynamicRouter()
        
        decision = router._try_static_routing(
            RoutingContext(
                current_role="architect",
                step_id="design",
                workflow_id="wf_2",
                available_next_roles=["qa", "devops", "director"],  # Multiple options
            )
        )
        
        # Should be None or low confidence (ambiguous)
        if decision:
            assert decision.confidence < 0.9

    def test_static_routing_no_options(self):
        """Test static routing with no valid options."""
        router = DynamicRouter()
        
        decision = router._try_static_routing(
            RoutingContext(
                current_role="director",
                step_id="approval",
                workflow_id="wf_3",
                available_next_roles=[],  # No next roles (director is terminal)
            )
        )
        
        if decision:
            assert decision.should_execute is False

    @pytest.mark.asyncio
    async def test_decide_without_llm(self):
        """Test routing decision without LLM (static rules only)."""
        router = DynamicRouter(llm_adapter=None)
        
        ctx = RoutingContext(
            current_role="pm",
            step_id="requirements",
            workflow_id="wf_4",
            available_next_roles=["architect"],
        )
        
        decision = await router.decide(ctx, use_llm=False)
        
        # Should use static rules
        assert decision is not None
        if decision.should_execute:
            assert decision.next_role in ctx.available_next_roles

    def test_build_decision_prompt(self):
        """Test building decision prompt for LLM."""
        router = DynamicRouter()
        
        ctx = RoutingContext(
            current_role="architect",
            step_id="design",
            workflow_id="wf_5",
            available_next_roles=["qa", "devops"],
            execution_state={"design_complete": True},
        )
        
        prompt = router._build_decision_prompt(ctx)
        
        # Prompt should contain key information
        assert "architect" in prompt
        assert "qa" in prompt or "devops" in prompt
        assert "JSON" in prompt

    def test_parse_llm_response_valid_json(self):
        """Test parsing valid JSON response from LLM."""
        router = DynamicRouter()
        
        response = json.dumps({
            "should_execute": True,
            "next_role": "qa",
            "confidence": 0.95,
            "reasoning": "Ready for testing",
        })
        
        ctx = RoutingContext(
            current_role="architect",
            step_id="design",
            workflow_id="wf_6",
            available_next_roles=["qa", "devops"],
        )
        
        decision = router._parse_llm_response(response, ctx)
        
        assert decision.should_execute is True
        assert decision.next_role == "qa"
        assert decision.confidence == 0.95

    def test_parse_llm_response_with_text(self):
        """Test parsing LLM response embedded in text."""
        router = DynamicRouter()
        
        # Response with JSON embedded in text
        response = """Based on the current state, I recommend:

{
    "should_execute": true,
    "next_role": "devops",
    "confidence": 0.88,
    "reasoning": "Architecture reviewed, ready for deployment planning"
}

This ensures all components are tested before deployment."""
        
        ctx = RoutingContext(
            current_role="qa",
            step_id="testing",
            workflow_id="wf_7",
            available_next_roles=["devops", "director"],
        )
        
        decision = router._parse_llm_response(response, ctx)
        
        assert decision.should_execute is True
        assert decision.next_role == "devops"

    def test_parse_llm_response_invalid_json(self):
        """Test parsing invalid JSON response."""
        router = DynamicRouter()
        
        response = "This is not JSON at all"
        
        ctx = RoutingContext(
            current_role="pm",
            step_id="requirements",
            workflow_id="wf_8",
            available_next_roles=["architect"],
        )
        
        decision = router._parse_llm_response(response, ctx)
        
        # Should have error state
        assert decision.should_execute is False or decision.confidence == 0.0

    def test_parse_llm_response_invalid_role(self):
        """Test handling invalid role in LLM response."""
        router = DynamicRouter()
        
        response = json.dumps({
            "should_execute": True,
            "next_role": "invalid_role",
            "confidence": 0.9,
            "reasoning": "Test",
        })
        
        ctx = RoutingContext(
            current_role="architect",
            step_id="design",
            workflow_id="wf_9",
            available_next_roles=["qa", "devops"],
        )
        
        decision = router._parse_llm_response(response, ctx)
        
        # Should fix invalid role to available option
        assert decision.should_execute is True
        assert decision.next_role in ctx.available_next_roles

    def test_explain_decision(self):
        """Test decision explanation generation."""
        router = DynamicRouter()
        
        decision = RoutingDecision(
            should_execute=True,
            next_role="qa",
            confidence=0.92,
            reasoning="Design ready for testing",
        )
        
        explanation = router.explain_decision(decision)
        
        assert "qa" in explanation
        assert "92" in explanation  # Confidence percentage

    def test_confidence_bounds_enforcement(self):
        """Test that confidence is bounded 0-1."""
        router = DynamicRouter()
        
        # Very high confidence
        response = json.dumps({
            "should_execute": True,
            "next_role": "qa",
            "confidence": 2.5,  # Over 1.0
            "reasoning": "Test",
        })
        
        ctx = RoutingContext(
            current_role="architect",
            step_id="design",
            workflow_id="wf_10",
            available_next_roles=["qa"],
        )
        
        decision = router._parse_llm_response(response, ctx)
        
        # Should be bounded to 1.0
        assert decision.confidence <= 1.0


class TestRoutingIntegration:
    """Integration tests for routing system."""

    @pytest.mark.asyncio
    async def test_workflow_routing_sequence(self):
        """Test routing through typical workflow sequence."""
        router = DynamicRouter()
        
        # Simulate typical PM -> Architect -> QA -> DevOps -> Director sequence
        roles_sequence = ["pm", "architect", "qa", "devops", "director"]
        
        for i, role in enumerate(roles_sequence[:-1]):  # All but last
            next_available = roles_sequence[i + 1:]
            
            ctx = RoutingContext(
                current_role=role,
                step_id=f"step_{i}",
                workflow_id="wf_seq",
                available_next_roles=next_available,
            )
            
            decision = await router.decide(ctx, use_llm=False)
            
            # Should make a valid decision
            assert decision is not None
            if decision.should_execute:
                assert decision.next_role is not None

    @pytest.mark.asyncio
    async def test_fallback_to_static_rules(self):
        """Test fallback from LLM to static rules on error."""
        # Mock LLM adapter that raises error
        class FailingLLMAdapter:
            async def complete(self, **kwargs):
                raise Exception("LLM unavailable")
        
        router = DynamicRouter(llm_adapter=FailingLLMAdapter())
        
        ctx = RoutingContext(
            current_role="architect",
            step_id="design",
            workflow_id="wf_fallback",
            available_next_roles=["qa"],
        )
        
        decision = await router.decide(ctx, use_llm=True)
        
        # Should fallback and make decision without LLM
        assert decision is not None
        # Should succeed via static rules
        assert decision.confidence >= 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
