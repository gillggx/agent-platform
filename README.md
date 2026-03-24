# Agent Platform — Multi-Agent Collaboration Platform

A FastAPI + React platform where multiple AI agents (PM, Architect, QA, DevOps, Director) collaborate through structured workflows to produce product specs, architecture documents, and QA checklists — driven by a conversational PM Co-pilot interface.

**Stack:** Python 3.12 / FastAPI / SQLite / React 18 / TypeScript / Vite / Ant Design / LiteLLM / OpenRouter

---

## Features

### PM Co-pilot (Chat-first UX)
- Full-screen conversational interface driven by the PM agent
- Streaming SSE responses with real-time typing animation
- **Memory routing** — global memory (cross-project context) + per-project memory, automatically associated based on project mentions in conversation
- **Intake detection** — PM agent recognises when all required info is gathered and shows a project confirmation card
- One-click project creation + workflow launch directly from the chat

### Multi-Agent Workflow Engine
- **DAG-based orchestration** — sequential, parallel, and loop execution
- **LLM dynamic routing** — agents decide the next step via `APPROVE` / `RETURN_TO_PM` output markers
- **Human approval gates** — workflow pauses and waits for human review at designated steps
- **Loop guard** — configurable max iterations with automatic escalation

### Standard Spec Workflow
```
PM Dialogue (2–3 rounds)
  → Architect Review  (APPROVE → QA | RETURN_TO_PM → PM Revise → loop ≤2)
    → QA Review       (APPROVE → Director | RETURN_TO_PM → PM Revise 2 → loop ≤2)
      → Director Approve  (APPROVE → Export | REJECT → PM Final Revise)
        → Export
```

### Workflow Management
- List, clone, edit, and delete workflow templates in the UI
- System templates are read-only; clone to customise
- DAG visual editor for building custom workflows

### Agent Settings
- Per-agent overview cards showing model, temperature, and max_tokens at a glance
- Full soul (system prompt) editor — Markdown, saved to DB and synced from `souls/*.md` on restart
- Per-agent LLM override: model, provider, API key, base URL

### LLM Support
- Default: OpenRouter (`openrouter/google/gemini-2.0-flash-001`)
- `OPENROUTER_BASE_URL` fully configurable — supports custom proxies
- Per-agent model override via Agent Settings UI
- Supports OpenAI, Anthropic, OpenRouter, local Ollama via LiteLLM

### Code Architect Integration (A2A)
- Link a local codebase path when creating a project
- Code Architect Agent is auto-triggered to analyse and build architecture memory
- Architect agent has `code_architect_query / generate / validate / impact` tools

---

## Ports

| Service | Port |
|---------|------|
| Backend (FastAPI) | **8080** |
| Frontend (Vite dev) | **2999** |
| Code Architect (optional) | **8001** |

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- OpenRouter API key (or any OpenAI-compatible key)

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # set LLM_API_KEY and LLM_MODEL

python init_db.py
uvicorn app.main:app --port 8080 --reload
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev   # http://localhost:2999
```

---

## Environment Variables

### `backend/.env`

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_KEY` | — | API key for your LLM provider (required) |
| `LLM_PROVIDER` | `openrouter` | Provider: `openrouter` / `openai` / `anthropic` |
| `LLM_MODEL` | `openrouter/google/gemini-2.0-flash-001` | Default model (LiteLLM format) |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | OpenRouter endpoint — set to your proxy URL if needed |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/app.db` | DB connection string |
| `SECRET_KEY` | `dev-secret-key` | Change in production |
| `CODE_ARCHITECT_URL` | `http://localhost:8001` | Code Architect Agent service URL |

### Switching Models

```bash
# OpenRouter (default)
LLM_PROVIDER=openrouter
LLM_MODEL=openrouter/google/gemini-2.0-flash-001
LLM_API_KEY=sk-or-...

# OpenAI
LLM_PROVIDER=openai
LLM_MODEL=openai/gpt-4o
LLM_API_KEY=sk-...

# Anthropic
LLM_PROVIDER=anthropic
LLM_MODEL=anthropic/claude-sonnet-4-6
LLM_API_KEY=sk-ant-...

# Custom proxy / self-hosted
LLM_PROVIDER=openrouter
OPENROUTER_BASE_URL=https://your-proxy.example.com/api/v1
LLM_API_KEY=...
```

Per-agent model overrides can also be configured in the **Agent Settings** page — these take priority over global settings.

---

## Project Structure

```
agent-platform/
├── backend/
│   ├── app/
│   │   ├── api/           # REST endpoints (agents, workflows, projects, artifacts, chat)
│   │   ├── core/          # Config & settings
│   │   ├── data/          # Seed data, default workflow templates
│   │   ├── db/            # SQLAlchemy async engine
│   │   ├── intelligence/  # LLMAdapterV2, tool definitions
│   │   ├── models/        # ORM models (project, workflow, agent, chat, memory)
│   │   ├── runtime/       # Workflow engine (DAG executor, agent runner)
│   │   └── services/      # LLM adapter, PM agent service (streaming + memory)
│   ├── souls/             # Per-agent personality definition files (Markdown)
│   │   ├── pm.md          # PM — intake protocol, spec output format
│   │   ├── architect.md   # Architect — APPROVE / RETURN_TO_PM decision format
│   │   ├── qa.md          # QA — checklist output, APPROVE / RETURN_TO_PM format
│   │   ├── devops.md
│   │   ├── director.md
│   │   └── pm_critic.md
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── ChatPanel.tsx          # PM Co-pilot streaming chat UI
│       │   ├── ProjectSidebar.tsx     # Project list + navigation
│       │   └── DAGEditor/             # Visual workflow editor
│       ├── pages/
│       │   ├── DashboardPage.tsx          # Co-pilot home (sidebar + chat)
│       │   ├── WorkflowManagePage.tsx     # Template CRUD
│       │   ├── AgentSettingsPage.tsx      # Agent config + soul editor
│       │   ├── WorkflowPage.tsx           # Live workflow run view
│       │   └── DAGEditorPage.tsx          # Workflow template editor
│       ├── services/api.ts            # Typed API client
│       └── store/dagStore.ts          # DAG editor state (Zustand)
└── start.sh
```

---

## Agent Souls

Each agent's personality, work style, output format, and decision rules are defined in `backend/souls/<role>.md`. Edits take effect automatically on the next backend restart (souls are synced to DB at startup).

| Role | Soul file | Key output |
|------|-----------|------------|
| PM | `pm.md` | Product Spec (intake flow → confirmation → spec) |
| Architect | `architect.md` | Tech Spec + `APPROVE` / `RETURN_TO_PM` |
| QA | `qa.md` | QA Checklist + `APPROVE` / `RETURN_TO_PM` |
| DevOps | `devops.md` | Deployment & operations review |
| Director | `director.md` | Final business decision |
| PM Critic | `pm_critic.md` | Devil's advocate in PM dialogue rounds |

---

## API Overview

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/chat/message` | Stream PM agent response (SSE) |
| `POST` | `/api/v1/chat/start-project` | Create project + launch workflow from chat |
| `GET` | `/api/v1/chat/history` | Chat message history |
| `GET` | `/api/v1/chat/memory` | View PM agent's global memory |
| `GET` | `/api/v1/workflows/templates` | List workflow templates |
| `POST` | `/api/v1/workflows/templates` | Create custom template |
| `PUT` | `/api/v1/workflows/templates/:id` | Update custom template |
| `DELETE` | `/api/v1/workflows/templates/:id` | Delete custom template |
| `POST` | `/api/v1/workflows/templates/:id/clone` | Clone any template |
| `POST` | `/api/v1/workflows/runs` | Start a workflow run |
| `GET` | `/api/v1/workflows/runs/:id` | Get run status + step executions |
| `POST` | `/api/v1/workflows/runs/:id/approve` | Human approval / rejection |
| `GET` | `/api/v1/agents` | List agent definitions |
| `PUT` | `/api/v1/agents/:role` | Update agent soul / config |
| `GET` | `/api/v1/projects` | List projects |
| `POST` | `/api/v1/projects` | Create project |

Full interactive docs: `http://localhost:8080/docs`
