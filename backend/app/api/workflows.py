from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from app.db.base import get_db
from app.models.user import User
from app.models.project import Project
from app.models.workflow_template import WorkflowTemplate
from app.models.workflow_run import WorkflowRun
from app.api.auth import get_current_user
from app.runtime.workflow_engine import workflow_engine

# Router
workflows_router = APIRouter()


# Pydantic models
class WorkflowTemplateResponse(BaseModel):
    id: str
    name: str
    description: str
    is_system: bool
    definition: Dict[str, Any]


class StartWorkflowRequest(BaseModel):
    project_id: str
    template_id: str
    user_input: str


class WorkflowRunResponse(BaseModel):
    id: str
    project_id: str
    template_id: str
    status: str
    user_input: str
    current_steps: List[str]
    created_at: str


class WorkflowRunDetailResponse(WorkflowRunResponse):
    step_executions: Dict[str, Any]
    template_snapshot: Dict[str, Any]


# Routes
@workflows_router.get("/templates", response_model=List[WorkflowTemplateResponse])
async def list_workflow_templates(
    db: AsyncSession = Depends(get_db)
):
    """List available workflow templates"""
    current_user = await get_current_user(db)
    
    # Load system templates and user's org templates
    result = await db.execute(
        select(WorkflowTemplate).where(
            (WorkflowTemplate.org_id == current_user.org_id) |
            (WorkflowTemplate.is_system == True) |
            (WorkflowTemplate.org_id == None)
        ).order_by(WorkflowTemplate.is_system.desc(), WorkflowTemplate.name)
    )
    templates = result.scalars().all()
    
    return [
        WorkflowTemplateResponse(
            id=str(template.id),
            name=template.name,
            description=template.description or "",
            is_system=template.is_system,
            definition=template.definition,
        )
        for template in templates
    ]


@workflows_router.get("/templates/{template_id}", response_model=WorkflowTemplateResponse)
async def get_workflow_template(
    template_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get workflow template details"""
    
    result = await db.execute(
        select(WorkflowTemplate).where(WorkflowTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    return WorkflowTemplateResponse(
        id=str(template.id),
        name=template.name,
        description=template.description or "",
        is_system=template.is_system,
        definition=template.definition,
    )


@workflows_router.post("/runs", response_model=WorkflowRunResponse)
async def start_workflow(
    request: StartWorkflowRequest,
    db: AsyncSession = Depends(get_db)
):
    """Start a new workflow execution"""
    current_user = await get_current_user(db)
    
    # Verify project ownership
    project_result = await db.execute(
        select(Project).where(
            Project.id == request.project_id,
            Project.org_id == current_user.org_id,
        )
    )
    project = project_result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Verify template access
    template_result = await db.execute(
        select(WorkflowTemplate).where(WorkflowTemplate.id == request.template_id)
    )
    template = template_result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    # Start workflow
    try:
        workflow_run = await workflow_engine.start_workflow(
            db, request.project_id, request.template_id, request.user_input, current_user.id
        )
        
        return WorkflowRunResponse(
            id=str(workflow_run.id),
            project_id=str(workflow_run.project_id),
            template_id=str(workflow_run.template_id),
            status=workflow_run.status,
            user_input=workflow_run.user_input or "",
            current_steps=list(workflow_run.current_steps or []),
            created_at=workflow_run.created_at.isoformat() if workflow_run.created_at else "",
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start workflow: {str(e)}"
        )


@workflows_router.get("/runs/{run_id}", response_model=WorkflowRunDetailResponse)
async def get_workflow_run(
    run_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get workflow run details"""
    
    result = await db.execute(
        select(WorkflowRun).where(WorkflowRun.id == run_id)
    )
    workflow_run = result.scalar_one_or_none()
    
    if not workflow_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow run not found"
        )
    
    return WorkflowRunDetailResponse(
        id=str(workflow_run.id),
        project_id=str(workflow_run.project_id),
        template_id=str(workflow_run.template_id),
        status=workflow_run.status,
        user_input=workflow_run.user_input or "",
        current_steps=list(workflow_run.current_steps or []),
        created_at=workflow_run.created_at.isoformat() if workflow_run.created_at else "",
        step_executions=dict(workflow_run.step_executions or {}),
        template_snapshot=dict(workflow_run.template_snapshot or {}),
    )


@workflows_router.post("/runs/{run_id}/approve")
async def approve_workflow_step(
    run_id: str,
    approved: bool = True,
    feedback: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Approve or reject a workflow step requiring human approval"""

    result = await db.execute(
        select(WorkflowRun).where(WorkflowRun.id == run_id)
    )
    workflow_run = result.scalar_one_or_none()

    if not workflow_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow run not found"
        )

    if workflow_run.status != "waiting_approval":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workflow is not waiting for approval (current status: {workflow_run.status})"
        )

    success = await workflow_engine.resume_after_approval(db, run_id, approved, feedback)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process approval — no waiting step found"
        )

    return {
        "message": "Approval recorded, workflow resumed",
        "approved": approved,
        "feedback": feedback,
    }


@workflows_router.get("/projects/{project_id}/runs", response_model=List[WorkflowRunResponse])
async def list_project_workflow_runs(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """List workflow runs for a project"""
    
    # Load workflow runs
    runs_result = await db.execute(
        select(WorkflowRun)
        .where(WorkflowRun.project_id == project_id)
        .order_by(WorkflowRun.created_at.desc())
    )
    runs = runs_result.scalars().all()
    
    return [
        WorkflowRunResponse(
            id=str(run.id),
            project_id=str(run.project_id),
            template_id=str(run.template_id),
            status=run.status,
            user_input=run.user_input or "",
            current_steps=list(run.current_steps or []),
            created_at=run.created_at.isoformat() if run.created_at else "",
        )
        for run in runs
    ]
