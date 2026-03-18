from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.sql import func
import uuid
from app.db.base import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    plan_type = Column(String(20), default="free")  # free | pro | enterprise
    llm_config = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
