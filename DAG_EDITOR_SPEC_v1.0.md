# DAG 編輯器規格 v1.0

**產品**: Agent-Platform DAG Visual Editor  
**版本**: 1.0  
**生成時間**: 2026-03-19 07:42 GMT+8  
**狀態**: 規格設計

---

## 1. 概述

### 目標
提供一個視覺化的 DAG（有向無環圖）編輯器，讓用戶能夠：
- ✅ 拖拽創建工作流節點
- ✅ 連接節點定義依賴關係
- ✅ 配置節點參數
- ✅ 實時驗證 DAG 完整性
- ✅ 保存/加載工作流配置

### 關鍵指標
| 指標 | 目標 |
|------|------|
| 加載時間 | < 2 秒 (100 節點) |
| 拖拽延遲 | < 16ms (60fps) |
| 支持節點數 | 200+ |
| 撤銷/重做深度 | 50+ 步 |

---

## 2. 核心功能

### 2.1 節點管理

#### 創建節點
```
方式 1: 側邊欄拖拽
- 從左側 Agent 面板拖拽 → 畫布
- 5 種預定義角色 (PM, Architect, QA, DevOps, Director)
- 自動分配唯一 ID

方式 2: 右鍵菜單
- 在畫布右鍵 → "Add Node"
- 選擇角色類型 → 創建

方式 3: 快捷鍵
- Ctrl/Cmd + A → Agent 選擇器
```

#### 節點類型
```json
{
  "id": "pm-1",
  "type": "agent",
  "role": "product_manager",
  "position": { "x": 100, "y": 200 },
  "data": {
    "title": "Product Manager",
    "color": "#3B82F6",
    "inputs": ["user_request"],
    "outputs": ["product_spec"],
    "config": {
      "llm_model": "gpt-4",
      "temperature": 0.7
    }
  }
}
```

#### 節點操作
| 操作 | 快捷鍵 | 說明 |
|------|--------|------|
| 選擇 | Click | 單擊節點 |
| 多選 | Shift+Click | 累積選擇 |
| 全選 | Ctrl/Cmd+A | 選擇所有 |
| 刪除 | Delete | 刪除選定 |
| 複製 | Ctrl/Cmd+C | 複製節點 |
| 粘貼 | Ctrl/Cmd+V | 粘貼節點 |
| 撤銷 | Ctrl/Cmd+Z | 撤銷上一步 |
| 重做 | Ctrl/Cmd+Y | 重做 |
| 對齐 | Right-Click | Align 菜單 |

### 2.2 連接管理

#### 創建邊（Edge）
```
步驟:
1. 在源節點點擊 → 出口點亮
2. 拖拽到目標節點
3. 在目標節點鬆開
4. 彈出「連接配置」對話框

驗證規則:
- ✅ 不允許自環 (A → A)
- ✅ 不允許環 (A → B → C → A)
- ✅ 多出邊允許 (A → B, A → C)
- ✅ 多入邊允許 (A → C, B → C)
```

#### 邊數據模型
```json
{
  "id": "edge-pm-to-arch",
  "source": "pm-1",
  "target": "arch-1",
  "data": {
    "label": "product_spec",
    "type": "data_flow",
    "format": "json",
    "validation": true
  },
  "style": {
    "stroke": "#10B981",
    "strokeWidth": 2
  }
}
```

#### 邊操作
- **選擇**: 點擊邊線高亮
- **刪除**: 選中後按 Delete
- **編輯**: 雙擊 → 配置對話框
- **重新路由**: 拖拽控制點

---

## 3. 配置面板

### 3.1 節點配置
```
左側邊欄面板 (當選中節點時):

📋 Node Properties
├─ 基本信息
│  ├─ ID: [pm-1]
│  ├─ Role: [Product Manager ▼]
│  └─ Title: [Custom name]
├─ LLM 配置
│  ├─ Model: [Claude Opus ▼]
│  ├─ Temperature: [0.7 ————]
│  ├─ Max Tokens: [4000]
│  └─ Top-P: [0.9]
├─ 提示詞
│  └─ System Prompt: [textarea]
├─ 輸入映射
│  ├─ input_1: workflow.previous_output
│  └─ input_2: user_input
└─ 輸出映射
   └─ product_spec → [Save as]
```

### 3.2 邊配置
```
雙擊邊後彈出:

🔗 Connection Properties
├─ 源: pm-1 (Product Manager)
├─ 目標: arch-1 (Architect)
├─ 數據類型: [JSON Schema ▼]
├─ 驗證規則
│  ├─ 必需字段: [required_fields]
│  └─ 格式驗證: [enabled]
└─ 標籤: [product_spec]
```

### 3.3 全局配置
```
右上角 ⚙️ Settings:

⚙️ Workflow Settings
├─ 基本信息
│  ├─ 名稱: [Agent-Platform MVP]
│  ├─ 描述: [长文本]
│  └─ 版本: [1.0.0]
├─ 執行設置
│  ├─ 超時: [3600] 秒
│  ├─ 重試次數: [3]
│  └─ 並行度: [4]
├─ 通知設置
│  ├─ 完成提醒: [enabled]
│  └─ 錯誤提醒: [enabled]
└─ 高級設置
   ├─ 啟用緩存: [enabled]
   └─ 成本限制: [50.00] USD
```

---

## 4. UI 組件架構

### 4.1 整體佈局
```
┌─────────────────────────────────────────────────────────────────┐
│ ← Back | DAG Editor: Agent-Platform MVP  | ⚙️ Settings | Run ▶️ │
├─────────┬───────────────────────────────────────────────────────┤
│         │                                                       │
│ 左邊欄  │                  Canvas 區域                         │
│ (nodes) │          (拖拽編輯 DAG 圖表)                        │
│         │                                                       │
│ ├─ PM   │                                                       │
│ ├─ Arch │                                                       │
│ ├─ QA   │      ┌─────┐         ┌─────┐                        │
│ ├─ DevOps│      │ PM  ├────────→│Arch │                        │
│ └─ Dir  │      └─────┘         └─────┘                        │
│         │                         │                            │
│  [+ Add]│                         ▼                            │
│         │                      ┌─────┐                         │
│ Layers: │                      │ QA  │                         │
│ ├─ All  │                      └─────┘                         │
│ ├─ P1   │                                                      │
│ ├─ P2   │                                                       │
│ └─ P3   │ 右側邊欄 (Node Props)                                │
│         │ ├─ ID: pm-1                                          │
│ [Zoom] ├─ Role: PM                                             │
│ [Center]│ ├─ Model: Claude                                     │
│         │ └─ [Config]                                          │
└─────────┴───────────────────────────────────────────────────────┘
```

### 4.2 組件詳解

#### Canvas 畫布
- **庫**: React Flow (react-flow-renderer)
- **功能**:
  - 平移、縮放、全屏
  - 節點拖拽
  - 邊拖拽重新連接
  - 網格背景 (snap-to-grid)
  - 迷你地圖

#### 節點面板 (左側)
```tsx
<NodePanel>
  <Category title="Agents">
    <DraggableNode type="agent" role="product_manager" />
    <DraggableNode type="agent" role="architect" />
    <DraggableNode type="agent" role="qa" />
    <DraggableNode type="agent" role="devops" />
    <DraggableNode type="agent" role="director" />
  </Category>
  <Category title="Tools">
    <DraggableNode type="tool" tool="code_generator" />
    <DraggableNode type="tool" tool="document_writer" />
  </Category>
</NodePanel>
```

#### 配置面板 (右側)
```tsx
<ConfigPanel>
  {selectedNode && (
    <NodeConfig node={selectedNode} onChange={onUpdate} />
  )}
  {selectedEdge && (
    <EdgeConfig edge={selectedEdge} onChange={onUpdate} />
  )}
  {!selectedNode && !selectedEdge && (
    <WorkflowConfig workflow={workflow} onChange={onUpdate} />
  )}
</ConfigPanel>
```

---

## 5. 驗證與錯誤處理

### 5.1 DAG 驗證
```
實時驗證 (邊改變時):

✅ 環檢測 (Cycle Detection)
   - 使用 DFS 檢查
   - 發現環 → 紅色邊 + 警告

✅ 完整性檢查
   - 所有節點有入邊或是起始節點
   - 所有節點有出邊或是終止節點
   - 孤立節點檢查

✅ 類型檢查
   - 邊的 output 類型 ⊆ target 的 input 類型
   - 類型不匹配 → 黃色邊 + 提示

✅ 必需字段檢查
   - 節點的必需配置項完整
   - 缺失 → 節點左上角紅點
```

### 5.2 錯誤提示
```
UI 反饋:

🔴 致命錯誤 (無法運行)
   - 環依賴 (紅邊)
   - 缺失必需配置 (紅點)
   - 無法執行按鈕灰化 + tooltip

🟡 警告 (可能問題)
   - 類型不匹配 (黃邊)
   - 孤立節點 (灰色節點)
   - 成本超限 (成本指示器)

🔵 信息 (提示)
   - 功能說明
   - 最佳實踐建議
```

---

## 6. 高級功能

### 6.1 工作流分層
```
支持將複雜工作流分為多層:

Layer 0 (Overview):
  ┌─────┐     ┌─────┐
  │ PM  ├────→│Arch │
  └─────┘     └──┬──┘
               ┌─┴──┐
          ┌────┴┐  ┌┴─────┐
          ▼     ▼  ▼      ▼
        [QA] [DevOps] [Output]

Layer 1 (Arch Detail):
  ┌─────────────────────┐
  │ Architect Subgraph  │
  │ ├─ Code Analysis    │
  │ ├─ Design Review    │
  │ └─ Code Generation  │
  └─────────────────────┘

功能:
- 雙擊節點進入子圖
- 麵包屑導航
- 摺疊/展開子圖
```

### 6.2 模板系統
```
預定義工作流模板:

📋 模板庫:
├─ Basic (PM → Arch → QA)
├─ Full (PM → Arch → QA → DevOps → Director)
├─ Code Generation (PM → Arch → Code Gen → Test)
└─ Custom Templates (用戶保存)

使用流程:
1. New Workflow → "From Template"
2. 選擇模板
3. 自動創建節點和連接
4. 修改配置 → 保存
```

### 6.3 撤銷/重做
```
完整撤銷堆棧:

操作類型:
- addNode
- removeNode
- updateNode
- addEdge
- removeEdge
- updateEdge
- updateWorkflow

實現:
- 每個操作推送到 undo stack
- 最多保存 50 步
- 按 Ctrl+Z / Ctrl+Y

UI:
- 工具欄 [↶] [↷] 按鈕
- 灰化禁用狀態
```

---

## 7. 數據模型

### 7.1 工作流數據結構
```json
{
  "workflow": {
    "id": "wf-123",
    "name": "Agent-Platform MVP",
    "version": "1.0.0",
    "created_at": "2026-03-19T07:42:00Z",
    "updated_at": "2026-03-19T07:42:00Z",
    "config": {
      "timeout_seconds": 3600,
      "max_retries": 3,
      "parallelism": 4,
      "cost_limit_usd": 50.0
    },
    "nodes": [
      {
        "id": "pm-1",
        "type": "agent",
        "role": "product_manager",
        "position": { "x": 100, "y": 200 },
        "data": {
          "title": "Product Manager",
          "config": {
            "llm_model": "anthropic/claude-opus",
            "temperature": 0.7,
            "max_tokens": 4000,
            "system_prompt": "You are a..."
          },
          "inputs": ["user_request"],
          "outputs": ["product_spec"]
        }
      },
      {
        "id": "arch-1",
        "type": "agent",
        "role": "architect",
        "position": { "x": 400, "y": 200 },
        "data": {
          "title": "Architect",
          "config": {
            "llm_model": "anthropic/claude-opus",
            "temperature": 0.5,
            "max_tokens": 8000
          },
          "inputs": ["product_spec"],
          "outputs": ["architecture_design", "implementation_plan"]
        }
      }
    ],
    "edges": [
      {
        "id": "edge-1",
        "source": "pm-1",
        "target": "arch-1",
        "data": {
          "label": "product_spec",
          "type": "data_flow",
          "format": "json"
        }
      }
    ]
  }
}
```

---

## 8. API 接口

### 8.1 工作流 API
```
創建工作流:
POST /api/workflows
{
  "name": "Agent-Platform MVP",
  "config": { ... }
}
→ 201 { workflow_id, ... }

獲取工作流:
GET /api/workflows/{workflow_id}
→ 200 { workflow, nodes, edges }

更新工作流:
PUT /api/workflows/{workflow_id}
{ nodes, edges, config }
→ 200 { updated_workflow }

刪除工作流:
DELETE /api/workflows/{workflow_id}
→ 204

運行工作流:
POST /api/workflows/{workflow_id}/run
{ inputs, ... }
→ 202 { job_id }
```

### 8.2 驗證 API
```
驗證 DAG:
POST /api/validate/dag
{
  "nodes": [...],
  "edges": [...]
}
→ 200 {
  "valid": true,
  "errors": [],
  "warnings": ["Node QA-1 is isolated"]
}

檢查環:
POST /api/validate/cycles
{ nodes, edges }
→ 200 { has_cycle: false, cycle_nodes: [] }
```

---

## 9. 技術實現

### 9.1 前端技術棧
```
UI 框架:
- React 18.2+
- TypeScript 5+
- Zustand (狀態管理)
- React Flow (圖編輯)

組件庫:
- React Flow (nodes + edges)
- react-icons (UI 圖標)
- Tailwind CSS (樣式)
- react-hotkeys-hook (快捷鍵)

性能:
- React.memo (避免重渲染)
- useCallback (穩定函數引用)
- 虛擬列表 (大型工作流)
- Web Worker (驗證計算)
```

### 9.2 後端集成
```
新增 API 端點:
- POST /api/workflows (創建)
- GET /api/workflows/{id} (查詢)
- PUT /api/workflows/{id} (更新)
- DELETE /api/workflows/{id} (刪除)
- POST /api/workflows/{id}/validate (驗證)
- POST /api/workflows/{id}/run (執行)

複用現有組件:
- WorkflowEngine (執行邏輯)
- AgentCoordinator (角色協調)
- DocumentGenerator (輸出)
```

---

## 10. 開發計劃

### Phase 1: MVP (Week 1-2)
```
Day 1-3: 基礎 UI
- Canvas 畫布 (React Flow)
- 節點面板
- 節點創建和刪除

Day 4-6: 連接和驗證
- 邊的創建和刪除
- 環檢測
- 錯誤提示 UI

Day 7-10: 配置面板
- 節點配置表單
- 邊配置對話框
- 工作流保存/加載

任務量: 10 天 (1 個前端工程師)
```

### Phase 2: 增強 (Week 3)
```
Day 11-12: 撤銷/重做
Day 13-14: 模板系統
Day 15: 測試和優化

任務量: 5 天
```

### Phase 3: 高級功能 (Week 4+)
```
- 分層視圖
- 實時協作
- 導入/導出 (YAML, JSON)
- 版本控制

任務量: 10+ 天
```

---

## 11. 測試要求

### 11.1 單元測試
```
- DAG 驗證邏輯 (環檢測、類型檢查)
- 數據模型轉換
- API 序列化

覆蓋率: > 80%
```

### 11.2 集成測試
```
- 創建、更新、刪除工作流
- 節點和邊的完整生命週期
- 驗證錯誤處理

數量: 50+ 測試
```

### 11.3 E2E 測試 (Playwright)
```
- 拖拽創建節點
- 連接節點
- 配置節點參數
- 保存和加載
- 運行工作流

數量: 20+ 測試
```

---

## 12. 驗收標準

### 必需功能 ✅
- [ ] 拖拽創建節點
- [ ] 連接節點
- [ ] 刪除節點和邊
- [ ] 節點配置
- [ ] DAG 驗證 (環檢測)
- [ ] 保存/加載
- [ ] 運行工作流

### 性能要求 ⚡
- [ ] 加載 < 2 秒 (100 節點)
- [ ] 拖拽延遲 < 16ms (60fps)
- [ ] 響應時間 < 100ms

### 質量指標 📊
- [ ] 單元測試 > 80% 覆蓋
- [ ] 集成測試 > 50 個
- [ ] E2E 測試 > 20 個
- [ ] 0 個編譯錯誤
- [ ] 0 個 TypeScript 錯誤

---

## 13. 風險和缺解

| 風險 | 概率 | 影響 | 缺解 |
|------|------|------|-----|
| 複雜圖的性能 | 中 | 中 | 虛擬列表 + Web Worker |
| 狀態管理複雜 | 中 | 中 | Zustand + Redux DevTools |
| 拖拽體驗 | 低 | 高 | React Flow + 充分測試 |
| 型別安全 | 低 | 中 | TypeScript + 嚴格模式 |

---

## 附錄：屏幕原型

### A1. 主編輯界面
```
[工具欄: 返回 | 工作流名稱 | ⚙️ 設置 | ▶️ 運行]

[左側面板]           [Canvas 區域]              [右側配置]
├─ 📋 Agents        ┌─────────────────────┐   ├─ Node: pm-1
│ ├─ PM ⬜           │   ┌─────┐           │   ├─ Role: PM
│ ├─ Arch ⬜         │   │ PM  │           │   ├─ Model: ▼
│ ├─ QA ⬜          │   └──┬──┘           │   ├─ Temp: [====]
│ ├─ DevOps ⬜      │      │              │   ├─ MaxTokens: 4000
│ └─ Director ⬜    │   ┌──▼──┐           │   └─ [Save]
├─ 🛠️ Tools         │   │Arch │           │
├─ Layers           │   └─────┘           │
└─ [Zoom Controls]  └─────────────────────┘
```

### A2. 節點配置對話框
```
┌──────────────────────────────────┐
│  Node Configuration: Product Manager
├──────────────────────────────────┤
│                                  │
│  📋 Basic                        │
│  Name: [Product Manager]         │
│  Role: [PM ▼]                    │
│                                  │
│  🤖 LLM Config                   │
│  Model: [Claude Opus ▼]          │
│  Temp: [0.7 ————————]            │
│  MaxTokens: [4000       ]        │
│  Top-P: [0.9 ————————]           │
│                                  │
│  💬 System Prompt                │
│  ┌──────────────────────────────┐│
│  │ You are a senior...          ││
│  │ Responsibilities:...         ││
│  │ Output format:...            ││
│  └──────────────────────────────┘│
│                                  │
│       [Cancel]      [Save]      │
└──────────────────────────────────┘
```

---

## 參考資源

- **React Flow**: https://reactflow.dev
- **DAG 算法**: Topological Sort + DFS Cycle Detection
- **Zustand**: State management library
- **Tailwind**: CSS utility framework

---

**Spec 版本**: 1.0  
**最後更新**: 2026-03-19 07:42 GMT+8  
**下一步**: 前端工程師評審 → 開發啟動
