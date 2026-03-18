"""
WebSocket Handler — Real-time workflow progress streaming.

Implements:
- WebSocketManager: Connection management and message broadcasting
- ProgressEvent: Workflow progress event data class
- WorkflowProgressTracker: Integration with WorkflowEngine

Features:
- Multiple concurrent client connections per workflow
- Connection lifecycle management
- JSON message formatting and broadcasting
- Error recovery and connection cleanup
- Progress event tracking with timestamps

Type annotations: 100%
Docstrings: 100%
Async-first design with error handling.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Set
from uuid import uuid4

from fastapi import WebSocket

from app.schemas.artifact import ProgressEventSchema, ProgressEventType

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class ProgressEvent:
    """
    Workflow progress event.
    
    Attributes:
        event_id: Unique event identifier
        workflow_id: ID of the workflow
        workflow_run_id: ID of the workflow run
        event_type: Type of event (step_started, step_completed, etc.)
        step_id: ID of the step (if applicable)
        role: Agent role that executed this step
        content: Event content (output, error, etc.)
        metadata: Additional metadata (duration, tokens, etc.)
        timestamp: When the event occurred
        status: Status/result (success, failure, etc.)
    """
    event_id: str = field(default_factory=lambda: str(uuid4()))
    workflow_id: str = ""
    workflow_run_id: str = ""
    event_type: ProgressEventType = ProgressEventType.STEP_STARTED
    step_id: Optional[str] = None
    role: Optional[str] = None
    content: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    status: str = "success"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_id": self.event_id,
            "workflow_id": self.workflow_id,
            "workflow_run_id": self.workflow_run_id,
            "event_type": self.event_type.value,
            "step_id": self.step_id,
            "role": self.role,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status,
        }

    def to_schema(self) -> ProgressEventSchema:
        """Convert to Pydantic schema."""
        return ProgressEventSchema(
            event_id=self.event_id,
            workflow_id=self.workflow_id,
            workflow_run_id=self.workflow_run_id,
            event_type=self.event_type,
            step_id=self.step_id,
            role=self.role,
            content=self.content,
            metadata=self.metadata,
            timestamp=self.timestamp,
            status=self.status,
        )


# ============================================================================
# WebSocket Manager
# ============================================================================

class WebSocketManager:
    """
    Manage WebSocket connections and broadcast progress events.
    
    Methods:
        connect(websocket: WebSocket, workflow_id: str): Accept new connection
        disconnect(workflow_id: str, websocket: WebSocket): Close connection
        broadcast(workflow_id: str, event: ProgressEvent): Send to all clients
        send_personal(websocket: WebSocket, event: ProgressEvent): Send to one client
        is_connected(workflow_id: str) -> bool: Check if any connections exist
        get_client_count(workflow_id: str) -> int: Get connected client count
    """

    def __init__(self) -> None:
        """Initialize the manager."""
        # Map workflow_id → set of connected WebSockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Lock for thread-safe operations
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, workflow_id: str) -> None:
        """
        Accept a new WebSocket connection.
        
        Args:
            websocket: FastAPI WebSocket connection
            workflow_id: ID of the workflow to subscribe to
            
        Raises:
            RuntimeError: If connection fails
        """
        try:
            await websocket.accept()

            async with self.lock:
                if workflow_id not in self.active_connections:
                    self.active_connections[workflow_id] = set()

                self.active_connections[workflow_id].add(websocket)

            logger.info(
                f"WebSocket connected for workflow {workflow_id}. "
                f"Total clients: {len(self.active_connections[workflow_id])}"
            )
        except Exception as e:
            logger.error(f"Failed to accept WebSocket connection: {e}")
            raise RuntimeError(f"Connection failed: {e}")

    async def disconnect(self, workflow_id: str, websocket: WebSocket) -> None:
        """
        Close a WebSocket connection.
        
        Args:
            workflow_id: ID of the workflow
            websocket: WebSocket connection to close
        """
        try:
            async with self.lock:
                if workflow_id in self.active_connections:
                    self.active_connections[workflow_id].discard(websocket)

                    if not self.active_connections[workflow_id]:
                        del self.active_connections[workflow_id]

            logger.info(
                f"WebSocket disconnected for workflow {workflow_id}. "
                f"Remaining clients: {len(self.active_connections.get(workflow_id, []))}"
            )
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")

    async def broadcast(
        self,
        workflow_id: str,
        event: ProgressEvent
    ) -> None:
        """
        Broadcast event to all clients connected to a workflow.
        
        Args:
            workflow_id: ID of the workflow
            event: Progress event to broadcast
        """
        if workflow_id not in self.active_connections:
            logger.debug(f"No clients connected for workflow {workflow_id}")
            return

        disconnected: List[WebSocket] = []
        message_dict = event.to_dict()
        message_json = json.dumps(message_dict)

        async with self.lock:
            connections = list(self.active_connections.get(workflow_id, []))

        # Send to all connected clients
        for websocket in connections:
            try:
                # Check if connected using client_state attribute (1 = CONNECTED)
                is_connected = getattr(websocket, 'client_state', 0) == 1 or \
                               getattr(websocket, 'application_state', None) is not None
                
                if is_connected:
                    await websocket.send_text(message_json)
                    logger.debug(f"Sent event {event.event_id} to client")
                else:
                    disconnected.append(websocket)
            except Exception as e:
                logger.warning(
                    f"Failed to send message to client: {e}. Marking for removal."
                )
                disconnected.append(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            await self.disconnect(workflow_id, websocket)

    async def send_personal(
        self,
        websocket: WebSocket,
        event: ProgressEvent
    ) -> None:
        """
        Send event to a single client.
        
        Args:
            websocket: WebSocket connection
            event: Progress event to send
        """
        try:
            message_dict = event.to_dict()
            message_json = json.dumps(message_dict)

            is_connected = getattr(websocket, 'client_state', 0) == 1 or \
                           getattr(websocket, 'application_state', None) is not None
            
            if is_connected:
                await websocket.send_text(message_json)
        except Exception as e:
            logger.warning(f"Failed to send personal message: {e}")

    async def is_connected(self, workflow_id: str) -> bool:
        """
        Check if any clients are connected to a workflow.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            True if at least one client connected
        """
        return workflow_id in self.active_connections and \
               len(self.active_connections[workflow_id]) > 0

    async def get_client_count(self, workflow_id: str) -> int:
        """
        Get number of connected clients for a workflow.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Number of connected clients
        """
        return len(self.active_connections.get(workflow_id, []))


# ============================================================================
# Workflow Progress Tracker
# ============================================================================

class WorkflowProgressTracker:
    """
    Track workflow execution progress and broadcast events via WebSocket.
    
    Integrates with WorkflowEngine to emit progress events for each step
    and broadcasts them to all connected WebSocket clients.
    
    Methods:
        set_websocket_manager(manager: WebSocketManager): Set manager
        on_step_started(workflow_id: str, workflow_run_id: str, step_id: str, role: str)
        on_step_completed(workflow_id: str, workflow_run_id: str, step_id: str, role: str, output: Any)
        on_agent_output(workflow_id: str, workflow_run_id: str, step_id: str, role: str, content: str)
        on_workflow_completed(workflow_id: str, workflow_run_id: str, artifacts: List[str])
        on_workflow_failed(workflow_id: str, workflow_run_id: str, error: str)
    """

    def __init__(self) -> None:
        """Initialize the tracker."""
        self.ws_manager: Optional[WebSocketManager] = None
        self.step_start_times: Dict[str, float] = {}

    def set_websocket_manager(self, manager: WebSocketManager) -> None:
        """
        Set the WebSocket manager for broadcasting.
        
        Args:
            manager: WebSocketManager instance
        """
        self.ws_manager = manager
        logger.info("WebSocketManager configured for progress tracking")

    async def on_step_started(
        self,
        workflow_id: str,
        workflow_run_id: str,
        step_id: str,
        role: str
    ) -> None:
        """
        Called when a workflow step starts.
        
        Args:
            workflow_id: ID of the workflow
            workflow_run_id: ID of the workflow run
            step_id: ID of the step
            role: Agent role executing this step
        """
        if not self.ws_manager:
            return

        event = ProgressEvent(
            workflow_id=workflow_id,
            workflow_run_id=workflow_run_id,
            event_type=ProgressEventType.STEP_STARTED,
            step_id=step_id,
            role=role,
            content=f"Step '{step_id}' started by agent '{role}'"
        )

        self.step_start_times[step_id] = datetime.utcnow().timestamp()

        await self.ws_manager.broadcast(workflow_id, event)
        logger.info(f"Step started event broadcast: {step_id}")

    async def on_step_completed(
        self,
        workflow_id: str,
        workflow_run_id: str,
        step_id: str,
        role: str,
        output: Any
    ) -> None:
        """
        Called when a workflow step completes.
        
        Args:
            workflow_id: ID of the workflow
            workflow_run_id: ID of the workflow run
            step_id: ID of the step
            role: Agent role that executed
            output: Step output/result
        """
        if not self.ws_manager:
            return

        # Calculate duration
        duration_ms = 0
        if step_id in self.step_start_times:
            duration_ms = (
                datetime.utcnow().timestamp() - self.step_start_times[step_id]
            ) * 1000
            del self.step_start_times[step_id]

        event = ProgressEvent(
            workflow_id=workflow_id,
            workflow_run_id=workflow_run_id,
            event_type=ProgressEventType.STEP_COMPLETED,
            step_id=step_id,
            role=role,
            content=f"Step '{step_id}' completed",
            metadata={
                "duration_ms": duration_ms,
                "output_type": type(output).__name__
            }
        )

        await self.ws_manager.broadcast(workflow_id, event)
        logger.info(f"Step completed event broadcast: {step_id} ({duration_ms:.0f}ms)")

    async def on_agent_output(
        self,
        workflow_id: str,
        workflow_run_id: str,
        step_id: str,
        role: str,
        content: str
    ) -> None:
        """
        Called when an agent produces output.
        
        Args:
            workflow_id: ID of the workflow
            workflow_run_id: ID of the workflow run
            step_id: ID of the step
            role: Agent role
            content: The agent's output content
        """
        if not self.ws_manager:
            return

        # Limit content size in event (full content stored in artifact)
        preview = content[:500] if len(content) > 500 else content

        event = ProgressEvent(
            workflow_id=workflow_id,
            workflow_run_id=workflow_run_id,
            event_type=ProgressEventType.AGENT_OUTPUT,
            step_id=step_id,
            role=role,
            content=preview,
            metadata={
                "content_length": len(content),
                "truncated": len(content) > 500
            }
        )

        await self.ws_manager.broadcast(workflow_id, event)
        logger.info(
            f"Agent output event broadcast: {role} "
            f"({len(content)} chars, {len(preview)} in preview)"
        )

    async def on_workflow_completed(
        self,
        workflow_id: str,
        workflow_run_id: str,
        artifacts: Optional[List[str]] = None
    ) -> None:
        """
        Called when workflow completes successfully.
        
        Args:
            workflow_id: ID of the workflow
            workflow_run_id: ID of the workflow run
            artifacts: List of artifact IDs generated
        """
        if not self.ws_manager:
            return

        event = ProgressEvent(
            workflow_id=workflow_id,
            workflow_run_id=workflow_run_id,
            event_type=ProgressEventType.WORKFLOW_COMPLETED,
            content="Workflow completed successfully",
            metadata={
                "artifacts_count": len(artifacts) if artifacts else 0,
                "artifacts": artifacts or []
            }
        )

        await self.ws_manager.broadcast(workflow_id, event)
        logger.info(f"Workflow completed event broadcast: {workflow_run_id}")

    async def on_workflow_failed(
        self,
        workflow_id: str,
        workflow_run_id: str,
        error: str
    ) -> None:
        """
        Called when workflow fails.
        
        Args:
            workflow_id: ID of the workflow
            workflow_run_id: ID of the workflow run
            error: Error message
        """
        if not self.ws_manager:
            return

        event = ProgressEvent(
            workflow_id=workflow_id,
            workflow_run_id=workflow_run_id,
            event_type=ProgressEventType.WORKFLOW_FAILED,
            content=f"Workflow failed: {error}",
            status="error"
        )

        await self.ws_manager.broadcast(workflow_id, event)
        logger.error(f"Workflow failed event broadcast: {workflow_run_id} - {error}")


# ============================================================================
# Global Instances
# ============================================================================

# Global WebSocket manager
ws_manager = WebSocketManager()

# Global progress tracker
progress_tracker = WorkflowProgressTracker()
progress_tracker.set_websocket_manager(ws_manager)
