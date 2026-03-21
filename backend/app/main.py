from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from contextlib import asynccontextmanager

from app.core.config import settings
from app.db.base import engine, Base, AsyncSessionLocal
from app.api.auth import auth_router
from app.api.projects import projects_router
from app.api.workflows import workflows_router
from app.api.artifacts import artifacts_router
from app.api.agents import agents_router
from app.api.tools import tools_router
from app.api.routine_checks import routine_checks_router
from app.api.mock_data import mock_data_router
from app.api.chat import chat_router
from app.services.llm_adapter import llm_adapter

# Import all models so Base.metadata knows about them
from app.models import (  # noqa: F401
    Organization, User, Project, AgentDefinition,
    KnowledgePack, KnowledgeDocument, WorkflowTemplate,
    WorkflowRun, StepExecution, AgentSession, Artifact, AgentMemory,
    ChatMessage, GlobalMemory, ProjectMemory,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    
    # Startup
    print(f"Starting {settings.app_name} v{settings.version}")
    
    # Auto-create all tables
    print("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables ready.")
    
    # Seed default data
    from app.data.seed_data import seed_all_defaults
    async with AsyncSessionLocal() as db:
        await seed_all_defaults(db)
    
    # Test LLM connection
    if settings.llm_api_key:
        print("Testing LLM connection...")
        try:
            is_connected = await llm_adapter.test_connection()
            print(f"LLM connection: {'✓' if is_connected else '✗'}")
        except Exception as e:
            print(f"LLM connection test failed: {e}")
    else:
        print("⚠️  LLM_API_KEY not set - some features will not work")
    
    print(f"Server ready at http://localhost:8080")
    print(f"Frontend should proxy to this backend")
    
    yield
    
    # Shutdown
    print("Shutting down...")
    await engine.dispose()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Multi-Agent Collaboration Platform API",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.version,
        "llm_model": settings.llm_model,
        "llm_configured": bool(settings.llm_api_key),
    }

# Include routers
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(projects_router, prefix="/api/v1/projects", tags=["Projects"])  
app.include_router(workflows_router, prefix="/api/v1/workflows", tags=["Workflows"])
app.include_router(artifacts_router, prefix="/api/v1/artifacts", tags=["Artifacts"])
app.include_router(agents_router, prefix="/api/v1/agents", tags=["Agents"])
app.include_router(tools_router, prefix="/api/v1/tools", tags=["Tools"])
app.include_router(routine_checks_router, prefix="/api/v1/routine-checks", tags=["Routine Checks"])
app.include_router(mock_data_router, prefix="/api/v1/mock-data", tags=["Mock Data"])
app.include_router(chat_router, prefix="/api/v1/chat", tags=["Chat"])

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    
    if settings.debug:
        import traceback
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": str(exc),
                "traceback": traceback.format_exc(),
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={"error": "Internal Server Error"}
        )

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.debug,
    )
