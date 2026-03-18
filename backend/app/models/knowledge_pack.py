from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.db.base import Base


class KnowledgePack(Base):
    __tablename__ = "knowledge_packs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Prompt Templates
    system_prompt = Column(Text, nullable=False)
    task_prompts = Column(JSON, default=dict)  # {"draft": "...", "review": "...", "revise": "..."}
    output_template = Column(Text)
    
    # LLM Config
    llm_config = Column(JSON, default=dict)  # model, temperature, max_tokens
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    organization = relationship("Organization")
    documents = relationship("KnowledgeDocument", back_populates="knowledge_pack")
    agent_definitions = relationship("AgentDefinition", back_populates="knowledge_pack")


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pack_id = Column(String(36), ForeignKey("knowledge_packs.id"), nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(Text)  # Small docs stored directly
    file_path = Column(String(1000))  # Local path for large files
    doc_type = Column(String(50))  # reference | template | example
    
    # Vector search support (P1)
    embedding_status = Column(String(20), default="pending")
    chunk_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=func.now())
    
    # Relationship
    knowledge_pack = relationship("KnowledgePack", back_populates="documents")
