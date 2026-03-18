from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.db.base import Base


class AgentDefinition(Base):
    __tablename__ = "agent_definitions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=True)
    role = Column(String(50), nullable=False)  # pm | architect | qa | devops | director
    display_name = Column(String(200), nullable=False)
    description = Column(Text)
    knowledge_pack_id = Column(String(36), ForeignKey("knowledge_packs.id"), nullable=True)
    soul = Column(Text, nullable=True)  # Agent personality / soul definition (Markdown)
    config = Column(JSON, default=dict)  # temperature, max_tokens, llm_model, llm_provider, llm_api_key
    is_system = Column(String(10), default="false")  # true for built-in agents
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    organization = relationship("Organization")
    knowledge_pack = relationship("KnowledgePack")
    sessions = relationship("AgentSession", back_populates="agent_definition")
