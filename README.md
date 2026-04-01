# Agent Platform — Multi-Agent Collaboration Platform

A FastAPI + React platform where multiple AI agents (PM, Architect, QA, DevOps, Director) collaborate through structured workflows to produce product specs, architecture documents, and QA checklists — driven by a conversational PM Co-pilot interface.

**Stack:** Python 3.12 / FastAPI / SQLite / React 18 / TypeScript / Vite / Ant Design / LiteLLM / OpenRouter

---

## Table of Contents

- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [Built-in Workflow Templates](#built-in-workflow-templates)
- [Workflow Engine](#workflow-engine)
- [Agent Souls](#agent-souls)
- [Document Export](#document-export)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [Extending the Platform](#extending-the-platform)

---

## Features

### PM Co-pilot (Chat-first UX)
- Full-screen conversational interface driven by the PM agent
- **Streaming SSE** responses with real-time typing animation
- **Memory routing** — global memory (cross-project context) + per-project memory, automatically loaded based on project mentions in the conversation
- **Intake detection** — PM agent recognises when all required fields are collected and presents a project confirmation card; user clicks once to create the project and launch the workflow
- Project list sidebar with quick access to workflow history, re-analysis, and workflow launch

### Multi-Agent Workflow Engine
- **DAG-based orchestration** — sequential steps, parallel branches, and configurable loop iterations
- **LLM dynamic routing** — agents decide the next step themselves by emitting `APPROVE` / `RETURN_TO_PM` decision markers in their output
- **Human approval gates** — workflow pauses at designated steps and waits for explicit human review before continuing
- **Loop guard** — each step has a configurable `max_iterations`; exceeding it auto-escalates to the next stage
- **Guardrails** — per-workflow `max_total_steps` and `timeout_minutes`

### Standard Spec Workflow (Default)
```
PM Dialogue  ──────────────────────────────────────────────────
  (2–3 rounds, PM + PM Critic)                                  │
       │                                                         │
       ▼                                                         │
Architect Review ─── APPROVE ──► QA Review ──── APPROVE ──► Director Approve ──► Export
       │                              │                          │
  RETURN_TO_PM                  RETURN_TO_PM                  REJECT
       │                              │                          │
       ▼                              ▼                          ▼
   PM Revise ─────────────────► PM Revise 2 ──────────────► PM Final Revise
  (loop ≤ 2)                    (loop ≤ 2)                  (loop ≤ 2)
```

### Workflow Management
- List, clone, edit, and delete workflow templates in the UI
- System templates are read-only; clone any template to create a customised version
- DAG visual editor for building workflows from scratch

### Agent Settings
- Per-agent overview cards showing current model, temperature, and max_tokens at a glance
- Full soul (system prompt) editor in Markdown — changes sync to DB on next backend restart
- Per-agent LLM override: model, provider, API key, base URL — takes priority over global settings

### LLM Support
- Default: OpenRouter (`openrouter/google/gemini-2.0-flash-001`)
- `OPENROUTER_BASE_URL` fully configurable — point to any compatible proxy
- Per-agent model override via Agent Settings UI
- Supports OpenAI, Anthropic, OpenRouter, local Ollama via LiteLLM

### Code Architect Integration (A2A)
- Link a local codebase path when creating a project; Code Architect Agent auto-triggers to build architecture memory
- Architect agent has `code_architect_query`, `code_architect_generate`, `code_architect_validate`, and `code_architect_impact` tools available during workflow execution

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Browser (React + TypeScript)                                │
│                                                              │
│  ┌─────────────────┐    ┌──────────────────────────────┐   │
│  │  PM Co-pilot    │    │  Workflow / Agent / Project   │   │
│  │  (ChatPanel +   │    │  pages (Ant Design + Zustand) │   │
│  │   ProjectSidebar│    └──────────────────────────────┘   │
│  └────────┬────────┘                   │                    │
└───────────┼────────────────────────────┼────────────────────┘
            │ SSE stream / REST          │ REST
            ▼                            ▼
┌─────────────────────────────────────────────────────────────┐
│  FastAPI Backend (port 8080)                                 │
│                                                              │
│  ┌──────────────┐  ┌────────────────┐  ┌────────────────┐  │
│  │  Chat API    │  │  Workflow API  │  │  Agent API     │  │
│  │  (SSE +      │  │  (templates,   │  │  (soul, config │  │
│  │   pm_agent)  │  │   runs, CRUD)  │  │   CRUD)        │  │
│  └──────┬───────┘  └───────┬────────┘  └────────────────┘  │
│         │                  │                                  │
│         ▼                  ▼                                  │
│  ┌─────────────────────────────────────┐                    │
│  │  Workflow Engine (DAG executor)     │                    │
│  │  ┌──────────┐  ┌─────────────────┐ │                    │
│  │  │ Session  │  │  Routing Engine │ │                    │
│  │  │ Manager  │  │  (static / LLM) │ │                    │
│  │  └──────────┘  └─────────────────┘ │                    │
│  └──────────────────────┬──────────────┘                    │
│                         │                                    │
│  ┌──────────────────────▼──────────────┐                    │
│  │  LLM Adapter (LiteLLM)              │                    │
│  │  OpenRouter / OpenAI / Anthropic    │                    │
│  └─────────────────────────────────────┘                    │
│                                                              │
│  SQLite (data/app.db)                                        │
└─────────────────────────────────────────────────────────────┘
            │ HTTP (optional)
            ▼
┌───────────────────────┐
│  Code Architect Agent │
│  (port 8001)          │
└───────────────────────┘
```

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

cp .env.example .env
# Edit .env — set LLM_API_KEY at minimum (see Environment Variables below)

# IMPORTANT: Run this once before first launch.
# Creates SQLite DB tables and seeds all default agents + workflow templates.
# Without this step, PM agent and workflows will not function.
python init_db.py

uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev   # http://localhost:2999
```

### 3. (Optional) Code Architect Agent

```bash
# https://github.com/gillggx/code-architect
cd code-architect
uvicorn app.main:app --port 8001 --reload
```

Set `CODE_ARCHITECT_URL=http://localhost:8001` in `backend/.env` and link a codebase path when creating a project.

---

## Production Setup

> **Key difference from dev:** run `init_db.py` once before the first server start. After that, restarting the server re-seeds souls and template definitions automatically.

```bash
# 1. Configure environment
cp backend/.env.example backend/.env
vi backend/.env   # set LLM_API_KEY, LLM_MODEL, SECRET_KEY

# 2. Init DB (run ONCE — idempotent, safe to re-run)
cd backend
source .venv/bin/activate
python init_db.py

# Expected output:
#   ✓ Database connection successful
#   ✓ Database tables created
#   Created system agent: PM Agent
#   Created system agent: Architect Agent
#   ...
#   Created system template: 標準 Spec 流程
#   ✓ Default system data seeded

# 3. Start backend
uvicorn app.main:app --host 0.0.0.0 --port 8080

# 4. Build and serve frontend
cd ../frontend
npm install && npm run build
# Serve dist/ with Nginx, or use: npx serve -s dist -l 2999
```

**Why PM agent doesn't respond without seeding:**
The workflow engine looks up agent definitions from the DB by role (`pm`, `architect`, etc.).
If `init_db.py` was never run, the DB has no agent rows and workflows fail silently.
Running `init_db.py` (or restarting the server after first run) fixes this.

---

## Environment Variables

### `backend/.env`

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_KEY` | — | API key for your LLM provider **(required)** |
| `LLM_PROVIDER` | `openrouter` | Provider: `openrouter` / `openai` / `anthropic` |
| `LLM_MODEL` | `openrouter/google/gemini-2.0-flash-001` | Default model in LiteLLM format |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | OpenRouter endpoint — override to use a proxy |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/app.db` | SQLAlchemy connection string |
| `SECRET_KEY` | `dev-secret-key` | **Change in production** |
| `CODE_ARCHITECT_URL` | `http://localhost:8001` | Code Architect Agent service URL |

### Switching Models

```bash
# OpenRouter (default) — access 100+ models with one key
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

Per-agent model overrides are also configurable from the **Agent Settings** page in the UI — these take priority over global settings.

---

## Built-in Workflow Templates

Four system templates are seeded on startup. All are read-only but can be cloned and customised.

| Template | Steps | Best for |
|----------|-------|----------|
| **標準 Spec 流程** | PM Dialogue → Architect → QA → Director → Export | Full product spec with review loops |
| **快速 Review** | PM Draft → Director → Export | Small changes, quick sign-off |
| **完整交付流程** | PM → Architect + DevOps (parallel) → QA → Director | Complete delivery including infra review |
| **PM 雙人協作流程** | PM Dialogue → Director → Export | Rapid spec drafting with critic |

Template definitions live in `backend/app/data/default_templates.py` and are automatically synced to the DB on every backend restart.

---

## Workflow Engine

### Step Task Types

| `task_type` | What the agent does |
|-------------|---------------------|
| `dialogue` | Two-PM back-and-forth discussion for `min_rounds`–`max_rounds` iterations to refine the requirement |
| `draft` | Single-pass: agent reads user input and produces a first draft document |
| `review` | Agent reviews upstream artifacts and outputs a decision (`APPROVE` / `RETURN_TO_PM`) |
| `revise` | Agent reads reviewer feedback and produces an improved document |
| `approve` | Final decision step — typically Director, produces a go/no-go decision |
| `export` | System step: marks the workflow as completed and consolidates output artifacts |

### Routing Types

**Static routing** — always goes to the next step:
```json
"routing": { "type": "static", "next_steps": ["qa_review"] }
```

**LLM decision routing** — the engine makes a secondary LLM call after the step completes to classify which branch to take based on the agent's output:
```json
"routing": {
  "type": "llm_decision",
  "decision_prompt": "根據文件末的決策標記判斷路由...",
  "options": [
    { "label": "APPROVE", "target_step": "qa_review", "condition_hint": "..." },
    { "label": "RETURN_TO_PM", "target_step": "pm_revise", "condition_hint": "..." }
  ]
}
```

### Loop Configuration

Prevent infinite cycles with `loop`:
```json
"loop": {
  "enabled": true,
  "max_iterations": 2,
  "escalate_to": "director_approve"
}
```
If a step is revisited more than `max_iterations` times, the engine automatically escalates to `escalate_to`, bypassing the loop.

### Guardrails

```json
"guardrails": {
  "max_total_steps": 30,
  "timeout_minutes": 45,
  "require_human_approval": ["director_approve"]
}
```

Steps listed in `require_human_approval` pause the workflow and set status to `waiting_approval`. Resume via `POST /api/v1/workflows/runs/:id/approve`.

---

## Agent Souls

Each agent's identity, work style, output format, and decision rules are defined in `backend/souls/<role>.md`. The files are loaded and synced to the database on every backend restart — edit the `.md` file and restart to see the change take effect immediately.

| Role | File | Personality & key output |
|------|------|--------------------------|
| PM | `pm.md` | Consultant-style PM; follows a 6-field intake protocol, produces a structured Product Spec, collaborates in dialogue mode with PM Critic |
| Architect | `architect.md` | Senior software architect; outputs a Tech Spec with component diagram, data model, API design, risk assessment; ends with `APPROVE` or `RETURN_TO_PM` |
| QA | `qa.md` | Sceptical QA engineer; outputs a QA Checklist (Given/When/Then format, boundary/exception/security tests); ends with `APPROVE` or `RETURN_TO_PM` |
| DevOps | `devops.md` | DevOps reviewer; covers deployment, infra, monitoring, and ops considerations |
| Director | `director.md` | Business-focused final decision maker; evaluates ROI, risk, and strategic alignment; ends with `APPROVE` or `REJECT` |
| PM Critic | `pm_critic.md` | Devil's advocate PM; challenges assumptions and forces completeness in PM Dialogue rounds |

### Writing Decision Markers

For `llm_decision` routing to work, agents must end their output with one of the defined markers. Example from `architect.md`:

```markdown
---
**決策：APPROVE**
技術規格已完成，無重大可行性問題。
```

```markdown
---
**決策：RETURN_TO_PM**
退回原因：
1. [問題 1]
PM 修改重點：[需要補充什麼]
```

The routing engine extracts these markers with a secondary LLM call to determine the next step.

---

## Document Export

Each agent session produces an **Artifact** (Markdown). When a workflow completes, the platform aggregates all artifacts and can export them as:

- **Markdown** — returned directly via API
- **DOCX** — `python-docx` converts the Markdown to a formatted Word document, downloadable via `GET /api/v1/artifacts/:id/download`
- **Project bundle** — all artifacts in a single ZIP: `GET /api/v1/artifacts/projects/:id/download`

Artifacts are versioned: if a PM revises a spec, the previous version is marked `superseded` and the new one becomes `draft` → `approved` after Director sign-off.

---

## Project Structure

```
agent-platform/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── agents.py          # GET/PUT agent definitions (soul + config)
│   │   │   ├── artifacts.py       # GET artifacts, download Markdown/DOCX/ZIP
│   │   │   ├── auth.py            # Demo auth (default org/user seeded on startup)
│   │   │   ├── chat.py            # SSE stream, start-project, history, memory
│   │   │   ├── projects.py        # Project CRUD, Code Architect wake
│   │   │   ├── tools.py           # Tool definitions exposed to agent runtime
│   │   │   └── workflows.py       # Template CRUD + run management + approval
│   │   ├── core/
│   │   │   └── config.py          # Pydantic settings, reads from .env
│   │   ├── data/
│   │   │   ├── default_templates.py   # 4 built-in workflow template definitions
│   │   │   └── seed_data.py           # DB seed (org, user, agents, templates)
│   │   ├── db/
│   │   │   └── base.py            # SQLAlchemy async engine + session factory
│   │   ├── intelligence/
│   │   │   └── llm_adapter_v2.py  # Advanced LLM adapter with complexity routing
│   │   ├── models/
│   │   │   ├── agent_definition.py    # Agent soul, config, is_system flag
│   │   │   ├── agent_session.py       # Per-step execution session (status, context, memory)
│   │   │   ├── artifact.py            # Output documents (Markdown + version + status)
│   │   │   ├── chat.py                # ChatMessage, GlobalMemory, ProjectMemory
│   │   │   ├── organization.py
│   │   │   ├── project.py             # Project (name, codebase_path, status)
│   │   │   ├── user.py
│   │   │   ├── workflow_run.py        # Run status, step_executions JSON log, current_steps
│   │   │   └── workflow_template.py   # Template definition (DAG JSON), is_system flag
│   │   ├── runtime/
│   │   │   ├── session_manager.py     # Agent session lifecycle, LLM conversation loop
│   │   │   └── workflow_engine.py     # DAG executor, routing, loop guard, approval gate
│   │   └── services/
│   │       ├── document_export.py     # Markdown → DOCX (python-docx)
│   │       ├── llm_adapter.py         # Unified LLM call (LiteLLM), retry, timeout
│   │       └── pm_agent.py            # PM Co-pilot: streaming, memory, intake detection
│   ├── souls/                         # Agent personality files (Markdown)
│   │   ├── architect.md
│   │   ├── devops.md
│   │   ├── director.md
│   │   ├── pm.md
│   │   ├── pm_critic.md
│   │   └── qa.md
│   ├── init_db.py                     # One-time DB init + seed script
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── AppHeader.tsx
│       │   ├── ChatPanel.tsx          # PM Co-pilot chat (SSE streaming, intake card)
│       │   ├── ProjectSidebar.tsx     # Project list, new-project modal, workflow launch
│       │   └── DAGEditor/             # Visual workflow editor (React Flow-based)
│       │       ├── DAGCanvas.tsx
│       │       ├── DAGEditor.tsx
│       │       ├── NodePanel.tsx
│       │       ├── EdgeConfigDialog.tsx
│       │       ├── Toolbar.tsx
│       │       └── ValidationPanel.tsx
│       ├── pages/
│       │   ├── AgentSettingsPage.tsx      # Agent overview cards + soul/config editor
│       │   ├── DAGEditorPage.tsx          # Workflow template editor (create/update)
│       │   ├── DashboardPage.tsx          # Full-screen co-pilot home
│       │   ├── ProjectPage.tsx            # Project detail (runs, artifacts)
│       │   ├── WorkflowManagePage.tsx     # Template list (clone/edit/delete)
│       │   └── WorkflowPage.tsx           # Live workflow run view (step-by-step log)
│       ├── services/
│       │   └── api.ts                 # Typed Axios + fetch API client
│       ├── store/
│       │   └── dagStore.ts            # DAG editor state (Zustand)
│       └── types/
│           ├── dag.ts                 # DAG editor types
│           └── index.ts               # Shared domain types
└── start.sh
```

---

## API Reference

### Chat

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/chat/message` | Stream PM agent response via SSE. Body: `{ message, intake_already_triggered }` |
| `POST` | `/api/v1/chat/start-project` | Create project + launch workflow. Body: `{ project_name, project_description, template_id? }` |
| `GET` | `/api/v1/chat/history` | Message history. Query: `?limit=50` |
| `DELETE` | `/api/v1/chat/history` | Clear chat history |
| `GET` | `/api/v1/chat/memory` | View PM agent's current global memory summary |

### Workflows

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/workflows/templates` | List all templates (system + org custom) |
| `POST` | `/api/v1/workflows/templates` | Create custom template |
| `GET` | `/api/v1/workflows/templates/:id` | Get template detail |
| `PUT` | `/api/v1/workflows/templates/:id` | Update custom template (403 for system) |
| `DELETE` | `/api/v1/workflows/templates/:id` | Delete custom template (403 for system) |
| `POST` | `/api/v1/workflows/templates/:id/clone` | Clone any template into a new custom one |
| `POST` | `/api/v1/workflows/runs` | Start a workflow run. Body: `{ project_id, template_id, user_input }` |
| `GET` | `/api/v1/workflows/runs/:id` | Run status + full step_executions log |
| `POST` | `/api/v1/workflows/runs/:id/approve` | Human approval/rejection. Query: `?approved=true&feedback=...` |
| `GET` | `/api/v1/workflows/projects/:project_id/runs` | List all runs for a project |

### Projects

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/projects` | List all projects |
| `POST` | `/api/v1/projects` | Create project. Body: `{ name, description?, codebase_path? }` |
| `GET` | `/api/v1/projects/:id` | Project detail |
| `DELETE` | `/api/v1/projects/:id` | Delete project |
| `GET` | `/api/v1/projects/:id/architect-status` | Code Architect analysis status |
| `POST` | `/api/v1/projects/:id/wake-architect` | Trigger Code Architect re-analysis |

### Agents

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/agents` | List all system agent definitions |
| `GET` | `/api/v1/agents/:role` | Get single agent (soul + full config) |
| `PUT` | `/api/v1/agents/:role` | Update soul, display_name, description, or config |

### Artifacts

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/artifacts/projects/:id/artifacts` | List artifacts for a project |
| `GET` | `/api/v1/artifacts/:id` | Get artifact detail (full Markdown content) |
| `GET` | `/api/v1/artifacts/:id/download` | Download as DOCX |
| `GET` | `/api/v1/artifacts/projects/:id/download` | Download all artifacts as ZIP |

Full interactive docs: `http://localhost:8080/docs`

---

## Extending the Platform

### Adding a New Agent

1. Create `backend/souls/<role>.md` — define personality, output format, and decision markers
2. Add an entry to `DEFAULT_AGENTS` in `backend/app/data/seed_data.py`
3. Restart backend — the agent is seeded automatically
4. Reference the `agent_role` in any workflow template step

### Creating a Custom Workflow Template

**Via UI:** Go to **流程管理** → **新建流程** to open the DAG editor.

**Via API:**
```bash
curl -X POST http://localhost:8080/api/v1/workflows/templates \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Custom Flow",
    "description": "...",
    "definition": {
      "workflow": {
        "id": "my-flow",
        "name": "My Custom Flow",
        "version": 1,
        "steps": [
          {
            "id": "pm_draft",
            "agent_role": "pm",
            "task_type": "draft",
            "depends_on": [],
            "routing": { "type": "static", "next_steps": ["director_approve"] }
          },
          {
            "id": "director_approve",
            "agent_role": "director",
            "task_type": "approve",
            "depends_on": ["pm_draft"],
            "routing": {
              "type": "llm_decision",
              "decision_prompt": "審核品質，決定是否通過。",
              "options": [
                { "label": "批准", "target_step": "export", "condition_hint": "品質達標" },
                { "label": "退回", "target_step": "pm_revise", "condition_hint": "需要修改" }
              ]
            }
          },
          {
            "id": "export",
            "agent_role": "system",
            "task_type": "export",
            "depends_on": ["director_approve"],
            "routing": { "type": "static", "next_steps": [] }
          }
        ],
        "guardrails": {
          "max_total_steps": 10,
          "timeout_minutes": 20,
          "require_human_approval": ["director_approve"]
        }
      }
    }
  }'
```

### Customising an Agent's Soul

Edit `backend/souls/<role>.md` directly and restart the backend. The seed runner always overwrites the DB with the latest file content, so there is no migration step needed.

To test a soul change without restarting:
```bash
PUT /api/v1/agents/:role
Body: { "soul": "# New soul content..." }
```
This takes effect immediately for the next workflow run.
