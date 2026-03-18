"""
End-to-End Code Generation Workflow Tests

Tests the complete workflow:
1. User requirement definition (PM)
2. Code generation by Architect Agent
3. Validation of generated code
4. Impact analysis
5. Review by PM and QA
6. Director approval
7. Export as artifacts

This is a high-level integration test demonstrating the full loop.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import json

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend/app"))

from intelligence.agent_conversation import (
    AgentConversation,
    ConversationContext,
    Message,
    MessageType,
)

from knowledge.code_architect_adapter import (
    CodeArchitectAdapter,
    CodeArchitectClient,
    CodeGenResult,
    ValidationResult,
    ImpactAnalysisResult,
    FileChange,
)

from knowledge.role_manager import RoleRegistry, RoleTemplate

from intelligence.code_generation_support import (
    CodeArtifact,
    CodeLanguage,
    format_code_generation_message,
    format_validation_message,
    format_impact_message,
)

from intelligence.llm_adapter_tools import ToolExecutor, get_code_generation_tools


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def project_id():
    """Test project ID."""
    return "test-project-e2e"


@pytest.fixture
def code_architect_adapter():
    """Code Architect adapter for tests."""
    return CodeArchitectAdapter(base_url="http://localhost:8000")


@pytest.fixture
def role_registry():
    """Role registry with all roles."""
    return RoleRegistry()


@pytest.fixture
def conversation_context():
    """Conversation context for tests."""
    return ConversationContext(
        conversation_id="e2e-test-123",
        workflow="code_generation",
        shared_context={
            "project_id": "test-project",
            "requirements": "Create a FastAPI route handler for user management",
            "features": ["list users", "get user by ID", "create user"],
        },
    )


# ============================================================================
# Test E2E Workflow
# ============================================================================

class TestE2ECodeGenWorkflow:
    """End-to-end code generation workflow tests."""

    def test_workflow_roles_are_present(self, role_registry):
        """Test that all required roles are registered."""
        required_roles = ["pm", "architect", "qa", "director"]
        for role in required_roles:
            assert role_registry.get_role(role) is not None

    def test_architect_has_code_generation_capability(self, role_registry):
        """Test that Architect role has code generation."""
        architect = role_registry.get_role("architect")
        assert "code_generation" in architect.capabilities
        assert "code_architect_generate" in architect.tools

    @pytest.mark.asyncio
    async def test_pm_defines_requirements(self, conversation_context):
        """Test: PM defines initial requirements."""
        # Simulate PM message
        pm_message = Message(
            from_role="pm",
            to_roles=["architect"],
            message_type=MessageType.REQUEST,
            content=(
                "I need a FastAPI route handler to manage users. "
                "Features: list all users, get user by ID, create new user."
            ),
            context={
                "project_id": "test-project",
                "requirements": "User management API",
            },
        )

        # Store in context
        conversation_context.message_history.append(pm_message)

        assert len(conversation_context.message_history) == 1
        assert conversation_context.message_history[0].from_role == "pm"

    @pytest.mark.asyncio
    async def test_architect_generates_code(
        self, conversation_context, code_architect_adapter
    ):
        """Test: Architect generates code using Code Architect."""
        # Mock Code Architect response
        with patch.object(CodeArchitectClient, "__aenter__") as mock_enter:
            mock_client = AsyncMock()
            
            # Create realistic code generation response
            fastapi_code = '''from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

app = FastAPI()

class User(BaseModel):
    id: int
    name: str
    email: str

# In-memory storage for demo
users = []

@app.get("/users", response_model=List[User])
async def list_users():
    """Get all users"""
    return users

@app.get("/users/{user_id}", response_model=User)
async def get_user(user_id: int):
    """Get user by ID"""
    for user in users:
        if user.id == user_id:
            return user
    raise HTTPException(status_code=404, detail="User not found")

@app.post("/users", response_model=User)
async def create_user(user: User):
    """Create a new user"""
    users.append(user)
    return user
'''
            
            mock_client.generate_code = AsyncMock(
                return_value=CodeGenResult(
                    success=True,
                    changes=[
                        FileChange(
                            file="src/routes/users.py",
                            action="create",
                            content=fastapi_code,
                        )
                    ],
                    explanation="Created FastAPI routes for user management with CRUD operations",
                    plan=[
                        "Define User Pydantic model",
                        "Implement list_users endpoint",
                        "Implement get_user endpoint",
                        "Implement create_user endpoint",
                    ],
                    patterns_used=["fastapi_route", "pydantic_model"],
                    tests_suggested=[
                        "test_list_users",
                        "test_get_user",
                        "test_get_user_not_found",
                        "test_create_user",
                    ],
                    model_used="gpt-4o",
                )
            )
            
            mock_enter.return_value = mock_client

            # Execute code generation
            executor = ToolExecutor(code_architect_adapter=code_architect_adapter)
            
            result = await executor.execute_tool(
                "code_architect_generate",
                {
                    "task": "Create FastAPI route handler for user management with list, get, and create endpoints",
                    "project_id": "test-project",
                    "context": {
                        "requirements": "User management API",
                        "framework": "FastAPI",
                    },
                },
            )

            # Verify success
            assert result.success
            assert result.result["success"]
            assert len(result.result["changes"]) == 1
            
            # Extract the generated code
            generated_code = result.result["changes"][0]["content"]
            assert "FastAPI" in generated_code
            assert "list_users" in generated_code
            assert "get_user" in generated_code
            assert "create_user" in generated_code

            # Create architect message with generated code
            architect_message = Message(
                from_role="architect",
                to_roles=["qa", "pm"],
                message_type=MessageType.RESPONSE,
                content=format_code_generation_message(
                    "Create FastAPI user management routes",
                    result.result,
                ),
                context={
                    "generated_code": generated_code,
                    "patterns_used": result.result["patterns_used"],
                    "tests_suggested": result.result["tests_suggested"],
                },
            )

            conversation_context.message_history.append(architect_message)
            assert len(conversation_context.message_history) == 1

    @pytest.mark.asyncio
    async def test_validate_generated_code(
        self, conversation_context, code_architect_adapter
    ):
        """Test: Validation of generated code."""
        with patch.object(CodeArchitectClient, "__aenter__") as mock_enter:
            mock_client = AsyncMock()
            
            mock_client.validate_code = AsyncMock(
                return_value=ValidationResult(
                    valid=True,
                    issues=[
                        # Some minor warnings
                    ],
                    patterns_matched=[
                        "fastapi_route",
                        "pydantic_model",
                        "error_handling",
                    ],
                    improvements=[
                        "Consider adding request validation middleware",
                        "Consider adding response caching",
                    ],
                    summary="Code follows FastAPI best practices and project patterns",
                )
            )
            
            mock_enter.return_value = mock_client

            executor = ToolExecutor(code_architect_adapter=code_architect_adapter)
            
            result = await executor.execute_tool(
                "code_architect_validate",
                {
                    "changes": [
                        {
                            "file": "src/routes/users.py",
                            "action": "create",
                            "content": "# FastAPI routes",
                        }
                    ],
                    "project_id": "test-project",
                },
            )

            assert result.success
            assert result.result["valid"]
            assert "fastapi_route" in result.result["patterns_matched"]

            # QA message
            qa_message = Message(
                from_role="qa",
                to_roles=["pm", "director"],
                message_type=MessageType.FEEDBACK,
                content=format_validation_message(result.result),
                context={"validation_result": result.result},
            )

            conversation_context.message_history.append(qa_message)

    @pytest.mark.asyncio
    async def test_analyze_impact(
        self, conversation_context, code_architect_adapter
    ):
        """Test: Impact analysis of generated code."""
        with patch.object(CodeArchitectClient, "__aenter__") as mock_enter:
            mock_client = AsyncMock()
            
            mock_client.analyze_impact = AsyncMock(
                return_value=ImpactAnalysisResult(
                    impact_score=0.25,
                    affected_modules=["api/routes", "models"],
                    dependencies=["fastapi", "pydantic"],
                    breaking_changes=[],
                    test_coverage_impact="low",
                    performance_impact="none",
                    summary="New route addition has minimal impact on existing code",
                )
            )
            
            mock_enter.return_value = mock_client

            executor = ToolExecutor(code_architect_adapter=code_architect_adapter)
            
            result = await executor.execute_tool(
                "code_architect_impact",
                {
                    "changes": [
                        {
                            "file": "src/routes/users.py",
                            "action": "create",
                            "content": "# FastAPI routes",
                        }
                    ],
                    "project_id": "test-project",
                },
            )

            assert result.success
            assert result.result["impact_score"] == 0.25
            assert result.result["breaking_changes"] == []

            # Architect message with impact analysis
            architect_message = Message(
                from_role="architect",
                to_roles=["director", "pm"],
                message_type=MessageType.UPDATE,
                content=format_impact_message(result.result),
                context={"impact_analysis": result.result},
            )

            conversation_context.message_history.append(architect_message)

    @pytest.mark.asyncio
    async def test_pm_reviews_and_approves(self, conversation_context):
        """Test: PM reviews and approves the implementation."""
        # PM creates review message
        pm_review = Message(
            from_role="pm",
            to_roles=["director"],
            message_type=MessageType.FEEDBACK,
            content=(
                "Code generation looks good. "
                "All required endpoints are implemented correctly. "
                "Ready for director approval."
            ),
            context={
                "approval_status": "ready_for_approval",
                "concerns": [],
            },
        )

        conversation_context.message_history.append(pm_review)
        assert len(conversation_context.message_history) >= 3

    @pytest.mark.asyncio
    async def test_director_approves(self, conversation_context):
        """Test: Director makes final approval."""
        director_message = Message(
            from_role="director",
            to_roles=["architect", "pm"],
            message_type=MessageType.DECISION,
            content="✅ APPROVED. Implementation meets all requirements. Ready for deployment.",
            context={
                "decision": "approved",
                "deployment_priority": "high",
            },
        )

        conversation_context.message_history.append(director_message)

        # Verify final state
        assert conversation_context.get_latest_message().from_role == "director"
        assert conversation_context.get_latest_message().message_type == MessageType.DECISION

    @pytest.mark.asyncio
    async def test_create_code_artifacts(self, conversation_context):
        """Test: Create code artifacts from generated code."""
        artifact = CodeArtifact(
            artifact_id="artifact-users-route",
            file_path="src/routes/users.py",
            language=CodeLanguage.PYTHON,
            content="""from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    email: str

@app.get("/users")
async def list_users():
    return []
""",
            description="FastAPI user management routes - APPROVED",
            metadata={
                "status": "approved",
                "approval_timestamp": datetime.utcnow().isoformat(),
                "approved_by": "director",
                "validation_status": "passed",
            },
        )

        assert artifact.artifact_id == "artifact-users-route"
        assert artifact.metadata["status"] == "approved"
        assert "FastAPI" in artifact.content

    def test_export_artifacts_summary(self):
        """Test: Export artifacts summary for documentation."""
        artifacts = [
            {
                "id": "artifact-users-route",
                "file": "src/routes/users.py",
                "language": "python",
                "status": "approved",
                "generated_by": "architect",
                "validated": True,
                "impact_score": 0.25,
            },
            {
                "id": "artifact-user-model",
                "file": "src/models/user.py",
                "language": "python",
                "status": "approved",
                "generated_by": "architect",
                "validated": True,
                "impact_score": 0.15,
            },
        ]

        # Create summary
        summary = {
            "workflow": "code_generation",
            "project": "test-project",
            "status": "completed",
            "artifacts_count": len(artifacts),
            "artifacts": artifacts,
            "timestamp": datetime.utcnow().isoformat(),
            "workflow_steps": [
                "PM: Requirements definition",
                "Architect: Code generation",
                "QA: Code validation",
                "Architect: Impact analysis",
                "PM: Review and feedback",
                "Director: Final approval",
            ],
        }

        assert summary["status"] == "completed"
        assert len(summary["artifacts"]) == 2
        assert summary["artifacts_count"] == 2


# ============================================================================
# Integration with Agent Conversation
# ============================================================================

class TestCodeGenWithAgentConversation:
    """Test code generation within agent conversation."""

    @pytest.mark.asyncio
    async def test_full_conversation_with_code_gen(self):
        """Test full conversation flow with code generation."""
        context = ConversationContext(
            conversation_id="full-flow-test",
            workflow="code_generation_with_review",
        )

        # Step 1: PM defines requirements
        pm_msg = Message(
            from_role="pm",
            to_roles=["architect"],
            message_type=MessageType.REQUEST,
            content="Create a database schema for storing products",
        )
        context.message_history.append(pm_msg)

        # Step 2: Architect generates code
        arch_msg = Message(
            from_role="architect",
            to_roles=["qa"],
            message_type=MessageType.RESPONSE,
            content="Generated product database schema using SQLAlchemy",
            context={"generated_files": ["models/product.py"]},
        )
        context.message_history.append(arch_msg)

        # Step 3: QA validates
        qa_msg = Message(
            from_role="qa",
            to_roles=["director"],
            message_type=MessageType.FEEDBACK,
            content="✅ Code validation passed. All patterns matched.",
        )
        context.message_history.append(qa_msg)

        # Step 4: Director approves
        dir_msg = Message(
            from_role="director",
            to_roles=["architect"],
            message_type=MessageType.DECISION,
            content="✅ APPROVED",
        )
        context.message_history.append(dir_msg)

        # Verify conversation state
        assert len(context.message_history) == 4
        assert context.get_latest_message().from_role == "director"
        
        pm_messages = context.get_messages_from("pm")
        arch_messages = context.get_messages_from("architect")
        
        assert len(pm_messages) == 1
        assert len(arch_messages) == 1


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
