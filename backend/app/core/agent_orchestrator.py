"""
Agent Orchestrator — multi-agent coordination and session management.

Manages Agent lifecycle:
- RoleDefinition: Agent role configuration (PM, Architect, QA, DevOps, Director)
- AgentSession: Per-agent execution context with memory and knowledge
- AgentOrchestrator: Creates and coordinates multiple agent instances

Design:
- Factory functions for dependency injection
- Async context managers for resource management
- Pluggable LLMAdapter for Phase 2
- Memory and context persistence

Type annotations: 100%
Docstrings: 100%
Async-first design.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)


class AgentRole(str, Enum):
    """Predefined agent roles."""
    PM = "pm"
    ARCHITECT = "architect"
    QA = "qa"
    DEVOPS = "devops"
    DIRECTOR = "director"
    CRITIC = "critic"


class AgentSessionStatus(str, Enum):
    """Agent session lifecycle status."""
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class KnowledgePack:
    """
    Knowledge assets passed to an agent during execution.
    
    Attributes:
        context_data: Workflow/project context
        upstream_artifacts: Outputs from previous steps
        domain_knowledge: Domain-specific information
        metadata: Additional knowledge metadata
    """
    context_data: Dict[str, Any] = field(default_factory=dict)
    upstream_artifacts: List[Dict[str, Any]] = field(default_factory=list)
    domain_knowledge: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "context_data": self.context_data,
            "upstream_artifacts": self.upstream_artifacts,
            "domain_knowledge": self.domain_knowledge,
            "metadata": self.metadata,
        }


@dataclass
class RoleDefinition:
    """
    Configuration for an agent role.
    
    Attributes:
        role: Agent role identifier (from AgentRole enum or custom)
        display_name: Human-readable name
        description: Role description and responsibilities
        system_prompt: System prompt for this role
        capabilities: List of capabilities/tasks this role can perform
        config: Role-specific configuration (temperature, max_tokens, etc.)
        metadata: Additional role metadata
    """
    role: str
    display_name: str
    description: str
    system_prompt: str
    capabilities: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def can_perform(self, task: str) -> bool:
        """Check if this role can perform a specific task."""
        return not self.capabilities or task in self.capabilities

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "role": self.role,
            "display_name": self.display_name,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "capabilities": self.capabilities,
            "config": self.config,
            "metadata": self.metadata,
        }


@dataclass
class AgentMemory:
    """
    In-session memory for an agent.
    
    Attributes:
        short_term: Current execution state and context
        long_term: Learned patterns and decisions
        interaction_history: Record of interactions in this session
    """
    short_term: Dict[str, Any] = field(default_factory=dict)
    long_term: Dict[str, Any] = field(default_factory=dict)
    interaction_history: List[Dict[str, Any]] = field(default_factory=list)

    def add_interaction(self, role: str, content: str) -> None:
        """Record an interaction in memory."""
        self.interaction_history.append({
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content,
        })
        # Keep recent interactions only
        if len(self.interaction_history) > 100:
            self.interaction_history = self.interaction_history[-100:]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "short_term": self.short_term,
            "long_term": self.long_term,
            "interaction_history": self.interaction_history,
        }


@dataclass
class AgentSession:
    """
    Execution session for a single agent instance.
    
    Attributes:
        id: Unique session identifier
        role: RoleDefinition for this agent
        status: Current session status
        context: Execution context with workflow data
        memory: Agent memory (short-term and long-term)
        knowledge_pack: Knowledge assets for this execution
        execution_metadata: Execution tracking data
        created_at: Session creation timestamp
        updated_at: Last update timestamp
    """
    id: str
    role: RoleDefinition
    context: Dict[str, Any]
    memory: AgentMemory = field(default_factory=AgentMemory)
    knowledge_pack: KnowledgePack = field(default_factory=KnowledgePack)
    status: AgentSessionStatus = AgentSessionStatus.CREATED
    execution_metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def is_active(self) -> bool:
        """Check if session is currently active."""
        return self.status in (AgentSessionStatus.CREATED, AgentSessionStatus.RUNNING)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "role": self.role.to_dict(),
            "status": self.status.value,
            "context": self.context,
            "memory": self.memory.to_dict(),
            "knowledge_pack": self.knowledge_pack.to_dict(),
            "execution_metadata": self.execution_metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class AgentOutput:
    """
    Standardized output from agent execution.
    
    Attributes:
        session_id: Session that produced this output
        role: Agent role
        output_type: Type of output (text, structured, artifact)
        content: The actual output content
        metadata: Output metadata
        execution_time_ms: Time taken to generate output
    """
    session_id: str
    role: str
    output_type: str
    content: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "role": self.role,
            "output_type": self.output_type,
            "content": self.content,
            "metadata": self.metadata,
            "execution_time_ms": self.execution_time_ms,
        }


class AgentOrchestrator:
    """
    Multi-agent coordination engine.
    
    Responsibilities:
    - Create and manage agent sessions
    - Execute steps with specific roles
    - Coordinate agent interactions
    - Collect and standardize outputs
    - Support pluggable LLMAdapter (Phase 2)
    
    Usage:
        orchestrator = AgentOrchestrator()
        session = await orchestrator.create_agent_session(pm_role)
        output = await orchestrator.execute_step(session, inputs, knowledge_pack)
    """

    def __init__(self) -> None:
        """Initialize the agent orchestrator."""
        self._llm_adapter: Optional[Callable] = None
        self._step_executor: Optional[Callable] = None
        self._sessions: Dict[str, AgentSession] = {}

    def register_llm_adapter(self, adapter: Callable) -> None:
        """
        Register LLM adapter for Phase 2 integration.
        
        Args:
            adapter: Async callable that handles LLM requests
        """
        self._llm_adapter = adapter
        logger.info("AgentOrchestrator: registered LLM adapter")

    def register_step_executor(self, executor: Callable) -> None:
        """
        Register step executor callback.
        
        Args:
            executor: Async callable that executes a step
        """
        self._step_executor = executor
        logger.info("AgentOrchestrator: registered step executor")

    async def create_agent_session(
        self,
        role: RoleDefinition,
        context: Dict[str, Any],
    ) -> AgentSession:
        """
        Create a new agent session.
        
        Args:
            role: RoleDefinition for the agent
            context: Execution context
        
        Returns:
            New AgentSession instance
        """
        session = AgentSession(
            id=str(uuid4()),
            role=role,
            context=context,
            status=AgentSessionStatus.CREATED,
        )
        
        self._sessions[session.id] = session
        logger.info(
            "Created agent session %s for role %s",
            session.id,
            role.role,
        )
        
        return session

    async def execute_step(
        self,
        session: AgentSession,
        inputs: Dict[str, Any],
        knowledge_pack: KnowledgePack,
    ) -> AgentOutput:
        """
        Execute a single step with an agent.
        
        Flow:
        1. Update session state with inputs and knowledge
        2. Call executor (agent or LLM adapter)
        3. Collect and standardize output
        4. Update memory
        5. Return AgentOutput
        
        Args:
            session: AgentSession to use
            inputs: Input data for this step
            knowledge_pack: Knowledge assets for this step
        
        Returns:
            AgentOutput with execution result
        
        Raises:
            RuntimeError: If executor not registered
        """
        if not self._step_executor:
            raise RuntimeError("Step executor not registered. Call register_step_executor().")
        
        start_time = datetime.now()
        
        try:
            # Update session
            session.status = AgentSessionStatus.RUNNING
            session.knowledge_pack = knowledge_pack
            session.updated_at = datetime.now()
            
            logger.info(
                "Executing step with agent %s (session: %s)",
                session.role.role,
                session.id,
            )
            
            # Execute step
            output = await self._step_executor(
                session=session,
                inputs=inputs,
                knowledge_pack=knowledge_pack,
            )
            
            # Update memory
            session.memory.short_term.update({
                "last_step": inputs.get("task", "unknown"),
                "last_output_type": output.output_type,
                "last_output_time": datetime.now().isoformat(),
            })
            session.memory.add_interaction("output", str(output.content)[:200])
            
            # Mark session as completed
            session.status = AgentSessionStatus.COMPLETED
            session.updated_at = datetime.now()
            
            # Record execution time
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            output.execution_time_ms = duration_ms
            
            logger.info(
                "Step completed with agent %s (duration: %.2fms)",
                session.role.role,
                duration_ms,
            )
            
            return output
            
        except Exception as exc:
            session.status = AgentSessionStatus.FAILED
            session.updated_at = datetime.now()
            
            logger.error(
                "Step execution failed for agent %s: %s",
                session.role.role,
                str(exc),
            )
            
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            return AgentOutput(
                session_id=session.id,
                role=session.role.role,
                output_type="error",
                content=None,
                metadata={"error": str(exc)},
                execution_time_ms=duration_ms,
            )

    async def get_session(self, session_id: str) -> Optional[AgentSession]:
        """
        Retrieve a session by ID.
        
        Args:
            session_id: Session identifier
        
        Returns:
            AgentSession if found, None otherwise
        """
        return self._sessions.get(session_id)

    async def list_sessions(self, role: Optional[str] = None) -> List[AgentSession]:
        """
        List all sessions, optionally filtered by role.
        
        Args:
            role: Optional role filter
        
        Returns:
            List of AgentSession instances
        """
        sessions = list(self._sessions.values())
        if role:
            sessions = [s for s in sessions if s.role.role == role]
        return sessions

    async def pause_session(self, session_id: str) -> bool:
        """
        Pause a session.
        
        Args:
            session_id: Session to pause
        
        Returns:
            True if paused, False if not found
        """
        session = self._sessions.get(session_id)
        if session:
            session.status = AgentSessionStatus.PAUSED
            session.updated_at = datetime.now()
            logger.info("Paused agent session %s", session_id)
            return True
        return False

    async def resume_session(self, session_id: str) -> bool:
        """
        Resume a paused session.
        
        Args:
            session_id: Session to resume
        
        Returns:
            True if resumed, False if not found
        """
        session = self._sessions.get(session_id)
        if session:
            session.status = AgentSessionStatus.RUNNING
            session.updated_at = datetime.now()
            logger.info("Resumed agent session %s", session_id)
            return True
        return False


# Predefined role templates

def create_pm_role() -> RoleDefinition:
    """Create a Product Manager role definition."""
    return RoleDefinition(
        role=AgentRole.PM.value,
        display_name="Product Manager",
        description="Responsible for requirements gathering and product specification",
        system_prompt="You are an experienced Product Manager. "
                     "Focus on clarity, user needs, and feasibility.",
        capabilities=["analysis", "specification", "requirement_gathering"],
        config={
            "temperature": 0.7,
            "max_tokens": 4096,
        },
    )


def create_architect_role() -> RoleDefinition:
    """Create a Software Architect role definition."""
    return RoleDefinition(
        role=AgentRole.ARCHITECT.value,
        display_name="Software Architect",
        description="Responsible for system design and technical architecture",
        system_prompt="You are a Senior Software Architect. "
                     "Focus on scalability, maintainability, and technical excellence.",
        capabilities=["design", "architecture", "technical_review"],
        config={
            "temperature": 0.5,
            "max_tokens": 4096,
        },
    )


def create_qa_role() -> RoleDefinition:
    """Create a QA Engineer role definition."""
    return RoleDefinition(
        role=AgentRole.QA.value,
        display_name="QA Engineer",
        description="Responsible for quality assurance and testing strategy",
        system_prompt="You are an experienced QA Engineer. "
                     "Focus on test coverage, edge cases, and quality metrics.",
        capabilities=["testing", "qa_review", "validation"],
        config={
            "temperature": 0.5,
            "max_tokens": 2048,
        },
    )


def create_devops_role() -> RoleDefinition:
    """Create a DevOps Engineer role definition."""
    return RoleDefinition(
        role=AgentRole.DEVOPS.value,
        display_name="DevOps Engineer",
        description="Responsible for deployment and operational excellence",
        system_prompt="You are an experienced DevOps Engineer. "
                     "Focus on deployment strategies, monitoring, and reliability.",
        capabilities=["deployment", "infrastructure", "monitoring"],
        config={
            "temperature": 0.5,
            "max_tokens": 2048,
        },
    )


def create_director_role() -> RoleDefinition:
    """Create a Director role definition."""
    return RoleDefinition(
        role=AgentRole.DIRECTOR.value,
        display_name="Director",
        description="Responsible for oversight and routing decisions",
        system_prompt="You are a Director with oversight responsibility. "
                     "Make clear routing decisions based on current state.",
        capabilities=["decision_making", "routing", "oversight"],
        config={
            "temperature": 0.3,
            "max_tokens": 512,
        },
    )


def create_agent_orchestrator() -> AgentOrchestrator:
    """
    Factory function to create an AgentOrchestrator instance.
    
    Returns:
        AgentOrchestrator instance
    """
    return AgentOrchestrator()
