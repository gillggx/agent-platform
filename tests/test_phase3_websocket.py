"""
Tests for WebSocket real-time progress (Phase 3).

Test Coverage:
- WebSocket connection management
- Event broadcasting
- Progress tracking
- Error handling and recovery
- Multiple concurrent connections

Type annotations: 100%
Docstrings: 100%
"""

from __future__ import annotations

import pytest
import asyncio
from datetime import datetime
from typing import List, Optional
from unittest.mock import Mock, AsyncMock, MagicMock

from app.websocket.websocket_handler import (
    WebSocketManager,
    ProgressEvent,
    WorkflowProgressTracker,
)
from app.schemas.artifact import ProgressEventType


# ============================================================================
# Mock WebSocket for Testing
# ============================================================================

class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self) -> None:
        """Initialize mock WebSocket."""
        self.client_state = 1  # CONNECTED
        self.sent_messages: List[str] = []
        self.accepted = False
        self.disconnected = False

    async def accept(self) -> None:
        """Mock accept."""
        self.accepted = True

    async def send_text(self, data: str) -> None:
        """Mock send_text."""
        if self.client_state != 1:
            raise RuntimeError("WebSocket not connected")
        self.sent_messages.append(data)

    async def send_json(self, data: dict) -> None:
        """Mock send_json."""
        import json
        await self.send_text(json.dumps(data))

    async def receive_text(self) -> str:
        """Mock receive_text."""
        await asyncio.sleep(0.1)
        return "ping"

    async def close(self) -> None:
        """Mock close."""
        self.client_state = 0
        self.disconnected = True

    def get_sent_messages(self) -> List[str]:
        """Get all sent messages."""
        return self.sent_messages

    def clear_messages(self) -> None:
        """Clear sent messages."""
        self.sent_messages.clear()


# ============================================================================
# WebSocketManager Tests
# ============================================================================

@pytest.mark.asyncio
class TestWebSocketManager:
    """Test WebSocket connection management."""

    async def test_connect_single_client(self) -> None:
        """Test connecting a single client."""
        manager = WebSocketManager()
        ws = MockWebSocket()

        await manager.connect(ws, "workflow-123")

        assert ws.accepted is True
        count = await manager.get_client_count("workflow-123")
        assert count == 1

    async def test_disconnect_client(self) -> None:
        """Test disconnecting a client."""
        manager = WebSocketManager()
        ws = MockWebSocket()

        await manager.connect(ws, "workflow-123")
        assert await manager.get_client_count("workflow-123") == 1

        await manager.disconnect("workflow-123", ws)
        assert await manager.get_client_count("workflow-123") == 0

    async def test_multiple_clients_same_workflow(self) -> None:
        """Test multiple clients for same workflow."""
        manager = WebSocketManager()
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        ws3 = MockWebSocket()

        await manager.connect(ws1, "workflow-123")
        await manager.connect(ws2, "workflow-123")
        await manager.connect(ws3, "workflow-123")

        count = await manager.get_client_count("workflow-123")
        assert count == 3

        await manager.disconnect("workflow-123", ws1)
        count = await manager.get_client_count("workflow-123")
        assert count == 2

    async def test_broadcast_to_multiple_clients(self) -> None:
        """Test broadcasting to multiple clients."""
        manager = WebSocketManager()
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()

        await manager.connect(ws1, "workflow-123")
        await manager.connect(ws2, "workflow-123")

        event = ProgressEvent(
            workflow_id="workflow-123",
            workflow_run_id="run-456",
            event_type=ProgressEventType.STEP_COMPLETED,
            step_id="step-1",
            role="product_manager",
            content="Step completed"
        )

        await manager.broadcast("workflow-123", event)

        # Both clients should receive the message
        assert len(ws1.get_sent_messages()) == 1
        assert len(ws2.get_sent_messages()) == 1

    async def test_broadcast_to_nonexistent_workflow(self) -> None:
        """Test broadcasting to workflow with no clients."""
        manager = WebSocketManager()

        event = ProgressEvent(
            workflow_id="nonexistent",
            workflow_run_id="run-456",
            event_type=ProgressEventType.STEP_COMPLETED
        )

        # Should not raise error
        await manager.broadcast("nonexistent", event)

    async def test_send_personal_message(self) -> None:
        """Test sending message to single client."""
        manager = WebSocketManager()
        ws = MockWebSocket()

        await manager.connect(ws, "workflow-123")

        event = ProgressEvent(
            workflow_id="workflow-123",
            workflow_run_id="run-456",
            event_type=ProgressEventType.AGENT_OUTPUT
        )

        await manager.send_personal(ws, event)

        assert len(ws.get_sent_messages()) == 1

    async def test_is_connected(self) -> None:
        """Test checking if workflow has connected clients."""
        manager = WebSocketManager()

        assert await manager.is_connected("workflow-123") is False

        ws = MockWebSocket()
        await manager.connect(ws, "workflow-123")

        assert await manager.is_connected("workflow-123") is True

        await manager.disconnect("workflow-123", ws)

        assert await manager.is_connected("workflow-123") is False

    async def test_client_count(self) -> None:
        """Test getting client count."""
        manager = WebSocketManager()

        count = await manager.get_client_count("workflow-123")
        assert count == 0

        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        ws3 = MockWebSocket()

        await manager.connect(ws1, "workflow-123")
        assert await manager.get_client_count("workflow-123") == 1

        await manager.connect(ws2, "workflow-123")
        assert await manager.get_client_count("workflow-123") == 2

        await manager.connect(ws3, "workflow-123")
        assert await manager.get_client_count("workflow-123") == 3

    async def test_different_workflows_isolated(self) -> None:
        """Test that different workflows are isolated."""
        manager = WebSocketManager()
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()

        await manager.connect(ws1, "workflow-123")
        await manager.connect(ws2, "workflow-456")

        assert await manager.get_client_count("workflow-123") == 1
        assert await manager.get_client_count("workflow-456") == 1

        # Broadcast to workflow-123 should only affect ws1
        event = ProgressEvent(
            workflow_id="workflow-123",
            workflow_run_id="run-123"
        )

        ws1.clear_messages()
        ws2.clear_messages()

        await manager.broadcast("workflow-123", event)

        assert len(ws1.get_sent_messages()) == 1
        assert len(ws2.get_sent_messages()) == 0


# ============================================================================
# Progress Event Tests
# ============================================================================

class TestProgressEvent:
    """Test ProgressEvent data class."""

    def test_progress_event_creation(self) -> None:
        """Test creating progress event."""
        event = ProgressEvent(
            workflow_id="workflow-123",
            workflow_run_id="run-456",
            event_type=ProgressEventType.STEP_STARTED,
            step_id="step-1",
            role="agent",
            content="Starting step"
        )

        assert event.workflow_id == "workflow-123"
        assert event.workflow_run_id == "run-456"
        assert event.event_type == ProgressEventType.STEP_STARTED
        assert event.step_id == "step-1"

    def test_progress_event_to_dict(self) -> None:
        """Test converting event to dictionary."""
        event = ProgressEvent(
            workflow_id="workflow-123",
            workflow_run_id="run-456",
            event_type=ProgressEventType.STEP_COMPLETED,
            metadata={"duration_ms": 1234}
        )

        event_dict = event.to_dict()

        assert event_dict["workflow_id"] == "workflow-123"
        assert event_dict["workflow_run_id"] == "run-456"
        assert event_dict["event_type"] == "step_completed"
        assert event_dict["metadata"]["duration_ms"] == 1234
        assert "timestamp" in event_dict

    def test_progress_event_to_schema(self) -> None:
        """Test converting event to Pydantic schema."""
        event = ProgressEvent(
            workflow_id="workflow-123",
            workflow_run_id="run-456",
            event_type=ProgressEventType.AGENT_OUTPUT,
            role="product_manager",
            content="Generated product spec"
        )

        schema = event.to_schema()

        assert schema.workflow_id == "workflow-123"
        assert schema.workflow_run_id == "run-456"
        assert schema.role == "product_manager"
        assert schema.content == "Generated product spec"


# ============================================================================
# Workflow Progress Tracker Tests
# ============================================================================

@pytest.mark.asyncio
class TestWorkflowProgressTracker:
    """Test workflow progress tracking."""

    async def test_step_started_event(self) -> None:
        """Test step started event."""
        manager = WebSocketManager()
        tracker = WorkflowProgressTracker()
        tracker.set_websocket_manager(manager)

        ws = MockWebSocket()
        await manager.connect(ws, "workflow-123")

        await tracker.on_step_started(
            workflow_id="workflow-123",
            workflow_run_id="run-456",
            step_id="step-1",
            role="product_manager"
        )

        messages = ws.get_sent_messages()
        assert len(messages) == 1

        import json
        event_data = json.loads(messages[0])
        assert event_data["event_type"] == "step_started"
        assert event_data["step_id"] == "step-1"
        assert event_data["role"] == "product_manager"

    async def test_step_completed_event_with_duration(self) -> None:
        """Test step completed event includes duration."""
        manager = WebSocketManager()
        tracker = WorkflowProgressTracker()
        tracker.set_websocket_manager(manager)

        ws = MockWebSocket()
        await manager.connect(ws, "workflow-123")

        # Start step
        await tracker.on_step_started(
            workflow_id="workflow-123",
            workflow_run_id="run-456",
            step_id="step-1",
            role="architect"
        )

        ws.clear_messages()

        # Wait a bit
        await asyncio.sleep(0.1)

        # Complete step
        await tracker.on_step_completed(
            workflow_id="workflow-123",
            workflow_run_id="run-456",
            step_id="step-1",
            role="architect",
            output="Design completed"
        )

        messages = ws.get_sent_messages()
        assert len(messages) == 1

        import json
        event_data = json.loads(messages[0])
        assert event_data["event_type"] == "step_completed"
        assert "duration_ms" in event_data["metadata"]
        assert event_data["metadata"]["duration_ms"] > 50

    async def test_agent_output_event(self) -> None:
        """Test agent output event."""
        manager = WebSocketManager()
        tracker = WorkflowProgressTracker()
        tracker.set_websocket_manager(manager)

        ws = MockWebSocket()
        await manager.connect(ws, "workflow-123")

        output = "Generated product specification with detailed requirements"

        await tracker.on_agent_output(
            workflow_id="workflow-123",
            workflow_run_id="run-456",
            step_id="step-1",
            role="product_manager",
            content=output
        )

        messages = ws.get_sent_messages()
        assert len(messages) == 1

        import json
        event_data = json.loads(messages[0])
        assert event_data["event_type"] == "agent_output"
        assert event_data["role"] == "product_manager"
        assert event_data["content"] == output

    async def test_agent_output_truncation(self) -> None:
        """Test that long agent output is truncated in event."""
        manager = WebSocketManager()
        tracker = WorkflowProgressTracker()
        tracker.set_websocket_manager(manager)

        ws = MockWebSocket()
        await manager.connect(ws, "workflow-123")

        # Create long output
        long_output = "x" * 1000

        await tracker.on_agent_output(
            workflow_id="workflow-123",
            workflow_run_id="run-456",
            step_id="step-1",
            role="architect",
            content=long_output
        )

        import json
        event_data = json.loads(ws.get_sent_messages()[0])
        assert len(event_data["content"]) == 500
        assert event_data["metadata"]["truncated"] is True
        assert event_data["metadata"]["content_length"] == 1000

    async def test_workflow_completed_event(self) -> None:
        """Test workflow completed event."""
        manager = WebSocketManager()
        tracker = WorkflowProgressTracker()
        tracker.set_websocket_manager(manager)

        ws = MockWebSocket()
        await manager.connect(ws, "workflow-123")

        artifact_ids = ["artifact-1", "artifact-2", "artifact-3"]

        await tracker.on_workflow_completed(
            workflow_id="workflow-123",
            workflow_run_id="run-456",
            artifacts=artifact_ids
        )

        import json
        event_data = json.loads(ws.get_sent_messages()[0])
        assert event_data["event_type"] == "workflow_completed"
        assert event_data["metadata"]["artifacts_count"] == 3
        assert len(event_data["metadata"]["artifacts"]) == 3

    async def test_workflow_failed_event(self) -> None:
        """Test workflow failed event."""
        manager = WebSocketManager()
        tracker = WorkflowProgressTracker()
        tracker.set_websocket_manager(manager)

        ws = MockWebSocket()
        await manager.connect(ws, "workflow-123")

        error_msg = "LLM API rate limit exceeded"

        await tracker.on_workflow_failed(
            workflow_id="workflow-123",
            workflow_run_id="run-456",
            error=error_msg
        )

        import json
        event_data = json.loads(ws.get_sent_messages()[0])
        assert event_data["event_type"] == "workflow_failed"
        assert event_data["status"] == "error"
        assert error_msg in event_data["content"]

    async def test_no_broadcast_without_manager(self) -> None:
        """Test that events aren't broadcast without manager."""
        tracker = WorkflowProgressTracker()
        # Don't set manager

        # Should not raise error
        await tracker.on_step_started(
            workflow_id="workflow-123",
            workflow_run_id="run-456",
            step_id="step-1",
            role="agent"
        )


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
class TestWebSocketIntegration:
    """Integration tests for WebSocket."""

    async def test_complete_workflow_progress_stream(self) -> None:
        """Test complete workflow progress streaming."""
        manager = WebSocketManager()
        tracker = WorkflowProgressTracker()
        tracker.set_websocket_manager(manager)

        # Connect client
        ws = MockWebSocket()
        await manager.connect(ws, "workflow-123")

        # Simulate workflow execution
        await tracker.on_step_started(
            workflow_id="workflow-123",
            workflow_run_id="run-456",
            step_id="step-1",
            role="product_manager"
        )

        await asyncio.sleep(0.05)

        await tracker.on_agent_output(
            workflow_id="workflow-123",
            workflow_run_id="run-456",
            step_id="step-1",
            role="product_manager",
            content="Product specification generated"
        )

        await tracker.on_step_completed(
            workflow_id="workflow-123",
            workflow_run_id="run-456",
            step_id="step-1",
            role="product_manager",
            output="Done"
        )

        await tracker.on_step_started(
            workflow_id="workflow-123",
            workflow_run_id="run-456",
            step_id="step-2",
            role="architect"
        )

        await asyncio.sleep(0.05)

        await tracker.on_step_completed(
            workflow_id="workflow-123",
            workflow_run_id="run-456",
            step_id="step-2",
            role="architect",
            output="Done"
        )

        await tracker.on_workflow_completed(
            workflow_id="workflow-123",
            workflow_run_id="run-456",
            artifacts=["artifact-1", "artifact-2"]
        )

        # Verify all events received
        messages = ws.get_sent_messages()
        assert len(messages) >= 6

        import json
        events = [json.loads(m) for m in messages]

        event_types = [e["event_type"] for e in events]
        assert "step_started" in event_types
        assert "agent_output" in event_types
        assert "step_completed" in event_types
        assert "workflow_completed" in event_types

    async def test_multiple_clients_receive_same_events(self) -> None:
        """Test multiple clients receive same events."""
        manager = WebSocketManager()
        tracker = WorkflowProgressTracker()
        tracker.set_websocket_manager(manager)

        # Connect multiple clients
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        ws3 = MockWebSocket()

        await manager.connect(ws1, "workflow-123")
        await manager.connect(ws2, "workflow-123")
        await manager.connect(ws3, "workflow-123")

        # Emit events
        await tracker.on_step_started(
            workflow_id="workflow-123",
            workflow_run_id="run-456",
            step_id="step-1",
            role="agent"
        )

        await tracker.on_step_completed(
            workflow_id="workflow-123",
            workflow_run_id="run-456",
            step_id="step-1",
            role="agent",
            output="Done"
        )

        # All clients should receive events
        assert len(ws1.get_sent_messages()) == 2
        assert len(ws2.get_sent_messages()) == 2
        assert len(ws3.get_sent_messages()) == 2

        # Messages should be identical
        assert ws1.get_sent_messages() == ws2.get_sent_messages()
        assert ws2.get_sent_messages() == ws3.get_sent_messages()
