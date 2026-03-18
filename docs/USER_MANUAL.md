# Agent-Platform MVP — 用户手册

> **版本:** 1.0.0-MVP  
> **适用对象:** 开发者、产品经理、技术团队负责人  
> **更新日期:** 2026-03-18

---

## 目录

1. [系统要求和安装](#1-系统要求和安装)
2. [快速开始（5 分钟 Demo）](#2-快速开始5-分钟-demo)
3. [基本概念](#3-基本概念)
4. [使用指南](#4-使用指南)
   - 4.1 [用户注册与登录](#41-用户注册与登录)
   - 4.2 [创建项目](#42-创建项目)
   - 4.3 [创建工作流](#43-创建工作流)
   - 4.4 [配置角色和知识库](#44-配置角色和知识库)
   - 4.5 [运行工作流](#45-运行工作流)
   - 4.6 [监视进度（WebSocket）](#46-监视进度websocket)
   - 4.7 [下载产出物（.docx）](#47-下载产出物docx)
5. [API 参考](#5-api-参考)
6. [配置参考](#6-配置参考)
7. [故障排除](#7-故障排除)
8. [FAQ](#8-faq)

---

## 1. 系统要求和安装

### 1.1 系统要求

#### 最低配置

| 组件 | 最低要求 |
|------|---------|
| **操作系统** | macOS 12+, Ubuntu 20.04+, Windows 10 (WSL2) |
| **CPU** | 2 核心 |
| **内存** | 4GB RAM |
| **磁盘** | 10GB 可用空间 |
| **Python** | 3.12+ |
| **Node.js** | 18+ |
| **Redis** | 6+ |

#### 推荐配置

| 组件 | 推荐配置 |
|------|---------|
| **CPU** | 4+ 核心 |
| **内存** | 8GB+ RAM |
| **磁盘** | 50GB SSD |
| **网络** | 10Mbps+ 宽带（用于 LLM API 调用）|

#### 外部依赖

| 依赖 | 说明 | 获取方式 |
|------|------|---------|
| **LLM API Key** | 必须，用于 Agent 推理 | [OpenRouter](https://openrouter.ai) 免费申请 |
| **Docker** | 可选，用于生产部署 | [docker.com](https://docker.com) |
| **Redis** | 必须，用于 Agent Worker 任务队列 | 随系统包管理器安装 |

### 1.2 安装 Redis

**macOS:**
```bash
brew install redis
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

**验证 Redis:**
```bash
redis-cli ping
# 预期输出: PONG
```

### 1.3 克隆与初始化

```bash
# 克隆仓库（假设已有代码目录）
cd /path/to/agent-platform

# 查看目录结构
ls -la
# 应见: backend/ frontend/ docker-compose.yml .env.example README.md
```

### 1.4 环境变量配置

```bash
# 复制模板
cp .env.example .env

# 打开编辑器配置
nano .env   # 或 vim .env / code .env
```

**必须配置的变量:**

```env
# ==========================================
# LLM 配置 (必须)
# ==========================================
LLM_API_KEY=sk-or-v1-xxxxxxxxxxxx    # OpenRouter API Key
LLM_PROVIDER=openrouter               # 使用 OpenRouter 代理多种模型
LLM_MODEL=google/gemini-2.0-flash-exp # 默认使用 Gemini Flash (低成本)

# ==========================================
# 安全配置 (必须)
# ==========================================
SECRET_KEY=your-random-32-char-string  # JWT 签名密钥
ACCESS_TOKEN_EXPIRE_MINUTES=30

# ==========================================
# 数据库配置 (可选, 默认 SQLite)
# ==========================================
# DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/agentplatform

# ==========================================
# Redis 配置 (可选, 默认本地 Redis)
# ==========================================
# REDIS_URL=redis://localhost:6379/0
```

**获取 OpenRouter API Key:**

1. 访问 https://openrouter.ai
2. 点击 "Sign Up" 注册账号
3. 在 Dashboard → API Keys 创建新 Key
4. 复制 `sk-or-v1-xxx...` 格式的 Key 到 `.env`

> 💡 **提示:** OpenRouter 提供多种免费模型，包括 Gemini Flash，适合开发测试。

### 1.5 后端安装

```bash
cd backend

# 创建 Python 虚拟环境
python3 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate         # macOS / Linux
# .venv\Scripts\activate.bat     # Windows CMD
# .venv\Scripts\Activate.ps1     # Windows PowerShell

# 安装 Python 依赖
pip install -r requirements.txt

# 验证安装
python -c "import fastapi; print('FastAPI OK')"
python -c "import sqlalchemy; print('SQLAlchemy OK')"
python -c "import docx; print('python-docx OK')"
```

### 1.6 数据库初始化

```bash
# 在 backend 目录下，激活虚拟环境后执行
mkdir -p data exports

# 初始化数据库表结构
python init_db.py

# 预期输出:
# Creating tables...
# Loading default knowledge packs...
# Database initialized successfully!
```

### 1.7 前端安装

```bash
cd ../frontend

# 安装 Node.js 依赖
npm install

# 验证安装
npm list react          # 应显示 react@18.x.x
npm list antd           # 应显示 antd@5.x.x
```

### 1.8 Docker 安装（推荐用于生产）

```bash
# 确保 Docker 和 Docker Compose 已安装
docker --version          # Docker 24+
docker-compose --version  # Docker Compose v2+

# 配置环境变量
cp .env.example .env
# 编辑 .env 设置 LLM_API_KEY 和 SECRET_KEY

# 一键启动所有服务
./start.sh
# 或:
docker-compose up -d

# 初始化数据库
docker-compose exec api python init_db.py

# 查看服务状态
docker-compose ps
```

---

## 2. 快速开始（5 分钟 Demo）

### 2.1 启动服务

打开三个终端窗口（或使用 tmux/screen）：

**终端 1 — 后端 API:**
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 看到以下输出表示启动成功:
# INFO:     Application startup complete.
# INFO:     Uvicorn running on http://0.0.0.0:8000
```

**终端 2 — Agent Worker:**
```bash
cd backend
source .venv/bin/activate
python -m agent_worker

# 看到以下输出表示 Worker 就绪:
# Worker started, listening for tasks...
# Connected to Redis: localhost:6379
```

**终端 3 — 前端:**
```bash
cd frontend
npm run dev

# 看到以下输出表示前端就绪:
# VITE v5.x.x  ready in 800ms
# ➜  Local:   http://localhost:5173/
```

### 2.2 访问系统

在浏览器打开：**http://localhost:5173**

### 2.3 注册账号

1. 点击 **"注册"** 按钮
2. 填写表单：

```
姓名: Demo User
邮件: demo@example.com
密码: Demo@123456
组织名称: My Company
```

3. 点击 **"注册"** → 自动跳转到 Dashboard

### 2.4 创建第一个项目

1. 在 Dashboard 点击 **"+ 新建项目"**
2. 填写项目信息：

```
项目名称: 在线书店
项目描述: 一个支持图书购买、用户评论和推荐系统的电商平台
```

3. 点击 **"创建"**

### 2.5 启动 AI 协作流程

1. 进入刚创建的项目
2. 点击 **"启动协作流程"**
3. 选择工作流模板: **"标准 Spec 流程"**
4. 在需求输入框填写：

```
请为在线书店系统设计完整规格：
- 用户注册/登录（支持 OAuth）
- 图书搜索与筛选（作者、类别、价格）
- 购物车与结账
- 用户评论与评分
- 个性化推荐（基于历史购买）
- 管理后台（库存管理、订单管理）
```

5. 点击 **"开始协作"**

### 2.6 观察 Agent 协作

切换到 **"工作流执行"** 标签页，你将实时看到：

```
[10:23:01] PM Agent: 正在分析需求，撰写产品规格初稿...
[10:23:15] PM Agent: ✅ 产品规格完成 (1,245 字)
[10:23:16] Architect Agent: 收到规格，开始技术方案设计...
[10:23:31] Architect Agent: ✅ 技术方案完成 (987 字)
[10:23:31] QA Agent: 开始制定测试策略...
[10:23:45] QA Agent: ✅ 测试计划完成 (654 字)
[10:23:46] Director Agent: 最终审核中...
[10:24:01] Director Agent: ✅ 审核通过，准备生成文档
[10:24:02] System: 正在生成 .docx 文档...
[10:24:03] ✅ 工作流完成！文档已就绪
```

### 2.7 下载产出文件

在 **"产出物"** 标签页，点击下载：
- `online_bookstore_spec.docx` — 完整规格文件（含 PM + Architect + QA + Director 产出）

🎉 **完成！** 整个流程约 2-3 分钟（取决于 LLM 响应速度）。

---

## 3. 基本概念

### 3.1 Workflow（工作流）

**定义:** 由多个有序步骤组成的自动化流程，使用 DAG（有向无环图）描述步骤间的依赖关系。

**核心属性:**

| 属性 | 说明 |
|------|------|
| `workflow_id` | 唯一标识符 |
| `name` | 工作流名称（如"标准 Spec 流程"）|
| `steps` | 步骤列表（DAG 节点）|
| `template` | 预定义模板（`standard_spec` / `quick_review` / `full_delivery`）|

**工作流模板:**

```
标准 Spec 流程 (standard_spec):
  PM → Architect → QA → Director → System(DOCX)
  约 3-5 分钟

快速 Review 流程 (quick_review):
  PM → Director → System(DOCX)
  约 1-2 分钟

完整交付流程 (full_delivery):
  PM → Architect + DevOps(并行) → QA → Director → System(DOCX)
  约 5-8 分钟
```

**Workflow 状态机:**

```
PENDING → RUNNING → COMPLETED
                 ↘ FAILED
                 ↘ PAUSED (等待人工审批)
```

### 3.2 Agent（智能体）

**定义:** 具有特定角色和专业能力的 AI 实体，通过 LLM 驱动，能够理解需求、生成内容、与其他 Agent 协作。

**内置 Agent 角色:**

| 角色 ID | 显示名称 | 职责 |
|---------|---------|------|
| `product_manager` | 产品经理 | 需求分析、PRD 撰写、用户故事 |
| `architect` | 软件架构师 | 技术方案、系统设计、可行性评估 |
| `qa_engineer` | QA 工程师 | 测试计划、验收标准、风险识别 |
| `devops_engineer` | DevOps 工程师 | 部署方案、基础设施、CI/CD 规划 |
| `director` | 总监 | 最终审核、质量把关、决策批准 |
| `system` | 系统 | 文档生成、工作流收尾（非 LLM 角色）|

**Agent Session 生命周期:**

```python
# 概念示意（非执行代码）
session = {
    "id": "sess-uuid",
    "role": "product_manager",
    "status": "RUNNING",           # CREATED | RUNNING | PAUSED | COMPLETED | FAILED
    "short_term_memory": {...},    # 当前轮次上下文
    "long_term_memory": {...},     # 跨步骤持久化知识
    "knowledge_pack": {...},       # 角色专属知识库
}
```

### 3.3 Artifact（产出物）

**定义:** Agent 在工作流执行过程中产出的内容，以 Markdown 格式存储，可导出为 `.docx` 文件。

**Artifact 类型:**

| 类型 ID | 描述 |
|---------|------|
| `product_spec` | 产品规格说明书 |
| `technical_design` | 技术设计方案 |
| `qa_checklist` | 测试/QA 检查清单 |
| `general_document` | 通用文档 |

**Artifact 数据结构:**

```json
{
  "id": "art-uuid-1234",
  "workflow_run_id": "run-uuid-5678",
  "artifact_type": "product_spec",
  "title": "在线书店产品规格 v1.0",
  "content": "# 产品规格\n\n## 用户故事\n...",
  "metadata": {
    "author": "product_manager",
    "created_at": "2026-03-18T10:23:15Z",
    "version": "1.0",
    "tags": ["spec", "ecommerce", "bookstore"]
  }
}
```

### 3.4 Role（角色）

**定义:** Agent 的职业身份配置，包含系统提示、能力范围和知识库引用。

**角色与工作流的关系:**

```
WorkflowStep
  └── agent_role: "product_manager"
        └── RoleTemplate
              ├── system_prompt: "你是一名经验丰富的产品经理..."
              ├── capabilities: ["需求分析", "用户研究", "PRD 撰写"]
              └── knowledge_pack_ids: ["general_product_knowledge", "best_practices"]
```

---

## 4. 使用指南

### 4.1 用户注册与登录

#### 注册

```
POST /api/v1/auth/register

请求体:
{
  "name": "张三",
  "email": "zhangsan@example.com",
  "password": "SecurePassword123!",
  "org_name": "我的公司"
}

响应:
{
  "user_id": "usr-uuid",
  "email": "zhangsan@example.com",
  "org_id": "org-uuid",
  "access_token": "eyJhbGci..."
}
```

#### 登录

```
POST /api/v1/auth/login

请求体:
{
  "email": "zhangsan@example.com",
  "password": "SecurePassword123!"
}

响应:
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### 在后续请求中使用 Token

所有需要认证的 API 请求，需在 Header 中携带 JWT Token：

```bash
curl -H "Authorization: Bearer eyJhbGci..." \
     http://localhost:8000/api/v1/projects
```

### 4.2 创建项目

#### 通过 UI

1. 登录后进入 Dashboard
2. 点击右上角 **"+ 新建项目"** 按钮
3. 填写项目名称和描述
4. 点击 **"创建项目"**

#### 通过 API

```bash
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "在线书店",
    "description": "一个现代化的电商平台，专注图书销售"
  }'
```

**响应:**
```json
{
  "id": "proj-uuid-1234",
  "name": "在线书店",
  "description": "一个现代化的电商平台，专注图书销售",
  "org_id": "org-uuid",
  "created_at": "2026-03-18T10:00:00Z",
  "status": "active"
}
```

### 4.3 创建工作流

#### 使用预设模板（推荐）

```bash
curl -X POST http://localhost:8000/api/v1/workflows/runs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "proj-uuid-1234",
    "template": "standard_spec",
    "input": {
      "requirement": "设计一个在线书店系统，支持用户注册、图书搜索、购物车和支付功能"
    }
  }'
```

#### 使用自定义工作流定义

```bash
curl -X POST http://localhost:8000/api/v1/workflows/runs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "proj-uuid-1234",
    "definition": {
      "name": "我的自定义流程",
      "steps": [
        {
          "id": "step-1",
          "name": "需求分析",
          "agent_role": "product_manager",
          "depends_on": []
        },
        {
          "id": "step-2",
          "name": "架构设计",
          "agent_role": "architect",
          "depends_on": ["step-1"]
        },
        {
          "id": "step-3",
          "name": "文档生成",
          "agent_role": "system",
          "depends_on": ["step-2"]
        }
      ]
    },
    "input": {
      "requirement": "..."
    }
  }'
```

**工作流定义结构说明:**

| 字段 | 类型 | 必须 | 说明 |
|------|------|------|------|
| `id` | string | ✅ | 步骤唯一 ID（在工作流内唯一）|
| `name` | string | ✅ | 步骤显示名称 |
| `agent_role` | string | ✅ | 执行角色 ID |
| `depends_on` | string[] | ✅ | 前置步骤 ID 列表（空数组表示起始步骤）|
| `timeout_seconds` | int | ❌ | 步骤超时时间（默认 300 秒）|
| `max_retries` | int | ❌ | 最大重试次数（默认 3）|
| `require_approval` | bool | ❌ | 是否需要人工审批（默认 false）|

### 4.4 配置角色和知识库

#### 查看可用角色

```bash
curl http://localhost:8000/api/v1/agents/roles \
  -H "Authorization: Bearer $TOKEN"
```

**响应示例:**
```json
{
  "roles": [
    {
      "id": "product_manager",
      "name": "产品经理",
      "description": "负责需求分析和产品规格撰写",
      "capabilities": ["需求分析", "用户研究", "PRD 撰写", "用户故事"],
      "knowledge_packs": ["general_product_knowledge"]
    },
    {
      "id": "architect",
      "name": "软件架构师",
      "description": "负责技术方案设计和可行性评估",
      "capabilities": ["系统设计", "技术选型", "性能评估"],
      "knowledge_packs": ["software_architecture_patterns"]
    }
  ]
}
```

#### 查看知识包

```bash
curl http://localhost:8000/api/v1/knowledge/packs \
  -H "Authorization: Bearer $TOKEN"
```

#### 向知识库添加自定义文档

```bash
curl -X POST http://localhost:8000/api/v1/knowledge/documents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "pack_id": "my_custom_pack",
    "title": "公司技术规范",
    "content": "# 技术规范\n\n## 编码规范\n- 使用 TypeScript...",
    "tags": ["standards", "typescript"]
  }'
```

> ⚠️ **注意:** 知识包 CRUD API 在 MVP 阶段部分实现，完整功能将在 v1.1 提供。

### 4.5 运行工作流

#### 启动工作流

创建工作流运行后，它将自动排入 Agent Worker 队列并开始执行。

```bash
# 查看工作流运行状态
curl http://localhost:8000/api/v1/workflows/runs/{run_id} \
  -H "Authorization: Bearer $TOKEN"
```

**响应示例:**
```json
{
  "id": "run-uuid-5678",
  "workflow_id": "wf-uuid",
  "project_id": "proj-uuid-1234",
  "status": "running",
  "current_step": "step-2",
  "steps": [
    {
      "id": "step-1",
      "name": "需求分析",
      "agent_role": "product_manager",
      "status": "completed",
      "started_at": "2026-03-18T10:23:00Z",
      "completed_at": "2026-03-18T10:23:15Z",
      "duration_ms": 15234
    },
    {
      "id": "step-2",
      "name": "架构设计",
      "agent_role": "architect",
      "status": "running",
      "started_at": "2026-03-18T10:23:16Z"
    }
  ],
  "created_at": "2026-03-18T10:22:58Z"
}
```

#### 处理人工审批请求

如果工作流步骤配置了 `require_approval: true`，工作流将在该步骤暂停并等待审批：

```bash
# 查看待审批列表
curl http://localhost:8000/api/v1/workflows/approvals/pending \
  -H "Authorization: Bearer $TOKEN"

# 批准
curl -X POST http://localhost:8000/api/v1/workflows/approvals/{approval_id}/approve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"comment": "内容符合要求，批准通过"}'

# 拒绝（并提供反馈，Agent 可重新生成）
curl -X POST http://localhost:8000/api/v1/workflows/approvals/{approval_id}/reject \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"comment": "需要增加安全性章节，请重新生成"}'
```

#### 取消工作流

```bash
curl -X POST http://localhost:8000/api/v1/workflows/runs/{run_id}/cancel \
  -H "Authorization: Bearer $TOKEN"
```

### 4.6 监视进度（WebSocket）

#### 浏览器 JavaScript 示例

```javascript
class WorkflowMonitor {
  constructor(workflowId, token) {
    this.workflowId = workflowId;
    this.ws = null;
  }

  connect() {
    const wsUrl = `ws://localhost:8000/ws/workflows/${this.workflowId}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleEvent(data);
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      // 自动重连（可选）
      setTimeout(() => this.connect(), 3000);
    };
  }

  handleEvent(event) {
    switch (event.event_type) {
      case 'step_started':
        this.onStepStarted(event);
        break;
      case 'step_completed':
        this.onStepCompleted(event);
        break;
      case 'agent_output':
        this.onAgentOutput(event);
        break;
      case 'workflow_completed':
        this.onWorkflowCompleted(event);
        break;
      case 'workflow_failed':
        this.onWorkflowFailed(event);
        break;
    }
  }

  onStepStarted({ step_id, role, timestamp }) {
    console.log(`[${timestamp}] 🚀 步骤 ${step_id} 开始 (角色: ${role})`);
    // 更新 UI 进度条
    updateProgressBar(step_id, 'running');
  }

  onStepCompleted({ step_id, role, metadata, timestamp }) {
    const { duration_ms } = metadata;
    console.log(`[${timestamp}] ✅ 步骤 ${step_id} 完成，耗时 ${duration_ms}ms`);
    updateProgressBar(step_id, 'completed');
  }

  onAgentOutput({ role, content, timestamp }) {
    console.log(`[${timestamp}] 💬 ${role}: ${content}`);
    appendToFeed(role, content);
  }

  onWorkflowCompleted({ metadata, timestamp }) {
    const { artifacts } = metadata;
    console.log(`[${timestamp}] 🎉 工作流完成！可下载文件: ${artifacts}`);
    showDownloadButtons(artifacts);
  }

  onWorkflowFailed({ content, timestamp }) {
    console.error(`[${timestamp}] ❌ 工作流失败: ${content}`);
    showErrorMessage(content);
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

// 使用示例
const monitor = new WorkflowMonitor('run-uuid-5678');
monitor.connect();
```

#### Python WebSocket 客户端示例

```python
import asyncio
import json
import websockets

async def monitor_workflow(run_id: str):
    uri = f"ws://localhost:8000/ws/workflows/{run_id}"
    
    async with websockets.connect(uri) as ws:
        print(f"Connected to workflow {run_id}")
        
        async for message in ws:
            event = json.loads(message)
            event_type = event['event_type']
            
            if event_type == 'step_started':
                print(f"▶  Step {event['step_id']} started ({event['role']})")
            
            elif event_type == 'step_completed':
                duration = event['metadata'].get('duration_ms', 'N/A')
                print(f"✅ Step {event['step_id']} completed in {duration}ms")
            
            elif event_type == 'agent_output':
                print(f"💬 {event['role']}: {event['content'][:100]}...")
            
            elif event_type == 'workflow_completed':
                artifacts = event['metadata'].get('artifacts', [])
                print(f"🎉 Workflow completed! Artifacts: {artifacts}")
                break
            
            elif event_type == 'workflow_failed':
                print(f"❌ Workflow failed: {event['content']}")
                break

# 运行
asyncio.run(monitor_workflow('run-uuid-5678'))
```

#### WebSocket 事件格式完整参考

```json
{
  "event_id": "evt-uuid",
  "workflow_id": "wf-uuid",
  "workflow_run_id": "run-uuid",
  "event_type": "step_completed",
  "step_id": "step-2",
  "role": "architect",
  "content": "技术方案设计完成：采用微服务架构...",
  "metadata": {
    "duration_ms": 12500,
    "output_type": "str",
    "token_count": 850,
    "artifacts": ["art-uuid-1"]
  },
  "timestamp": "2026-03-18T10:23:31Z",
  "status": "success"
}
```

| 事件类型 | 触发时机 | content 内容 |
|---------|---------|-------------|
| `step_started` | 步骤开始执行 | 空 |
| `step_completed` | 步骤执行完成 | 步骤输出摘要（≤500 字符）|
| `agent_output` | Agent 产出内容 | 内容预览（≤500 字符）|
| `workflow_completed` | 工作流全部完成 | 完成摘要 |
| `workflow_failed` | 工作流执行失败 | 错误信息 |
| `error` | 步骤执行出错 | 错误详情 |

### 4.7 下载产出物（.docx）

#### 通过 UI 下载

1. 进入工作流执行页面
2. 等待状态变为 **"已完成"**
3. 点击 **"产出物"** 标签
4. 点击各产出物旁的 **"下载 .docx"** 按钮

#### 通过 API 下载

```bash
# 1. 列出工作流的所有产出物
curl http://localhost:8000/api/v1/workflows/run-uuid-5678/artifacts \
  -H "Authorization: Bearer $TOKEN"
```

**响应:**
```json
[
  {
    "id": "art-uuid-1",
    "artifact_type": "product_spec",
    "title": "在线书店产品规格 v1.0",
    "created_at": "2026-03-18T10:23:15Z"
  },
  {
    "id": "art-uuid-2",
    "artifact_type": "technical_design",
    "title": "在线书店技术方案 v1.0",
    "created_at": "2026-03-18T10:23:31Z"
  }
]
```

```bash
# 2. 下载特定产出物为 .docx
curl -O -J http://localhost:8000/api/v1/artifacts/art-uuid-1/download \
  -H "Authorization: Bearer $TOKEN"

# 文件将被保存为: online_bookstore_product_spec_v1.0.docx
```

```bash
# 3. 查看产出物的 Markdown 原文
curl http://localhost:8000/api/v1/artifacts/art-uuid-1 \
  -H "Authorization: Bearer $TOKEN"
```

---

## 5. API 参考

### 5.1 认证 API

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/v1/auth/register` | 用户注册 |
| POST | `/api/v1/auth/login` | 用户登录 |
| POST | `/api/v1/auth/refresh` | 刷新 Token |
| GET | `/api/v1/auth/me` | 获取当前用户信息 |

### 5.2 项目 API

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/v1/projects` | 列出所有项目 |
| POST | `/api/v1/projects` | 创建项目 |
| GET | `/api/v1/projects/{id}` | 获取项目详情 |
| PUT | `/api/v1/projects/{id}` | 更新项目 |
| DELETE | `/api/v1/projects/{id}` | 删除项目 |

### 5.3 工作流 API

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/v1/workflows/runs` | 创建并启动工作流 |
| GET | `/api/v1/workflows/runs` | 列出工作流运行记录 |
| GET | `/api/v1/workflows/runs/{id}` | 获取运行详情 |
| POST | `/api/v1/workflows/runs/{id}/cancel` | 取消工作流 |
| GET | `/api/v1/workflows/approvals/pending` | 获取待审批列表 |
| POST | `/api/v1/workflows/approvals/{id}/approve` | 批准 |
| POST | `/api/v1/workflows/approvals/{id}/reject` | 拒绝 |

### 5.4 Artifact API

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/v1/artifacts` | 创建 Artifact |
| GET | `/api/v1/artifacts/{id}` | 获取 Artifact |
| GET | `/api/v1/artifacts/{id}/download` | 下载为 .docx |
| GET | `/api/v1/workflows/{run_id}/artifacts` | 列出工作流产出物 |
| DELETE | `/api/v1/artifacts/{id}` | 删除 Artifact |

### 5.5 Agent API

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/v1/agents/roles` | 列出可用角色 |
| GET | `/api/v1/agents/sessions` | 列出 Agent 会话 |
| GET | `/api/v1/agents/sessions/{id}` | 获取会话详情 |

### 5.6 WebSocket API

| 端点 | 描述 | 连接方式 |
|------|------|---------|
| `/ws/workflows/{workflow_run_id}` | 工作流进度推送 | WebSocket |

### 5.7 系统 API

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/docs` | Swagger API 文档 |
| GET | `/redoc` | ReDoc API 文档 |

**完整 API 文档:** http://localhost:8000/docs

---

## 6. 配置参考

### 6.1 完整 .env 配置说明

```env
# ==========================================
# 应用配置
# ==========================================
DEBUG=false                              # 是否启用调试模式
APP_NAME="Agent Platform"
APP_VERSION="1.0.0"

# ==========================================
# 安全配置
# ==========================================
SECRET_KEY=your-super-secret-key-here   # 至少 32 字符
ACCESS_TOKEN_EXPIRE_MINUTES=30          # Token 过期时间（分钟）
ALGORITHM=HS256                         # JWT 签名算法

# ==========================================
# LLM 配置
# ==========================================
LLM_PROVIDER=openrouter                 # openai | anthropic | openrouter | local
LLM_API_KEY=sk-or-v1-xxxxxxxxxxxx       # API Key
LLM_MODEL=google/gemini-2.0-flash-exp   # 默认模型

# OpenRouter 可用模型示例:
# google/gemini-2.0-flash-exp    (免费，快速)
# openai/gpt-4o                  (高质量，收费)
# anthropic/claude-3-5-sonnet    (高质量，收费)
# meta-llama/llama-3.1-70b       (开源，免费)

# OpenAI 直连
# LLM_PROVIDER=openai
# LLM_API_KEY=sk-xxxx
# OPENAI_MODEL=gpt-4o

# Anthropic 直连
# LLM_PROVIDER=anthropic
# LLM_API_KEY=sk-ant-xxxx
# ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# 本地 Ollama
# LLM_PROVIDER=local
# OLLAMA_BASE_URL=http://localhost:11434
# OLLAMA_MODEL=llama3.1

# ==========================================
# 数据库配置
# ==========================================
# SQLite (默认，适合开发)
DATABASE_URL=sqlite+aiosqlite:///./data/agentplatform.db

# PostgreSQL (推荐生产使用)
# DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/agentplatform

# ==========================================
# Redis 配置
# ==========================================
REDIS_URL=redis://localhost:6379/0

# ==========================================
# 文件存储
# ==========================================
EXPORTS_DIR=./exports                   # DOCX 文件输出目录

# MinIO (可选，生产环境文件存储)
# MINIO_ENDPOINT=localhost:9000
# MINIO_ACCESS_KEY=minioadmin
# MINIO_SECRET_KEY=minioadmin
# MINIO_BUCKET=agent-platform
```

### 6.2 LLM Provider 对比

| Provider | 速度 | 质量 | 成本 | 适合场景 |
|----------|------|------|------|---------|
| OpenRouter + Gemini Flash | ⚡⚡⚡ | ⭐⭐⭐ | 💰 免费 | 开发测试 |
| OpenRouter + GPT-4o | ⚡⚡ | ⭐⭐⭐⭐⭐ | 💰💰💰 | 生产/高质量 |
| Anthropic Claude 3.5 | ⚡⚡ | ⭐⭐⭐⭐⭐ | 💰💰💰 | 生产/高质量 |
| Ollama (本地) | ⚡ | ⭐⭐⭐ | 免费 | 隐私/离线 |

---

## 7. 故障排除

### 7.1 服务无法启动

**问题: `ModuleNotFoundError` 或 `ImportError`**

```bash
# 检查虚拟环境是否激活
which python
# 应显示: /path/to/backend/.venv/bin/python

# 重新安装依赖
pip install -r requirements.txt --force-reinstall

# 检查 Python 版本
python --version
# 应为 Python 3.12+
```

**问题: `Address already in use` 端口冲突**

```bash
# 查找占用 8000 端口的进程
lsof -i :8000
# 或
netstat -tulpn | grep 8000

# 终止占用进程
kill -9 <PID>
```

**问题: `Database error` 或 `Table not found`**

```bash
# 重新初始化数据库
cd backend
source .venv/bin/activate
rm -f data/agentplatform.db    # 删除旧数据库（开发环境）
mkdir -p data exports
python init_db.py
```

### 7.2 LLM API 问题

**问题: `LLM API connection failed` 或 `401 Unauthorized`**

```bash
# 检查 API Key 配置
cat .env | grep LLM_API_KEY
# 应显示: LLM_API_KEY=sk-or-xxx...（非空）

# 测试 LLM 连接
cd backend
source .venv/bin/activate
python -c "
import asyncio
from app.intelligence.llm_adapter_v2 import LLMAdapterV2
adapter = LLMAdapterV2()
result = asyncio.run(adapter.test_connection())
print('LLM OK:', result)
"
```

**问题: `Rate limit exceeded`**

```bash
# LLMAdapterV2 有自动重试机制，通常会自动恢复
# 如果持续发生，考虑:
# 1. 降低并发 Agent 数量
# 2. 切换到有更高速率限制的模型
# 3. 使用付费 API Key

# 查看当前配置的模型
cat .env | grep LLM_MODEL
```

**问题: 工作流运行但 Agent 一直在 `running` 状态**

```bash
# 检查 Agent Worker 是否在运行
ps aux | grep agent_worker

# 如未运行，重新启动 Worker
cd backend
source .venv/bin/activate
python -m agent_worker

# 检查 Redis 连接
redis-cli ping
```

### 7.3 WebSocket 问题

**问题: WebSocket 连接被拒绝**

```bash
# 检查后端是否支持 WebSocket
curl -i http://localhost:8000/health
# 应返回 200 OK

# 确认使用正确的端口（非前端端口）
# WebSocket: ws://localhost:8000/ws/workflows/{run_id}
# 不是: ws://localhost:5173/ws/...
```

**问题: WebSocket 连接立即断开**

```javascript
// 添加错误处理和重连逻辑
ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};

ws.onclose = (event) => {
    console.log('Closed:', event.code, event.reason);
    // code 1000: 正常关闭（工作流完成）
    // code 1006: 异常断开（网络问题，可重连）
};
```

### 7.4 文档生成问题

**问题: 下载的 .docx 文件无法打开**

```bash
# 验证 python-docx 安装
python -c "import docx; print(docx.__version__)"

# 检查文件是否完整（文件大小应 > 0）
ls -lh exports/

# 手动测试文档生成
python -c "
from docx import Document
doc = Document()
doc.add_heading('Test', 0)
doc.save('/tmp/test.docx')
print('DOCX generated successfully')
"
```

**问题: 中文字符在 .docx 中显示为乱码**

这通常是字体问题。确保系统安装了 CJK 字体：

```bash
# macOS
brew install --cask font-noto-sans-cjk

# Ubuntu
sudo apt-get install fonts-noto-cjk
```

### 7.5 前端问题

**问题: 前端无法连接到后端 API**

检查 `frontend/src/config.ts` 中的 API URL 配置：

```typescript
// 开发环境
export const API_BASE_URL = 'http://localhost:8000';

// 生产环境（通过 nginx 代理）
export const API_BASE_URL = '/api';
```

**问题: 构建失败**

```bash
cd frontend
rm -rf node_modules
npm install
npm run build
```

---

## 8. FAQ

### Q1: 我需要付费的 LLM API 才能使用吗？

**A:** 不需要。推荐使用 [OpenRouter](https://openrouter.ai) 的免费模型（如 Gemini 2.0 Flash），完全免费，适合开发和测试。如果需要更高质量的输出，可以选择付费模型（GPT-4o, Claude 3.5 等）。

---

### Q2: 系统支持中文输入和输出吗？

**A:** 完全支持。Agent 的 Prompt、需求输入、Agent 输出、以及最终 .docx 文件均支持中文。系统本身为中文优化，所有 Agent 角色的系统提示均支持中英文双语。

---

### Q3: 可以同时运行多个工作流吗？

**A:** 可以。Agent Worker 支持并发处理多个工作流任务。默认情况下，受 LLM API 速率限制，建议同时运行不超过 5-10 个工作流。

---

### Q4: Agent 的输出质量如何控制？

**A:** 有几种方式：

1. **选择高质量 LLM 模型**（如 GPT-4o 或 Claude 3.5）
2. **使用人工审批步骤** (`require_approval: true`)，在关键节点人工确认
3. **丰富知识库**，向角色专属知识包添加公司规范和最佳实践
4. **调整 Director Agent 的审核标准**（通过自定义系统提示）

---

### Q5: 工作流执行失败后可以重新运行吗？

**A:** 可以。目前需要创建新的工作流运行。未来版本将支持从失败步骤重试（断点续跑）。

---

### Q6: 产出的 .docx 文件格式可以自定义吗？

**A:** MVP 版本使用固定的专业文档样式。自定义模板功能计划在 v1.2 版本提供，届时可以上传 `.docx` 模板文件并指定使用。

---

### Q7: 可以在没有网络的环境中运行吗？

**A:** 可以，但需要本地 LLM。设置 `LLM_PROVIDER=local`，并运行 [Ollama](https://ollama.com)：

```bash
# 安装 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 下载模型（约 4.7GB）
ollama pull llama3.1

# 在 .env 中配置
LLM_PROVIDER=local
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
```

> 注意：本地模型的输出质量通常低于云端模型，建议至少使用 70B 参数的模型以获得可接受的质量。

---

### Q8: 数据安全性如何保障？

**A:** 

- 所有 API 请求需要 JWT 身份认证
- 用户数据按组织隔离，跨组织无法访问彼此数据
- 本地部署（SQLite/PostgreSQL）：数据仅存储于本地服务器
- LLM API 调用：内容会发送至第三方 LLM 服务（OpenAI/Anthropic），请避免输入敏感信息
- 如需完全数据隔离，请使用本地 Ollama 部署

---

### Q9: 如何查看完整的 API 文档？

**A:** 系统已内置 Swagger UI，启动后端后访问：

```
http://localhost:8000/docs     (Swagger UI)
http://localhost:8000/redoc    (ReDoc)
```

---

### Q10: 如何贡献代码或报告问题？

**A:** 欢迎贡献！请通过以下方式参与：

1. **报告 Bug**: 开启 GitHub Issue，提供复现步骤和错误日志
2. **功能请求**: 在 Issues 中标记为 `enhancement`
3. **提交代码**: Fork → 功能分支 → PR，确保新功能有对应测试
4. **文档改进**: 直接提交 PR 更新文档

---

## 附录 A：完整工作流模板示例

```json
{
  "name": "企业级 Spec 流程",
  "description": "适合大型项目的完整交付流程",
  "steps": [
    {
      "id": "requirements",
      "name": "需求分析",
      "agent_role": "product_manager",
      "depends_on": [],
      "timeout_seconds": 300
    },
    {
      "id": "architecture",
      "name": "架构设计",
      "agent_role": "architect",
      "depends_on": ["requirements"],
      "timeout_seconds": 600
    },
    {
      "id": "devops_plan",
      "name": "DevOps 方案",
      "agent_role": "devops_engineer",
      "depends_on": ["requirements"],
      "timeout_seconds": 300
    },
    {
      "id": "qa_plan",
      "name": "测试策略",
      "agent_role": "qa_engineer",
      "depends_on": ["architecture"],
      "timeout_seconds": 300
    },
    {
      "id": "director_review",
      "name": "总监审核",
      "agent_role": "director",
      "depends_on": ["architecture", "devops_plan", "qa_plan"],
      "timeout_seconds": 300,
      "require_approval": true
    },
    {
      "id": "export",
      "name": "文档生成",
      "agent_role": "system",
      "depends_on": ["director_review"]
    }
  ]
}
```

## 附录 B：健康检查与监控

```bash
# 一键健康检查脚本
#!/bin/bash

echo "=== Agent-Platform Health Check ==="

# API
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
echo "API Server: $([ $STATUS -eq 200 ] && echo '✅ OK' || echo '❌ FAIL (HTTP $STATUS)')"

# Redis
REDIS=$(redis-cli ping 2>&1)
echo "Redis: $([ "$REDIS" = "PONG" ] && echo '✅ OK' || echo '❌ FAIL')"

# Worker
WORKER=$(ps aux | grep agent_worker | grep -v grep | wc -l)
echo "Agent Worker: $([ $WORKER -gt 0 ] && echo '✅ Running' || echo '❌ Not Running')"

# Frontend
FE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5173)
echo "Frontend: $([ $FE -eq 200 ] && echo '✅ OK' || echo '❌ FAIL')"
```

---

*Agent-Platform MVP 用户手册 v1.0.0*  
*如有问题，请查看 [API 文档](http://localhost:8000/docs) 或提交 GitHub Issue*  
*更新日期: 2026-03-18*
