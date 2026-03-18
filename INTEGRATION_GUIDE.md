# Code Architect Integration Guide

This guide explains how to enable and use Code Architect for code generation within agent-platform.

## Overview

Code Architect integration enables the **Architect Agent** to:
- Generate code based on requirements
- Validate generated code against project patterns
- Analyze impact of code changes
- Track generated code as artifacts
- Support full end-to-end workflows with agent team review

## Architecture

```
┌──────────────────────────────────┐
│   Agent Conversation Flow        │
├──────────────────────────────────┤
│ PM defines requirements           │
│ ↓                                │
│ Architect calls Code Architect   │
│ ↓                                │
│ QA validates generated code      │
│ ↓                                │
│ Architect analyzes impact        │
│ ↓                                │
│ PM/QA review and feedback       │
│ ↓                                │
│ Director approves                │
└──────────────────────────────────┘
         ↓
    Artifacts created
    Documentation generated
```

## Installation

### 1. Install Dependencies

```bash
# In agent-platform directory
pip install httpx pydantic

# Optional: For docx export
pip install python-docx
```

### 2. Code Architect Service

Ensure Code Architect is running on a known address:

```bash
# Start Code Architect (example)
cd /path/to/code-architect-agent-platform
python -m architect.api.main
# Server runs on http://localhost:8000
```

### 3. Configuration

Create `.env` file or configure environment variables:

```bash
# Code Architect API Configuration
CODE_ARCHITECT_BASE_URL=http://localhost:8000
CODE_ARCHITECT_API_KEY=optional-api-key  # If required
CODE_ARCHITECT_ENABLED=true
```

## Usage in Agent Conversation

### Basic Setup

```python
from knowledge.code_architect_adapter import get_code_architect_adapter
from intelligence.llm_adapter_tools import ToolExecutor, get_code_generation_tools

# Initialize adapter
adapter = get_code_architect_adapter(
    base_url="http://localhost:8000",
    enabled=True
)

# Create tool executor
executor = ToolExecutor(code_architect_adapter=adapter)

# Add code generation tools to available tools
tools = get_code_generation_tools()
```

### Tool Definitions

Three tools are available to the Architect Agent:

#### 1. Generate Code

```python
{
    "name": "code_architect_generate",
    "description": "Generate code using Code Architect",
    "parameters": {
        "task": "Task description for code generation",
        "project_id": "Project identifier",
        "mode": "dry_run or apply",  # default: dry_run
        "context": {
            "framework": "FastAPI",
            "requirements": "..."
        }
    }
}
```

**Example:**

```python
result = await executor.execute_tool(
    "code_architect_generate",
    {
        "task": "Create FastAPI route handler for user management with CRUD operations",
        "project_id": "my-project",
        "context": {
            "framework": "FastAPI",
            "database": "SQLAlchemy"
        }
    }
)
```

**Response:**

```python
{
    "success": True,
    "changes": [
        {
            "file": "src/routes/users.py",
            "action": "create",
            "content": "# Generated code here",
            "diff": None,
            "applied": False
        }
    ],
    "explanation": "Created FastAPI routes with CRUD operations",
    "plan": ["Define models", "Create routes", "Add validation"],
    "patterns_used": ["fastapi_route", "pydantic_model"],
    "tests_suggested": ["test_user_crud"],
    "model_used": "gpt-4o"
}
```

#### 2. Validate Code

```python
result = await executor.execute_tool(
    "code_architect_validate",
    {
        "changes": [
            {
                "file": "src/routes/users.py",
                "action": "create",
                "content": "# Generated code"
            }
        ],
        "project_id": "my-project"
    }
)
```

**Response:**

```python
{
    "valid": True,
    "issues": [
        {
            "severity": "warning",
            "message": "Missing docstring",
            "file": "src/routes/users.py",
            "line": 5,
            "suggestion": "Add function docstring"
        }
    ],
    "patterns_matched": ["fastapi_route", "pydantic_model"],
    "improvements": ["Add type hints"],
    "summary": "Code follows project patterns"
}
```

#### 3. Analyze Impact

```python
result = await executor.execute_tool(
    "code_architect_impact",
    {
        "changes": [
            {
                "file": "src/routes/users.py",
                "action": "create",
                "content": "# Generated code"
            }
        ],
        "project_id": "my-project"
    }
)
```

**Response:**

```python
{
    "impact_score": 0.25,  # 0.0 to 1.0
    "affected_modules": ["api/routes", "models"],
    "dependencies": ["fastapi", "pydantic"],
    "breaking_changes": [],
    "test_coverage_impact": "low",
    "performance_impact": "none",
    "summary": "Minimal impact, safe to merge"
}
```

## Agent Integration

### Architect Agent with Code Generation

The Architect Agent automatically has access to code generation tools:

```python
from knowledge.role_manager import RoleRegistry

registry = RoleRegistry()
architect = registry.get_role("architect")

# Check available tools
print(architect.tools)
# Output: [..., "code_architect_generate", "code_architect_validate", "code_architect_impact"]

# Check capabilities
print(architect.capabilities)
# Output: [..., "code_generation"]
```

### Workflow Example

```python
from intelligence.agent_conversation import AgentConversation, ConversationContext

# Initialize conversation
context = ConversationContext(
    conversation_id="codegen-flow-1",
    workflow="code_generation_with_review"
)

# Agent conversation handles:
# 1. PM request → Architect
# 2. Architect generates code
# 3. QA validates
# 4. Architect analyzes impact
# 5. Director approves
# 6. Artifacts saved
```

## Code Generation Support

### Code Formatting

```python
from intelligence.code_generation_support import (
    format_code_block,
    format_validation_issues,
    format_impact_analysis,
    CodeLanguage
)

# Format code block for display
markdown = format_code_block(
    content="def hello():\n    pass",
    language=CodeLanguage.PYTHON,
    title="hello.py",
    line_numbers=True
)

# Format validation result
presentation = format_validation_issues(issues_list)
markdown = presentation.to_markdown()

# Format impact analysis
presentation = format_impact_analysis(impact_data)
markdown = presentation.to_markdown()
```

### Code Artifacts

```python
from intelligence.code_generation_support import CodeArtifact, CodeLanguage

artifact = CodeArtifact(
    artifact_id="artifact-1",
    file_path="src/models.py",
    language=CodeLanguage.PYTHON,
    content="# Generated code",
    description="User model for product database",
    metadata={
        "status": "approved",
        "validated": True,
        "impact_score": 0.25
    }
)

# Convert to markdown
markdown = artifact.to_markdown()

# Save to file
with open(artifact.file_path, "w") as f:
    f.write(artifact.content)
```

## Error Handling

### Common Issues

#### Code Architect Service Unavailable

```python
# Check service health
is_available = await adapter.is_available()

if not is_available:
    logger.warning("Code Architect service unavailable")
    # Fallback to manual code review
```

#### Tool Call Failed

```python
result = await executor.execute_tool(...)

if not result.success:
    error = result.error
    # Handle error appropriately
    logger.error(f"Tool failed: {error}")
```

#### Validation Issues

```python
validation_result = await executor.execute_tool("code_architect_validate", ...)

if not validation_result.result["valid"]:
    issues = validation_result.result["issues"]
    # Display issues to user
    # Request fixes from Architect
```

### Retry Logic

Code Architect client implements automatic retries:

```python
client = CodeArchitectClient(
    base_url="http://localhost:8000",
    max_retries=3  # Retry up to 3 times
)

# Automatic retry on timeout
try:
    result = await client.generate_code(...)
except ValueError as e:
    # Handle error after all retries failed
    logger.error(f"Code generation failed: {e}")
```

## Configuration Options

### Environment Variables

```bash
# Base URL of Code Architect service
CODE_ARCHITECT_BASE_URL=http://localhost:8000

# API key (if required)
CODE_ARCHITECT_API_KEY=your-api-key

# Enable/disable code generation
CODE_ARCHITECT_ENABLED=true

# Request timeout (seconds)
CODE_ARCHITECT_TIMEOUT=30

# Maximum retries
CODE_ARCHITECT_MAX_RETRIES=3
```

### Programmatic Configuration

```python
from knowledge.code_architect_adapter import get_code_architect_adapter

adapter = get_code_architect_adapter(
    base_url="http://custom-host:9000",
    api_key="your-api-key",
    enabled=True
)
```

## Testing

### Unit Tests

```bash
# Run Code Architect integration tests
pytest tests/test_code_architect_integration.py -v

# Run specific test
pytest tests/test_code_architect_integration.py::TestCodeArchitectAdapter -v
```

### Integration Tests

```bash
# Run end-to-end workflow tests
pytest tests/test_e2e_codegen_workflow.py -v

# Run with mocked Code Architect
pytest tests/test_e2e_codegen_workflow.py --mock-external -v
```

### Mock Code Architect for Testing

```python
from unittest.mock import AsyncMock, patch
from knowledge.code_architect_adapter import CodeArchitectClient

# Mock the client
with patch.object(CodeArchitectClient, "__aenter__") as mock_enter:
    mock_client = AsyncMock()
    mock_client.generate_code = AsyncMock(
        return_value=CodeGenResult(
            success=True,
            changes=[...]
        )
    )
    mock_enter.return_value = mock_client
    
    # Test code generation
```

## Export to Documentation

### Generate DOCX Report

```python
from docx import Document
from intelligence.code_generation_support import CodeArtifact

# Create document
doc = Document()

# Add artifacts
for artifact in artifacts:
    doc.add_heading(artifact.file_path, level=2)
    doc.add_paragraph(artifact.description)
    doc.add_paragraph(artifact.to_markdown())

# Save
doc.save("code_generation_report.docx")
```

### Generate Markdown Report

```python
# Create markdown report
report = "# Code Generation Report\n\n"

for artifact in artifacts:
    report += f"## {artifact.file_path}\n\n"
    report += artifact.description + "\n\n"
    report += artifact.to_markdown() + "\n\n"

# Save
with open("code_generation_report.md", "w") as f:
    f.write(report)
```

## Monitoring and Logging

### Enable Debug Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("code_architect_adapter")
logger.setLevel(logging.DEBUG)
```

### Track Tool Calls

```python
from intelligence.llm_adapter_tools import ToolExecutor

executor = ToolExecutor(...)

# Each tool execution is logged
result = await executor.execute_tool("code_architect_generate", ...)
# Logs: Tool execution started, parameters, result, duration
```

## Troubleshooting

### Service Connection Issues

```bash
# Test Code Architect connectivity
curl http://localhost:8000/api/health
# Expected response: {"status": "ok"}
```

### Code Generation Fails

1. Check Code Architect logs
2. Verify project_id is correct
3. Ensure task description is clear and detailed
4. Check context parameters are valid

### Validation Fails

1. Review validation issues returned
2. Check project patterns in Code Architect
3. Request pattern update if needed
4. Regenerate with updated context

## Best Practices

1. **Always use dry_run mode first** - Review changes before applying
2. **Always validate generated code** - Check against patterns
3. **Always analyze impact** - Understand scope of changes
4. **Document decisions** - Record approvals and feedback
5. **Test generated code** - Use suggested tests
6. **Iterate as needed** - Regenerate with refined requirements

## Support and Issues

For issues with:

- **Code Architect service**: See code-architect-agent-platform/README.md
- **agent-platform integration**: Check this guide and test files
- **Specific code patterns**: Contribute to project pattern definitions

## Next Steps

- [See E2E Examples](E2E_EXAMPLES.md)
- [Run Integration Tests](tests/test_code_architect_integration.py)
- [Check E2E Workflow Tests](tests/test_e2e_codegen_workflow.py)
