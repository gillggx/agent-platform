# Multi-Agent Collaboration Platform — 技術架構文件

**版本**：v1.0  
**日期**：2026-03-16  
**作者**：Architect Agent  
**依據**：Product Spec v3 \+ Director 修正（流程模板 UX）

---

## 目錄

1. [系統架構總覽](#1-系統架構總覽)  
2. [Agent Runtime 設計](#2-agent-runtime-設計)  
3. [流程引擎](#3-流程引擎)  
4. [知識庫封裝](#4-知識庫封裝)  
5. [文件產出](#5-文件產出)  
6. [部署架構](#6-部署架構)  
7. [技術棧選型](#7-技術棧選型)  
8. [ADR（架構決策記錄）](#8-adr架構決策記錄)

---

## 1\. 系統架構總覽

### 1.1 四層架構

┌─────────────────────────────────────────────────────┐

│                  Presentation Layer                  │

│  React \+ TypeScript SPA                             │

│  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │

│  │ Project  │ │ Chat UI  │ │ Workflow Designer    │ │

│  │ Dashboard│ │ (討論面板)│ │ (P1: 拖拉式流程圖)  │ │

│  └──────────┘ └──────────┘ └──────────────────────┘ │

├─────────────────────────────────────────────────────┤

│                   API Layer                          │

│  FastAPI (Python 3.12+)                             │

│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │

│  │ Project  │ │ Agent    │ │ Workflow │ │ Export │ │

│  │ API      │ │ API      │ │ API      │ │ API    │ │

│  └──────────┘ └──────────┘ └──────────┘ └────────┘ │

├─────────────────────────────────────────────────────┤

│                Agent Runtime Layer                   │

│  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │

│  │ Agent    │ │ Session  │ │ Workflow Engine      │ │

│  │ Lifecycle│ │ Manager  │ │ (DAG \+ LLM Router)  │ │

│  └──────────┘ └──────────┘ └──────────────────────┘ │

│  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │

│  │ Memory   │ │ Context  │ │ LLM Provider        │ │

│  │ Store    │ │ Bus      │ │ Adapter             │ │

│  └──────────┘ └──────────┘ └──────────────────────┘ │

├─────────────────────────────────────────────────────┤

│                Infrastructure Layer                  │

│  PostgreSQL │ Redis │ MinIO/S3 │ Docker             │

└─────────────────────────────────────────────────────┘

### 1.2 核心資料流

使用者輸入需求

    │

    ▼

\[API Gateway\] ──► \[Project Service\] ──► 建立 Project \+ 選擇流程模板

    │

    ▼

\[Workflow Engine\] ──► 解析 DAG，決定第一個 Agent

    │

    ▼

\[Agent Runtime\] ──► 啟動 Agent Session

    │                    │

    │              ┌─────▼─────┐

    │              │ LLM Call  │ ◄── Knowledge Base (prompt \+ docs)

    │              └─────┬─────┘

    │                    │

    │              Agent 產出 artifact

    │                    │

    ▼                    ▼

\[Workflow Engine\] ──► Director/LLM 決定下一步

    │                    │

    │              (迴圈 or 下一個 Agent)

    │                    │

    ▼                    ▼

\[Export Service\] ──► Markdown → .docx

    │

    ▼

使用者下載 .docx

### 1.3 核心模組清單

| 模組 | 職責 | 技術 |
| :---- | :---- | :---- |
| **Web App** | 使用者介面、即時討論顯示 | React 18, TypeScript, TanStack Query |
| **API Server** | RESTful API \+ WebSocket | FastAPI, Uvicorn, Pydantic v2 |
| **Workflow Engine** | DAG 解析、步驟排程、迴圈控制 | 自建 Python 模組 |
| **Agent Runtime** | Agent 生命週期、LLM 呼叫、context 管理 | 自建 Python 模組 |
| **Knowledge Store** | Prompt template \+ reference docs 儲存 | PostgreSQL \+ MinIO |
| **Export Service** | Markdown → .docx 轉換 | python-docx \+ pypandoc |
| **Message Broker** | Agent 間非同步通訊 | Redis Streams |
| **Database** | 結構化資料持久化 | PostgreSQL 16 |
| **Object Storage** | 檔案、附件、產出物 | MinIO (self-hosted) / S3 (SaaS) |
| **Cache / PubSub** | Session 快取、即時推送 | Redis 7 |

---

## 2\. Agent Runtime 設計

### 2.1 核心概念

Agent Definition (靜態)

├── role: str              \# "pm", "architect", "qa", "devops", "director"

├── display\_name: str      \# "PM Agent"

├── system\_prompt: str     \# 基礎人設 prompt

├── knowledge\_pack\_id: FK  \# 綁定的知識庫

├── capabilities: list     \# 可使用的工具 (P1)

└── config: dict           \# temperature, max\_tokens 等

Agent Session (動態)

├── session\_id: UUID

├── agent\_def\_id: FK

├── project\_id: FK

├── status: enum           \# idle | thinking | waiting\_review | done | error

├── memory: AgentMemory

├── workspace: AgentWorkspace

└── context\_window: list\[Message\]

### 2.2 Agent 生命週期

                    ┌──────────┐

                    │  CREATED │

                    └────┬─────┘

                         │ workflow engine dispatch

                         ▼

                    ┌──────────┐

              ┌────►│  ACTIVE  │◄────┐

              │     └────┬─────┘     │

              │          │           │

              │    LLM 呼叫完成      │ 被打回重做

              │          │           │

              │          ▼           │

              │     ┌──────────┐    │

              │     │ PRODUCED │────┘

              │     └────┬─────┘

              │          │ review 通過

              │          ▼

              │     ┌──────────┐

              │     │   DONE   │

              │     └──────────┘

              │

              │ 重啟 (新 iteration)

              └──────────────────────

**狀態轉換規則**：

| 當前狀態 | 觸發事件 | 下一狀態 |
| :---- | :---- | :---- |
| CREATED | Workflow Engine dispatch | ACTIVE |
| ACTIVE | LLM 回應完成 | PRODUCED |
| PRODUCED | Review 通過 (Director/下游 Agent) | DONE |
| PRODUCED | Review 打回 | ACTIVE (新 iteration) |
| ACTIVE | LLM 錯誤 / 超時 | ERROR |
| ERROR | 重試 (max 3 次) | ACTIVE |

### 2.3 Session Manager

class SessionManager:

    """管理所有 Agent Session 的生命週期"""

    

    async def create\_session(

        self, project\_id: UUID, agent\_def\_id: UUID

    ) \-\> AgentSession:

        """建立新 session，初始化 memory 和 workspace"""

    

    async def dispatch(

        self, session\_id: UUID, input\_context: Context

    ) \-\> Artifact:

        """

        執行 agent：

        1\. 載入 knowledge pack (system prompt \+ docs)

        2\. 組裝 context window (input \+ memory \+ 上游 artifacts)

        3\. 呼叫 LLM

        4\. 解析並儲存 artifact

        5\. 更新 memory

        """

    

    async def get\_context\_for\_agent(

        self, session: AgentSession

    ) \-\> list\[Message\]:

        """

        組裝 context window：

        \- system prompt (from knowledge pack)

        \- project-level context (需求描述)

        \- 上游 agent 的 artifacts (由 workflow engine 決定哪些)

        \- agent 自己的 memory (前幾輪的重點摘要)

        \- 當前任務指令

        """

    

    async def terminate(self, session\_id: UUID) \-\> None:

        """結束 session，持久化最終 memory"""

### 2.4 Memory 設計

每個 Agent Session 有兩層 memory：

**Short-term Memory（Session 內）**：

- 儲存在 Redis，key \= `session:{session_id}:memory`  
- 包含本次 session 所有的 LLM 對話紀錄  
- Session 結束時持久化到 PostgreSQL

**Long-term Memory（跨 Session）**：

- 儲存在 PostgreSQL `agent_memories` 表  
- 每次 session 結束時，用 LLM 摘要關鍵決策，存入 long-term  
- 下次同 project 的同 agent 啟動時自動載入

CREATE TABLE agent\_memories (

    id UUID PRIMARY KEY DEFAULT gen\_random\_uuid(),

    project\_id UUID NOT NULL REFERENCES projects(id),

    agent\_def\_id UUID NOT NULL REFERENCES agent\_definitions(id),

    session\_id UUID NOT NULL REFERENCES agent\_sessions(id),

    summary TEXT NOT NULL,          \-- LLM 產生的摘要

    key\_decisions JSONB DEFAULT '\[\]', \-- 關鍵決策列表

    created\_at TIMESTAMPTZ DEFAULT NOW()

);

### 2.5 Workspace（產出物管理）

CREATE TABLE artifacts (

    id UUID PRIMARY KEY DEFAULT gen\_random\_uuid(),

    project\_id UUID NOT NULL REFERENCES projects(id),

    session\_id UUID NOT NULL REFERENCES agent\_sessions(id),

    agent\_role VARCHAR(50) NOT NULL,

    artifact\_type VARCHAR(50) NOT NULL,  \-- 'product\_spec', 'tech\_design', 'qa\_checklist'

    version INT NOT NULL DEFAULT 1,

    content\_md TEXT NOT NULL,             \-- Markdown 內容

    metadata JSONB DEFAULT '{}',

    status VARCHAR(20) DEFAULT 'draft',   \-- draft | approved | superseded

    created\_at TIMESTAMPTZ DEFAULT NOW()

);

每次 Agent 產出新版本，前一版標記為 `superseded`，保留完整歷史。

### 2.6 Context 傳遞機制

Agent 間透過 **Context Bus** 傳遞資訊：

@dataclass

class Context:

    project\_id: UUID

    current\_step: WorkflowStep

    upstream\_artifacts: list\[Artifact\]   \# 上游產出

    user\_input: str | None               \# 使用者原始需求

    director\_notes: str | None           \# Director 的指示

    iteration: int                       \# 當前迴圈次數

    max\_iterations: int                  \# 護欄

Workflow Engine 負責決定哪些 upstream artifacts 要傳給下游 Agent，避免 context window 爆掉。策略：

1. **全量傳遞**：artifact \< 4K tokens 時直接傳  
2. **摘要傳遞**：artifact \> 4K tokens 時，先用 LLM 產生摘要  
3. **引用傳遞**：只傳 artifact ID \+ 標題，Agent 需要時再拉全文

---

## 3\. 流程引擎

### 3.1 設計原則

**使用者永遠不碰 YAML/JSON。** 底層用 YAML 定義流程，但使用者接觸的是：

- **P0**：預設流程模板（選一個就能用）  
- **P1**：拖拉式流程圖 UI（進階自訂）

### 3.2 底層 YAML Schema

\# workflow\_schema.yaml

workflow:

  id: string                    \# unique identifier

  name: string                  \# 顯示名稱

  description: string           \# 說明

  version: int

  

  \# 流程步驟定義

  steps:

    \- id: string                \# step unique id, e.g. "pm\_draft"

      agent\_role: string        \# "pm" | "architect" | "qa" | "devops" | "director"

      task\_type: string         \# "draft" | "review" | "approve" | "revise"

      prompt\_override: string?  \# 可選，覆蓋 agent 預設任務提示

      

      \# DAG 依賴

      depends\_on: list\[string\]  \# 前置步驟 id 列表（全部完成才執行）

      

      \# 動態路由（LLM 決策點）

      routing:

        type: "static" | "llm\_decision"

        \# static: 固定走 next\_steps

        \# llm\_decision: Director 根據 context 決定

        next\_steps: list\[string\]        \# static 路由的下一步

        decision\_prompt: string?        \# llm\_decision 時給 Director 的 prompt

        options:                        \# llm\_decision 的可選路徑

          \- label: string

            target\_step: string

            condition\_hint: string      \# 給 LLM 的判斷提示

      

      \# 迴圈控制

      loop:

        enabled: bool

        max\_iterations: int     \# 預設 2

        escalate\_to: string     \# 超過次數後升級到哪個步驟（通常是人工審核）

  

  \# 護欄設定

  guardrails:

    max\_total\_steps: int        \# 整個流程最多執行幾步，防止無限迴圈

    timeout\_minutes: int        \# 整個流程超時時間

    require\_human\_approval:     \# 哪些步驟需要人工確認

      \- step\_id: string

### 3.3 預設流程模板

#### 模板 1：標準 Spec 流程（P0 預設）

workflow:

  id: "standard-spec"

  name: "標準 Spec 流程"

  description: "PM 起草 → Architect 技術審核 → QA 建立測試 → Director 最終審批"

  version: 1

  

  steps:

    \- id: "pm\_draft"

      agent\_role: "pm"

      task\_type: "draft"

      depends\_on: \[\]

      routing:

        type: "static"

        next\_steps: \["architect\_review"\]

    

    \- id: "architect\_review"

      agent\_role: "architect"

      task\_type: "review"

      depends\_on: \["pm\_draft"\]

      routing:

        type: "llm\_decision"

        decision\_prompt: "Review PM 的 spec，判斷技術可行性。"

        options:

          \- label: "通過，進入 QA"

            target\_step: "qa\_checklist"

            condition\_hint: "技術方案可行，無重大問題"

          \- label: "打回 PM 修改"

            target\_step: "pm\_revise"

            condition\_hint: "有技術問題需要 PM 調整需求"

      loop:

        enabled: true

        max\_iterations: 2

        escalate\_to: "director\_approve"

    

    \- id: "pm\_revise"

      agent\_role: "pm"

      task\_type: "revise"

      depends\_on: \["architect\_review"\]

      routing:

        type: "static"

        next\_steps: \["architect\_review"\]

    

    \- id: "qa\_checklist"

      agent\_role: "qa"

      task\_type: "draft"

      depends\_on: \["architect\_review"\]

      routing:

        type: "static"

        next\_steps: \["director\_approve"\]

    

    \- id: "director\_approve"

      agent\_role: "director"

      task\_type: "approve"

      depends\_on: \["qa\_checklist"\]

      routing:

        type: "llm\_decision"

        decision\_prompt: "最終審核所有產出物的品質與完整度。"

        options:

          \- label: "批准，產出文件"

            target\_step: "export"

            condition\_hint: "所有文件品質達標"

          \- label: "需要修改"

            target\_step: "pm\_revise"

            condition\_hint: "仍有需要改善的地方"

    

    \- id: "export"

      agent\_role: "system"

      task\_type: "export"

      depends\_on: \["director\_approve"\]

      routing:

        type: "static"

        next\_steps: \[\]

  

  guardrails:

    max\_total\_steps: 20

    timeout\_minutes: 30

    require\_human\_approval:

      \- step\_id: "director\_approve"

#### 模板 2：快速 Review

workflow:

  id: "quick-review"

  name: "快速 Review"

  description: "PM 起草 → Director 直接審批，適合小變更"

  version: 1

  steps:

    \- id: "pm\_draft"

      agent\_role: "pm"

      task\_type: "draft"

      depends\_on: \[\]

      routing:

        type: "static"

        next\_steps: \["director\_approve"\]

    \- id: "director\_approve"

      agent\_role: "director"

      task\_type: "approve"

      depends\_on: \["pm\_draft"\]

      routing:

        type: "static"

        next\_steps: \["export"\]

    \- id: "export"

      agent\_role: "system"

      task\_type: "export"

      depends\_on: \["director\_approve"\]

      routing:

        type: "static"

        next\_steps: \[\]

  guardrails:

    max\_total\_steps: 10

    timeout\_minutes: 10

    require\_human\_approval: \[\]

#### 模板 3：完整交付流程

workflow:

  id: "full-delivery"

  name: "完整交付流程"

  description: "PM → Architect → DevOps → QA → Director，含所有角色的完整流程"

  version: 1

  steps:

    \- id: "pm\_draft"

      agent\_role: "pm"

      task\_type: "draft"

      depends\_on: \[\]

      routing:

        type: "static"

        next\_steps: \["architect\_review", "devops\_review"\]  \# 並行

    \- id: "architect\_review"

      agent\_role: "architect"

      task\_type: "review"

      depends\_on: \["pm\_draft"\]

      routing:

        type: "llm\_decision"

        decision\_prompt: "審核技術架構可行性"

        options:

          \- label: "通過"

            target\_step: "qa\_checklist"

            condition\_hint: "架構可行"

          \- label: "打回"

            target\_step: "pm\_revise"

            condition\_hint: "需要修改"

      loop:

        enabled: true

        max\_iterations: 2

        escalate\_to: "director\_approve"

    \- id: "devops\_review"

      agent\_role: "devops"

      task\_type: "review"

      depends\_on: \["pm\_draft"\]

      routing:

        type: "static"

        next\_steps: \["qa\_checklist"\]

    \- id: "pm\_revise"

      agent\_role: "pm"

      task\_type: "revise"

      depends\_on: \["architect\_review"\]

      routing:

        type: "static"

        next\_steps: \["architect\_review"\]

    \- id: "qa\_checklist"

      agent\_role: "qa"

      task\_type: "draft"

      depends\_on: \["architect\_review", "devops\_review"\]  \# 等兩個都完成

      routing:

        type: "static"

        next\_steps: \["director\_approve"\]

    \- id: "director\_approve"

      agent\_role: "director"

      task\_type: "approve"

      depends\_on: \["qa\_checklist"\]

      routing:

        type: "llm\_decision"

        decision\_prompt: "最終審核"

        options:

          \- label: "批准"

            target\_step: "export"

            condition\_hint: "品質達標"

          \- label: "需改善"

            target\_step: "pm\_revise"

            condition\_hint: "需要修改"

    \- id: "export"

      agent\_role: "system"

      task\_type: "export"

      depends\_on: \["director\_approve"\]

      routing:

        type: "static"

        next\_steps: \[\]

  guardrails:

    max\_total\_steps: 30

    timeout\_minutes: 45

    require\_human\_approval:

      \- step\_id: "director\_approve"

### 3.4 Workflow Engine 實作

class WorkflowEngine:

    """DAG \+ LLM 動態路由的流程引擎"""

    

    def \_\_init\_\_(self, llm\_router: LLMRouter, session\_mgr: SessionManager):

        self.llm\_router \= llm\_router

        self.session\_mgr \= session\_mgr

    

    async def start(self, project\_id: UUID, template\_id: str) \-\> WorkflowRun:

        """

        啟動流程：

        1\. 載入 workflow template (YAML → Python DAG)

        2\. 找到所有 depends\_on=\[\] 的 root steps

        3\. dispatch 第一批 agent sessions

        """

    

    async def on\_step\_complete(self, run\_id: UUID, step\_id: str, artifact: Artifact):

        """

        某 step 完成時：

        1\. 更新 DAG 狀態

        2\. 檢查護欄 (max\_total\_steps, timeout)

        3\. 根據 routing type 決定下一步：

           \- static: 直接啟動 next\_steps

           \- llm\_decision: 呼叫 Director LLM 判斷

        4\. 檢查 next\_steps 的 depends\_on 是否全滿足

        5\. 滿足的 steps 進入執行佇列

        """

    

    async def \_llm\_route(

        self, run: WorkflowRun, step: WorkflowStep, context: Context

    ) \-\> str:

        """

        LLM 動態路由：

        \- 把當前 context \+ routing options 傳給 Director LLM

        \- LLM 回傳選擇的 option label

        \- 回傳對應的 target\_step id

        """

    

    async def \_check\_loop(self, run: WorkflowRun, step\_id: str) \-\> bool:

        """

        迴圈檢查：

        \- 計算該 step 已執行次數

        \- 超過 max\_iterations → escalate

        \- 未超過 → 允許回到上游 step

        """

### 3.5 DAG 狀態管理

CREATE TABLE workflow\_runs (

    id UUID PRIMARY KEY DEFAULT gen\_random\_uuid(),

    project\_id UUID NOT NULL REFERENCES projects(id),

    template\_id VARCHAR(100) NOT NULL,

    template\_snapshot JSONB NOT NULL,    \-- 快照，防止模板更新影響進行中的流程

    status VARCHAR(20) DEFAULT 'running', \-- running | completed | failed | timeout

    step\_executions JSONB DEFAULT '{}',   \-- { "step\_id": { count: N, last\_status: "..." } }

    current\_steps TEXT\[\] DEFAULT '{}',    \-- 目前正在執行的 step ids

    created\_at TIMESTAMPTZ DEFAULT NOW(),

    updated\_at TIMESTAMPTZ DEFAULT NOW()

);

CREATE TABLE step\_executions (

    id UUID PRIMARY KEY DEFAULT gen\_random\_uuid(),

    run\_id UUID NOT NULL REFERENCES workflow\_runs(id),

    step\_id VARCHAR(100) NOT NULL,

    iteration INT NOT NULL DEFAULT 1,

    session\_id UUID REFERENCES agent\_sessions(id),

    status VARCHAR(20) DEFAULT 'pending', \-- pending | running | completed | failed

    routing\_decision JSONB,               \-- LLM 路由決策記錄

    started\_at TIMESTAMPTZ,

    completed\_at TIMESTAMPTZ

);

### 3.6 P1：拖拉式流程圖 UI

- 前端使用 **React Flow**（MIT License）作為流程圖編輯器  
- 使用者拖拉 Agent 節點、連線定義依賴  
- 前端將圖轉換為上述 YAML schema，存入後端  
- 使用者只看到視覺化的流程圖，不碰 YAML

┌────────────────────────────────────────────┐

│  Workflow Designer (React Flow)            │

│                                            │

│  \[PM Agent\] ──► \[Architect\] ──► \[QA\]      │

│       │              │            │        │

│       ◄──────────────┘            │        │

│       (打回修改)                   ▼        │

│                            \[Director\]      │

│                                 │          │

│                                 ▼          │

│                            \[Export\]        │

│                                            │

│  每個節點可設定：角色、任務類型、迴圈次數   │

│  每條連線可設定：routing type、條件        │

└────────────────────────────────────────────┘

        │

        ▼ 前端自動轉換

    YAML schema (存入 DB)

---

## 4\. 知識庫封裝

### 4.1 Knowledge Pack 結構

知識庫是本產品的核心價值——讓每個 Agent 攜帶客戶特定的 domain knowledge。

@dataclass

class KnowledgePack:

    id: UUID

    name: str                        \# "Fintech PM 知識庫"

    description: str

    

    \# Prompt Template

    system\_prompt: str               \# Agent 的人設和行為指引

    task\_prompts: dict\[str, str\]     \# { "draft": "...", "review": "...", "revise": "..." }

    output\_template: str             \# 產出物的格式模板 (Markdown)

    

    \# Reference Documents

    documents: list\[KnowledgeDoc\]    \# 綁定的參考文件

    

    \# 設定

    config: KnowledgeConfig

### 4.2 資料模型

CREATE TABLE knowledge\_packs (

    id UUID PRIMARY KEY DEFAULT gen\_random\_uuid(),

    org\_id UUID NOT NULL REFERENCES organizations(id),

    name VARCHAR(200) NOT NULL,

    description TEXT,

    

    \-- Prompt Templates

    system\_prompt TEXT NOT NULL,

    task\_prompts JSONB DEFAULT '{}',

    output\_template TEXT,

    

    \-- 設定

    llm\_config JSONB DEFAULT '{}',   \-- model, temperature, max\_tokens

    

    created\_at TIMESTAMPTZ DEFAULT NOW(),

    updated\_at TIMESTAMPTZ DEFAULT NOW()

);

CREATE TABLE knowledge\_documents (

    id UUID PRIMARY KEY DEFAULT gen\_random\_uuid(),

    pack\_id UUID NOT NULL REFERENCES knowledge\_packs(id),

    title VARCHAR(500) NOT NULL,

    content TEXT,                     \-- 純文字內容（小文件直接存）

    file\_path VARCHAR(1000),         \-- MinIO 路徑（大文件）

    doc\_type VARCHAR(50),            \-- 'reference', 'template', 'example'

    

    \-- 向量搜尋用（P1）

    embedding\_status VARCHAR(20) DEFAULT 'pending',

    chunk\_count INT DEFAULT 0,

    

    created\_at TIMESTAMPTZ DEFAULT NOW()

);

\-- P1: 向量搜尋支援

CREATE TABLE document\_chunks (

    id UUID PRIMARY KEY DEFAULT gen\_random\_uuid(),

    doc\_id UUID NOT NULL REFERENCES knowledge\_documents(id),

    chunk\_index INT NOT NULL,

    content TEXT NOT NULL,

    embedding vector(1536),          \-- pgvector

    created\_at TIMESTAMPTZ DEFAULT NOW()

);

### 4.3 知識載入策略

Agent 啟動時，Knowledge Pack 的內容如何進入 context window：

1\. system\_prompt          → 永遠放在 context 最前面

2\. task\_prompts\[當前任務\]  → 接在 system prompt 後面

3\. reference documents    → 根據策略載入：

   

   策略 A (P0)：全量注入

   \- 文件總 tokens \< 8K → 全部塞進 context

   \- 適合知識庫較小的場景

   

   策略 B (P1)：RAG

   \- 文件已向量化 → 根據當前任務語意搜尋 top-K chunks

   \- 適合知識庫較大的場景

   

4\. output\_template        → 告訴 Agent 產出格式

### 4.4 知識庫管理 API

POST   /api/v1/knowledge-packs              \# 建立知識庫

GET    /api/v1/knowledge-packs              \# 列表

GET    /api/v1/knowledge-packs/{id}         \# 取得

PUT    /api/v1/knowledge-packs/{id}         \# 更新

DELETE /api/v1/knowledge-packs/{id}         \# 刪除

POST   /api/v1/knowledge-packs/{id}/documents       \# 上傳文件

DELETE /api/v1/knowledge-packs/{id}/documents/{did}  \# 刪除文件

POST   /api/v1/knowledge-packs/{id}/test    \# 測試：用當前知識庫跑一次 Agent 看效果

---

## 5\. 文件產出

### 5.1 工具選型比較

| 方案 | 授權 | 優點 | 缺點 | 評估 |
| :---- | :---- | :---- | :---- | :---- |
| **python-docx** | MIT | 純 Python，無外部依賴，精確控制格式 | 需手動處理 Markdown 解析 | ⭐ 主力方案 |
| **pypandoc** (Pandoc wrapper) | GPL (Pandoc) \+ MIT (wrapper) | Markdown → docx 一行搞定，支援模板 | 需安裝 Pandoc binary，GPL 需注意 | ⭐ 備選 |
| **docxtpl** | MIT | Jinja2 模板語法，適合固定格式 | 不適合動態結構 | 特定場景用 |

### 5.2 選定方案：python-docx \+ 自建 Markdown Parser

**理由**：

- 純 MIT，無 GPL 顧慮  
- 不需安裝額外 binary（Docker image 更乾淨）  
- 可精確控制輸出樣式（客戶品牌、頁首頁尾）

**實作架構**：

class DocxExporter:

    """Markdown → .docx 轉換器"""

    

    def \_\_init\_\_(self, template\_path: str | None \= None):

        """

        template\_path: .docx 模板檔（定義樣式、頁首頁尾）

        若無則使用預設樣式

        """

    

    def export(self, artifacts: list\[Artifact\], metadata: dict) \-\> bytes:

        """

        1\. 解析每個 artifact 的 Markdown

        2\. 用 python-docx 建立 Document

        3\. 套用樣式模板

        4\. 加入 metadata（專案名、日期、版本）

        5\. 回傳 .docx bytes

        """

    

    def \_parse\_markdown(self, md: str) \-\> list\[DocElement\]:

        """

        用 mistune (MIT) 解析 Markdown，轉成中間格式：

        \- Heading → DocElement(type='heading', level=1, text='...')

        \- Paragraph → DocElement(type='paragraph', text='...')

        \- List → DocElement(type='list', items=\[...\])

        \- Table → DocElement(type='table', headers=\[...\], rows=\[...\])

        \- Code → DocElement(type='code', language='...', text='...')

        """

    

    def \_render\_to\_docx(self, elements: list\[DocElement\], doc: Document):

        """將中間格式寫入 python-docx Document"""

### 5.3 樣式模板

提供預設 `.docx` 模板，定義：

- 標題樣式（Heading 1\~4）  
- 正文字體（思源黑體 / Noto Sans CJK）  
- 表格樣式  
- 頁首：專案名稱 \+ Logo  
- 頁尾：頁碼 \+ 日期

客戶可上傳自訂 `.docx` 模板覆蓋預設樣式。

---

## 6\. 部署架構

### 6.1 模式一：Docker Self-Hosted

\# docker-compose.yml

version: '3.8'

services:

  \# 前端

  web:

    build: ./frontend

    ports:

      \- "3000:80"

    environment:

      \- API\_URL=http://api:8000

  

  \# 後端 API

  api:

    build: ./backend

    ports:

      \- "8000:8000"

    environment:

      \- DATABASE\_URL=postgresql://user:pass@db:5432/agentplatform

      \- REDIS\_URL=redis://redis:6379

      \- MINIO\_ENDPOINT=minio:9000

      \- LLM\_PROVIDER=openai  \# or anthropic, local

      \- LLM\_API\_KEY=${LLM\_API\_KEY}

    depends\_on:

      \- db

      \- redis

      \- minio

  

  \# Agent Worker（處理長時間 LLM 呼叫）

  worker:

    build: ./backend

    command: python \-m agent\_worker

    environment:

      \- DATABASE\_URL=postgresql://user:pass@db:5432/agentplatform

      \- REDIS\_URL=redis://redis:6379

      \- LLM\_API\_KEY=${LLM\_API\_KEY}

    deploy:

      replicas: 2  \# 可依負載調整

    depends\_on:

      \- db

      \- redis

  

  \# 資料庫

  db:

    image: pgvector/pgvector:pg16

    volumes:

      \- pgdata:/var/lib/postgresql/data

    environment:

      \- POSTGRES\_DB=agentplatform

      \- POSTGRES\_USER=user

      \- POSTGRES\_PASSWORD=pass

  

  \# 快取 \+ 訊息佇列

  redis:

    image: redis:7-alpine

    volumes:

      \- redisdata:/data

  

  \# 物件儲存

  minio:

    image: minio/minio:latest

    command: server /data \--console-address ":9001"

    volumes:

      \- miniodata:/data

    environment:

      \- MINIO\_ROOT\_USER=minioadmin

      \- MINIO\_ROOT\_PASSWORD=minioadmin

volumes:

  pgdata:

  redisdata:

  miniodata:

**最低硬體需求**：

- CPU: 2 cores  
- RAM: 4 GB  
- Disk: 20 GB  
- 不需 GPU（LLM 呼叫走 API）

### 6.2 模式二：SaaS

┌─────────────────────────────────────────┐

│              CDN (CloudFront)           │

│              React SPA                   │

├─────────────────────────────────────────┤

│          Load Balancer (ALB)            │

├──────────┬──────────┬───────────────────┤

│ API Pod  │ API Pod  │ API Pod           │  ← ECS / K8s

├──────────┴──────────┴───────────────────┤

│ Worker Pod │ Worker Pod │ Worker Pod    │  ← Auto-scaling

├─────────────────────────────────────────┤

│ Aurora PostgreSQL │ ElastiCache (Redis)  │

│ S3 (物件儲存)                            │

└─────────────────────────────────────────┘

**SaaS 額外考量**：

- **多租戶**：`org_id` 作為所有資料表的租戶隔離欄位  
- **API Key 管理**：每個租戶自帶 LLM API Key（或使用平台提供的 pooled key）  
- **用量計費**：追蹤每個 org 的 LLM token 用量  
- **資料隔離**：S3 bucket 按 org 分 prefix

### 6.3 多租戶隔離策略

\-- 所有業務表都有 org\_id

CREATE TABLE projects (

    id UUID PRIMARY KEY,

    org\_id UUID NOT NULL REFERENCES organizations(id),

    name VARCHAR(500) NOT NULL,

    ...

);

\-- Row Level Security

ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

CREATE POLICY org\_isolation ON projects

    USING (org\_id \= current\_setting('app.current\_org\_id')::UUID);

---

## 7\. 技術棧選型

### 7.1 總覽

| 層級 | 技術 | 版本 | 授權 | 選擇理由 |
| :---- | :---- | :---- | :---- | :---- |
| **前端框架** | React | 18+ | MIT | 生態最成熟，元件庫豐富 |
| **前端語言** | TypeScript | 5+ | Apache-2.0 | 型別安全，大型專案必備 |
| **狀態管理** | Zustand | 4+ | MIT | 輕量，比 Redux 簡潔 |
| **API 層** | TanStack Query | 5+ | MIT | 伺服器狀態管理，快取、重試內建 |
| **流程圖 UI** | React Flow | 11+ | MIT | 拖拉式流程編輯器首選 |
| **UI 元件庫** | Ant Design | 5+ | MIT | 企業級元件，表格/表單完整 |
| **後端框架** | FastAPI | 0.110+ | MIT | 高效能，自動 OpenAPI 文件 |
| **ORM** | SQLAlchemy | 2.0+ | MIT | Python 標準 ORM，async 支援 |
| **DB Migration** | Alembic | 1.13+ | MIT | SQLAlchemy 官方 migration 工具 |
| **資料庫** | PostgreSQL | 16+ | PostgreSQL License | 穩定可靠，支援 JSONB \+ pgvector |
| **向量擴充** | pgvector | 0.7+ | PostgreSQL License | RAG 向量搜尋（P1） |
| **快取/佇列** | Redis | 7+ | BSD-3 (Redis 7\) | Session 快取 \+ Streams 訊息佇列 |
| **物件儲存** | MinIO | latest | AGPL-3.0 (server) | S3 相容，self-hosted 檔案儲存 |
| **LLM 整合** | LiteLLM | latest | MIT | 統一 100+ LLM provider 的呼叫介面 |
| **Markdown 解析** | mistune | 3+ | BSD-3 | 快速 Markdown parser |
| **Docx 產出** | python-docx | 1.1+ | MIT | .docx 生成，無外部依賴 |
| **WebSocket** | FastAPI WebSocket | built-in | MIT | 即時討論推送 |
| **任務佇列** | arq | 0.26+ | MIT | 輕量 async 任務佇列（基於 Redis） |
| **容器化** | Docker \+ Compose | latest | Apache-2.0 | 標準部署方案 |
| **認證** | FastAPI Users \+ JWT | latest | MIT | 使用者管理 \+ JWT 認證 |
| **即時通訊** | Redis Pub/Sub | built-in | \- | Agent 間訊息 \+ 前端 WebSocket 推送 |

### 7.2 LLM Provider 抽象層

使用 **LiteLLM** 作為統一介面：

from litellm import acompletion

class LLMAdapter:

    """統一的 LLM 呼叫介面"""

    

    PROVIDER\_MAP \= {

        "openai": "gpt-4o",

        "anthropic": "claude-sonnet-4-20250514",

        "local": "ollama/llama3",  \# 透過 Ollama

    }

    

    async def complete(

        self,

        messages: list\[dict\],

        model: str | None \= None,

        temperature: float \= 0.7,

        max\_tokens: int \= 4096,

        org\_config: OrgLLMConfig | None \= None,

    ) \-\> str:

        """

        1\. 確定使用哪個 model（org 設定 \> 傳入參數 \> 系統預設）

        2\. 確定 API key（org 自帶 \> 系統 pooled key）

        3\. 透過 LiteLLM 呼叫

        4\. 記錄 token 用量

        """

        model \= org\_config.preferred\_model if org\_config else (model or self.default\_model)

        

        response \= await acompletion(

            model=model,

            messages=messages,

            temperature=temperature,

            max\_tokens=max\_tokens,

            api\_key=org\_config.api\_key if org\_config else self.system\_key,

        )

        

        \# 記錄用量

        await self.\_track\_usage(org\_config.org\_id, response.usage)

        

        return response.choices\[0\].message.content

### 7.3 MinIO 授權說明

MinIO server 是 AGPL-3.0，但：

- 我們是**使用者**（透過 S3 API 呼叫），不修改 MinIO 原始碼  
- AGPL 要求的是修改後的 MinIO server 需開源，不影響我們的應用程式碼  
- SaaS 模式直接用 AWS S3，完全避開 AGPL  
- 若仍有顧慮，替代方案：**SeaweedFS**（Apache-2.0）

---

## 8\. ADR（架構決策記錄）

### ADR-001: 自建 Agent Orchestration 而非使用現有框架

**狀態**：已決定

**背景**：市面上有 LangChain、CrewAI、AutoGen 等 Agent 框架。

**決定**：自建輕量 orchestration 層。

**理由**：

1. 現有框架過於通用，我們需要的是「有狀態的 session \+ workflow DAG」，這些框架的抽象不完全匹配  
2. 減少外部依賴，避免上游框架 breaking change 影響穩定性  
3. 核心邏輯其實不複雜：session 管理 \+ DAG 排程 \+ LLM 呼叫，自建可控性最高  
4. 用 LiteLLM 處理 LLM provider 差異已足夠，不需要完整 Agent 框架

**風險**：需自行維護 orchestration 邏輯，但程式碼量預估 \< 2000 行。

---

### ADR-002: Redis Streams 作為 Agent 間通訊機制

**狀態**：已決定

**背景**：Agent 間需要非同步通訊（一個 Agent 完成後通知 Workflow Engine）。

**選項**：

- A) RabbitMQ — 功能完整但部署重  
- B) Redis Streams — 輕量，Redis 已存在於架構中  
- C) PostgreSQL LISTEN/NOTIFY — 最輕量但不持久

**決定**：Redis Streams（選項 B）

**理由**：

1. Redis 已是架構必備元件（session 快取），不增加新依賴  
2. Streams 支援 consumer group，worker 可水平擴展  
3. 訊息持久化（相比 Pub/Sub），worker 重啟不丟訊息  
4. 效能遠超過需求（我們的訊息量不大）

---

### ADR-003: python-docx 而非 Pandoc 作為文件產出工具

**狀態**：已決定

**背景**：需要將 Markdown 產出物轉換為 .docx。

**選項**：

- A) Pandoc (pypandoc) — 一行轉換，但需安裝 binary，Pandoc 本身 GPL  
- B) python-docx \+ mistune — 純 Python，MIT，需自建轉換邏輯  
- C) WeasyPrint → PDF → docx — 路徑太長，轉換品質差

**決定**：python-docx \+ mistune（選項 B）

**理由**：

1. 全 MIT 授權，無 GPL 顧慮  
2. Docker image 更乾淨，不需安裝 Pandoc binary  
3. 可精確控制輸出樣式（客戶品牌模板）  
4. Markdown → docx 的轉換邏輯不複雜，約 300\~500 行程式碼

---

### ADR-004: 預設模板 \+ 拖拉 UI 取代直接 YAML 編輯

**狀態**：已決定

**背景**：Product Spec v3 提到使用者提供 YAML/JSON workflow template，但老闆認為對一般使用者太技術。

**決定**：

- P0：提供 3\~5 個預設流程模板，使用者選擇即可  
- P1：React Flow 拖拉式流程圖 UI  
- YAML/JSON 是內部格式，使用者永遠不直接接觸

**理由**：

1. 降低使用門檻，非技術使用者也能上手  
2. 預設模板覆蓋 80% 場景（標準 Spec、快速 Review、完整交付）  
3. React Flow 是成熟的 MIT 開源方案，P1 實作成本可控  
4. YAML schema 仍保留，作為進階 API / CLI 使用者的底層接口

---

### ADR-005: PostgreSQL \+ pgvector 而非獨立向量資料庫

**狀態**：已決定

**背景**：知識庫的 RAG 功能需要向量搜尋。

**選項**：

- A) Pinecone / Weaviate — 專業向量 DB，但增加外部依賴  
- B) pgvector — PostgreSQL 擴充，與主 DB 同一個  
- C) ChromaDB — 輕量，但不適合生產環境

**決定**：pgvector（選項 B）

**理由**：

1. 不增加新的基礎設施元件  
2. 向量搜尋與 relational query 可在同一個 SQL 裡做 JOIN  
3. 對我們的資料規模（每個知識庫幾十到幾百份文件）pgvector 效能足夠  
4. 官方 Docker image `pgvector/pgvector:pg16` 開箱即用

---

### ADR-006: arq 作為任務佇列而非 Celery

**狀態**：已決定

**背景**：Agent 的 LLM 呼叫是耗時操作（10\~60 秒），需要非同步處理。

**選項**：

- A) Celery — 老牌，功能全，但 heavy \+ 需要額外 broker  
- B) arq — 輕量 async 任務佇列，基於 Redis  
- C) Dramatiq — 中間路線

**決定**：arq（選項 B）

**理由**：

1. 原生 async，與 FastAPI 的 async 生態一致  
2. 基於 Redis（已在架構中），不增加依賴  
3. 我們的任務類型單純（LLM 呼叫 \+ 文件產出），不需要 Celery 的複雜功能  
4. 程式碼量小，容易理解和除錯

---

## 附錄 A：資料庫 ER 圖

organizations

├── id (PK)

├── name

├── plan\_type         \# free | pro | enterprise

└── llm\_config (JSONB)

users

├── id (PK)

├── org\_id (FK → organizations)

├── email

├── role              \# admin | member

└── hashed\_password

projects

├── id (PK)

├── org\_id (FK → organizations)

├── name

├── description

├── created\_by (FK → users)

└── status            \# draft | running | completed

agent\_definitions

├── id (PK)

├── org\_id (FK → organizations)

├── role              \# pm | architect | qa | devops | director

├── display\_name

├── knowledge\_pack\_id (FK → knowledge\_packs)

└── config (JSONB)

knowledge\_packs

├── id (PK)

├── org\_id (FK → organizations)

├── name

├── system\_prompt

├── task\_prompts (JSONB)

└── output\_template

knowledge\_documents

├── id (PK)

├── pack\_id (FK → knowledge\_packs)

├── title

├── content / file\_path

└── doc\_type

workflow\_templates

├── id (PK)

├── org\_id (FK, nullable for system templates)

├── name

├── definition (JSONB)  \# YAML 轉 JSON 存入

└── is\_system           \# true \= 預設模板

workflow\_runs

├── id (PK)

├── project\_id (FK → projects)

├── template\_id (FK → workflow\_templates)

├── template\_snapshot (JSONB)

├── status

└── current\_steps

agent\_sessions

├── id (PK)

├── project\_id (FK)

├── agent\_def\_id (FK)

├── run\_id (FK → workflow\_runs)

├── status

└── created\_at

artifacts

├── id (PK)

├── project\_id (FK)

├── session\_id (FK)

├── artifact\_type

├── version

├── content\_md

└── status

step\_executions

├── id (PK)

├── run\_id (FK → workflow\_runs)

├── step\_id

├── session\_id (FK)

├── iteration

├── status

└── routing\_decision (JSONB)

agent\_memories

├── id (PK)

├── project\_id (FK)

├── agent\_def\_id (FK)

├── session\_id (FK)

├── summary

└── key\_decisions (JSONB)

---

## 附錄 B：API 路由總覽

\# 認證

POST   /api/v1/auth/register

POST   /api/v1/auth/login

POST   /api/v1/auth/refresh

\# 組織

GET    /api/v1/org

PUT    /api/v1/org

PUT    /api/v1/org/llm-config

\# 專案

POST   /api/v1/projects

GET    /api/v1/projects

GET    /api/v1/projects/{id}

DELETE /api/v1/projects/{id}

\# Agent 定義

POST   /api/v1/agents

GET    /api/v1/agents

GET    /api/v1/agents/{id}

PUT    /api/v1/agents/{id}

DELETE /api/v1/agents/{id}

\# 知識庫

POST   /api/v1/knowledge-packs

GET    /api/v1/knowledge-packs

GET    /api/v1/knowledge-packs/{id}

PUT    /api/v1/knowledge-packs/{id}

DELETE /api/v1/knowledge-packs/{id}

POST   /api/v1/knowledge-packs/{id}/documents

DELETE /api/v1/knowledge-packs/{id}/documents/{did}

\# 流程模板

GET    /api/v1/workflow-templates          \# 列出（含系統預設）

POST   /api/v1/workflow-templates          \# 建立自訂模板 (P1)

GET    /api/v1/workflow-templates/{id}

PUT    /api/v1/workflow-templates/{id}

DELETE /api/v1/workflow-templates/{id}

\# 流程執行

POST   /api/v1/projects/{id}/runs         \# 啟動流程（帶 template\_id \+ 使用者輸入）

GET    /api/v1/projects/{id}/runs          \# 歷史

GET    /api/v1/runs/{run\_id}               \# 執行狀態

GET    /api/v1/runs/{run\_id}/steps         \# 步驟細節

POST   /api/v1/runs/{run\_id}/approve       \# 人工審批

\# 產出物

GET    /api/v1/projects/{id}/artifacts

GET    /api/v1/artifacts/{id}

GET    /api/v1/artifacts/{id}/download      \# .docx 下載

\# WebSocket

WS     /ws/runs/{run\_id}                   \# 即時推送 Agent 討論過程

---

## 附錄 C：P0 開發里程碑建議

| 階段 | 範圍 | 預估時間 |
| :---- | :---- | :---- |
| **M1：基礎骨架** | FastAPI \+ DB \+ Auth \+ React 空殼 | 1 週 |
| **M2：Agent Runtime** | Session Manager \+ LLM Adapter \+ 單一 Agent 可跑 | 1 週 |
| **M3：Workflow Engine** | DAG 解析 \+ 預設模板 \+ 迴圈控制 | 1.5 週 |
| **M4：知識庫** | Knowledge Pack CRUD \+ 全量注入 | 1 週 |
| **M5：前端 Chat UI** | WebSocket \+ Agent 討論即時顯示 | 1 週 |
| **M6：文件產出** | Markdown → .docx \+ 下載 | 0.5 週 |
| **M7：整合測試** | End-to-End 流程跑通 \+ 修 bug | 1 週 |
| **合計** |  | **\~7 週** |

---

*此文件為 Architect Agent 根據 Product Spec v3 與 Director 修正意見產出的技術架構方案，供 Coder 團隊作為開發依據。*  
