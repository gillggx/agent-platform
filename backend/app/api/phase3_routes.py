"""
Phase 3 API Routes — Document generation + WebSocket real-time progress.

Endpoints:
- POST /api/v1/artifacts/generate — Generate artifact from content
- GET /api/v1/artifacts/{artifact_id} — Get artifact details
- GET /api/v1/artifacts/{artifact_id}/download — Download as .docx
- GET /api/v1/workflows/{workflow_id}/artifacts — List workflow artifacts
- WS /ws/workflows/{workflow_id} — Subscribe to workflow progress

Type annotations: 100%
Docstrings: 100%
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse, StreamingResponse
import io

from app.schemas.artifact import (
    ArtifactSchema,
    ArtifactMetadata,
    ArtifactType,
    ProgressEventSchema,
)
from app.output.document_generator import (
    DocumentGenerator,
    ArtifactStore,
)
from app.websocket.websocket_handler import (
    ws_manager,
    progress_tracker,
)

logger = logging.getLogger(__name__)

# Router
phase3_router = APIRouter()

# Global instances
artifact_store = ArtifactStore()
document_generator = DocumentGenerator()


# ============================================================================
# Artifact Routes
# ============================================================================

@phase3_router.post("/artifacts", response_model=ArtifactSchema)
async def create_artifact(
    workflow_run_id: str,
    artifact_type: str,
    title: str,
    content: str,
    author: str = "system",
    description: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> ArtifactSchema:
    """
    Create and store a new artifact.
    
    Args:
        workflow_run_id: ID of the workflow run that created this
        artifact_type: Type of artifact (product_spec, technical_design, qa_checklist)
        title: Artifact title
        content: Markdown formatted content
        author: Creator/author name
        description: Optional description
        tags: Optional tags for organization
        
    Returns:
        Created ArtifactSchema
        
    Raises:
        HTTPException: If creation fails
    """
    try:
        # Validate artifact type
        try:
            ArtifactType(artifact_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid artifact type: {artifact_type}"
            )

        # Create metadata
        metadata = ArtifactMetadata(
            title=title,
            author=author,
            description=description,
            tags=tags or [],
            workflow_run_id=workflow_run_id
        )

        # Create artifact
        artifact = ArtifactSchema(
            workflow_run_id=workflow_run_id,
            artifact_type=ArtifactType(artifact_type),
            content=content,
            metadata=metadata
        )

        # Save to store
        artifact_id = await artifact_store.save_artifact(workflow_run_id, artifact)

        logger.info(f"Created artifact {artifact_id} for workflow {workflow_run_id}")

        return artifact

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create artifact: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create artifact: {str(e)}"
        )


@phase3_router.get("/artifacts/{artifact_id}", response_model=ArtifactSchema)
async def get_artifact(artifact_id: str) -> ArtifactSchema:
    """
    Get artifact details by ID.
    
    Args:
        artifact_id: ID of the artifact
        
    Returns:
        ArtifactSchema
        
    Raises:
        HTTPException: If artifact not found
    """
    artifact = await artifact_store.get_artifact(artifact_id)

    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact {artifact_id} not found"
        )

    return artifact


@phase3_router.get("/artifacts/{artifact_id}/download")
async def download_artifact(artifact_id: str) -> FileResponse:
    """
    Download artifact as Word document (.docx).
    
    Args:
        artifact_id: ID of the artifact
        
    Returns:
        Word document file response
        
    Raises:
        HTTPException: If artifact not found or generation fails
    """
    artifact = await artifact_store.get_artifact(artifact_id)

    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact {artifact_id} not found"
        )

    try:
        # Generate DOCX
        docx_bytes = await document_generator.generate_docx(artifact)

        # Create file response
        filename = f"{artifact.metadata.title.replace(' ', '_')}.docx"

        return FileResponse(
            io.BytesIO(docx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=filename
        )

    except Exception as e:
        logger.error(f"Failed to generate DOCX for {artifact_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate document: {str(e)}"
        )


@phase3_router.get("/workflows/{workflow_id}/artifacts", response_model=List[ArtifactSchema])
async def list_workflow_artifacts(workflow_id: str) -> List[ArtifactSchema]:
    """
    List all artifacts created by a workflow.
    
    Args:
        workflow_id: ID of the workflow (or workflow_run_id)
        
    Returns:
        List of artifacts
    """
    artifacts = await artifact_store.list_artifacts(workflow_id)
    return artifacts


# ============================================================================
# WebSocket Routes
# ============================================================================

@phase3_router.websocket("/ws/workflows/{workflow_id}")
async def websocket_endpoint(websocket: WebSocket, workflow_id: str) -> None:
    """
    WebSocket endpoint for real-time workflow progress streaming.
    
    Connection flow:
    1. Client connects to /ws/workflows/{workflow_id}
    2. Connection accepted
    3. Receive progress events from WorkflowEngine
    4. Broadcast to all connected clients
    5. Connection closes on disconnect or error
    
    Args:
        websocket: FastAPI WebSocket connection
        workflow_id: ID of the workflow to subscribe to
        
    Message format (JSON):
    {
        "event_id": "uuid",
        "workflow_id": "workflow-123",
        "workflow_run_id": "run-456",
        "event_type": "step_completed",
        "step_id": "step-1",
        "role": "product_manager",
        "content": "Product spec generated",
        "metadata": {"duration_ms": 1234},
        "timestamp": "2026-03-18T08:57:00Z",
        "status": "success"
    }
    """
    try:
        # Accept connection
        await ws_manager.connect(websocket, workflow_id)
        logger.info(f"WebSocket client connected for workflow {workflow_id}")

        # Send connection confirmation
        await websocket.send_json({
            "type": "connection",
            "message": f"Connected to workflow {workflow_id}",
            "workflow_id": workflow_id,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Keep connection alive and listen for client messages
        # (Clients can send keep-alive pings, we respond with pong)
        while True:
            try:
                # Wait for client message (with timeout to detect disconnects)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60.0  # 60 second timeout
                )

                # Echo pong for ping
                if data == "ping":
                    await websocket.send_text("pong")

            except asyncio.TimeoutError:
                # Check if still connected
                if websocket.client_state != WebSocketState.CONNECTED:
                    break
                # Keep alive
                continue

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected for workflow {workflow_id}")
        await ws_manager.disconnect(workflow_id, websocket)

    except Exception as e:
        logger.error(f"WebSocket error for workflow {workflow_id}: {e}")
        try:
            await ws_manager.disconnect(workflow_id, websocket)
        except:
            pass


# ============================================================================
# Helper Functions for Integration
# ============================================================================

async def emit_progress_event(
    workflow_id: str,
    workflow_run_id: str,
    event_type: str,
    step_id: Optional[str] = None,
    role: Optional[str] = None,
    content: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Helper function to emit progress events.
    
    Called by WorkflowEngine during execution.
    
    Args:
        workflow_id: ID of the workflow
        workflow_run_id: ID of the workflow run
        event_type: Type of event (step_started, step_completed, etc.)
        step_id: ID of the step (if applicable)
        role: Agent role (if applicable)
        content: Event content
        metadata: Additional metadata
    """
    # This would be called by WorkflowEngine to emit events
    # For now, it's here as a helper for integration
    pass


# ============================================================================
# Imports needed
# ============================================================================

from datetime import datetime
from fastapi import WebSocketDisconnect, WebSocketState
import asyncio
from starlette.websockets import WebSocketState as WS_State

# Fix circular import by using late binding
try:
    from starlette.websockets import WebSocketState
except ImportError:
    class WebSocketState:
        CONNECTED = 1
        DISCONNECTED = 0
