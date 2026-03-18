# Agent Platform QA 測試文件 v1.0

> 基於 spec v3 與技術架構文件，覆蓋 P0/P1 功能的完整測試計劃。

---

## 1. 測試範圍與環境

### 測試環境
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`
- API Docs: `http://localhost:8000/docs`
- 預設 Demo User org: `DEFAULT_ORG_ID`

### 前置條件
```bash
# 啟動服務
cd backend && uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev

# 初始化 DB（首次）
cd backend && python init_db.py
```

---

## 2. P0 功能測試

### TC-001：建立專案

| 欄位 | 內容 |
|------|------|
| **測試目標** | 驗證使用者可以成功建立專案 |
| **前置條件** | 服務正常運行 |
| **測試步驟** | 1. 開啟 Dashboard (`/`) <br> 2. 點擊「新建專案」<br> 3. 輸入名稱「測試專案」、描述「這是一個測試」<br> 4. 點擊「建立專案」 |
| **預期結果** | 專案出現在列表中，狀態為「草稿」 |
| **API 驗證** | `GET /api/v1/projects` 回傳包含新專案的列表 |
| **目前狀態** | ✅ 預計可通過 |

---

### TC-002：啟動標準 Spec 工作流程

| 欄位 | 內容 |
|------|------|
| **測試目標** | 驗證 PM → Architect → QA → Director 完整流程可以啟動 |
| **前置條件** | 已有專案，系統 Agent 定義存在 |
| **測試步驟** | 1. 在 Dashboard 選擇專案，點「啟動流程」<br> 2. 選擇「標準 Spec 流程」模板<br> 3. 輸入需求：「我要做一個設備監控 dashboard，含即時數據顯示與告警功能」<br> 4. 點擊「啟動工作流程」 |
| **預期結果** | 跳轉到 WorkflowPage，顯示 run_id，狀態為「執行中」，PM 步驟顯示執行中 |
| **API 驗證** | `GET /api/v1/workflows/runs/{run_id}` 回傳 `status: running`, `current_steps: ["pm_draft"]` |
| **目前狀態** | ✅ 預計可通過（已有實作） |

---

### TC-003：工作流程執行完整 E2E

| 欄位 | 內容 |
|------|------|
| **測試目標** | 驗證整個 Agent 協作流程跑完，產出所有 Artifact |
| **前置條件** | LLM API Key 已設定，TC-002 執行中 |
| **測試步驟** | 1. 等待 WorkflowPage 輪詢更新（每 5 秒）<br> 2. 觀察步驟依序完成：PM → Architect → QA → Director<br> 3. 確認最終狀態變為「已完成」 |
| **預期結果** | <ul><li>每個步驟有 `completed` 狀態</li><li>產生 4 個 Artifacts：product_spec / tech_design / qa_checklist / review_report</li><li>WorkflowRun.status = `completed`</li></ul> |
| **API 驗證** | `GET /api/v1/artifacts/projects/{project_id}/artifacts` 回傳 4 個 artifacts |
| **目前狀態** | ⚠️ 部分可通過（LLM routing 需驗證） |

---

### TC-004：下載 DOCX 文件

| 欄位 | 內容 |
|------|------|
| **測試目標** | 驗證流程完成後可下載 .docx 格式文件 |
| **前置條件** | TC-003 完成，至少有 1 個 Artifact |
| **測試步驟** | 1. 在 WorkflowPage 點擊「查看產出文件」<br> 2. 點擊「下載完整文件」 |
| **預期結果** | 瀏覽器下載 `{project_name}_完整規格.docx`，可用 Word 開啟，格式正常 |
| **API 驗證** | `GET /api/v1/artifacts/projects/{project_id}/download` 回傳 Content-Type: `application/vnd.openxmlformats...` |
| **目前狀態** | ✅ 已修復（2026-03-16）：下載按鈕串接 API，完成頁面有「下載完整規格文件」按鈕 |

---

### TC-005：工作流程步驟狀態即時更新

| 欄位 | 內容 |
|------|------|
| **測試目標** | 驗證前端 polling 正確顯示步驟進度 |
| **前置條件** | TC-002 已啟動流程 |
| **測試步驟** | 1. 開啟 WorkflowPage，記錄初始 current_steps<br> 2. 等待 5-10 秒<br> 3. 觀察頁面自動刷新 |
| **預期結果** | 步驟由灰色 → 藍色（執行中）→ 綠色（完成），無需手動刷新 |
| **目前狀態** | ✅ Polling 邏輯已實作（5 秒間隔） |

---

### TC-006：知識庫封裝（KnowledgePack）

| 欄位 | 內容 |
|------|------|
| **測試目標** | 驗證 Agent 可以使用自訂 system_prompt 和 task_prompts |
| **前置條件** | 已有 KnowledgePack 設定 |
| **測試步驟** | 1. 直接修改 DB 中的 KnowledgePack（目前無 UI）<br> 2. 設定 PM 的 `system_prompt` 為自訂內容<br> 3. 啟動工作流程，觀察 PM 產出是否符合自訂 prompt |
| **預期結果** | PM Agent 的 LLM 呼叫使用自訂 system_prompt |
| **目前狀態** | ⚠️ 後端邏輯已實作，無管理 UI |

---

## 3. P1 功能測試

### TC-007：Human Approval 暫停/繼續

| 欄位 | 內容 |
|------|------|
| **測試目標** | 驗證 Director 步驟可以觸發人工審批等待 |
| **前置條件** | 工作流程執行中，達到需要審批的步驟 |
| **測試步驟** | 1. 等待 Workflow 狀態變為 `waiting_approval`<br> 2. 在前端看到審批 UI<br> 3. 點擊「批准」<br> 4. 觀察流程繼續執行 |
| **預期結果** | 流程在等待時暫停，批准後繼續推進到下一步 |
| **API 驗證** | `POST /api/v1/workflows/runs/{run_id}/approve` 成功更新狀態 |
| **目前狀態** | ✅ 已修復（2026-03-16）：`resume_after_approval()` 實作，批准繼續 LLM 路由，退回傳回 PM 修改 |

---

### TC-008：流程迴圈與升級機制

| 欄位 | 內容 |
|------|------|
| **測試目標** | 驗證超過 max_iterations 後自動升級為人工審批 |
| **前置條件** | 設定 max_loop_iterations = 1，啟動流程 |
| **測試步驟** | 1. 啟動含 loop 設定的流程<br> 2. 等待 Architect 回傳「打回 PM 重寫」的路由決策<br> 3. 確認 PM 步驟執行第 2 次後觸發升級 |
| **預期結果** | `iteration_count > max_iterations` 時觸發 `escalate_to` 步驟（Director 人工審批） |
| **目前狀態** | ⚠️ 迴圈邏輯已寫，升級機制待驗證 |

---

### TC-009：Artifact 版本管理

| 欄位 | 內容 |
|------|------|
| **測試目標** | 驗證 PM 重跑後版本號遞增，舊版本標記為 superseded |
| **前置條件** | PM 步驟已產出 v1 Artifact |
| **測試步驟** | 1. 觸發 PM 重跑（例如 Architect 打回）<br> 2. 查詢 Artifacts |
| **預期結果** | 舊 Artifact `status = superseded`，新 Artifact `version = 2` |
| **API 驗證** | `GET /api/v1/artifacts/projects/{project_id}/artifacts` 有 version 1 (superseded) 和 version 2 (draft) |
| **目前狀態** | ✅ 邏輯已實作（session_manager.py _create_artifact） |

---

### TC-010：步驟執行失敗處理

| 欄位 | 內容 |
|------|------|
| **測試目標** | 驗證 LLM 呼叫失敗時工作流程狀態正確更新 |
| **前置條件** | 設定無效的 LLM API Key |
| **測試步驟** | 1. 設定錯誤的 `LLM_API_KEY`<br> 2. 啟動工作流程<br> 3. 等待執行失敗 |
| **預期結果** | StepExecution.status = `failed`，WorkflowRun.status = `failed` |
| **目前狀態** | ✅ 已修復（2026-03-16）：成功、失敗、例外三種情況皆更新 StepExecution.status |

---

## 4. E2E 使用者旅程測試

### TC-E01：完整端到端（設備監控 Dashboard）

```
步驟 1: 建立專案 "設備監控 Dashboard 專案"
步驟 2: 啟動「標準 Spec 流程」，輸入需求
步驟 3: PM Agent 產出 product_spec（含使用者故事、驗收標準）
步驟 4: Architect Agent review，若需要修改則回傳給 PM
步驟 5: QA Agent 產出 qa_checklist（測試項目、測試案例）
步驟 6: Director Agent 最終審核批准
步驟 7: 下載 .docx 文件，確認格式正確
```

**驗收標準：**
- [ ] 全程無 500 錯誤
- [ ] 每個 Agent 步驟產出非空 Markdown 內容
- [ ] DOCX 可正常開啟，包含所有 Agent 的輸出
- [ ] WorkflowRun.status 最終為 `completed`

---

### TC-E02：LLM 動態路由決策

```
步驟 1: 啟動流程，等待 PM 產出
步驟 2: 觀察 Architect review 後的 LLM routing 決策
步驟 3: 確認路由結果（通過 → QA，不通過 → 回 PM）
步驟 4: 驗證 StepExecution.routing_decision 欄位有記錄
```

**驗收標準：**
- [ ] LLM routing 回傳合法的 option 編號（1 或 2）
- [ ] 流程根據決策正確流向下一步
- [ ] 不存在無限迴圈

---

## 5. API 介面測試

### TC-A01：工作流程模板列表

```http
GET /api/v1/workflows/templates
Expected: 200 OK, 陣列包含至少 3 個系統模板
```

### TC-A02：啟動工作流程

```http
POST /api/v1/workflows/runs
Body: {"project_id": "...", "template_id": "...", "user_input": "..."}
Expected: 201, 回傳 WorkflowRun 物件含 id, status: "running"
```

### TC-A03：Approval ✅（已修復）

```http
POST /api/v1/workflows/runs/{run_id}/approve?approved=true
Expected: 200, workflow 繼續執行下一步
修復後: ✅ 批准時觸發 LLM 路由繼續執行；非 waiting_approval 狀態回傳 400
```

### TC-A04：下載 DOCX

```http
GET /api/v1/artifacts/{artifact_id}/download
Expected: 200, Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
```

### TC-A05：批量下載

```http
GET /api/v1/artifacts/projects/{project_id}/download
Expected: 200, DOCX 包含所有 artifact 內容，依 agent_role 分章節
```

---

## 6. 已知 Bug 清單

| Bug ID | 位置 | 描述 | 嚴重度 |
|--------|------|------|--------|
| BUG-001 | `workflows.py:217` | `/approve` endpoint 是空的，流程無法因人工審批而推進 | 🔴 Critical | ✅ 已修復 |
| BUG-002 | `agent_worker.py:110` | 步驟執行失敗時，StepExecution.status 不更新為 `failed` | 🔴 Critical | ✅ 已修復 |
| BUG-003 | `WorkflowPage.tsx:146` | 「查看產出文件」按鈕沒有 onClick，點擊無反應 | 🟠 Major | ✅ 已修復 |
| BUG-004 | `session_manager.py:432` | AgentMemory.key_decisions 永遠是空陣列，不提取決策 | 🟡 Minor | ❌ 待處理 |
| BUG-005 | `_has_pending_steps()` | 迴圈步驟計算邏輯可能導致已完成流程仍顯示 pending | 🟡 Minor | ❌ 待處理 |

---

## 7. 測試檢查清單

### 後端
- [ ] `python init_db.py` 無報錯，種入預設 Agent 和 Template
- [ ] `GET /health` 回傳 `{"status": "healthy"}`
- [ ] LLM 測試連線成功（需有效 API Key）
- [ ] 工作流程可啟動並執行到第一個 Agent 步驟
- [ ] Artifact 產生並可查詢
- [ ] DOCX 匯出無錯誤

### 前端
- [ ] Dashboard 顯示專案列表
- [ ] 新建專案成功
- [ ] 選擇模板啟動工作流程
- [ ] WorkflowPage 步驟狀態正確顯示（灰/藍/綠）
- [ ] 步驟執行次數顯示正確
- [ ] 完成後可下載文件

### 待修復後驗證（需實際環境驗收）
- [x] BUG-001：Approval 後流程推進 — 已修復，待環境驗收
- [x] BUG-002：失敗步驟顯示 `failed` 狀態 — 已修復，待環境驗收
- [x] BUG-003：文件下載按鈕可用 — 已修復，待環境驗收
- [ ] BUG-004：key_decisions 提取（minor，可延後）
- [ ] BUG-005：_has_pending_steps 邏輯驗證
