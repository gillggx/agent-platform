"""Generic Tools Router - List, search, execute, and manage tools with categories and favorites"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import uuid4
from datetime import datetime

from app.db.base import get_db

tools_router = APIRouter()

# ============================================================================
# Schemas
# ============================================================================

class ToolExecutionRequest(BaseModel):
    """Request to execute a tool with parameters"""
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    metadata: Optional[Dict[str, Any]] = None


class ToolExecutionResponse(BaseModel):
    """Result of tool execution"""
    execution_id: str
    tool_id: str
    status: str  # success, error, pending
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: float
    executed_at: datetime


class ToolResponse(BaseModel):
    """Complete tool definition"""
    id: str
    name: str
    description: str
    category: str
    version: str
    enabled: bool
    parameters: Dict[str, Any]
    output_schema: Dict[str, Any]
    is_favorite: bool = False
    execution_count: int = 0
    last_executed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ToolListResponse(BaseModel):
    """Paginated list of tools"""
    total: int
    items: List[ToolResponse]
    page: int
    page_size: int


class ToolCategoryResponse(BaseModel):
    """Tool category with metadata"""
    name: str
    description: str
    tool_count: int
    is_visible: bool


class ToolFavoriteRequest(BaseModel):
    """Add/remove favorite tool"""
    tool_id: str
    is_favorite: bool


class ToolSearchRequest(BaseModel):
    """Search tools by criteria"""
    query: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    enabled_only: bool = True


# ============================================================================
# In-Memory Storage (for MVP - can be migrated to DB)
# ============================================================================

# Simulated tool registry
tools_db: Dict[str, Dict[str, Any]] = {}

# Tool categories
categories_db: Dict[str, Dict[str, Any]] = {
    "data": {"description": "Data manipulation tools", "is_visible": True},
    "visualization": {"description": "Data visualization tools", "is_visible": True},
    "analysis": {"description": "Analysis and reporting tools", "is_visible": True},
    "integration": {"description": "Integration tools", "is_visible": True},
    "automation": {"description": "Automation tools", "is_visible": True},
}

# User favorites
favorites_db: Dict[str, set] = {}  # org_id -> set of tool_ids

# Execution history
execution_history_db: List[Dict[str, Any]] = []

# Sample tools

def _seed_tools():
    """Initialize sample tools"""
    if not tools_db:
        sample_tools = [
            {
                "id": "tool_001",
                "name": "CSV Importer",
                "description": "Import and parse CSV files",
                "category": "data",
                "version": "1.0.0",
                "enabled": True,
                "parameters": {
                    "file_path": {"type": "string", "required": True},
                    "encoding": {"type": "string", "default": "utf-8"},
                },
                "output_schema": {"rows": "array", "columns": "array"},
                "execution_count": 42,
                "last_executed_at": datetime.now().isoformat(),
            },
            {
                "id": "tool_002",
                "name": "JSON Validator",
                "description": "Validate and format JSON data",
                "category": "data",
                "version": "1.0.0",
                "enabled": True,
                "parameters": {
                    "json_string": {"type": "string", "required": True},
                },
                "output_schema": {"valid": "boolean", "formatted": "string"},
                "execution_count": 156,
                "last_executed_at": datetime.now().isoformat(),
            },
            {
                "id": "tool_003",
                "name": "Time Series Chart",
                "description": "Generate time series visualization",
                "category": "visualization",
                "version": "2.0.0",
                "enabled": True,
                "parameters": {
                    "data": {"type": "array", "required": True},
                    "title": {"type": "string", "required": False},
                    "x_label": {"type": "string"},
                    "y_label": {"type": "string"},
                },
                "output_schema": {"chart_url": "string", "chart_data": "object"},
                "execution_count": 89,
                "last_executed_at": datetime.now().isoformat(),
            },
            {
                "id": "tool_004",
                "name": "Scatter Plot Generator",
                "description": "Generate scatter plot visualizations",
                "category": "visualization",
                "version": "1.5.0",
                "enabled": True,
                "parameters": {
                    "x_data": {"type": "array", "required": True},
                    "y_data": {"type": "array", "required": True},
                },
                "output_schema": {"plot_url": "string"},
                "execution_count": 34,
                "last_executed_at": None,
            },
            {
                "id": "tool_005",
                "name": "Statistical Summary",
                "description": "Calculate statistical metrics",
                "category": "analysis",
                "version": "1.0.0",
                "enabled": True,
                "parameters": {
                    "data": {"type": "array", "required": True},
                    "include_percentiles": {"type": "boolean", "default": True},
                },
                "output_schema": {"mean": "number", "median": "number", "std": "number"},
                "execution_count": 203,
                "last_executed_at": datetime.now().isoformat(),
            },
        ]
        for tool in sample_tools:
            tools_db[tool["id"]] = tool


# ============================================================================
# Endpoints
# ============================================================================

@tools_router.get("", response_model=ToolListResponse)
async def list_tools(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    category: Optional[str] = None,
    enabled_only: bool = True,
    db: AsyncSession = Depends(get_db),
) -> ToolListResponse:
    """
    List all tools with pagination and filtering
    
    - **page**: Page number (1-indexed)
    - **page_size**: Items per page
    - **category**: Filter by category
    - **enabled_only**: Only show enabled tools
    """
    # Filter tools
    filtered = list(tools_db.values())
    
    if enabled_only:
        filtered = [t for t in filtered if t["enabled"]]
    
    if category:
        filtered = [t for t in filtered if t["category"] == category]
    
    # Pagination
    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    items = filtered[start:end]
    
    return ToolListResponse(
        total=total,
        items=[
            ToolResponse(
                id=t["id"],
                name=t["name"],
                description=t["description"],
                category=t["category"],
                version=t["version"],
                enabled=t["enabled"],
                parameters=t["parameters"],
                output_schema=t["output_schema"],
                execution_count=t.get("execution_count", 0),
                last_executed_at=t.get("last_executed_at"),
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            for t in items
        ],
        page=page,
        page_size=page_size,
    )


@tools_router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(
    tool_id: str,
    db: AsyncSession = Depends(get_db),
) -> ToolResponse:
    """Get tool details by ID"""
    tool = tools_db.get(tool_id)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{tool_id}' not found",
        )
    
    return ToolResponse(
        id=tool["id"],
        name=tool["name"],
        description=tool["description"],
        category=tool["category"],
        version=tool["version"],
        enabled=tool["enabled"],
        parameters=tool["parameters"],
        output_schema=tool["output_schema"],
        execution_count=tool.get("execution_count", 0),
        last_executed_at=tool.get("last_executed_at"),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@tools_router.post("/{tool_id}/execute", response_model=ToolExecutionResponse)
async def execute_tool(
    tool_id: str,
    request: ToolExecutionRequest,
    db: AsyncSession = Depends(get_db),
) -> ToolExecutionResponse:
    """Execute a tool with parameters"""
    tool = tools_db.get(tool_id)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{tool_id}' not found",
        )
    
    if not tool["enabled"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Tool '{tool_id}' is disabled",
        )
    
    # Simulate tool execution
    execution_id = str(uuid4())
    import time
    start_time = time.time()
    
    # Mock execution (in production, would call actual tool)
    result = {
        "tool_name": tool["name"],
        "parameters_received": request.parameters,
        "status": "executed",
    }
    
    execution_time_ms = (time.time() - start_time) * 1000
    
    # Update execution count
    tool["execution_count"] = tool.get("execution_count", 0) + 1
    tool["last_executed_at"] = datetime.now().isoformat()
    
    # Log execution
    execution_history_db.append({
        "execution_id": execution_id,
        "tool_id": tool_id,
        "timestamp": datetime.now().isoformat(),
        "parameters": request.parameters,
    })
    
    return ToolExecutionResponse(
        execution_id=execution_id,
        tool_id=tool_id,
        status="success",
        result=result,
        execution_time_ms=execution_time_ms,
        executed_at=datetime.now(),
    )


@tools_router.get("/categories/list", response_model=List[ToolCategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)) -> List[ToolCategoryResponse]:
    """List all tool categories"""
    result = []
    for cat_name, cat_info in categories_db.items():
        tool_count = sum(1 for t in tools_db.values() if t["category"] == cat_name)
        result.append(
            ToolCategoryResponse(
                name=cat_name,
                description=cat_info["description"],
                tool_count=tool_count,
                is_visible=cat_info["is_visible"],
            )
        )
    return result


@tools_router.get("/search/query", response_model=ToolListResponse)
async def search_tools(
    query: Optional[str] = Query(None),
    category: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> ToolListResponse:
    """
    Search tools by name, description, or category
    
    - **query**: Search query (searches name and description)
    - **category**: Filter by category
    """
    results = list(tools_db.values())
    
    if query:
        q_lower = query.lower()
        results = [
            t for t in results
            if q_lower in t["name"].lower() or q_lower in t["description"].lower()
        ]
    
    if category:
        results = [t for t in results if t["category"] == category]
    
    # Pagination
    total = len(results)
    start = (page - 1) * page_size
    end = start + page_size
    items = results[start:end]
    
    return ToolListResponse(
        total=total,
        items=[
            ToolResponse(
                id=t["id"],
                name=t["name"],
                description=t["description"],
                category=t["category"],
                version=t["version"],
                enabled=t["enabled"],
                parameters=t["parameters"],
                output_schema=t["output_schema"],
                execution_count=t.get("execution_count", 0),
                last_executed_at=t.get("last_executed_at"),
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            for t in items
        ],
        page=page,
        page_size=page_size,
    )


@tools_router.post("/favorites/add", response_model=Dict[str, Any])
async def add_favorite(
    request: ToolFavoriteRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Add tool to favorites"""
    tool = tools_db.get(request.tool_id)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{request.tool_id}' not found",
        )
    
    org_id = "default_org"  # In production, get from auth context
    if org_id not in favorites_db:
        favorites_db[org_id] = set()
    
    if request.is_favorite:
        favorites_db[org_id].add(request.tool_id)
    else:
        favorites_db[org_id].discard(request.tool_id)
    
    return {
        "tool_id": request.tool_id,
        "is_favorite": request.is_favorite,
        "message": "Favorite status updated",
    }


@tools_router.get("/favorites/list", response_model=ToolListResponse)
async def list_favorites(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> ToolListResponse:
    """List all favorite tools for current user"""
    org_id = "default_org"  # In production, get from auth context
    fav_ids = favorites_db.get(org_id, set())
    
    favorites = [tools_db[tid] for tid in fav_ids if tid in tools_db]
    
    # Pagination
    total = len(favorites)
    start = (page - 1) * page_size
    end = start + page_size
    items = favorites[start:end]
    
    return ToolListResponse(
        total=total,
        items=[
            ToolResponse(
                id=t["id"],
                name=t["name"],
                description=t["description"],
                category=t["category"],
                version=t["version"],
                enabled=t["enabled"],
                parameters=t["parameters"],
                output_schema=t["output_schema"],
                is_favorite=True,
                execution_count=t.get("execution_count", 0),
                last_executed_at=t.get("last_executed_at"),
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            for t in items
        ],
        page=page,
        page_size=page_size,
    )


@tools_router.get("/categories/{category}/list", response_model=ToolListResponse)
async def list_tools_by_category(
    category: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> ToolListResponse:
    """List all tools in a specific category"""
    if category not in categories_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category '{category}' not found",
        )
    
    tools_in_category = [
        t for t in tools_db.values()
        if t["category"] == category
    ]
    
    # Pagination
    total = len(tools_in_category)
    start = (page - 1) * page_size
    end = start + page_size
    items = tools_in_category[start:end]
    
    return ToolListResponse(
        total=total,
        items=[
            ToolResponse(
                id=t["id"],
                name=t["name"],
                description=t["description"],
                category=t["category"],
                version=t["version"],
                enabled=t["enabled"],
                parameters=t["parameters"],
                output_schema=t["output_schema"],
                execution_count=t.get("execution_count", 0),
                last_executed_at=t.get("last_executed_at"),
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            for t in items
        ],
        page=page,
        page_size=page_size,
    )


@tools_router.post("/execution-history/query", response_model=List[Dict[str, Any]])
async def get_execution_history(
    tool_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get tool execution history"""
    history = execution_history_db
    
    if tool_id:
        history = [e for e in history if e["tool_id"] == tool_id]
    
    # Return most recent first, limited
    return sorted(
        history[-limit:],
        key=lambda x: x["timestamp"],
        reverse=True,
    )


@tools_router.get("/usage/stats", response_model=Dict[str, Any])
async def get_usage_stats(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Get tool usage statistics"""
    total_tools = len(tools_db)
    enabled_tools = sum(1 for t in tools_db.values() if t["enabled"])
    total_executions = sum(t.get("execution_count", 0) for t in tools_db.values())
    
    # Top 5 most used tools
    top_tools = sorted(
        tools_db.values(),
        key=lambda t: t.get("execution_count", 0),
        reverse=True,
    )[:5]
    
    return {
        "total_tools": total_tools,
        "enabled_tools": enabled_tools,
        "total_executions": total_executions,
        "average_executions_per_tool": total_executions / total_tools if total_tools > 0 else 0,
        "top_tools": [
            {
                "id": t["id"],
                "name": t["name"],
                "execution_count": t.get("execution_count", 0),
            }
            for t in top_tools
        ],
    }

_seed_tools()
