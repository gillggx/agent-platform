from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.db.base import get_db
from app.api.auth import get_current_user
from app.models.chat import ChatMessage, GlobalMemory
from app.models.project import Project
from app.models.workflow_template import WorkflowTemplate
from app.services.pm_agent import stream_pm_response
from app.runtime.workflow_engine import WorkflowEngine

workflow_engine = WorkflowEngine()

chat_router = APIRouter()

DEFAULT_TEMPLATE_NAME = "標準 Spec 流程"


class SendMessageRequest(BaseModel):
    message: str
    intake_already_triggered: bool = False


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    project_context_ids: List[str]
    created_at: str


class StartProjectRequest(BaseModel):
    project_name: str
    project_description: Optional[str] = ""
    template_id: Optional[str] = None  # if None, use default template


class StartProjectResponse(BaseModel):
    project_id: str
    run_id: str
    project_name: str
    template_name: str


@chat_router.post("/message")
async def send_message(
    request: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send a message to PM Agent and stream the response via SSE."""
    current_user = await get_current_user(db)

    async def event_stream():
        async for chunk in stream_pm_response(
            user_id=str(current_user.id),
            org_id=str(current_user.org_id),
            user_message=request.message,
            db=db,
            intake_already_triggered=request.intake_already_triggered,
        ):
            yield chunk

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@chat_router.post("/start-project", response_model=StartProjectResponse)
async def start_project(
    request: StartProjectRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a project and kick off the default workflow from an intake conversation.
    Called when user confirms the PM intake summary.
    """
    current_user = await get_current_user(db)

    # Resolve template
    if request.template_id:
        result = await db.execute(
            select(WorkflowTemplate).where(WorkflowTemplate.id == request.template_id)
        )
        template = result.scalar_one_or_none()
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
    else:
        result = await db.execute(
            select(WorkflowTemplate).where(
                WorkflowTemplate.name == DEFAULT_TEMPLATE_NAME,
                WorkflowTemplate.is_system == True,  # noqa: E712
            )
        )
        template = result.scalar_one_or_none()
        if not template:
            # Fallback: use first available template
            result = await db.execute(select(WorkflowTemplate).limit(1))
            template = result.scalar_one_or_none()
        if not template:
            raise HTTPException(status_code=404, detail="No workflow template available")

    user_input = request.project_description or request.project_name

    # Create project
    project = Project(
        org_id=current_user.org_id,
        name=request.project_name,
        description=request.project_description,
        status="running",
        created_by=current_user.id,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    # Start workflow (creates WorkflowRun + kicks off execution in background)
    run = await workflow_engine.start_workflow(
        db, str(project.id), str(template.id), user_input, str(current_user.id)
    )

    return StartProjectResponse(
        project_id=str(project.id),
        run_id=str(run.id),
        project_name=project.name,
        template_name=template.name,
    )


@chat_router.get("/history", response_model=List[ChatMessageResponse])
async def get_history(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    current_user = await get_current_user(db)
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()
    return [
        ChatMessageResponse(
            id=str(m.id),
            role=m.role,
            content=m.content,
            project_context_ids=m.project_context_ids or [],
            created_at=m.created_at.isoformat() if m.created_at else "",
        )
        for m in reversed(messages)
    ]


@chat_router.delete("/history")
async def clear_history(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import delete
    current_user = await get_current_user(db)
    await db.execute(delete(ChatMessage).where(ChatMessage.user_id == current_user.id))
    await db.commit()
    return {"message": "Chat history cleared"}


@chat_router.get("/memory")
async def get_memory(db: AsyncSession = Depends(get_db)):
    current_user = await get_current_user(db)
    result = await db.execute(
        select(GlobalMemory).where(GlobalMemory.user_id == current_user.id)
    )
    mem = result.scalar_one_or_none()
    return {
        "global_memory": mem.content if mem else "",
        "updated_at": mem.updated_at.isoformat() if mem and mem.updated_at else None,
    }
