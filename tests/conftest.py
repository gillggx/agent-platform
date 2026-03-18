"""
Pytest configuration and fixtures for Phase 1 tests.
"""

import pytest
import asyncio
import sys
from pathlib import Path

# Add backend app to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_workflow_data():
    """Provide sample workflow definition data."""
    return {
        "id": "sample-workflow",
        "name": "Sample Workflow",
        "description": "A sample workflow for testing",
        "steps": [
            {
                "id": "step-1",
                "agent_role": "pm",
                "task_type": "analysis",
                "depends_on": [],
            },
            {
                "id": "step-2",
                "agent_role": "architect",
                "task_type": "design",
                "depends_on": ["step-1"],
            },
        ],
    }


@pytest.fixture
def sample_role_data():
    """Provide sample role definition data."""
    return {
        "role": "test_role",
        "display_name": "Test Role",
        "description": "A test role",
        "system_prompt": "You are a test agent",
        "capabilities": ["test_task"],
        "config": {
            "temperature": 0.7,
            "max_tokens": 2048,
        },
    }
