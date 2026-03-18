from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from pydantic import BaseModel
from typing import List, Optional

from app.db.base import get_db
from app.models.user import User
from app.models.project import Project
from app.models.workflow_run import WorkflowRun, StepExecution
from app.models.artifact import Artifact
from app.models.agent_session import AgentSession
from app.api.auth import get_current_user

# Router
projects_router = APIRouter()


# Pydantic models
class CreateProjectRequest(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    status: str
    latest_run_id: Optional[str] = None
    created_by: str
    created_at: str
    updated_at: Optional[str]


class ProjectDetailResponse(ProjectResponse):
    workflow_runs: List[dict] = []


# Routes
@projects_router.post("", response_model=ProjectResponse)
async def create_project(
    request: CreateProjectRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create new project"""
    current_user = await get_current_user(db)
    
    project = Project(
        org_id=current_user.org_id,
        name=request.name,
        description=request.description,
        status="draft",
        created_by=current_user.id,
    )
    
    db.add(project)
    await db.commit()
    await db.refresh(project)
    
    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        description=project.description,
        status=project.status,
        created_by=str(project.created_by),
        created_at=project.created_at.isoformat() if project.created_at else "",
        updated_at=project.updated_at.isoformat() if project.updated_at else None,
    )


@projects_router.get("", response_model=List[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db)
):
    """List user's projects"""
    current_user = await get_current_user(db)

    result = await db.execute(
        select(Project)
        .where(Project.org_id == current_user.org_id)
        .order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()

    # Fetch latest workflow run for each project
    project_ids = [project.id for project in projects]
    latest_runs: dict[str, WorkflowRun] = {}
    if project_ids:
        # Subquery: latest run id per project
        subq = (
            select(
                WorkflowRun.project_id,
                func.max(WorkflowRun.created_at).label("max_created_at"),
            )
            .where(WorkflowRun.project_id.in_(project_ids))
            .group_by(WorkflowRun.project_id)
            .subquery()
        )
        runs_result = await db.execute(
            select(WorkflowRun).join(
                subq,
                (WorkflowRun.project_id == subq.c.project_id) &
                (WorkflowRun.created_at == subq.c.max_created_at),
            )
        )
        for run in runs_result.scalars().all():
            latest_runs[str(run.project_id)] = run

    return [
        ProjectResponse(
            id=str(project.id),
            name=project.name,
            description=project.description,
            status=latest_runs[str(project.id)].status if str(project.id) in latest_runs else project.status,
            latest_run_id=str(latest_runs[str(project.id)].id) if str(project.id) in latest_runs else None,
            created_by=str(project.created_by),
            created_at=project.created_at.isoformat() if project.created_at else "",
            updated_at=project.updated_at.isoformat() if project.updated_at else None,
        )
        for project in projects
    ]


@projects_router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get project details"""
    current_user = await get_current_user(db)
    
    # Load project
    result = await db.execute(
        select(Project)
        .where(
            Project.id == project_id,
            Project.org_id == current_user.org_id,
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Load workflow runs
    runs_result = await db.execute(
        select(WorkflowRun)
        .where(WorkflowRun.project_id == project.id)
        .order_by(WorkflowRun.created_at.desc())
    )
    workflow_runs = runs_result.scalars().all()
    
    return ProjectDetailResponse(
        id=str(project.id),
        name=project.name,
        description=project.description,
        status=project.status,
        created_by=str(project.created_by),
        created_at=project.created_at.isoformat() if project.created_at else "",
        updated_at=project.updated_at.isoformat() if project.updated_at else None,
        workflow_runs=[
            {
                "id": str(run.id),
                "template_id": str(run.template_id),
                "status": run.status,
                "user_input": run.user_input,
                "created_at": run.created_at.isoformat() if run.created_at else "",
            }
            for run in workflow_runs
        ]
    )


@projects_router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete project"""
    current_user = await get_current_user(db)
    
    result = await db.execute(
        select(Project)
        .where(
            Project.id == project_id,
            Project.org_id == current_user.org_id,
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Cascade delete: step_executions → workflow_runs → artifacts → agent_sessions → project
    run_ids_result = await db.execute(
        select(WorkflowRun.id).where(WorkflowRun.project_id == project_id)
    )
    run_ids = [r[0] for r in run_ids_result.fetchall()]

    if run_ids:
        await db.execute(delete(StepExecution).where(StepExecution.run_id.in_(run_ids)))
        await db.execute(delete(WorkflowRun).where(WorkflowRun.id.in_(run_ids)))

    await db.execute(delete(Artifact).where(Artifact.project_id == project_id))

    session_ids_result = await db.execute(
        select(AgentSession.id).where(AgentSession.project_id == project_id)
    )
    session_ids = [r[0] for r in session_ids_result.fetchall()]
    if session_ids:
        await db.execute(delete(AgentSession).where(AgentSession.id.in_(session_ids)))

    await db.delete(project)
    await db.commit()

    return {"message": "Project deleted successfully"}
