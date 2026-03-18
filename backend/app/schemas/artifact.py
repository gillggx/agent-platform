"""
Artifact Schemas — Pydantic models for workflow artifacts.

Provides:
- ArtifactType: Type enumeration (product_spec, technical_design, qa_checklist)
- ArtifactMetadata: Metadata for artifacts
- ArtifactSchema: Artifact model with content and metadata
- ProgressEventSchema: Workflow progress event for WebSocket

Type annotations: 100%
Docstrings: 100%
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ArtifactType(str, Enum):
    """Types of workflow artifacts."""
    PRODUCT_SPEC = "product_spec"
    TECHNICAL_DESIGN = "technical_design"
    QA_CHECKLIST = "qa_checklist"
    GENERAL_DOCUMENT = "general_document"


class ProgressEventType(str, Enum):
    """Types of workflow progress events."""
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    AGENT_OUTPUT = "agent_output"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    ERROR = "error"


class ArtifactMetadata(BaseModel):
    """
    Metadata for an artifact.
    
    Attributes:
        title: Artifact title
        author: Person/agent who created it
        created_at: Creation timestamp
        updated_at: Last update timestamp
        version: Version number
        description: Optional description
        tags: Optional tags for organization
        workflow_run_id: ID of the workflow that created this
        step_id: ID of the step that created this (optional)
    """
    title: str = Field(..., min_length=1, max_length=255)
    author: str = Field(default="system", max_length=100)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="1.0")
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    workflow_run_id: str = Field(..., min_length=1)
    step_id: Optional[str] = None


class ArtifactSchema(BaseModel):
    """
    Workflow artifact (output document).
    
    Attributes:
        artifact_id: Unique artifact identifier
        workflow_run_id: ID of the workflow that created this
        artifact_type: Type of artifact (product_spec, technical_design, etc.)
        content: Markdown formatted content
        metadata: Artifact metadata
        created_at: Creation timestamp
        format: Output format (markdown, docx, etc.)
    """
    artifact_id: str = Field(
        default_factory=lambda: str(__import__('uuid').uuid4()),
        min_length=1
    )
    workflow_run_id: str = Field(..., min_length=1)
    artifact_type: ArtifactType
    content: str = Field(..., min_length=1)
    metadata: ArtifactMetadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    format: str = Field(default="markdown")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "artifact_id": self.artifact_id,
            "workflow_run_id": self.workflow_run_id,
            "artifact_type": self.artifact_type.value,
            "content": self.content,
            "metadata": self.metadata.dict(),
            "created_at": self.created_at.isoformat(),
            "format": self.format,
        }


class ProgressEventSchema(BaseModel):
    """
    Workflow progress event for WebSocket broadcasting.
    
    Attributes:
        event_id: Unique event identifier
        workflow_id: ID of the workflow
        workflow_run_id: ID of the workflow run
        event_type: Type of event (step_started, step_completed, agent_output, etc.)
        step_id: ID of the step (if applicable)
        role: Agent role that executed this step
        content: Event content (output, error message, etc.)
        metadata: Additional metadata (duration, token count, etc.)
        timestamp: When the event occurred
        status: Status code or result (success, failure, etc.)
    """
    event_id: str = Field(
        default_factory=lambda: str(__import__('uuid').uuid4()),
        min_length=1
    )
    workflow_id: str = Field(..., min_length=1)
    workflow_run_id: str = Field(..., min_length=1)
    event_type: ProgressEventType
    step_id: Optional[str] = None
    role: Optional[str] = None
    content: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="success")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "workflow_id": self.workflow_id,
            "workflow_run_id": self.workflow_run_id,
            "event_type": self.event_type.value,
            "step_id": self.step_id,
            "role": self.role,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status,
        }
