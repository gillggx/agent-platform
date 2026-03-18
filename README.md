# Multi-Agent Collaboration Platform

A FastAPI + React platform where PM, Architect, QA, DevOps, and Director agents automatically collaborate to produce complete product specs, architecture documents, and code.

**Stack:** Python 3.12+ / FastAPI / SQLite / React 18 / TypeScript / Vite / LiteLLM / OpenRouter

---

## Features

- **Multi-role agent collaboration** — PM, Architect, QA, DevOps, Director agents work together in structured workflows
- **Workflow engine** — DAG + LLM dynamic routing; fully customizable collaboration flows
- **Real-time discussion UI** — WebSocket streaming shows agent-to-agent conversations live
- **Document export** — Markdown auto-converted to professional `.docx` files
- **Unified LLM interface** — supports OpenAI, Anthropic, OpenRouter, local Ollama via LiteLLM
- **A2A integration** — Architect agent calls Code Architect service (`http://localhost:8001`) for codebase queries, code generation, validation, and impact analysis
- **Codebase linking** — when creating a project, optionally link a local codebase path; Code Architect is automatically triggered to analyze and build architecture memory. Projects with memory show a 🧠 badge with a one-click re-analyze button.
- **SQLite by default** — no Docker or PostgreSQL required for local development

---

## Ports

| Service | Port |
|---------|------|
| Backend (FastAPI) | **8080** |
| Frontend (Vite/React) | **2999** |

Designed to run alongside [Code Architect Agent](https://github.com/gillggx/code-architect) (ports 8001/3001) on the same machine without conflicts.

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- An [OpenRouter](https://openrouter.ai) API key

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set LLM_API_KEY
python init_db.py
uvicorn app.main:app --port 8080 --reload
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev   # starts on http://localhost:2999
```

---

## Project Structure

```
agent-platform/
├── backend/
│   ├── app/
│   │   ├── api/           # REST endpoints (agents, workflows, projects, artifacts)
│   │   ├── core/          # Config, settings
│   │   ├── db/            # SQLAlchemy async engine, migrations
│   │   ├── intelligence/  # LLMAdapter, tool definitions, ToolExecutor
│   │   ├── knowledge/     # CodeArchitectAdapter (A2A client), knowledge base
│   │   ├── models/        # SQLAlchemy ORM models
│   │   ├── runtime/       # Workflow engine, agent runner
│   │   └── services/      # LLM adapter service
│   ├── requirements.txt
│   └── souls/             # Per-agent SOUL personality files
├── frontend/
│   └── src/
│       ├── components/    # UI components
│       └── store/         # Zustand state
└── start.sh
```

---

## A2A Integration with Code Architect

The Architect agent has access to `code_architect_query`, `code_architect_generate`, `code_architect_validate`, and `code_architect_impact` tools that call the Code Architect service:

```python
# Agent tool call example
{
  "tool": "code_architect_query",
  "parameters": {
    "question": "Is it feasible to add WebSocket support?",
    "project_id": "my-project",
    "query_type": "feasibility"
  }
}
```

Requires Code Architect Agent running at `http://localhost:8001`.

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_KEY` | — | OpenRouter API key (required) |
| `LLM_PROVIDER` | `openrouter` | LLM provider |
| `LLM_MODEL` | `openrouter/google/gemini-2.0-flash-001` | Default model |
| `DATABASE_URL` | SQLite (`data/app.db`) | Database connection string |
| `SECRET_KEY` | `dev-secret-key` | Change in production |
