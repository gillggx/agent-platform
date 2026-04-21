from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path

# Ensure data directories exist
DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
(DATA_DIR / "exports").mkdir(exist_ok=True)


class Settings(BaseSettings):
    # App
    app_name: str = "Multi-Agent Collaboration Platform"
    version: str = "1.0.0"
    debug: bool = True
    
    # Database — SQLite (no Docker/PG needed)
    database_url: str = os.getenv(
        "DATABASE_URL",
        f"sqlite+aiosqlite:///{DATA_DIR / 'app.db'}"
    )
    
    # LLM — use litellm, supports OpenRouter, OpenAI, Anthropic, and any
    # OpenAI-compatible endpoint (internal vLLM/TGI/Ollama/gateway etc.)
    llm_provider: str = os.getenv("LLM_PROVIDER", "openrouter")
    llm_api_key: Optional[str] = os.getenv("LLM_API_KEY")
    llm_model: str = os.getenv("LLM_MODEL", "openrouter/google/gemini-2.0-flash-001")
    # Generic override. Use for internal / self-hosted endpoints.
    # Takes priority over provider-specific defaults when set.
    llm_base_url: Optional[str] = os.getenv("LLM_BASE_URL")
    
    # Agent Settings
    agent_session_timeout_minutes: int = 5
    max_workflow_steps: int = 20
    max_loop_iterations: int = 2
    
    # Local export directory
    export_dir: str = str(DATA_DIR / "exports")
    
    # OpenRouter
    openrouter_base_url: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    
    # Security
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
