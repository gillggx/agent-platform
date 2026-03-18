"""Routine Checks Router - Manage and execute scheduled routine checks"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import uuid4
from datetime import datetime
from enum import Enum

from app.db.base import get_db

routine_checks_router = APIRouter()

# ============================================================================
# Enums
# ============================================================================

class CheckStatus(str, Enum):
    """Status of a routine check"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"
    FAILED = "failed"


class CheckFrequency(str, Enum):
    """Execution frequency"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class ExecutionStatus(str, Enum):
    """Status of a single execution"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


# ============================================================================
# Schemas
# ============================================================================

class RoutineCheckRequest(BaseModel):
    """Request to create or update a routine check"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    check_type: str  # e.g., "database", "api", "file_system", "memory"
    frequency: CheckFrequency
    cron_expression: Optional[str] = None  # For custom frequency
    is_enabled: bool = True
    parameters: Dict[str, Any] = Field(default_factory=dict)
    alert_on_failure: bool = True
    max_retries: int = Field(3, ge=0, le=10)


class RoutineCheckResponse(BaseModel):
    """Complete routine check definition"""
    id: str
    name: str
    description: Optional[str]
    check_type: str
    frequency: CheckFrequency
    cron_expression: Optional[str]
    is_enabled: bool
    status: CheckStatus
    parameters: Dict[str, Any]
    alert_on_failure: bool
    max_retries: int
    last_executed_at: Optional[datetime]
    next_execution_at: Optional[datetime]
    last_result: Optional[Dict[str, Any]]
    execution_count: int
    failure_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoutineCheckListResponse(BaseModel):
    """Paginated list of routine checks"""
    total: int
    items: List[RoutineCheckResponse]
    page: int
    page_size: int


class ExecutionLogEntry(BaseModel):
    """Single execution result"""
    execution_id: str
    check_id: str
    status: ExecutionStatus
    started_at: datetime
    completed_at: Optional[datetime]
    duration_ms: Optional[float]
    error_message: Optional[str]
    result_data: Optional[Dict[str, Any]]


class ExecuteNowResponse(BaseModel):
    """Response from executing a check immediately"""
    execution_id: str
    check_id: str
    status: ExecutionStatus
    message: str


# ============================================================================
# In-Memory Storage
# ============================================================================

checks_db: Dict[str, Dict[str, Any]] = {}
execution_log_db: List[Dict[str, Any]] = []


def _seed_routine_checks():
    """Initialize sample routine checks"""
    if not checks_db:
        sample_checks = [
            {
                "id": "check_001",
                "name": "Database Health",
                "description": "Check database connectivity and performance",
                "check_type": "database",
                "frequency": "hourly",
                "is_enabled": True,
                "status": "active",
                "parameters": {
                    "max_query_time_ms": 5000,
                    "min_connections": 5,
                },
                "alert_on_failure": True,
                "max_retries": 3,
                "last_executed_at": datetime.now().isoformat(),
                "next_execution_at": datetime.now().isoformat(),
                "last_result": {"status": "healthy", "response_time_ms": 45},
                "execution_count": 168,
                "failure_count": 0,
            },
            {
                "id": "check_002",
                "name": "API Response Time",
                "description": "Monitor API endpoint response times",
                "check_type": "api",
                "frequency": "daily",
                "is_enabled": True,
                "status": "active",
                "parameters": {
                    "endpoint": "/api/v1/health",
                    "timeout_ms": 10000,
                },
                "alert_on_failure": True,
                "max_retries": 3,
                "last_executed_at": datetime.now().isoformat(),
                "next_execution_at": datetime.now().isoformat(),
                "last_result": {"status": "ok", "response_time_ms": 123},
                "execution_count": 42,
                "failure_count": 1,
            },
            {
                "id": "check_003",
                "name": "Disk Space",
                "description": "Monitor available disk space",
                "check_type": "file_system",
                "frequency": "daily",
                "is_enabled": True,
                "status": "active",
                "parameters": {
                    "warn_threshold_percent": 80,
                    "critical_threshold_percent": 95,
                },
                "alert_on_failure": True,
                "max_retries": 1,
                "last_executed_at": datetime.now().isoformat(),
                "next_execution_at": datetime.now().isoformat(),
                "last_result": {"available_percent": 65, "status": "healthy"},
                "execution_count": 42,
                "failure_count": 0,
            },
        ]
        for check in sample_checks:
            checks_db[check["id"]] = check


_seed_routine_checks()


# ============================================================================
# Endpoints
# ============================================================================

@routine_checks_router.post("", response_model=RoutineCheckResponse)
async def create_routine_check(
    request: RoutineCheckRequest,
    db: AsyncSession = Depends(get_db),
) -> RoutineCheckResponse:
    """Create a new routine check"""
    check_id = str(uuid4())
    
    check = {
        "id": check_id,
        "name": request.name,
        "description": request.description,
        "check_type": request.check_type,
        "frequency": request.frequency.value,
        "cron_expression": request.cron_expression,
        "is_enabled": request.is_enabled,
        "status": "active" if request.is_enabled else "inactive",
        "parameters": request.parameters,
        "alert_on_failure": request.alert_on_failure,
        "max_retries": request.max_retries,
        "last_executed_at": None,
        "next_execution_at": datetime.now().isoformat(),
        "last_result": None,
        "execution_count": 0,
        "failure_count": 0,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    
    checks_db[check_id] = check
    
    return _to_response(check)


@routine_checks_router.get("", response_model=RoutineCheckListResponse)
async def list_routine_checks(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status_filter: Optional[CheckStatus] = None,
    enabled_only: bool = False,
    db: AsyncSession = Depends(get_db),
) -> RoutineCheckListResponse:
    """
    List all routine checks with pagination and filtering
    
    - **page**: Page number
    - **page_size**: Items per page
    - **status_filter**: Filter by status (active, inactive, etc.)
    - **enabled_only**: Only show enabled checks
    """
    checks = list(checks_db.values())
    
    if enabled_only:
        checks = [c for c in checks if c["is_enabled"]]
    
    if status_filter:
        checks = [c for c in checks if c["status"] == status_filter.value]
    
    # Pagination
    total = len(checks)
    start = (page - 1) * page_size
    end = start + page_size
    items = checks[start:end]
    
    return RoutineCheckListResponse(
        total=total,
        items=[_to_response(c) for c in items],
        page=page,
        page_size=page_size,
    )


@routine_checks_router.get("/{check_id}", response_model=RoutineCheckResponse)
async def get_routine_check(
    check_id: str,
    db: AsyncSession = Depends(get_db),
) -> RoutineCheckResponse:
    """Get routine check details by ID"""
    check = checks_db.get(check_id)
    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Routine check '{check_id}' not found",
        )
    
    return _to_response(check)


@routine_checks_router.put("/{check_id}", response_model=RoutineCheckResponse)
async def update_routine_check(
    check_id: str,
    request: RoutineCheckRequest,
    db: AsyncSession = Depends(get_db),
) -> RoutineCheckResponse:
    """Update routine check configuration"""
    check = checks_db.get(check_id)
    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Routine check '{check_id}' not found",
        )
    
    # Update fields
    check["name"] = request.name
    check["description"] = request.description
    check["check_type"] = request.check_type
    check["frequency"] = request.frequency.value
    check["cron_expression"] = request.cron_expression
    check["is_enabled"] = request.is_enabled
    check["status"] = "active" if request.is_enabled else "inactive"
    check["parameters"] = request.parameters
    check["alert_on_failure"] = request.alert_on_failure
    check["max_retries"] = request.max_retries
    check["updated_at"] = datetime.now()
    
    return _to_response(check)


@routine_checks_router.delete("/{check_id}", response_model=Dict[str, Any])
async def delete_routine_check(
    check_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Delete routine check"""
    check = checks_db.get(check_id)
    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Routine check '{check_id}' not found",
        )
    
    name = check["name"]
    del checks_db[check_id]
    
    return {"message": f"Routine check '{name}' deleted"}


@routine_checks_router.post("/{check_id}/execute", response_model=ExecuteNowResponse)
async def execute_routine_check_now(
    check_id: str,
    db: AsyncSession = Depends(get_db),
) -> ExecuteNowResponse:
    """Execute a routine check immediately"""
    check = checks_db.get(check_id)
    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Routine check '{check_id}' not found",
        )
    
    if not check["is_enabled"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Routine check '{check_id}' is disabled",
        )
    
    # Simulate execution
    execution_id = str(uuid4())
    import time
    start_time = time.time()
    
    # Mock check execution
    success = check["check_type"] != "unreliable"  # Simulate occasional failures
    status_result = ExecutionStatus.SUCCESS if success else ExecutionStatus.FAILED
    
    duration_ms = (time.time() - start_time) * 1000
    
    # Update check metadata
    check["last_executed_at"] = datetime.now().isoformat()
    check["execution_count"] = check.get("execution_count", 0) + 1
    if not success:
        check["failure_count"] = check.get("failure_count", 0) + 1
        check["status"] = "failed"
    
    check["last_result"] = {
        "status": "healthy" if success else "unhealthy",
        "check_type": check["check_type"],
        "timestamp": datetime.now().isoformat(),
    }
    
    # Log execution
    execution_log_db.append({
        "execution_id": execution_id,
        "check_id": check_id,
        "status": status_result.value,
        "started_at": datetime.now().isoformat(),
        "completed_at": datetime.now().isoformat(),
        "duration_ms": duration_ms,
        "error_message": None if success else "Check failed",
        "result_data": check["last_result"],
    })
    
    return ExecuteNowResponse(
        execution_id=execution_id,
        check_id=check_id,
        status=status_result,
        message=f"Check execution {'succeeded' if success else 'failed'}",
    )


# ============================================================================
# Helper Functions
# ============================================================================

def _to_response(check: Dict[str, Any]) -> RoutineCheckResponse:
    """Convert check dict to response model"""
    return RoutineCheckResponse(
        id=check["id"],
        name=check["name"],
        description=check.get("description"),
        check_type=check["check_type"],
        frequency=CheckFrequency(check["frequency"]),
        cron_expression=check.get("cron_expression"),
        is_enabled=check["is_enabled"],
        status=CheckStatus(check.get("status", "inactive")),
        parameters=check["parameters"],
        alert_on_failure=check["alert_on_failure"],
        max_retries=check["max_retries"],
        last_executed_at=check.get("last_executed_at"),
        next_execution_at=check.get("next_execution_at"),
        last_result=check.get("last_result"),
        execution_count=check.get("execution_count", 0),
        failure_count=check.get("failure_count", 0),
        created_at=check.get("created_at", datetime.now()),
        updated_at=check.get("updated_at", datetime.now()),
    )
