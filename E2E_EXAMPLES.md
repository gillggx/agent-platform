# End-to-End Code Generation Examples

This document provides complete, runnable examples of using Code Architect within agent-platform.

## Example 1: FastAPI User Management API

### Scenario

A PM has a requirement to create a user management API with CRUD operations. The Architect Agent uses Code Architect to generate the implementation, which is then validated and approved through the agent team workflow.

### Step 1: PM Defines Requirements

```python
from intelligence.agent_conversation import Message, MessageType

pm_requirement = Message(
    from_role="pm",
    to_roles=["architect"],
    message_type=MessageType.REQUEST,
    content="""
    Create a FastAPI application with user management endpoints:
    - List all users (GET /users)
    - Get user by ID (GET /users/{id})
    - Create new user (POST /users)
    - Update user (PUT /users/{id})
    - Delete user (DELETE /users/{id})
    
    Requirements:
    - Use Pydantic for request/response validation
    - Include proper error handling
    - Add docstrings to all endpoints
    - Use SQLAlchemy for database model
    """,
    context={
        "project_id": "user-api-project",
        "framework": "FastAPI",
        "database": "SQLAlchemy",
        "api_version": "1.0",
    }
)
```

### Step 2: Architect Generates Code

```python
from intelligence.llm_adapter_tools import ToolExecutor
from knowledge.code_architect_adapter import get_code_architect_adapter

# Setup
adapter = get_code_architect_adapter()
executor = ToolExecutor(code_architect_adapter=adapter)

# Generate code
generation_result = await executor.execute_tool(
    "code_architect_generate",
    {
        "task": """
        Create a complete FastAPI user management API with:
        - Pydantic UserSchema for request/response validation
        - SQLAlchemy User model for database
        - CRUD endpoints (list, get, create, update, delete)
        - Proper error handling with HTTPException
        - Docstrings for all functions
        - Type hints throughout
        """,
        "project_id": "user-api-project",
        "context": {
            "framework": "FastAPI",
            "database": "SQLAlchemy",
            "validation": "Pydantic",
            "endpoints": ["list", "get", "create", "update", "delete"]
        },
        "mode": "dry_run"  # Review first before applying
    }
)

# Result
if generation_result.success:
    print("Generated files:")
    for change in generation_result.result["changes"]:
        print(f"  - {change['action']}: {change['file']}")
        
    # Display generated code
    for change in generation_result.result["changes"]:
        print(f"\n### {change['file']}")
        print(change['content'])
```

**Generated Code Example:**

```python
# src/models.py
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# src/schemas.py
from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserCreate(BaseModel):
    name: str
    email: EmailStr

class UserUpdate(BaseModel):
    name: str = None
    email: EmailStr = None

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# src/routes/users.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from ..models import User
from ..schemas import UserCreate, UserUpdate, UserResponse
from typing import List

router = APIRouter(prefix="/users", tags=["users"])

def get_db():
    # Database session dependency
    pass

@router.get("", response_model=List[UserResponse])
async def list_users(db: Session = Depends(get_db)):
    """Get all users"""
    return db.query(User).all()

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get user by ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("", response_model=UserResponse)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user"""
    db_user = User(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user: UserUpdate,
    db: Session = Depends(get_db)
):
    """Update user"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = user.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user

@router.delete("/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    """Delete user"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(db_user)
    db.commit()
    return {"message": "User deleted successfully"}
```

### Step 3: QA Validates Generated Code

```python
# Validate generated code
validation_result = await executor.execute_tool(
    "code_architect_validate",
    {
        "changes": generation_result.result["changes"],
        "project_id": "user-api-project",
        "context": {
            "framework": "FastAPI",
            "standards": ["pep8", "type_hints", "docstrings"]
        }
    }
)

# Display validation results
print("Validation Results:")
print(f"Valid: {validation_result.result['valid']}")
print(f"Patterns Matched: {validation_result.result['patterns_matched']}")

if validation_result.result['issues']:
    print("\nIssues:")
    for issue in validation_result.result['issues']:
        severity = issue['severity'].upper()
        print(f"  [{severity}] {issue['message']}")
        if issue.get('file'):
            print(f"    at {issue['file']}:{issue.get('line', '?')}")
        if issue.get('suggestion'):
            print(f"    Suggestion: {issue['suggestion']}")

if validation_result.result['improvements']:
    print("\nSuggested Improvements:")
    for improvement in validation_result.result['improvements']:
        print(f"  - {improvement}")
```

**Sample Output:**

```
Validation Results:
Valid: True
Patterns Matched: ['fastapi_route', 'pydantic_schema', 'sqlalchemy_model', 'error_handling']

Patterns:
  ✓ FastAPI route definition
  ✓ Pydantic model validation
  ✓ SQLAlchemy ORM model
  ✓ HTTP error handling

Suggested Improvements:
  - Consider adding request validation middleware
  - Add API documentation with examples
  - Consider adding caching for list endpoint
```

### Step 4: Architect Analyzes Impact

```python
# Analyze impact
impact_result = await executor.execute_tool(
    "code_architect_impact",
    {
        "changes": generation_result.result["changes"],
        "project_id": "user-api-project"
    }
)

# Display impact
print("Impact Analysis:")
print(f"Impact Score: {impact_result.result['impact_score']:.2%}")
print(f"Risk Level: {'🟢 LOW' if impact_result.result['impact_score'] < 0.3 else '🟡 MEDIUM' if impact_result.result['impact_score'] < 0.7 else '🔴 HIGH'}")
print(f"\nAffected Modules: {', '.join(impact_result.result['affected_modules'])}")

if impact_result.result['breaking_changes']:
    print(f"\nBreaking Changes:")
    for change in impact_result.result['breaking_changes']:
        print(f"  ⚠️  {change}")

print(f"\nTest Coverage Impact: {impact_result.result['test_coverage_impact']}")
print(f"Performance Impact: {impact_result.result['performance_impact']}")
print(f"\nSummary: {impact_result.result['summary']}")
```

**Sample Output:**

```
Impact Analysis:
Impact Score: 35%
Risk Level: 🟢 LOW

Affected Modules: api/routes, models, schemas
Dependencies: fastapi, sqlalchemy, pydantic

Test Coverage Impact: LOW
Performance Impact: NONE

Summary: New route addition has minimal impact on existing code.
Backward compatible with all existing endpoints.
Ready for production deployment.
```

### Step 5: PM Reviews and Approves

```python
from intelligence.agent_conversation import AgentConversation, ConversationContext

# Create conversation context
context = ConversationContext(
    conversation_id="user-api-flow",
    workflow="code_generation_with_review"
)

# PM sends requirement
context.add_message(pm_requirement)

# Architect responds with generated code
architect_response = Message(
    from_role="architect",
    to_roles=["qa", "pm"],
    message_type=MessageType.RESPONSE,
    content=f"""
    Generated user management API:
    - 5 endpoints (list, get, create, update, delete)
    - Pydantic schemas for request/response validation
    - SQLAlchemy ORM model with timestamps
    - Proper error handling with meaningful messages
    - Full type hints and docstrings
    
    Patterns used: {', '.join(generation_result.result['patterns_used'])}
    Suggested tests: {', '.join(generation_result.result['tests_suggested'])}
    """
)
context.add_message(architect_response)

# QA validates
qa_response = Message(
    from_role="qa",
    to_roles=["pm", "director"],
    message_type=MessageType.FEEDBACK,
    content="✅ Code validation PASSED. All patterns matched. Zero critical issues."
)
context.add_message(qa_response)

# PM approves
pm_approval = Message(
    from_role="pm",
    to_roles=["director"],
    message_type=MessageType.FEEDBACK,
    content="✅ Approved. Implementation meets all requirements perfectly."
)
context.add_message(pm_approval)

# Director makes final decision
director_message = Message(
    from_role="director",
    to_roles=["architect"],
    message_type=MessageType.DECISION,
    content="✅ APPROVED FOR DEPLOYMENT. Ready to merge to main."
)
context.add_message(director_message)
```

### Step 6: Export as Artifacts

```python
from intelligence.code_generation_support import CodeArtifact, CodeLanguage

# Create artifacts from generated code
artifacts = []

for change in generation_result.result["changes"]:
    artifact = CodeArtifact(
        artifact_id=f"artifact-{change['file'].replace('/', '-')}",
        file_path=change['file'],
        language=CodeLanguage.PYTHON,
        content=change['content'],
        description=f"User API - {change['file']} (APPROVED)",
        metadata={
            "status": "approved",
            "validated": True,
            "approved_by": "director",
            "approval_timestamp": datetime.utcnow().isoformat(),
            "impact_score": impact_result.result['impact_score'],
            "patterns": generation_result.result['patterns_used']
        }
    )
    artifacts.append(artifact)

# Export to markdown
import os
os.makedirs("artifacts", exist_ok=True)

for artifact in artifacts:
    filepath = f"artifacts/{artifact.file_path.replace('/', '_')}.md"
    with open(filepath, "w") as f:
        f.write(f"# {artifact.file_path}\n\n")
        f.write(f"{artifact.description}\n\n")
        f.write(artifact.to_markdown())
    print(f"Saved: {filepath}")
```

---

## Example 2: Database Schema Generation

### Scenario

Generate a database schema for a product e-commerce application.

```python
# PM requirement
schema_requirement = """
Generate database schema for e-commerce platform:
- Products table: id, name, description, price, stock, created_at, updated_at
- Categories table: id, name, description
- Product-Category relationship (many-to-many)
- Orders table: id, user_id, order_date, status, total
- Order Items table: id, order_id, product_id, quantity, price
"""

# Architect generates
schema_result = await executor.execute_tool(
    "code_architect_generate",
    {
        "task": schema_requirement,
        "project_id": "ecommerce-platform",
        "context": {
            "database": "PostgreSQL",
            "orm": "SQLAlchemy",
            "migrations": "Alembic"
        }
    }
)

# Result: Generated models.py with all tables, relationships, and constraints
```

---

## Example 3: Testing Code Generation

### Mocking Code Architect for Development

```python
from unittest.mock import AsyncMock, patch
from knowledge.code_architect_adapter import CodeArchitectClient, CodeGenResult, FileChange

async def test_code_generation_with_mock():
    """Test code generation with mocked Code Architect"""
    
    with patch.object(CodeArchitectClient, "__aenter__") as mock_enter:
        mock_client = AsyncMock()
        
        # Define mock response
        mock_client.generate_code = AsyncMock(
            return_value=CodeGenResult(
                success=True,
                changes=[
                    FileChange(
                        file="test.py",
                        action="create",
                        content="# Test code"
                    )
                ],
                explanation="Generated test code",
                patterns_used=["test_pattern"],
                tests_suggested=["test_all"]
            )
        )
        
        mock_enter.return_value = mock_client
        
        # Execute
        adapter = get_code_architect_adapter()
        result = await executor.execute_tool("code_architect_generate", {...})
        
        # Assert
        assert result.success
        assert len(result.result["changes"]) == 1

# Run test
asyncio.run(test_code_generation_with_mock())
```

---

## Example 4: CI/CD Integration

### Automated Code Generation in Pipeline

```python
# .github/workflows/codegen.yml
name: Code Generation

on:
  pull_request:
    paths:
      - ".codegen/*"

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run Code Generation
        run: |
          python -m agent_platform.codegen \
            --requirement ".codegen/requirement.txt" \
            --project-id ${{ github.event.pull_request.head.ref }} \
            --output "generated/"
      
      - name: Validate Generated Code
        run: |
          python -m agent_platform.validate \
            --files "generated/*" \
            --project-id ${{ github.event.pull_request.head.ref }}
      
      - name: Create Comment with Results
        uses: actions/github-script@v6
        with:
          script: |
            // Post generation results as PR comment
```

---

## Example 5: Interactive Code Generation

### User-Driven Iteration

```python
# Interactive mode
async def interactive_code_generation():
    adapter = get_code_architect_adapter()
    executor = ToolExecutor(code_architect_adapter=adapter)
    
    while True:
        # Get user requirement
        requirement = input("Enter requirement (or 'done'): ")
        if requirement == "done":
            break
        
        # Generate
        result = await executor.execute_tool(
            "code_architect_generate",
            {
                "task": requirement,
                "project_id": "interactive-project",
                "mode": "dry_run"
            }
        )
        
        # Show results
        if result.success:
            for change in result.result["changes"]:
                print(f"\n{'='*60}")
                print(f"File: {change['file']}")
                print(f"Action: {change['action']}")
                print(f"Content:\n{change['content']}")
            
            # Ask for approval
            approve = input("\nApply these changes? (y/n): ")
            if approve.lower() == "y":
                # Apply changes
                pass
        else:
            print(f"Error: {result.error}")

# Run interactive
asyncio.run(interactive_code_generation())
```

---

## Quick Reference

### Tool Parameters

| Tool | Key Parameters |
|------|---|
| **generate** | task, project_id, context, mode |
| **validate** | changes, project_id, context |
| **impact** | changes, project_id, context |

### Response Fields

| Field | Type | Description |
|-------|------|---|
| **success** | bool | Whether operation succeeded |
| **changes** | array | File changes (file, action, content) |
| **valid** | bool | Whether validation passed |
| **issues** | array | Validation issues found |
| **impact_score** | float | Impact severity (0.0-1.0) |
| **patterns_matched** | array | Matched project patterns |

### Common Workflow

1. **Dry Run** → Review → **Validate** → **Analyze Impact** → **Approve** → **Apply**

2. **Iteration Loop**: Require ment → Generate → Validate → Feedback → Refine → Regenerate

---

## Troubleshooting Examples

### Handle Service Unavailable

```python
try:
    result = await executor.execute_tool(...)
except Exception as e:
    if "connection refused" in str(e):
        print("Code Architect service is down")
        # Fallback to manual implementation
    else:
        raise
```

### Handle Validation Failures

```python
validation = await executor.execute_tool("code_architect_validate", ...)

if not validation.result["valid"]:
    # Request regeneration with feedback
    new_requirement = f"""
    Previous code had issues:
    {validation.result['issues']}
    
    Please fix and regenerate.
    """
```

---

For more details, see [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md).
