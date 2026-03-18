from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.db.base import Base


class AgentMemory(Base):
    __tablename__ = "agent_memories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    agent_def_id = Column(String(36), ForeignKey("agent_definitions.id"), nullable=False)
    session_id = Column(String(36), ForeignKey("agent_sessions.id"), nullable=False)
    summary = Column(Text, nullable=False)  # LLM-generated summary
    key_decisions = Column(JSON, default=list)  # Important decisions made
    
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    project = relationship("Project")
    agent_definition = relationship("AgentDefinition")
    session = relationship("AgentSession", back_populates="memories")
