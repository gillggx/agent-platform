# Agent-Platform MVP — 项目介绍

> **版本:** 1.0.0-MVP  
> **状态:** Phase 1-3 全部完成 ✅  
> **总代码量:** 6,428 行  
> **更新日期:** 2026-03-18

---

## 目录

1. [项目概览](#1-项目概览)
2. [核心功能介绍](#2-核心功能介绍)
3. [MVP 架构图](#3-mvp-架构图)
4. [关键特性详解](#4-关键特性详解)
5. [技术栈总结](#5-技术栈总结)
6. [与 Code Architect 的关系](#6-与-code-architect-的关系)
7. [快速开始（Quick Start）](#7-快速开始quick-start)
8. [路线图与下一步](#8-路线图与下一步)

---

## 1. 项目概览

**Agent-Platform** 是一个基于 FastAPI + React 构建的多 Agent 协作平台，旨在让 PM、Architect、QA、DevOps 等角色的 AI Agent 自动协作，产出完整的产品规格文件与技术交付物。

### 背景与动机

随着大语言模型（LLM）的快速发展，单一 Agent 的能力已逐渐无法满足复杂软件工程场景的需求。在真实的软件开发流程中，往往需要多个专业角色协同工作：产品经理定义需求、架构师设计系统、QA 制定测试策略、DevOps 规划部署方案。

Agent-Platform MVP 的核心使命是：**将这一协作流程自动化、标准化、可视化**，让 AI Agent 团队像真实的工程团队一样运作。

### 核心价值主张

| 价值维度 | 描述 |
|----------|------|
| **效率提升** | 多 Agent 并行工作，数分钟内完成原需数小时的规格文件撰写 |
| **质量保证** | 每个 Agent 专注于自身领域，通过 DAG 引擎保证流程完整性 |
| **可追溯性** | WebSocket 实时推送，每一步决策全程可见 |
| **灵活扩展** | 插件式 LLM 接入，支持 OpenAI、Anthropic、Ollama 等多种后端 |
| **专业输出** | Markdown 自动转换为格式规范的 `.docx` 文件 |

### 项目规模

```
总代码行数: 6,428 行（不含 node_modules、migrations）

阶段分布:
  Phase 1 (DAG 引擎 + Agent 协调):     2,882 行
  Phase 2 (LLM 集成 + 对话引擎):       1,853 行
  Phase 3 (文档生成 + WebSocket 推送): 1,693 行

测试代码: 1,113+ 行
文档: 10+ 份技术文档
```

---

## 2. 核心功能介绍

### 2.1 多角色 Agent 协作

平台内置五种专业 Agent 角色，每种角色具有独立的职责范围、专业知识库与 LLM 交互风格：

| 角色 | 英文标识 | 职责 | LLM 复杂度 |
|------|----------|------|------------|
| 产品经理 | `product_manager` | 需求分析、PRD 撰写 | MEDIUM |
| 软件架构师 | `architect` | 技术方案设计、可行性审核 | COMPLEX |
| QA 工程师 | `qa_engineer` | 测试计划、验收标准制定 | SIMPLE |
| DevOps 工程师 | `devops_engineer` | 部署方案、基础设施规划 | MEDIUM |
| 总监 | `director` | 最终审核、质量把关 | COMPLEX |

每种角色通过 **RoleTemplate** 定义，包含：
- 系统提示（System Prompt）
- 专业知识文档库
- 输出格式规范
- 与其他角色的协作接口

### 2.2 工作流程引擎（Workflow Engine）

基于 **有向无环图（DAG）** 的工作流引擎，支持：

- **拓扑排序执行**：使用 Kahn 算法确保步骤依赖关系正确
- **环路检测**：DFS 算法在启动前检测循环依赖，快速失败
- **并发批量执行**：依赖相同前置步骤的任务可并行运行
- **动态路由**：LLM 可根据上下文动态决定下一执行步骤
- **Human Approval**：支持工作流在关键节点等待人工审批

### 2.3 LLM 统一适配层

通过 **LLMAdapterV2** 提供统一的 LLM 调用接口：

- 支持 OpenAI、Anthropic Claude、本地 Ollama 等多种 Provider
- 基于角色的模型选择（Director → GPT-4, QA → 轻量模型）
- 三级降级策略（超时 → 速率限制 → 错误回退）
- Token 使用量统计与成本估算

### 2.4 多 Agent 对话引擎

**AgentConversation** 实现多 Agent 间的结构化对话：

- 支持多轮对话与消息历史追踪
- 共享上下文（Context）对所有参与 Agent 可见
- 消息广播机制，Agent 之间可相互响应与评审
- 对话生命周期管理（创建 → 进行中 → 结束）

### 2.5 文档生成引擎

**DocumentGenerator** 将 Agent 产出的 Markdown 内容自动转换为专业 Word 文档：

- 支持标题层级（H1-H3）、代码块（带语言标注）、表格、列表、引用块
- 自动写入文档元数据（标题、作者、时间戳）
- 支持多 Artifact 打包下载
- Artifact 分类：`product_spec` / `technical_design` / `qa_checklist`

### 2.6 实时 WebSocket 推送

**WebSocketManager** 提供工作流执行的实时进度推送：

- 每个 Workflow 可有多个并发客户端连接
- 事件类型：步骤开始、步骤完成、Agent 输出、工作流完成/失败
- 断开时自动清理连接资源
- 每个工作流连接相互隔离

---

## 3. MVP 架构图

### 3.1 整体系统架构

```
┌──────────────────────────────────────────────────────────────────┐
│                        前端 (React + TypeScript)                   │
│                                                                    │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────┐  │
│  │  Dashboard  │  │ Workflow Page │  │  Real-time Progress Feed │  │
│  └─────────────┘  └──────────────┘  └─────────────────────────┘  │
│         │                │                         │               │
│         └────────────────┼─────────────────────────┘               │
│                          │ HTTP / WebSocket                        │
└──────────────────────────┼─────────────────────────────────────────┘
                           │
┌──────────────────────────┼─────────────────────────────────────────┐
│               后端 API (FastAPI + Uvicorn)                          │
│                          │                                          │
│  ┌────────────┐  ┌───────▼────────┐  ┌────────────────────────┐   │
│  │  Auth API  │  │  Workflow API  │  │   WebSocket Endpoint    │   │
│  └────────────┘  └───────┬────────┘  └────────────────────────┘   │
│                          │                                          │
│  ┌───────────────────────▼───────────────────────────────────┐     │
│  │                    核心引擎层                               │     │
│  │                                                            │     │
│  │  ┌──────────────────┐    ┌──────────────────────────┐     │     │
│  │  │  WorkflowEngine  │    │   AgentOrchestrator       │     │     │
│  │  │  (DAG 执行)      │◄──►│   (Session 管理)          │     │     │
│  │  └────────┬─────────┘    └──────────┬───────────────┘     │     │
│  │           │                         │                       │     │
│  │  ┌────────▼─────────┐    ┌──────────▼───────────────┐     │     │
│  │  │  DocumentGen     │    │   AgentConversation       │     │     │
│  │  │  (DOCX 输出)     │    │   (多 Agent 对话)         │     │     │
│  │  └──────────────────┘    └──────────┬───────────────┘     │     │
│  │                                     │                       │     │
│  │  ┌──────────────────────────────────▼───────────────┐     │     │
│  │  │                  LLM Adapter V2                   │     │     │
│  │  │   OpenAI │ Anthropic │ Ollama │ OpenRouter        │     │     │
│  │  └──────────────────────────────────────────────────┘     │     │
│  └────────────────────────────────────────────────────────────┘     │
│                                                                       │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────────┐  │
│  │  PostgreSQL  │  │     Redis     │  │   arq Worker (Async)      │  │
│  │  + pgvector  │  │  (Task Queue) │  │   (LLM 长任务处理)        │  │
│  └──────────────┘  └───────────────┘  └──────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────┘
```

### 3.2 DAG 工作流执行流程

```
用户输入需求
      │
      ▼
WorkflowEngine.execute()
      │
      ├── 1. DAG 验证（环路检测）
      ├── 2. 拓扑排序（Kahn 算法）
      │
      ▼
按批次执行（可并发）:
  ┌─────────────────────────────────────────┐
  │  Batch 1:  [PM Agent]                   │
  │      │                                  │
  │  Batch 2:  [Architect] ← PM 输出       │
  │      │                                  │
  │  Batch 3:  [QA] + [DevOps] (并行)      │
  │      │                                  │
  │  Batch 4:  [Director] ← 所有输出       │
  │      │                                  │
  │  Batch 5:  [System] → 生成 DOCX        │
  └─────────────────────────────────────────┘
      │
      ▼
Artifact 存储 → WebSocket 推送 → 用户下载
```

### 3.3 数据模型关系图

```
Organization
    │
    └─► Project
            │
            └─► WorkflowRun
                    │
                    ├─► Step (多个，按 DAG 顺序)
                    │       ├── agent_role
                    │       ├── status
                    │       └── output
                    │
                    └─► Artifact (多个)
                            ├── type (product_spec / technical_design / qa_checklist)
                            ├── content (Markdown)
                            └── .docx file (生成时)
```

---

## 4. 关键特性详解

### 4.1 DAG 引擎

DAG（有向无环图）引擎是整个平台的调度核心，确保工作流步骤按照正确的依赖顺序执行。

**拓扑排序（Kahn 算法）**

```python
def _topological_sort(self, steps: List[WorkflowStep]) -> List[List[str]]:
    """
    返回按批次分组的步骤 ID，同批次可并发执行。
    时间复杂度: O(V + E)，其中 V=步骤数，E=依赖边数
    """
    in_degree = {step.id: len(step.depends_on) for step in steps}
    batches = []
    
    while in_degree:
        # 收集所有入度为 0 的步骤（可并行执行）
        ready = [sid for sid, deg in in_degree.items() if deg == 0]
        if not ready:
            raise CycleDetectedError("DAG contains a cycle")
        batches.append(ready)
        # 移除并更新入度
        for sid in ready:
            del in_degree[sid]
            for dependent in dependents[sid]:
                in_degree[dependent] -= 1
    
    return batches
```

**环路检测（DFS）**

在 DAG 验证阶段，使用深度优先搜索检测循环依赖，确保工作流定义合法：

```python
def _has_cycle(self, steps: List[WorkflowStep]) -> bool:
    """DFS 环路检测，O(V + E) 复杂度"""
    visited, rec_stack = set(), set()
    
    def dfs(node: str) -> bool:
        visited.add(node)
        rec_stack.add(node)
        for neighbor in adjacency[node]:
            if neighbor not in visited and dfs(neighbor):
                return True
            if neighbor in rec_stack:
                return True
        rec_stack.remove(node)
        return False
    
    return any(dfs(s.id) for s in steps if s.id not in visited)
```

### 4.2 多 Agent 协调

AgentOrchestrator 管理 Agent 会话的完整生命周期：

```
Session 状态机:
  CREATED → RUNNING → PAUSED → RUNNING → COMPLETED
                               ↘ FAILED
```

每个 Agent Session 包含：
- **短期记忆**：当前对话轮次的上下文
- **长期记忆**：跨步骤持久化的知识与决策
- **知识包（KnowledgePack）**：角色专属的领域知识文档

### 4.3 LLM 集成

LLMAdapterV2 实现了生产级的 LLM 调用管理：

```python
# 基于角色的复杂度路由
ROLE_COMPLEXITY = {
    "product_manager": ModelComplexity.MEDIUM,
    "architect":       ModelComplexity.COMPLEX,
    "qa_engineer":     ModelComplexity.SIMPLE,
    "devops_engineer": ModelComplexity.MEDIUM,
    "director":        ModelComplexity.COMPLEX,
}

# 三级降级策略
async def call_with_fallback(self, messages, role):
    try:
        return await self._call_primary(messages, role)
    except TimeoutError:
        await asyncio.sleep(exponential_backoff())
        return await self._call_fallback(messages)
    except RateLimitError as e:
        await asyncio.sleep(e.retry_after)
        return await self._call_fallback(messages)
    except LLMError:
        return await self._call_default(messages)
```

### 4.4 文档生成

DocumentGenerator 支持完整的 Markdown 语法到 DOCX 的转换：

| Markdown 元素 | DOCX 输出 |
|---------------|-----------|
| `# H1` | Word 标题 1 样式 |
| `## H2` | Word 标题 2 样式 |
| `` ```python `` | 代码块 + 语言标注 |
| `\| 表格 \|` | Word 表格 |
| `- 无序列表` | Word 列表 |
| `1. 有序列表` | Word 编号列表 |
| `> 引用` | 缩进引用块 |

### 4.5 WebSocket 实时推送

```javascript
// 前端连接示例
const ws = new WebSocket('ws://localhost:8000/ws/workflows/workflow-123');

ws.onmessage = (event) => {
    const { event_type, step_id, role, content, metadata } = JSON.parse(event.data);
    
    switch(event_type) {
        case 'step_started':
            console.log(`Step ${step_id} (${role}) started`);
            break;
        case 'step_completed':
            console.log(`Completed in ${metadata.duration_ms}ms`);
            break;
        case 'agent_output':
            appendToFeed(`${role}: ${content}`);
            break;
        case 'workflow_completed':
            showDownloadLinks(metadata.artifacts);
            break;
    }
};
```

---

## 5. 技术栈总结

### 5.1 后端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| **FastAPI** | 0.110.0 | Web 框架，自动生成 OpenAPI 文档 |
| **Uvicorn** | 0.27.1 | ASGI 服务器，支持 WebSocket |
| **SQLAlchemy** | 2.0.28 | ORM，Async 模式 |
| **PostgreSQL** | 16 | 主数据库 + pgvector 向量搜索 |
| **Redis** | 7 | 任务队列（arq）与缓存 |
| **LiteLLM** | 最新 | 统一 LLM 调用接口 |
| **python-docx** | 1.1.0 | Word 文档生成 |
| **Pydantic** | 2.6.3 | 数据验证与序列化 |
| **arq** | 最新 | Redis-based 异步任务队列 |
| **pytest** | 8.1.1 | 测试框架 |
| **pytest-asyncio** | 0.23.5 | 异步测试支持 |

### 5.2 前端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| **React** | 18 | UI 框架 |
| **TypeScript** | 最新 | 类型安全 |
| **Vite** | 最新 | 构建工具 |
| **Ant Design** | 5 | UI 组件库 |
| **Zustand** | 最新 | 轻量状态管理 |
| **TanStack Query** | 最新 | 服务端状态缓存 |
| **React Router** | v6 | 客户端路由 |

### 5.3 基础设施

| 技术 | 用途 |
|------|------|
| **Docker** | 容器化部署 |
| **Docker Compose** | 本地多服务编排 |
| **MinIO** | 对象存储（文件上传） |
| **nginx** | 反向代理 |

### 5.4 代码质量

- **Type Annotations**: 100% 覆盖
- **Docstrings**: 100% 覆盖
- **PEP 8**: 完全遵循
- **Async-First**: 全异步设计
- **Error Handling**: 全面的异常处理

---

## 6. 与 Code Architect 的关系

Agent-Platform 是与 **Code Architect** 系统紧密集成的配套产品，两者构成完整的 AI 辅助软件工程生态：

### 分工与协作

```
Code Architect (代码层)              Agent-Platform (流程层)
─────────────────────                ──────────────────────
• 代码生成与优化                     • 产品规格制定
• 代码审查与重构                     • 架构设计讨论
• 函数/模块级别的实现                • 测试策略定义
• 技术债务分析                       • 交付文档产出
        │                                    │
        └──────────────┬─────────────────────┘
                       │
               Agent 协作接口
        (共享 LLM Adapter, Role 定义)
```

### 典型工作流

1. **需求阶段**：Agent-Platform 的 PM Agent 撰写 PRD
2. **设计阶段**：Agent-Platform 的 Architect Agent 产出技术方案
3. **实现阶段**：Code Architect 依据技术方案生成代码
4. **验证阶段**：Agent-Platform 的 QA Agent 产出测试用例，Code Architect 运行测试
5. **交付阶段**：Agent-Platform 的 Director Agent 审核，产出最终 `.docx` 文件

### 共享组件

- **LLM Adapter**: 两个系统共用相同的 LLM 调用抽象层
- **Role 定义**: Agent 角色定义可在系统间共享
- **Knowledge Base**: 技术知识库对两个系统的 Agent 均可见

---

## 7. 快速开始（Quick Start）

### 7.1 前置需求

```
• Python 3.12+
• Node.js 18+
• Redis（Agent Worker 必须）
• Docker & Docker Compose（可选，用于生产部署）
• LLM API Key（OpenAI / Anthropic / OpenRouter）
```

### 7.2 5 分钟启动（开发模式）

**步骤 1：克隆与配置**

```bash
cd /path/to/agent-platform

# 复制环境变量模板
cp .env.example .env

# 编辑 .env，设置 LLM API Key
# 推荐使用 OpenRouter（免费申请：https://openrouter.ai）
LLM_API_KEY=sk-or-xxxxxxxxxxxxxxxx
LLM_PROVIDER=openrouter
SECRET_KEY=your-32-char-random-secret
```

**步骤 2：启动后端**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

mkdir -p data exports
python init_db.py                   # 初始化数据库

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**步骤 3：启动 Agent Worker（新终端）**

```bash
# 确保 Redis 正在运行
redis-server &   # 或 brew services start redis

cd backend
source .venv/bin/activate
python -m agent_worker
```

**步骤 4：启动前端（新终端）**

```bash
cd frontend
npm install
npm run dev
```

**步骤 5：访问服务**

| 服务 | 地址 |
|------|------|
| 前端界面 | http://localhost:5173 |
| API 文档（Swagger） | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |

### 7.3 Docker 一键部署

```bash
cp .env.example .env
# 编辑 .env 设置 LLM_API_KEY

./start.sh
# 或手动：
docker-compose up -d
docker-compose exec api python init_db.py
```

访问：
- 前端：http://localhost:3000
- API：http://localhost:8000

### 7.4 运行你的第一个工作流

1. **注册账号** → http://localhost:5173/register
2. **创建项目** → Dashboard → 新建项目
3. **启动协作流程** → 选择"标准 Spec 流程"
4. **输入需求** → 例如："设计一个在线书店系统"
5. **观察实时协作** → 在 Workflow 页面观看 Agent 讨论
6. **下载文档** → 流程完成后下载 `.docx` 规格文件

### 7.5 验证安装

```bash
# 运行完整测试套件
cd backend
source .venv/bin/activate
python -m pytest tests/ -v

# 预期输出: 92 tests passed ✅
```

---

## 8. 路线图与下一步

### 当前状态（MVP）

| 模块 | 状态 | 说明 |
|------|------|------|
| M1 基础骨架（Auth/DB）| ✅ 完成 | JWT auth、SQLite/PostgreSQL、数据模型 |
| M2 Agent Runtime | ✅ 完成 | SessionManager、状态机、LLM Adapter |
| M3 Workflow Engine | ✅ 完成 | DAG 执行、LLM routing、DOCX export |
| M4 Knowledge Pack | 🔧 部分 | 预设知识包载入完成；CRUD API 建置中 |
| M5 前端 UI | ✅ 完成 | WorkflowPage、Artifact 查看/下载、审批 |
| M6 文件产出 | ✅ 完成 | Markdown → DOCX，步骤级下载 |
| M7 集成测试 | 🔧 部分 | API 手动测试通过；E2E 自动化建置中 |

### Alpha 测试目标

- [ ] Knowledge Pack 完整 CRUD API
- [ ] E2E 自动化测试（Playwright）
- [ ] 前端 WebSocket 实时进度面板
- [ ] Workflow 可视化（节点图）
- [ ] 多租户隔离验证

### 生产就绪目标

- [ ] 向量搜索（pgvector）集成
- [ ] Workflow 模板市场
- [ ] 用户自定义 Agent 角色
- [ ] 审计日志与权限管理
- [ ] 高可用部署（Redis Sentinel、PG 主从）

---

## 附录

### 相关文档

- [用户手册](./USER_MANUAL.md) — 详细使用指南与 API 参考
- [测试报告](./TEST_REPORT.md) — 完整测试覆盖率与质量分析
- [Phase 1 实现文档](../PHASE_1_IMPLEMENTATION.md) — DAG 引擎与 Agent 协调详解
- [Phase 2 总结](../PHASE_2_SUMMARY.md) — LLM 集成与对话引擎
- [Phase 3 完成报告](../PHASE3_COMPLETION.md) — 文档生成与 WebSocket 推送
- [API 端点清单](../ENDPOINT_INVENTORY.md) — 完整 REST API 索引

### 许可证

本项目采用 **MIT 许可证**。详见 [LICENSE](../LICENSE) 文件。

---

*Agent-Platform MVP — 让 AI Agent 协作更简单、更高效 🚀*

*Generated: 2026-03-18 | Version: 1.0.0-MVP*
