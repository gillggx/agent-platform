from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from app.db.base import get_db
from app.models.agent_definition import AgentDefinition

agents_router = APIRouter()


class AgentResponse(BaseModel):
    id: str
    role: str
    display_name: str
    description: Optional[str]
    soul: Optional[str]
    config: Dict[str, Any]
    is_system: str


class UpdateAgentRequest(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    soul: Optional[str] = None
    config: Optional[Dict[str, Any]] = None  # can include llm_model, llm_provider, llm_api_key, temperature, max_tokens


@agents_router.get("", response_model=List[AgentResponse])
async def list_agents(db: AsyncSession = Depends(get_db)):
    """List all system agent definitions"""
    result = await db.execute(
        select(AgentDefinition)
        .where(AgentDefinition.is_system == "true")
        .order_by(AgentDefinition.role)
    )
    agents = result.scalars().all()
    return [
        AgentResponse(
            id=str(a.id),
            role=a.role,
            display_name=a.display_name,
            description=a.description or "",
            soul=a.soul or "",
            config=a.config or {},
            is_system=a.is_system,
        )
        for a in agents
    ]


@agents_router.get("/{role}", response_model=AgentResponse)
async def get_agent(role: str, db: AsyncSession = Depends(get_db)):
    """Get agent definition by role"""
    result = await db.execute(
        select(AgentDefinition).where(
            AgentDefinition.role == role,
            AgentDefinition.is_system == "true",
        )
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent '{role}' not found")
    return AgentResponse(
        id=str(agent.id),
        role=agent.role,
        display_name=agent.display_name,
        description=agent.description or "",
        soul=agent.soul or "",
        config=agent.config or {},
        is_system=agent.is_system,
    )


@agents_router.put("/{role}", response_model=AgentResponse)
async def update_agent(role: str, req: UpdateAgentRequest, db: AsyncSession = Depends(get_db)):
    """Update agent soul and/or config (display_name, description, llm settings, temperature)"""
    result = await db.execute(
        select(AgentDefinition).where(
            AgentDefinition.role == role,
            AgentDefinition.is_system == "true",
        )
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent '{role}' not found")

    if req.display_name is not None:
        agent.display_name = req.display_name
    if req.description is not None:
        agent.description = req.description
    if req.soul is not None:
        agent.soul = req.soul
    if req.config is not None:
        # Merge with existing config (don't overwrite unrelated keys)
        existing = dict(agent.config or {})
        existing.update(req.config)
        agent.config = existing

    await db.commit()
    await db.refresh(agent)

    return AgentResponse(
        id=str(agent.id),
        role=agent.role,
        display_name=agent.display_name,
        description=agent.description or "",
        soul=agent.soul or "",
        config=agent.config or {},
        is_system=agent.is_system,
    )
