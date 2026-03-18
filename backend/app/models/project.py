from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.db.base import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    name = Column(String(500), nullable=False)
    description = Column(Text)
    status = Column(String(20), default="draft")  # draft | running | completed | failed
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    organization = relationship("Organization")
    creator = relationship("User")
    workflow_runs = relationship("WorkflowRun", back_populates="project")
    artifacts = relationship("Artifact", back_populates="project")
