from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.db.base import Base


class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    session_id = Column(String(36), ForeignKey("agent_sessions.id"), nullable=True)
    agent_role = Column(String(50), nullable=False)  # pm | architect | qa | devops
    artifact_type = Column(String(50), nullable=False)  # product_spec | tech_design | qa_checklist
    version = Column(Integer, default=1)
    content_md = Column(Text, nullable=False)  # Markdown content
    extra_metadata = Column("metadata", JSON, default=dict)
    status = Column(String(20), default="draft")  # draft | approved | superseded
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="artifacts")
    session = relationship("AgentSession", back_populates="artifacts")
