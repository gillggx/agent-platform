"""
Dynamic Routing — LLM-based dynamic workflow routing decisions.

Features:
- DynamicRouter: Makes routing decisions via LLM when static rules don't apply
- RoutingDecision: Encapsulates routing decisions with confidence and reasoning
- Integration with WorkflowEngine for dynamic step selection

Architecture:
- DynamicRouter delegates to LLMAdapterV2 for decision-making
- Director Agent makes the routing decision via LLM
- Returns structured decision with confidence level
- Fallback to default routing if LLM call fails

Type annotations: 100%
Docstrings: 100%
Async-first design.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class RoutingDecision:
    """
    Result of a routing decision.
    
    Attributes:
        should_execute: Whether to execute the next step
        next_role: Agent role to route to (if should_execute=True)
        confidence: Confidence level (0.0-1.0)
        reasoning: Explanation for this decision
        metadata: Additional decision metadata
        created_at: When decision was made
    """
    should_execute: bool
    next_role: Optional[str] = None
    confidence: float = 1.0
    reasoning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "should_execute": self.should_execute,
            "next_role": self.next_role,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class RoutingContext:
    """
    Context for making a routing decision.
    
    Attributes:
        current_role: Current executing role
        step_id: Current step identifier
        workflow_id: Parent workflow identifier
        execution_state: State of execution so far
        available_next_roles: Candidate roles to route to
        execution_metadata: Metadata about execution progress
    """
    current_role: str
    step_id: str
    workflow_id: str
    execution_state: Dict[str, Any] = field(default_factory=dict)
    available_next_roles: List[str] = field(default_factory=list)
    execution_metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Static Routing Rules
# ============================================================================

class RoutingRuleSet:
    """
    Static routing rules as fallback.
    
    Defines:
    - Default role sequences
    - Role-to-role transitions
    - Conditional routing based on step type
    """

    # Default workflow sequence if no dynamic routing
    DEFAULT_SEQUENCE = ["pm", "architect", "qa", "devops", "director"]

    # Role transition rules (from_role → possible_next_roles)
    TRANSITION_RULES: Dict[str, List[str]] = {
        "pm": ["architect", "director"],
        "architect": ["qa", "devops", "director"],
        "qa": ["devops", "director"],
        "devops": ["director"],
        "director": [],  # Terminal role
        "critic": [],
    }

    @staticmethod
    def get_next_roles(current_role: str) -> List[str]:
        """Get possible next roles after current role."""
        return RoutingRuleSet.TRANSITION_RULES.get(current_role, [])

    @staticmethod
    def get_sequence_position(role: str) -> Optional[int]:
        """Get position of role in default sequence."""
        try:
            return RoutingRuleSet.DEFAULT_SEQUENCE.index(role)
        except ValueError:
            return None

    @staticmethod
    def suggest_next_role(current_role: str) -> Optional[str]:
        """Suggest next role based on default sequence."""
        next_roles = RoutingRuleSet.get_next_roles(current_role)
        if next_roles:
            return next_roles[0]  # Return first candidate
        return None


# ============================================================================
# DynamicRouter
# ============================================================================

class DynamicRouter:
    """
    Makes dynamic routing decisions via LLM.
    
    Design:
    1. Try static routing rules first
    2. If ambiguous, call LLMAdapterV2 (Director Agent) to decide
    3. LLM returns JSON with {should_execute, next_role, confidence, reasoning}
    4. Return structured RoutingDecision
    5. On LLM failure, fallback to static rules
    
    Example:
        router = DynamicRouter(llm_adapter)
        
        decision = await router.decide(
            context=RoutingContext(
                current_role="architect",
                step_id="design",
                workflow_id="wf_123",
                execution_state={"design_complete": True},
                available_next_roles=["qa", "devops", "director"],
            ),
        )
        
        if decision.should_execute:
            # Route to decision.next_role
    """

    def __init__(self, llm_adapter: Optional[Any] = None):
        """
        Initialize dynamic router.
        
        Args:
            llm_adapter: LLMAdapterV2 instance (optional, for LLM-based decisions)
        """
        self.llm_adapter = llm_adapter
        self.rules = RoutingRuleSet()

    async def decide(
        self,
        context: RoutingContext,
        use_llm: bool = True,
    ) -> RoutingDecision:
        """
        Make routing decision.
        
        Args:
            context: Routing context with current state
            use_llm: Whether to use LLM for decision (vs static rules)
            
        Returns:
            RoutingDecision with next role and confidence
        """
        logger.info(
            f"Making routing decision for {context.current_role} → {context.available_next_roles}"
        )

        # Try static rules first
        static_decision = self._try_static_routing(context)
        if static_decision and static_decision.confidence >= 0.9:
            logger.info(
                f"Using static rule: {context.current_role} → {static_decision.next_role}"
            )
            return static_decision

        # If static rules are ambiguous and LLM is available, use LLM
        if use_llm and self.llm_adapter:
            try:
                llm_decision = await self._call_director_llm(context)
                logger.info(
                    f"LLM decision: {context.current_role} → {llm_decision.next_role} "
                    f"(confidence={llm_decision.confidence})"
                )
                return llm_decision
            except Exception as e:
                logger.warning(f"LLM routing failed: {str(e)}, falling back to static rules")
                # Fall through to static rules
        
        # Fallback to static rules
        if static_decision:
            return static_decision
        
        # Final fallback: suggest default next role
        next_role = self.rules.suggest_next_role(context.current_role)
        return RoutingDecision(
            should_execute=bool(next_role),
            next_role=next_role,
            confidence=0.5,
            reasoning="Fallback to default sequence",
        )

    def _try_static_routing(self, context: RoutingContext) -> Optional[RoutingDecision]:
        """
        Try to make decision using static rules.
        
        Args:
            context: Routing context
            
        Returns:
            RoutingDecision if rules apply, None otherwise
        """
        # Get possible next roles from rules
        possible_next = self.rules.get_next_roles(context.current_role)
        
        # Filter by available roles
        available = [r for r in possible_next if r in context.available_next_roles]
        
        if len(available) == 0:
            # No valid transitions
            return RoutingDecision(
                should_execute=False,
                reasoning=f"No static transitions from {context.current_role}",
                confidence=0.95,
            )
        
        if len(available) == 1:
            # Clear choice
            return RoutingDecision(
                should_execute=True,
                next_role=available[0],
                reasoning=f"Static rule: {context.current_role} → {available[0]}",
                confidence=0.95,
            )
        
        # Multiple choices (ambiguous)
        return None

    async def _call_director_llm(self, context: RoutingContext) -> RoutingDecision:
        """
        Call LLM (Director Agent) to make routing decision.
        
        Args:
            context: Routing context
            
        Returns:
            RoutingDecision from LLM
            
        Raises:
            Exception: If LLM call fails
        """
        if not self.llm_adapter:
            raise Exception("LLM adapter not configured")

        # Build decision prompt
        prompt = self._build_decision_prompt(context)
        
        # Call LLM as Director Agent
        response = await self.llm_adapter.complete(
            prompt=prompt,
            role="director",
            context={
                "workflow_id": context.workflow_id,
                "current_role": context.current_role,
                "available_roles": context.available_next_roles,
            },
        )

        # Parse LLM response
        decision = self._parse_llm_response(response.content, context)
        return decision

    def _build_decision_prompt(self, context: RoutingContext) -> str:
        """
        Build decision prompt for Director Agent.
        
        Args:
            context: Routing context
            
        Returns:
            Prompt text for LLM
        """
        prompt_parts = [
            "You are a Director Agent. Make a routing decision for the next workflow step.",
            "",
            f"Current Role: {context.current_role}",
            f"Current Step: {context.step_id}",
            f"Workflow: {context.workflow_id}",
            "",
            "Execution State:",
        ]

        # Add execution state
        for key, value in context.execution_state.items():
            if isinstance(value, (dict, list)):
                prompt_parts.append(f"  {key}: {json.dumps(value, indent=2)}")
            else:
                prompt_parts.append(f"  {key}: {value}")

        prompt_parts.extend([
            "",
            "Available Next Roles:",
        ])

        # Add available roles
        for role in context.available_next_roles:
            prompt_parts.append(f"  - {role}")

        prompt_parts.extend([
            "",
            "Decision Instructions:",
            "1. Should we execute the next step? (yes/no)",
            "2. If yes, which role should execute it?",
            "3. Provide confidence level (0.0-1.0)",
            "4. Explain your reasoning",
            "",
            "Respond in JSON format:",
            '{"should_execute": true/false, "next_role": "role_name", "confidence": 0.95, "reasoning": "..."}',
        ])

        return "\n".join(prompt_parts)

    def _parse_llm_response(self, response: str, context: RoutingContext) -> RoutingDecision:
        """
        Parse LLM response to RoutingDecision.
        
        Args:
            response: LLM response text
            context: Routing context
            
        Returns:
            Parsed RoutingDecision
        """
        try:
            # Try to extract JSON from response
            json_str = response
            
            # Look for JSON object in response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
            
            data = json.loads(json_str)
            
            # Validate response
            should_execute = bool(data.get("should_execute", False))
            next_role = data.get("next_role")
            confidence = float(data.get("confidence", 0.5))
            reasoning = data.get("reasoning", "")
            
            # Ensure next_role is valid if should_execute
            if should_execute and next_role not in context.available_next_roles:
                # Try to find similar role
                available = context.available_next_roles
                if available:
                    next_role = available[0]
            
            return RoutingDecision(
                should_execute=should_execute,
                next_role=next_role,
                confidence=min(1.0, max(0.0, confidence)),
                reasoning=reasoning,
            )
        
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {str(e)}")
            # Return safe fallback
            return RoutingDecision(
                should_execute=False,
                reasoning=f"Failed to parse LLM response: {str(e)}",
                confidence=0.0,
            )

    def explain_decision(self, decision: RoutingDecision) -> str:
        """
        Generate human-readable explanation of a decision.
        
        Args:
            decision: RoutingDecision to explain
            
        Returns:
            Explanation text
        """
        if not decision.should_execute:
            return f"Stop execution. Reason: {decision.reasoning}"
        else:
            return (
                f"Route to {decision.next_role}. "
                f"Confidence: {decision.confidence:.1%}. "
                f"Reason: {decision.reasoning}"
            )
