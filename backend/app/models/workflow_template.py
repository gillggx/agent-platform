from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.db.base import Base


class WorkflowTemplate(Base):
    __tablename__ = "workflow_templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=True)  # NULL for system templates
    name = Column(String(200), nullable=False)
    description = Column(Text)
    definition = Column(JSON, nullable=False)  # YAML converted to JSON
    is_system = Column(Boolean, default=False)  # True for built-in templates
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    organization = relationship("Organization")
    workflow_runs = relationship("WorkflowRun", back_populates="template")
