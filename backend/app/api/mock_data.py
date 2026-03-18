"""Mock Data Router - Create, manage, and generate mock data for testing and development"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import uuid4
from datetime import datetime
from enum import Enum

from app.db.base import get_db

mock_data_router = APIRouter()

# ============================================================================
# Enums
# ============================================================================

class DataType(str, Enum):
    """Type of mock data"""
    USERS = "users"
    PRODUCTS = "products"
    ORDERS = "orders"
    TRANSACTIONS = "transactions"
    EVENTS = "events"
    DOCUMENTS = "documents"
    CUSTOM = "custom"


class GenerationStrategy(str, Enum):
    """How to generate mock data"""
    RANDOM = "random"
    SEQUENTIAL = "sequential"
    TEMPLATE = "template"
    FAKER = "faker"


# ============================================================================
# Schemas
# ============================================================================

class MockDataFieldConfig(BaseModel):
    """Configuration for a single field"""
    name: str
    type: str  # string, number, date, email, phone, uuid, etc.
    required: bool = True
    faker_type: Optional[str] = None  # e.g., "name", "email", "phone_number"


class MockDataRequest(BaseModel):
    """Request to create mock data"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    data_type: DataType
    generation_strategy: GenerationStrategy
    record_count: int = Field(10, ge=1, le=100000)
    fields: List[MockDataFieldConfig] = Field(default_factory=list)
    template_data: Optional[Dict[str, Any]] = None
    seed: Optional[int] = None  # For reproducible random data
    is_active: bool = True


class MockDataResponse(BaseModel):
    """Complete mock data definition"""
    id: str
    name: str
    description: Optional[str]
    data_type: DataType
    generation_strategy: GenerationStrategy
    record_count: int
    fields: List[MockDataFieldConfig]
    template_data: Optional[Dict[str, Any]]
    seed: Optional[int]
    is_active: bool
    status: str  # idle, generating, completed, failed
    generated_records: int
    generated_size_bytes: int
    last_generated_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MockDataListResponse(BaseModel):
    """Paginated list of mock data definitions"""
    total: int
    items: List[MockDataResponse]
    page: int
    page_size: int


class GenerateResponse(BaseModel):
    """Response from generation request"""
    dataset_id: str
    status: str
    generated_records: int
    generated_size_mb: float
    generation_time_ms: float
    message: str


class ExportResponse(BaseModel):
    """Response from export request"""
    dataset_id: str
    format: str  # json, csv, parquet
    file_size_mb: float
    download_url: str
    expires_in_hours: int


# ============================================================================
# In-Memory Storage
# ============================================================================

mock_data_db: Dict[str, Dict[str, Any]] = {}
generated_records_db: Dict[str, List[Dict[str, Any]]] = {}


def _seed_mock_data():
    """Initialize sample mock data definitions"""
    if not mock_data_db:
        sample_datasets = [
            {
                "id": "dataset_001",
                "name": "Sample Users",
                "description": "Generated user profiles for testing",
                "data_type": "users",
                "generation_strategy": "faker",
                "record_count": 1000,
                "fields": [
                    {"name": "id", "type": "uuid", "required": True, "faker_type": None},
                    {"name": "email", "type": "email", "required": True, "faker_type": "email"},
                    {"name": "name", "type": "string", "required": True, "faker_type": "name"},
                    {"name": "phone", "type": "phone", "required": False, "faker_type": "phone_number"},
                ],
                "template_data": None,
                "seed": 12345,
                "is_active": True,
                "status": "completed",
                "generated_records": 1000,
                "generated_size_bytes": 256000,
                "last_generated_at": datetime.now().isoformat(),
            },
            {
                "id": "dataset_002",
                "name": "Sample Products",
                "description": "E-commerce product catalog",
                "data_type": "products",
                "generation_strategy": "template",
                "record_count": 500,
                "fields": [
                    {"name": "sku", "type": "string", "required": True, "faker_type": None},
                    {"name": "name", "type": "string", "required": True, "faker_type": "word"},
                    {"name": "price", "type": "number", "required": True, "faker_type": None},
                    {"name": "category", "type": "string", "required": True, "faker_type": None},
                ],
                "template_data": {
                    "currency": "USD",
                    "categories": ["Electronics", "Clothing", "Books"],
                },
                "seed": None,
                "is_active": True,
                "status": "completed",
                "generated_records": 500,
                "generated_size_bytes": 128000,
                "last_generated_at": datetime.now().isoformat(),
            },
            {
                "id": "dataset_003",
                "name": "Sample Events",
                "description": "User interaction events",
                "data_type": "events",
                "generation_strategy": "random",
                "record_count": 5000,
                "fields": [
                    {"name": "event_id", "type": "uuid", "required": True, "faker_type": None},
                    {"name": "user_id", "type": "uuid", "required": True, "faker_type": None},
                    {"name": "event_type", "type": "string", "required": True, "faker_type": None},
                    {"name": "timestamp", "type": "date", "required": True, "faker_type": "date_time"},
                    {"name": "metadata", "type": "string", "required": False, "faker_type": None},
                ],
                "template_data": None,
                "seed": 67890,
                "is_active": True,
                "status": "idle",
                "generated_records": 0,
                "generated_size_bytes": 0,
                "last_generated_at": None,
            },
        ]
        for dataset in sample_datasets:
            mock_data_db[dataset["id"]] = dataset


_seed_mock_data()


# ============================================================================
# Endpoints
# ============================================================================

@mock_data_router.post("", response_model=MockDataResponse)
async def create_mock_data(
    request: MockDataRequest,
    db: AsyncSession = Depends(get_db),
) -> MockDataResponse:
    """Create a new mock data definition"""
    dataset_id = str(uuid4())
    
    dataset = {
        "id": dataset_id,
        "name": request.name,
        "description": request.description,
        "data_type": request.data_type.value,
        "generation_strategy": request.generation_strategy.value,
        "record_count": request.record_count,
        "fields": [field.dict() for field in request.fields],
        "template_data": request.template_data,
        "seed": request.seed,
        "is_active": request.is_active,
        "status": "idle",
        "generated_records": 0,
        "generated_size_bytes": 0,
        "last_generated_at": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    
    mock_data_db[dataset_id] = dataset
    
    return _to_response(dataset)


@mock_data_router.get("", response_model=MockDataListResponse)
async def list_mock_data(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    data_type: Optional[DataType] = None,
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
) -> MockDataListResponse:
    """
    List all mock data definitions with pagination and filtering
    
    - **page**: Page number
    - **page_size**: Items per page
    - **data_type**: Filter by data type
    - **active_only**: Only show active datasets
    """
    datasets = list(mock_data_db.values())
    
    if active_only:
        datasets = [d for d in datasets if d["is_active"]]
    
    if data_type:
        datasets = [d for d in datasets if d["data_type"] == data_type.value]
    
    # Pagination
    total = len(datasets)
    start = (page - 1) * page_size
    end = start + page_size
    items = datasets[start:end]
    
    return MockDataListResponse(
        total=total,
        items=[_to_response(d) for d in items],
        page=page,
        page_size=page_size,
    )


@mock_data_router.get("/{dataset_id}", response_model=MockDataResponse)
async def get_mock_data(
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
) -> MockDataResponse:
    """Get mock data definition by ID"""
    dataset = mock_data_db.get(dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mock data dataset '{dataset_id}' not found",
        )
    
    return _to_response(dataset)


@mock_data_router.put("/{dataset_id}", response_model=MockDataResponse)
async def update_mock_data(
    dataset_id: str,
    request: MockDataRequest,
    db: AsyncSession = Depends(get_db),
) -> MockDataResponse:
    """Update mock data definition"""
    dataset = mock_data_db.get(dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mock data dataset '{dataset_id}' not found",
        )
    
    # Update fields
    dataset["name"] = request.name
    dataset["description"] = request.description
    dataset["data_type"] = request.data_type.value
    dataset["generation_strategy"] = request.generation_strategy.value
    dataset["record_count"] = request.record_count
    dataset["fields"] = [field.dict() for field in request.fields]
    dataset["template_data"] = request.template_data
    dataset["seed"] = request.seed
    dataset["is_active"] = request.is_active
    dataset["updated_at"] = datetime.now()
    
    return _to_response(dataset)


@mock_data_router.delete("/{dataset_id}", response_model=Dict[str, Any])
async def delete_mock_data(
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Delete mock data definition"""
    dataset = mock_data_db.get(dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mock data dataset '{dataset_id}' not found",
        )
    
    name = dataset["name"]
    del mock_data_db[dataset_id]
    
    # Cleanup generated records
    if dataset_id in generated_records_db:
        del generated_records_db[dataset_id]
    
    return {"message": f"Mock data dataset '{name}' deleted"}


@mock_data_router.post("/{dataset_id}/generate", response_model=GenerateResponse)
async def generate_mock_data(
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
) -> GenerateResponse:
    """Generate mock data records based on definition"""
    dataset = mock_data_db.get(dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mock data dataset '{dataset_id}' not found",
        )
    
    import time
    start_time = time.time()
    
    # Update status
    dataset["status"] = "generating"
    
    # Simulate data generation
    generated_records = []
    for i in range(min(dataset["record_count"], 1000)):  # Limit for demo
        record = {
            "id": str(uuid4()),
            "_index": i,
        }
        
        # Add fields based on configuration
        for field in dataset["fields"]:
            if field["type"] == "uuid":
                record[field["name"]] = str(uuid4())
            elif field["type"] == "email":
                record[field["name"]] = f"user{i}@example.com"
            elif field["type"] == "number":
                record[field["name"]] = i * 10 + 100
            elif field["type"] == "date":
                record[field["name"]] = datetime.now().isoformat()
            else:
                record[field["name"]] = f"{field['name']}_value_{i}"
        
        generated_records.append(record)
    
    generation_time_ms = (time.time() - start_time) * 1000
    generated_size_bytes = len(str(generated_records).encode())
    
    # Store generated records
    generated_records_db[dataset_id] = generated_records
    
    # Update dataset metadata
    dataset["status"] = "completed"
    dataset["generated_records"] = len(generated_records)
    dataset["generated_size_bytes"] = generated_size_bytes
    dataset["last_generated_at"] = datetime.now().isoformat()
    dataset["updated_at"] = datetime.now()
    
    return GenerateResponse(
        dataset_id=dataset_id,
        status="completed",
        generated_records=len(generated_records),
        generated_size_mb=generated_size_bytes / (1024 * 1024),
        generation_time_ms=generation_time_ms,
        message=f"Generated {len(generated_records)} records successfully",
    )


@mock_data_router.get("/{dataset_id}/export", response_model=ExportResponse)
async def export_mock_data(
    dataset_id: str,
    format: str = Query("json", regex="^(json|csv|parquet)$"),
    db: AsyncSession = Depends(get_db),
) -> ExportResponse:
    """Export generated mock data in specified format"""
    dataset = mock_data_db.get(dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mock data dataset '{dataset_id}' not found",
        )
    
    if dataset_id not in generated_records_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No generated data available. Run generation first.",
        )
    
    generated_records = generated_records_db[dataset_id]
    
    # Simulate different file sizes based on format
    size_multipliers = {
        "json": 1.0,
        "csv": 0.7,
        "parquet": 0.3,
    }
    
    file_size_bytes = dataset["generated_size_bytes"] * size_multipliers.get(format, 1.0)
    file_size_mb = file_size_bytes / (1024 * 1024)
    
    return ExportResponse(
        dataset_id=dataset_id,
        format=format,
        file_size_mb=file_size_mb,
        download_url=f"/api/v1/mock-data/{dataset_id}/download?format={format}",
        expires_in_hours=24,
    )


@mock_data_router.get("/{dataset_id}/records", response_model=Dict[str, Any])
async def get_generated_records(
    dataset_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get generated records from dataset"""
    dataset = mock_data_db.get(dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mock data dataset '{dataset_id}' not found",
        )
    
    if dataset_id not in generated_records_db:
        return {
            "dataset_id": dataset_id,
            "total": 0,
            "records": [],
            "limit": limit,
            "offset": offset,
        }
    
    records = generated_records_db[dataset_id]
    total = len(records)
    paginated = records[offset : offset + limit]
    
    return {
        "dataset_id": dataset_id,
        "total": total,
        "records": paginated,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < total,
    }


# ============================================================================
# Helper Functions
# ============================================================================

def _to_response(dataset: Dict[str, Any]) -> MockDataResponse:
    """Convert dataset dict to response model"""
    fields = []
    for field in dataset.get("fields", []):
        if isinstance(field, dict):
            fields.append(MockDataFieldConfig(**field))
        else:
            fields.append(field)
    
    return MockDataResponse(
        id=dataset["id"],
        name=dataset["name"],
        description=dataset.get("description"),
        data_type=DataType(dataset["data_type"]),
        generation_strategy=GenerationStrategy(dataset["generation_strategy"]),
        record_count=dataset["record_count"],
        fields=fields,
        template_data=dataset.get("template_data"),
        seed=dataset.get("seed"),
        is_active=dataset["is_active"],
        status=dataset.get("status", "idle"),
        generated_records=dataset.get("generated_records", 0),
        generated_size_bytes=dataset.get("generated_size_bytes", 0),
        last_generated_at=dataset.get("last_generated_at"),
        created_at=dataset.get("created_at", datetime.now()),
        updated_at=dataset.get("updated_at", datetime.now()),
    )
