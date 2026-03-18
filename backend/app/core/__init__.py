"""
Core Engine Module — Workflow execution and agent orchestration.

Exports:
- WorkflowEngine: DAG execution engine with concurrent processing
- AgentOrchestrator: Multi-agent coordination engine
- Related data classes and enums
"""

from app.core.workflow_engine import (
    WorkflowEngine,
    WorkflowDefinition,
    WorkflowStep,
    WorkflowStatus,
    StepStatus,
    StepContext,
    StepOutput,
    WorkflowExecutionResult,
    create_workflow_engine,
)

from app.core.agent_orchestrator import (
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
    create_devops_role,
    create_director_role,
)

__all__ = [
    # Workflow Engine
    "WorkflowEngine",
    "WorkflowDefinition",
    "WorkflowStep",
    "WorkflowStatus",
    "StepStatus",
    "StepContext",
    "StepOutput",
    "WorkflowExecutionResult",
    "create_workflow_engine",
    # Agent Orchestrator
    "AgentOrchestrator",
    "AgentSession",
    "AgentSessionStatus",
    "AgentRole",
    "RoleDefinition",
    "KnowledgePack",
    "AgentMemory",
    "AgentOutput",
    "create_agent_orchestrator",
    "create_pm_role",
    "create_architect_role",
    "create_qa_role",
    "create_devops_role",
    "create_director_role",
]
