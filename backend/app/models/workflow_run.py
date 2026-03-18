from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.db.base import Base


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    template_id = Column(String(36), ForeignKey("workflow_templates.id"), nullable=False)
    template_snapshot = Column(JSON, nullable=False)  # Template definition at time of run
    user_input = Column(Text)  # Original user requirement
    status = Column(String(20), default="running")  # running | completed | failed | timeout
    step_executions = Column(JSON, default=dict)  # {"step_id": {"count": N, "last_status": "..."}}
    current_steps = Column(JSON, default=list)  # Currently executing step IDs (stored as JSON list)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="workflow_runs")
    template = relationship("WorkflowTemplate", back_populates="workflow_runs")
    step_executions_rel = relationship("StepExecution", back_populates="workflow_run")
    agent_sessions = relationship("AgentSession", back_populates="workflow_run")


class StepExecution(Base):
    __tablename__ = "step_executions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String(36), ForeignKey("workflow_runs.id"), nullable=False)
    step_id = Column(String(100), nullable=False)
    iteration = Column(Integer, default=1)
    session_id = Column(String(36), ForeignKey("agent_sessions.id"), nullable=True)
    status = Column(String(20), default="pending")  # pending | running | completed | failed
    routing_decision = Column(JSON)  # LLM routing decision record
    
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    workflow_run = relationship("WorkflowRun", back_populates="step_executions_rel")
    agent_session = relationship("AgentSession")
