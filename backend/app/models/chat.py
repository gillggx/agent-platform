from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.db.base import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    role = Column(String(20), nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)
    # project IDs that were referenced/loaded as context for this message
    project_context_ids = Column(JSON, default=list)
    created_at = Column(DateTime, default=func.now())

    user = relationship("User")


class GlobalMemory(Base):
    """Long-term cross-project memory per user."""
    __tablename__ = "global_memories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True)
    content = Column(Text, default="")  # LLM-maintained rolling summary
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User")


class ProjectMemory(Base):
    """Per-project distilled memory: key decisions, artifacts summary."""
    __tablename__ = "project_memories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, unique=True)
    content = Column(Text, default="")  # LLM-maintained rolling summary
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    project = relationship("Project")
