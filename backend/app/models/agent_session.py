from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.db.base import Base


class AgentSession(Base):
    __tablename__ = "agent_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    agent_def_id = Column(String(36), ForeignKey("agent_definitions.id"), nullable=False)
    run_id = Column(String(36), ForeignKey("workflow_runs.id"), nullable=False)
    status = Column(String(20), default="created")  # created | active | produced | done | error
    
    # Context and state
    context = Column(JSON, default=dict)
    memory_key = Column(String(200))  # Key for in-memory cache
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    project = relationship("Project")
    agent_definition = relationship("AgentDefinition", back_populates="sessions")
    workflow_run = relationship("WorkflowRun", back_populates="agent_sessions")
    artifacts = relationship("Artifact", back_populates="session")
    memories = relationship("AgentMemory", back_populates="session")
