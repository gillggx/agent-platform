from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
import io
import os
import urllib.parse

from app.db.base import get_db
from app.models.project import Project
from app.models.artifact import Artifact
from app.api.auth import get_current_user
from app.services.document_export import docx_exporter, build_final_delivery_zip
from app.models.workflow_run import WorkflowRun
from app.models.workflow_template import WorkflowTemplate
from app.core.config import settings

# Router
artifacts_router = APIRouter()


# Pydantic models
class ArtifactResponse(BaseModel):
    id: str
    project_id: str
    agent_role: str
    artifact_type: str
    version: int
    status: str
    content_preview: str  # First 200 chars
    metadata: dict
    created_at: str


class ArtifactDetailResponse(ArtifactResponse):
    content_md: str  # Full markdown content


# Routes
@artifacts_router.get("/projects/{project_id}/artifacts", response_model=List[ArtifactResponse])
async def list_project_artifacts(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """List artifacts for a project"""
    
    # Load artifacts
    result = await db.execute(
        select(Artifact)
        .where(Artifact.project_id == project_id)
        .order_by(Artifact.created_at.desc())
    )
    artifacts = result.scalars().all()
    
    return [
        ArtifactResponse(
            id=str(artifact.id),
            project_id=str(artifact.project_id),
            agent_role=artifact.agent_role,
            artifact_type=artifact.artifact_type,
            version=artifact.version,
            status=artifact.status,
            content_preview=artifact.content_md[:200] + "..." if len(artifact.content_md) > 200 else artifact.content_md,
            metadata=artifact.extra_metadata or {},
            created_at=artifact.created_at.isoformat() if artifact.created_at else "",
        )
        for artifact in artifacts
    ]


@artifacts_router.get("/{artifact_id}", response_model=ArtifactDetailResponse)
async def get_artifact(
    artifact_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get artifact details"""

    result = await db.execute(
        select(Artifact).where(Artifact.id == artifact_id)
    )
    artifact = result.scalar_one_or_none()

    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found"
        )

    return ArtifactDetailResponse(
        id=str(artifact.id),
        project_id=str(artifact.project_id),
        agent_role=artifact.agent_role,
        artifact_type=artifact.artifact_type,
        version=artifact.version,
        status=artifact.status,
        content_preview=artifact.content_md[:200] + "..." if len(artifact.content_md) > 200 else artifact.content_md,
        content_md=artifact.content_md,
        metadata=artifact.extra_metadata or {},
        created_at=artifact.created_at.isoformat() if artifact.created_at else "",
    )


@artifacts_router.get("/{artifact_id}/download")
async def download_artifact_md(
    artifact_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Download artifact as .md file"""

    result = await db.execute(
        select(Artifact).where(Artifact.id == artifact_id)
    )
    artifact = result.scalar_one_or_none()

    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found"
        )

    project_result = await db.execute(
        select(Project).where(Project.id == artifact.project_id)
    )
    project = project_result.scalar_one()

    header = (
        f"# {project.name} — {artifact.artifact_type.replace('_', ' ').title()}\n\n"
        f"> Agent: {artifact.agent_role}  |  版本: v{artifact.version}  |  產出時間: {artifact.created_at}\n\n"
        f"---\n\n"
    )
    md_content = (header + (artifact.content_md or "")).encode("utf-8")

    filename = f"{project.name}_{artifact.artifact_type}_v{artifact.version}.md".replace(" ", "_")
    return StreamingResponse(
        io.BytesIO(md_content),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{urllib.parse.quote(filename)}"}
    )


@artifacts_router.get("/projects/{project_id}/download")
async def download_project_artifacts(
    project_id: str,
    mode: str = "final",  # final | all
    db: AsyncSession = Depends(get_db),
):
    """
    Download project artifacts.

    - mode=final (default): ZIP with one DOCX per agent role (latest version
      only) + a workflow history markdown.
    - mode=all: single .md file containing every non-superseded artifact
      (legacy behaviour, kept for archival / debugging).
    """

    project_result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Load all non-superseded artifacts
    result = await db.execute(
        select(Artifact)
        .where(Artifact.project_id == project_id)
        .where(Artifact.status != "superseded")
        .order_by(Artifact.agent_role, Artifact.version.desc())
    )
    artifacts = result.scalars().all()

    if not artifacts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No artifacts found for this project"
        )

    if mode == "all":
        # Legacy single-markdown mode
        from datetime import datetime
        sections = [
            f"# {project.name} — 完整規格文件\n\n"
            f"> 產出時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  產出物: {len(artifacts)} 份\n\n"
            f"---\n\n"
        ]
        for artifact in artifacts:
            title = artifact.artifact_type.replace("_", " ").title()
            sections.append(
                f"## {title}（{artifact.agent_role} · v{artifact.version}）\n\n"
                + (artifact.content_md or "")
                + "\n\n---\n\n"
            )
        md_content = "".join(sections).encode("utf-8")
        filename = f"{project.name}_完整規格.md".replace(" ", "_")
        return StreamingResponse(
            io.BytesIO(md_content),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{urllib.parse.quote(filename)}"},
        )

    # Default: mode=final — build ZIP with one DOCX per role + history.md
    # Load latest workflow run for history context
    run_result = await db.execute(
        select(WorkflowRun)
        .where(WorkflowRun.project_id == project_id)
        .order_by(WorkflowRun.created_at.desc())
        .limit(1)
    )
    workflow_run = run_result.scalar_one_or_none()

    template_name = ""
    if workflow_run:
        tmpl_result = await db.execute(
            select(WorkflowTemplate).where(WorkflowTemplate.id == workflow_run.template_id)
        )
        tmpl = tmpl_result.scalar_one_or_none()
        template_name = tmpl.name if tmpl else ""

    zip_bytes = build_final_delivery_zip(
        project_name=project.name,
        artifacts=list(artifacts),
        workflow_run=workflow_run,
        template_name=template_name,
    )

    filename = f"{project.name}_Final_Delivery.zip".replace(" ", "_")
    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{urllib.parse.quote(filename)}"}
    )
