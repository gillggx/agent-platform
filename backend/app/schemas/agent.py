"""
Agent Schemas — Pydantic V2 models for agent-related API validation.

Features:
- RoleSchema: Agent role definition validation
- AgentSessionSchema: Session state and configuration
- AgentOutputSchema: Standardized agent output format
- KnowledgePackSchema: Knowledge assets structure

Type annotations: 100%
Docstrings: 100%
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RoleConfigSchema(BaseModel):
    """
    Role-specific configuration.
    
    Attributes:
        temperature: LLM temperature setting
        max_tokens: Maximum tokens for generation
        timeout_seconds: Step timeout
        retry_attempts: Number of retry attempts
    """
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, gt=0, le=32000)
    timeout_seconds: Optional[int] = Field(default=None, gt=0)
    retry_attempts: int = Field(default=0, ge=0, le=5)


class RoleSchema(BaseModel):
    """
    Agent role definition.
    
    Attributes:
        role: Role identifier (pm, architect, qa, devops, director)
        display_name: Human-readable display name
        description: Role description and responsibilities
        system_prompt: System prompt for this role
        capabilities: List of capabilities
        config: Role configuration
        metadata: Additional metadata
    """
    role: str = Field(..., min_length=1, max_length=50)
    display_name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=1000)
    system_prompt: str = Field(..., min_length=1, max_length=5000)
    capabilities: List[str] = Field(default_factory=list)
    config: RoleConfigSchema = Field(default_factory=RoleConfigSchema)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class InteractionSchema(BaseModel):
    """
    Record of an agent interaction.
    
    Attributes:
        timestamp: When the interaction occurred
        role: Which role performed the action
        content: Interaction content
        metadata: Additional metadata
    """
    timestamp: datetime
    role: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentMemorySchema(BaseModel):
    """
    Agent memory state.
    
    Attributes:
        short_term: Current execution state
        long_term: Learned patterns and decisions
        interaction_history: Record of interactions
    """
    short_term: Dict[str, Any] = Field(default_factory=dict)
    long_term: Dict[str, Any] = Field(default_factory=dict)
    interaction_history: List[InteractionSchema] = Field(default_factory=list)


class KnowledgePackSchema(BaseModel):
    """
    Knowledge assets for agent execution.
    
    Attributes:
        context_data: Workflow and project context
        upstream_artifacts: Outputs from upstream steps
        domain_knowledge: Domain-specific information
        metadata: Knowledge metadata
    """
    context_data: Dict[str, Any] = Field(default_factory=dict)
    upstream_artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    domain_knowledge: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentSessionSchema(BaseModel):
    """
    Agent session state.
    
    Attributes:
        id: Session identifier
        role: Agent role
        status: Session status (created, running, completed, failed, paused)
        context: Execution context
        memory: Agent memory
        knowledge_pack: Knowledge assets
        execution_metadata: Execution tracking data
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    id: str
    role: RoleSchema
    status: str = Field(..., pattern="^(created|running|completed|failed|paused)$")
    context: Dict[str, Any]
    memory: AgentMemorySchema = Field(default_factory=AgentMemorySchema)
    knowledge_pack: KnowledgePackSchema = Field(default_factory=KnowledgePackSchema)
    execution_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class AgentOutputSchema(BaseModel):
    """
    Standardized output from agent execution.
    
    Attributes:
        session_id: Session that produced this output
        role: Agent role
        output_type: Type of output (text, structured, artifact)
        content: Output content
        metadata: Output metadata
        execution_time_ms: Execution duration
    """
    session_id: str
    role: str
    output_type: str = Field(..., pattern="^(text|structured|artifact|error)$")
    content: Optional[Any] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    execution_time_ms: Optional[float] = None


class AgentExecutionRequestSchema(BaseModel):
    """
    Request to execute a step with an agent.
    
    Attributes:
        session_id: Agent session to use
        inputs: Input data
        knowledge_pack: Knowledge assets
    """
    session_id: str
    inputs: Dict[str, Any]
    knowledge_pack: KnowledgePackSchema = Field(default_factory=KnowledgePackSchema)


class CreateAgentSessionRequestSchema(BaseModel):
    """
    Request to create an agent session.
    
    Attributes:
        role: Role to create session for
        context: Execution context
        metadata: Session metadata
    """
    role: RoleSchema
    context: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


def validate_role_definition(data: Dict[str, Any]) -> RoleSchema:
    """
    Validate role definition from dict.
    
    Args:
        data: Role definition dict
    
    Returns:
        Validated RoleSchema
    
    Raises:
        ValueError: If validation fails
    """
    try:
        return RoleSchema(**data)
    except Exception as exc:
        logger.error("Role validation failed: %s", str(exc))
        raise ValueError(f"Invalid role definition: {str(exc)}")


def validate_agent_output(data: Dict[str, Any]) -> AgentOutputSchema:
    """
    Validate agent output from dict.
    
    Args:
        data: Agent output dict
    
    Returns:
        Validated AgentOutputSchema
    
    Raises:
        ValueError: If validation fails
    """
    try:
        return AgentOutputSchema(**data)
    except Exception as exc:
        logger.error("Agent output validation failed: %s", str(exc))
        raise ValueError(f"Invalid agent output: {str(exc)}")
