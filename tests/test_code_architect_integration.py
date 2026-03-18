"""
Integration Tests — Code Architect + Agent Platform

Tests:
- CodeArchitectAdapter initialization and health checks
- Code generation tool calls
- Code validation and impact analysis
- Integration with RoleManager (Architect Agent)
- Tool execution through LLMAdapter
- Full agent conversation workflow with code generation
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json
from datetime import datetime

# Import modules under test
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend/app"))

from knowledge.code_architect_adapter import (
    CodeArchitectAdapter,
    CodeArchitectClient,
    CodeGenResult,
    ValidationResult,
    ImpactAnalysisResult,
    FileChange,
    ValidationIssue,
)

from intelligence.code_generation_support import (
    CodeArtifact,
    CodeLanguage,
    format_code_block,
    format_validation_issues,
    format_impact_analysis,
    detect_language_from_filename,
)

from intelligence.llm_adapter_tools import (
    ToolExecutor,
    get_built_in_tools,
    get_code_generation_tools,
    ToolCall,
    extract_tool_calls_from_response,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def code_architect_adapter():
    """Create Code Architect adapter instance."""
    adapter = CodeArchitectAdapter(
        base_url="http://localhost:8000",
        enabled=True,
    )
    return adapter


@pytest.fixture
def mock_code_architect_client():
    """Create mock Code Architect client."""
    client = AsyncMock()
    client.generate_code = AsyncMock()
    client.validate_code = AsyncMock()
    client.analyze_impact = AsyncMock()
    client.health_check = AsyncMock(return_value=True)
    return client


@pytest.fixture
def sample_generation_result():
    """Sample code generation result."""
    return {
        "success": True,
        "changes": [
            {
                "file": "src/models.py",
                "action": "create",
                "content": "from pydantic import BaseModel\n\nclass User(BaseModel):\n    id: int\n    name: str\n    email: str\n",
                "diff": None,
                "applied": False,
            }
        ],
        "explanation": "Created Pydantic User model",
        "plan": ["Define model structure", "Add validations"],
        "patterns_used": ["pydantic_model"],
        "tests_suggested": ["test_user_creation"],
        "model_used": "gpt-4o",
    }


@pytest.fixture
def sample_validation_result():
    """Sample code validation result."""
    return {
        "valid": True,
        "issues": [
            {
                "severity": "warning",
                "message": "Missing docstring",
                "file": "src/models.py",
                "line": 3,
                "suggestion": "Add docstring to class",
            }
        ],
        "patterns_matched": ["pydantic_model", "dataclass_pattern"],
        "improvements": ["Consider adding field descriptions"],
        "summary": "Code follows project patterns",
    }


@pytest.fixture
def sample_impact_result():
    """Sample impact analysis result."""
    return {
        "impact_score": 0.35,
        "affected_modules": ["src/models", "src/api"],
        "dependencies": ["pydantic", "sqlalchemy"],
        "breaking_changes": [],
        "test_coverage_impact": "low",
        "performance_impact": "none",
        "summary": "Low-risk change with good test coverage",
    }


# ============================================================================
# Test CodeArchitectAdapter
# ============================================================================

class TestCodeArchitectAdapter:
    """Tests for CodeArchitectAdapter."""

    def test_adapter_initialization(self, code_architect_adapter):
        """Test adapter initialization."""
        assert code_architect_adapter.enabled
        assert code_architect_adapter.base_url == "http://localhost:8000"
        assert code_architect_adapter.api_key is None

    def test_get_tools(self, code_architect_adapter):
        """Test tool definition generation."""
        tools = code_architect_adapter.get_tools()

        assert len(tools) == 3
        tool_names = [t["function"]["name"] for t in tools]
        assert "code_architect_generate" in tool_names
        assert "code_architect_validate" in tool_names
        assert "code_architect_impact" in tool_names

    def test_get_tools_when_disabled(self):
        """Test that tools are not returned when disabled."""
        adapter = CodeArchitectAdapter(enabled=False)
        tools = adapter.get_tools()
        assert len(tools) == 0

    @pytest.mark.asyncio
    async def test_handle_generate_tool_call(
        self, code_architect_adapter, sample_generation_result
    ):
        """Test handling generate tool call."""
        with patch.object(
            CodeArchitectClient, "__aenter__"
        ) as mock_enter, patch.object(
            CodeArchitectClient, "__aexit__"
        ) as mock_exit:
            mock_client = AsyncMock()
            mock_client.generate_code = AsyncMock(
                return_value=CodeGenResult(
                    success=True,
                    changes=[
                        FileChange(
                            file="src/models.py",
                            action="create",
                            content="class User:\n    pass\n",
                        )
                    ],
                    explanation="Created User model",
                )
            )
            mock_enter.return_value = mock_client
            mock_exit.return_value = None

            result = await code_architect_adapter.handle_tool_call(
                "code_architect_generate",
                {"task": "Create User model", "project_id": "test"},
            )

            assert result["status"] == "success"
            assert result["result"]["success"]
            assert len(result["result"]["changes"]) == 1

    @pytest.mark.asyncio
    async def test_is_available(self, code_architect_adapter):
        """Test service availability check."""
        with patch.object(
            CodeArchitectClient, "__aenter__"
        ) as mock_enter, patch.object(
            CodeArchitectClient, "__aexit__"
        ) as mock_exit:
            mock_client = AsyncMock()
            mock_client.health_check = AsyncMock(return_value=True)
            mock_enter.return_value = mock_client
            mock_exit.return_value = None

            is_available = await code_architect_adapter.is_available()
            assert is_available


# ============================================================================
# Test CodeGeneration Support
# ============================================================================

class TestCodeGenerationSupport:
    """Tests for code generation support utilities."""

    def test_language_detection(self):
        """Test programming language detection."""
        test_cases = [
            ("user.py", CodeLanguage.PYTHON),
            ("api/routes.js", CodeLanguage.JAVASCRIPT),
            ("models.ts", CodeLanguage.TYPESCRIPT),
            ("schema.sql", CodeLanguage.SQL),
            ("config.yaml", CodeLanguage.YAML),
            ("Dockerfile", CodeLanguage.DOCKERFILE),
        ]

        for filename, expected_lang in test_cases:
            detected = detect_language_from_filename(filename)
            assert detected == expected_lang

    def test_code_artifact_creation(self):
        """Test code artifact creation."""
        artifact = CodeArtifact(
            artifact_id="test-1",
            file_path="src/models.py",
            language=CodeLanguage.PYTHON,
            content="class User:\n    pass\n",
            description="User model",
        )

        assert artifact.file_path == "src/models.py"
        assert artifact.language == CodeLanguage.PYTHON
        assert "class User" in artifact.content

    def test_code_block_formatting(self):
        """Test code block formatting."""
        code = "def hello():\n    print('Hello')\n"
        formatted = format_code_block(code, CodeLanguage.PYTHON, "hello.py")

        assert "```python" in formatted
        assert "hello.py" in formatted
        assert "def hello" in formatted

    def test_validation_result_formatting(self):
        """Test validation result formatting."""
        issues = [
            {
                "severity": "error",
                "message": "Missing import",
                "file": "models.py",
                "line": 1,
            },
            {
                "severity": "warning",
                "message": "Unused variable",
                "file": "models.py",
                "line": 5,
            },
        ]

        presentation = format_validation_issues(issues)

        assert not presentation.valid
        assert len(presentation.critical_issues) == 1
        assert len(presentation.warnings) == 1
        assert "models.py:1" in presentation.critical_issues[0]

    def test_impact_analysis_formatting(self):
        """Test impact analysis formatting."""
        impact_data = {
            "impact_score": 0.75,
            "affected_modules": ["models", "api"],
            "breaking_changes": ["Changed User schema"],
            "test_coverage_impact": "high",
            "performance_impact": "positive",
            "summary": "High impact change with performance benefits",
        }

        presentation = format_impact_analysis(impact_data)

        assert presentation.impact_score == 0.75
        assert presentation.risk_level == "high"
        assert "User schema" in presentation.breaking_changes
        markdown = presentation.to_markdown()
        assert "Impact Analysis" in markdown


# ============================================================================
# Test LLM Adapter Tools
# ============================================================================

class TestLLMAdapterTools:
    """Tests for LLM adapter tools."""

    def test_get_built_in_tools(self):
        """Test built-in tools retrieval."""
        tools = get_built_in_tools()

        assert len(tools) >= 3
        tool_names = [t["function"]["name"] for t in tools]
        assert "search_knowledge" in tool_names
        assert "get_project_context" in tool_names
        assert "list_artifacts" in tool_names

    def test_get_code_generation_tools(self):
        """Test code generation tools retrieval."""
        tools = get_code_generation_tools()

        assert len(tools) == 3
        tool_names = [t["function"]["name"] for t in tools]
        assert "code_architect_generate" in tool_names
        assert "code_architect_validate" in tool_names
        assert "code_architect_impact" in tool_names

    def test_tool_call_creation(self):
        """Test tool call object creation."""
        call = ToolCall(
            tool_id="call-123",
            tool_name="code_architect_generate",
            parameters={"task": "Create User model", "project_id": "test"},
        )

        assert call.tool_name == "code_architect_generate"
        assert call.parameters["project_id"] == "test"
        call_dict = call.to_dict()
        assert "tool_id" in call_dict

    @pytest.mark.asyncio
    async def test_tool_executor_code_architect(self):
        """Test tool executor with Code Architect."""
        mock_adapter = AsyncMock()
        mock_adapter.handle_tool_call = AsyncMock(
            return_value={"status": "success", "result": {"success": True}}
        )

        executor = ToolExecutor(code_architect_adapter=mock_adapter)

        result = await executor.execute_tool(
            "code_architect_generate",
            {"task": "Create model", "project_id": "test"},
        )

        assert result.success
        assert result.tool_name == "code_architect_generate"
        mock_adapter.handle_tool_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_tool_executor_unknown_tool(self):
        """Test tool executor with unknown tool."""
        executor = ToolExecutor()

        result = await executor.execute_tool(
            "unknown_tool", {"param": "value"}
        )

        assert not result.success
        assert "Unknown tool" in result.error

    def test_extract_tool_calls_from_response(self):
        """Test extracting tool calls from LLM response."""
        response = {
            "message": {
                "tool_calls": [
                    {
                        "id": "call-1",
                        "function": {
                            "name": "code_architect_generate",
                            "arguments": json.dumps(
                                {"task": "Create model", "project_id": "test"}
                            ),
                        },
                    }
                ]
            }
        }

        tool_calls = extract_tool_calls_from_response(response)

        assert len(tool_calls) == 1
        assert tool_calls[0].tool_name == "code_architect_generate"
        assert tool_calls[0].parameters["task"] == "Create model"


# ============================================================================
# Integration Tests
# ============================================================================

class TestCodeArchitectIntegration:
    """Integration tests combining Code Architect and agent-platform."""

    def test_architect_role_has_code_generation_tools(self):
        """Test that Architect role has code generation tools."""
        from knowledge.role_manager import RoleRegistry

        registry = RoleRegistry()
        architect_role = registry.get_role("architect")

        assert architect_role is not None
        assert "code_generation" in architect_role.capabilities
        assert "code_architect_generate" in architect_role.tools
        assert "code_architect_validate" in architect_role.tools

    @pytest.mark.asyncio
    async def test_full_code_generation_flow(self, sample_generation_result):
        """Test full code generation flow."""
        # Setup
        adapter = CodeArchitectAdapter(base_url="http://localhost:8000")
        executor = ToolExecutor(code_architect_adapter=adapter)

        # Mock the Code Architect client
        with patch.object(CodeArchitectClient, "__aenter__") as mock_enter:
            mock_client = AsyncMock()
            mock_client.generate_code = AsyncMock(
                return_value=CodeGenResult(
                    success=True,
                    changes=[
                        FileChange(
                            file="src/models.py",
                            action="create",
                            content=sample_generation_result["changes"][0][
                                "content"
                            ],
                        )
                    ],
                    explanation=sample_generation_result["explanation"],
                )
            )
            mock_enter.return_value = mock_client

            # Execute
            result = await executor.execute_tool(
                "code_architect_generate",
                {"task": "Create User model", "project_id": "test-project"},
            )

            # Verify
            assert result.success
            assert result.result["success"]
            assert len(result.result["changes"]) == 1

    @pytest.mark.asyncio
    async def test_code_validation_and_impact_flow(
        self, sample_validation_result, sample_impact_result
    ):
        """Test validation and impact analysis flow."""
        adapter = CodeArchitectAdapter()
        executor = ToolExecutor(code_architect_adapter=adapter)

        with patch.object(CodeArchitectClient, "__aenter__") as mock_enter:
            mock_client = AsyncMock()
            
            # Setup mock returns
            mock_client.validate_code = AsyncMock(
                return_value=ValidationResult(
                    valid=sample_validation_result["valid"],
                    issues=[
                        ValidationIssue(
                            severity=issue["severity"],
                            message=issue["message"],
                            file=issue.get("file"),
                            line=issue.get("line"),
                        )
                        for issue in sample_validation_result["issues"]
                    ],
                    patterns_matched=sample_validation_result["patterns_matched"],
                )
            )
            
            mock_client.analyze_impact = AsyncMock(
                return_value=ImpactAnalysisResult(
                    impact_score=sample_impact_result["impact_score"],
                    affected_modules=sample_impact_result["affected_modules"],
                )
            )
            
            mock_enter.return_value = mock_client

            # Execute validation
            validation_result = await executor.execute_tool(
                "code_architect_validate",
                {
                    "changes": [
                        {
                            "file": "src/models.py",
                            "action": "create",
                            "content": "class User: pass",
                        }
                    ],
                    "project_id": "test-project",
                },
            )

            assert validation_result.success

            # Execute impact analysis
            impact_result = await executor.execute_tool(
                "code_architect_impact",
                {
                    "changes": [
                        {
                            "file": "src/models.py",
                            "action": "create",
                            "content": "class User: pass",
                        }
                    ],
                    "project_id": "test-project",
                },
            )

            assert impact_result.success


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
