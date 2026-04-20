"""
Auth module — anonymous ID based isolation.

Each browser generates a UUID stored in localStorage and sends it as
X-Client-ID header. We look up (or create) a User bound to that
anonymous_id, giving each browser its own chat history / memory / projects.

If no client_id is provided, we fall back to the default demo user for
backwards compatibility.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.db.base import get_db
from app.models.user import User
from app.models.organization import Organization

auth_router = APIRouter()

DEFAULT_ORG_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000002"


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    org_id: str
    organization_name: str


async def _ensure_default_org(db: AsyncSession) -> Organization:
    result = await db.execute(
        select(Organization).where(Organization.id == DEFAULT_ORG_ID)
    )
    org = result.scalar_one_or_none()
    if org is None:
        org = Organization(id=DEFAULT_ORG_ID, name="Demo Organization", plan_type="free")
        db.add(org)
        await db.flush()
    return org


async def _get_or_create_default_user(db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.id == DEFAULT_USER_ID))
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    await _ensure_default_org(db)
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


async def _get_or_create_anonymous_user(db: AsyncSession, client_id: str) -> User:
    result = await db.execute(select(User).where(User.anonymous_id == client_id))
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    await _ensure_default_org(db)
    short = client_id[:8]
    user = User(
        org_id=DEFAULT_ORG_ID,
        email=f"{short}@local",
        hashed_password="anonymous",
        full_name=f"Guest {short}",
        role="member",
        is_active=True,
        is_verified=False,
        anonymous_id=client_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_current_user(
    db: AsyncSession,
    client_id: Optional[str] = None,
) -> User:
    """
    Resolve the current user.

    Routes call this directly after reading the `X-Client-ID` header
    via their own `Header(...)` dependency and passing it in.

    - If client_id is provided, find or create the matching anonymous user.
    - Otherwise fall back to the default demo user.
    """
    if client_id:
        return await _get_or_create_anonymous_user(db, client_id)
    return await _get_or_create_default_user(db)


@auth_router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    db: AsyncSession = Depends(get_db),
    x_client_id: Optional[str] = Header(default=None, alias="X-Client-ID"),
):
    """Get current user information (resolved from X-Client-ID if present)"""
    user = await get_current_user(db, client_id=x_client_id)

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
