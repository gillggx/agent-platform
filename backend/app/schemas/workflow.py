"""
Workflow Schemas — Pydantic V2 models for workflow API validation.

Features:
- WorkflowDefSchema: API input/output for workflow definitions
- StepDefSchema: Step definition validation
- DAG validation (cycle detection, completeness)
- JSON serialization support

Type annotations: 100%
Docstrings: 100%
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)


class StepRoutingSchema(BaseModel):
    """
    Step routing configuration.
    
    Attributes:
        type: Routing type ("static" or "dynamic")
        next_steps: Next step IDs for static routing
        condition: Condition expression for conditional routing
        llm_decision: Enable LLM-based routing decision
    """
    type: str = Field(default="static", description="Routing type")
    next_steps: List[str] = Field(default_factory=list, description="Next steps for static routing")
    condition: Optional[str] = Field(default=None, description="Conditional routing expression")
    llm_decision: bool = Field(default=False, description="Use LLM for routing")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate routing type."""
        if v not in ("static", "dynamic", "conditional"):
            raise ValueError(f"Invalid routing type: {v}")
        return v


class StepConfigSchema(BaseModel):
    """
    Step-specific configuration.
    
    Attributes:
        retry_on_failure: Number of retries on failure
        timeout_seconds: Timeout for this step
        priority: Execution priority
        metadata: Additional configuration metadata
    """
    retry_on_failure: int = Field(default=0, ge=0, le=5)
    timeout_seconds: Optional[int] = Field(default=None, gt=0)
    priority: int = Field(default=0, ge=0, le=10)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StepDefSchema(BaseModel):
    """
    Workflow step definition.
    
    Attributes:
        id: Unique step identifier
        agent_role: Agent role to execute (pm, architect, qa, devops, director)
        task_type: Type of task (analysis, design, review, etc.)
        depends_on: List of step IDs this step depends on
        prompt_override: Optional custom prompt for this step
        routing: Routing configuration
        config: Step configuration
        metadata: Additional step metadata
    """
    id: str = Field(..., min_length=1, max_length=100, description="Unique step identifier")
    agent_role: str = Field(..., description="Agent role")
    task_type: str = Field(..., description="Task type")
    depends_on: List[str] = Field(default_factory=list, description="Upstream step dependencies")
    prompt_override: Optional[str] = Field(default=None, description="Custom prompt override")
    routing: StepRoutingSchema = Field(default_factory=StepRoutingSchema)
    config: StepConfigSchema = Field(default_factory=StepConfigSchema)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("agent_role")
    @classmethod
    def validate_agent_role(cls, v: str) -> str:
        """Validate agent role is not empty."""
        if not v or not v.strip():
            raise ValueError("agent_role cannot be empty")
        return v.lower()


class WorkflowDefSchema(BaseModel):
    """
    Complete workflow definition for API.
    
    Attributes:
        id: Unique workflow identifier
        name: Human-readable name
        description: Workflow description
        steps: List of steps
        metadata: Workflow metadata
    """
    id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=2000)
    steps: List[StepDefSchema] = Field(..., min_items=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_dag(self) -> WorkflowDefSchema:
        """Validate DAG properties."""
        # Check for duplicate step IDs
        step_ids = [s.id for s in self.steps]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("Duplicate step IDs found")

        # Check for undefined dependencies
        valid_step_ids = set(step_ids)
        for step in self.steps:
            for dep in step.depends_on:
                if dep not in valid_step_ids:
                    raise ValueError(f"Step {step.id} depends on undefined step {dep}")

        # Check for cycles (DFS)
        if self._has_cycle():
            raise ValueError("Circular dependency detected in workflow")

        return self

    def _has_cycle(self) -> bool:
        """Detect cycles using DFS."""
        visited: set[str] = set()
        in_stack: set[str] = set()
        step_map = {s.id: s for s in self.steps}

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            in_stack.add(node_id)

            step = step_map.get(node_id)
            if step:
                for dep in step.depends_on:
                    if dep not in visited:
                        if dfs(dep):
                            return True
                    elif dep in in_stack:
                        return True

            in_stack.discard(node_id)
            return False

        for step in self.steps:
            if step.id not in visited:
                if dfs(step.id):
                    return True

        return False

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "id": "workflow-1",
                "name": "Product Development Workflow",
                "description": "End-to-end product development workflow",
                "steps": [
                    {
                        "id": "step-1",
                        "agent_role": "pm",
                        "task_type": "analysis",
                        "depends_on": [],
                        "routing": {"type": "static", "next_steps": ["step-2"]},
                    },
                    {
                        "id": "step-2",
                        "agent_role": "architect",
                        "task_type": "design",
                        "depends_on": ["step-1"],
                        "routing": {"type": "static", "next_steps": ["step-3"]},
                    },
                ],
            }
        }


class WorkflowExecutionRequestSchema(BaseModel):
    """
    Request to execute a workflow.
    
    Attributes:
        workflow_id: Workflow to execute
        context: Execution context with inputs
        metadata: Execution metadata
    """
    workflow_id: str = Field(..., description="Workflow to execute")
    context: Dict[str, Any] = Field(default_factory=dict, description="Execution context")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Execution metadata")


class StepOutputSchema(BaseModel):
    """
    Output from a step execution.
    
    Attributes:
        step_id: Step identifier
        role: Agent role
        status: Execution status
        output_type: Type of output
        content: Output content
        metadata: Output metadata
        duration_ms: Execution duration
        error: Error message if failed
    """
    step_id: str
    role: str
    status: str = Field(..., pattern="^(pending|running|completed|failed|skipped)$")
    output_type: str
    content: Optional[Any] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: Optional[float] = None
    error: Optional[str] = None


class WorkflowExecutionResultSchema(BaseModel):
    """
    Result of workflow execution.
    
    Attributes:
        workflow_id: Executed workflow
        status: Final status
        step_outputs: Mapping of step results
        execution_order: Order of execution
        total_duration_ms: Total execution time
        errors: List of errors
        metadata: Execution metadata
    """
    workflow_id: str
    status: str = Field(..., pattern="^(pending|running|completed|failed|timeout)$")
    step_outputs: Dict[str, StepOutputSchema]
    execution_order: List[str] = Field(default_factory=list)
    total_duration_ms: Optional[float] = None
    errors: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


def validate_workflow_definition(data: Dict[str, Any]) -> WorkflowDefSchema:
    """
    Validate workflow definition from dict.
    
    Args:
        data: Workflow definition dict
    
    Returns:
        Validated WorkflowDefSchema
    
    Raises:
        ValueError: If validation fails
    """
    try:
        return WorkflowDefSchema(**data)
    except Exception as exc:
        logger.error("Workflow validation failed: %s", str(exc))
        raise ValueError(f"Invalid workflow definition: {str(exc)}")
