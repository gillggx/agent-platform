"""
Auth module — simplified for prototype (no authentication required).
All APIs use a default demo user/org.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.db.base import get_db
from app.models.user import User
from app.models.organization import Organization

# Router (kept for backwards compat but minimal)
auth_router = APIRouter()

# Default demo user ID and org ID (set during seed)
DEFAULT_ORG_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000002"


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    org_id: str
    organization_name: str


async def get_current_user(db: AsyncSession = Depends(get_db)) -> User:
    """
    No-auth: always return the default demo user.
    Creates it if it doesn't exist yet.
    """
    result = await db.execute(
        select(User).where(User.id == DEFAULT_USER_ID)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        # Shouldn't happen if seed ran, but create on-the-fly
        # Ensure org exists
        org_result = await db.execute(
            select(Organization).where(Organization.id == DEFAULT_ORG_ID)
        )
        org = org_result.scalar_one_or_none()
        if not org:
            org = Organization(id=DEFAULT_ORG_ID, name="Demo Organization", plan_type="free")
            db.add(org)
            await db.flush()
        
        user = User(
            id=DEFAULT_USER_ID,
            org_id=DEFAULT_ORG_ID,
            email="demo@example.com",
            hashed_password="not-used",
            full_name="Demo User",
            role="admin",
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    return user


@auth_router.get("/me", response_model=UserResponse)
async def get_current_user_info(db: AsyncSession = Depends(get_db)):
    """Get current user information (always returns demo user)"""
    user = await get_current_user(db)
    
    result = await db.execute(
        select(Organization).where(Organization.id == user.org_id)
    )
    organization = result.scalar_one()
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name or "",
        role=user.role,
        org_id=str(user.org_id),
        organization_name=organization.name,
    )
