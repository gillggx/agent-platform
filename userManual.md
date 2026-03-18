# Agent Platform 使用手冊 & 驗證指南

本文件同時服務兩個目的：
1. **使用者操作手冊** — 從建立專案到下載文件的完整流程說明
2. **QA 驗證指南** — 對照 QA Checklist，逐步驗證系統關鍵功能

---

## 目錄

- [系統啟動確認](#系統啟動確認)
- [第一次使用：登入與帳號設定](#第一次使用登入與帳號設定)
- [完整使用流程](#完整使用流程)
- [QA 驗證步驟（對照 Checklist）](#qa-驗證步驟對照-checklist)
- [常見狀態說明](#常見狀態說明)
- [下載產出文件](#下載產出文件)
- [人工審批流程](#人工審批流程)
- [已知限制與注意事項](#已知限制與注意事項)

---

## 系統啟動確認

開始使用前，請確認以下三個服務**都在執行中**：

### Dev 模式檢查清單

```bash
# 1. 確認 API 服務正常
curl http://localhost:8000/health
# 預期回應: {"status": "ok", ...}

# 2. 確認前端可存取
# 瀏覽器開啟: http://localhost:5173
# 應該看到登入或 Dashboard 頁面

# 3. 確認 Agent Worker 在執行中（重要！）
# Worker 沒跑的話，工作流程會永遠卡在 running
ps aux | grep agent_worker   # 應看到 python -m agent_worker 行程

# 4. 確認 Redis 正常（Worker 需要）
redis-cli ping               # 應回 PONG
```

### 快速確認 API 端點

```bash
# API 文件 (Swagger UI)
open http://localhost:8000/docs

# 或用 curl 確認各模組健康
curl http://localhost:8000/health
```

---

## 第一次使用：登入與帳號設定

### 取得 JWT Token（API 方式）

系統使用 JWT 驗證。開發環境可用 Swagger UI 登入：

1. 開啟 http://localhost:8000/docs
2. 找到 `POST /api/v1/auth/login`
3. 點 **Try it out** → 輸入：
   ```json
   {
     "email": "demo@example.com",
     "password": "demo123"
   }
   ```
4. 執行，複製回應中的 `access_token`
5. 點頁面右上角 **Authorize**，貼入 `Bearer <token>`

> 若 demo 帳號不存在，請先執行：
> ```bash
> cd backend && python init_db.py
> ```
> init_db.py 會自動建立 demo 組織和帳號。

### 前端登入

1. 開啟 http://localhost:5173
2. 輸入 Email: `demo@example.com`，Password: `demo123`
3. 登入後進入 Dashboard

---

## 完整使用流程

### Step 1：建立專案

**透過前端：**
1. 在 Dashboard 點擊「新建專案」
2. 填入：
   - 名稱：例如 `電商訂單系統`
   - 描述（選填）：`B2C 電商平台的訂單管理模組`
3. 點確認，專案建立完成

**透過 API：**
```bash
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "電商訂單系統", "description": "B2C 電商平台"}'
```

### Step 2：啟動工作流程

1. 進入專案頁面，點擊「啟動工作流程」
2. 選擇工作流程模板（預設：`標準 Spec 流程`）
3. 在「需求描述」欄位輸入你的需求，例如：

   ```
   我需要一個電商訂單管理系統，支援以下功能：
   - 訂單建立、查詢、取消
   - 多種付款方式（信用卡、Line Pay、ATM）
   - 訂單狀態追蹤（待付款、已付款、出貨中、已送達）
   - 退款申請流程

   預估 DAU 10,000，需考慮高峰時段 QPS 500。
   ```

4. 點「開始執行」，系統會將任務丟進 Agent Worker 執行

**透過 API：**
```bash
# 先取得 template_id
curl http://localhost:8000/api/v1/workflows/templates \
  -H "Authorization: Bearer <token>"

# 啟動工作流程
curl -X POST http://localhost:8000/api/v1/workflows/runs \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "<project_id>",
    "template_id": "<template_id>",
    "user_input": "我需要一個電商訂單管理系統..."
  }'
```

### Step 3：監控執行進度

工作流程啟動後，前往「工作流程執行」頁面：

- 頁面每 **5 秒自動更新**
- 可看到各 Agent 步驟的即時狀態：
  - ⏳ 灰色時鐘：等待中
  - 🔵 藍色旋轉：執行中
  - ✅ 綠色勾勾：已完成
  - ❌ 紅色驚嘆號：執行失敗

**標準 Spec 流程執行順序：**
```
pm_draft → architect_review → qa_plan → director_review → export
```
每個步驟完成後，可點「查看產出」預覽該 Agent 的輸出內容。

### Step 4：人工審批（若需要）

當狀態變為「等待人工審批」（橘色 banner 出現時）：

1. 點擊「前往審批」按鈕
2. 閱讀各 Agent 的產出物
3. 決定：
   - **批准** → 繼續執行，產出最終文件
   - **退回修改** → 必須填寫意見，系統退回 PM Agent 重新撰寫

詳見下方「[人工審批流程](#人工審批流程)」章節。

### Step 5：下載文件

流程完成後（狀態：已完成）：
- 點擊「下載完整文件」→ 下載所有 Agent 產出的合併 `.docx`
- 或點每個步驟旁的「下載」→ 下載單一 Agent 的輸出

---

## QA 驗證步驟（對照 Checklist）

以下按照 **Agent Platform QA Checklist.md** 的里程碑順序，說明如何驗證每個關鍵功能。

---

### M1：基礎骨架驗證

#### 1.1 資料庫初始化

```bash
cd backend
python init_db.py
```

**預期：**
- 輸出 `✓ Database tables created`
- 輸出 `✓ Default system data seeded`
- 在 `data/app.db` 看到 SQLite 檔案

#### 1.2 API 健康檢查

```bash
curl http://localhost:8000/health
```

**預期回應：**
```json
{"status": "ok"}
```

#### 1.3 登入驗證

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "demo@example.com", "password": "demo123"}'
```

**預期：** 回傳含 `access_token` 的 JSON，HTTP 200

---

### M2：Agent Runtime 驗證

#### 2.1 建立專案

```bash
TOKEN="<your-jwt-token>"

curl -X POST http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "M2 Test Project"}'
```

**預期：** HTTP 201，回傳含 `id` 的 project 物件

#### 2.2 取得工作流程模板

```bash
curl http://localhost:8000/api/v1/workflows/templates \
  -H "Authorization: Bearer $TOKEN"
```

**預期：** 回傳模板列表，包含至少一個 `is_system: true` 的模板

#### 2.3 啟動簡單工作流程並觀察 Agent Session

啟動後，Worker 日誌應顯示：
```
[worker] dispatching step: pm_draft for session <id>
[worker] LLM call starting...
[worker] Step pm_draft completed, artifact saved
```

若看到這些 log，表示 Agent Runtime（M2）運作正常。

---

### M3：Workflow Engine 驗證（最重要）

#### 3.1 完整 E2E 流程驗證

**測試案例：標準 Spec 流程**

```bash
# 1. 建立專案
PROJECT=$(curl -s -X POST http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "E2E Test"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "Project ID: $PROJECT"

# 2. 取得模板 ID
TEMPLATE=$(curl -s http://localhost:8000/api/v1/workflows/templates \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")

echo "Template ID: $TEMPLATE"

# 3. 啟動工作流程
RUN=$(curl -s -X POST http://localhost:8000/api/v1/workflows/runs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"project_id\": \"$PROJECT\", \"template_id\": \"$TEMPLATE\", \"user_input\": \"建立一個簡單的 Todo 應用，支援新增、刪除、完成任務\"}" | \
  python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "Run ID: $RUN"
```

**持續查詢狀態（每 10 秒一次）：**

```bash
watch -n 10 "curl -s http://localhost:8000/api/v1/workflows/runs/$RUN \
  -H 'Authorization: Bearer $TOKEN' | python3 -c \"import sys,json; d=json.load(sys.stdin); print(d['status'], d['current_steps'])\""
```

**預期狀態流轉：**
```
running → running → ... → waiting_approval → completed
```

#### 3.2 驗證人工審批流程

當狀態變為 `waiting_approval`：

```bash
# 批准
curl -X POST http://localhost:8000/api/v1/workflows/runs/$RUN/approve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'

# 或退回（需填意見）
curl -X POST http://localhost:8000/api/v1/workflows/runs/$RUN/approve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"approved": false, "feedback": "請補充非功能性需求，包含效能指標和安全性要求"}'
```

**驗證退回行為：**
- 退回後，`current_steps` 應回到 `["pm_revise"]` 或類似修改步驟
- PM Agent 應重新執行，並在上下文中包含退回意見

#### 3.3 驗證 LLM Routing

執行完成後，查看 `step_executions` 裡的 routing_decision：

```bash
curl -s http://localhost:8000/api/v1/workflows/runs/$RUN \
  -H "Authorization: Bearer $TOKEN" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d.get('step_executions', {}), indent=2, ensure_ascii=False))"
```

**預期：** 有 `routing_decision` 欄位，包含 `chosen_label`、`target_step`

#### 3.4 驗證 Artifact 產出

```bash
# 列出所有產出物
curl http://localhost:8000/api/v1/artifacts?project_id=$PROJECT \
  -H "Authorization: Bearer $TOKEN"
```

**預期：**
- 每個 Agent 步驟都有對應的 artifact
- `status` 欄位為 `active`（非 `superseded`）
- `content_preview` 非空

#### 3.5 驗證 DOCX 下載

```bash
# 下載完整文件
curl -o output.docx \
  http://localhost:8000/api/v1/artifacts/project/$PROJECT/download \
  -H "Authorization: Bearer $TOKEN"

# 確認是有效的 docx（zip 格式）
file output.docx
# 預期: output.docx: Microsoft Word 2007+
```

#### 3.6 驗證 Timeout 行為

模擬超時：在 `.env` 設 `AGENT_SESSION_TIMEOUT_MINUTES=0`，啟動一個工作流程。

**預期：** Agent session 變為 `error` 狀態，workflow run 變為 `failed`

---

### M5：前端 UI 驗證

在瀏覽器進行以下檢查：

| 項目 | 驗證方式 | 預期 |
|------|---------|------|
| 狀態顯示 | 工作流程執行頁面 | 各步驟有正確圖示（勾/旋轉/叉/時鐘）|
| 自動刷新 | running 狀態時等待 | 頁面每 5 秒更新狀態 |
| Artifact 查看 | 點「查看產出」 | 展開顯示 Markdown 內容 |
| 單檔下載 | 點各步驟的「下載」 | 下載對應 `.docx` 檔案 |
| 完整下載 | 流程完成後點「下載完整文件」 | 下載合併版 `.docx` |
| 審批 Modal | 狀態 waiting_approval 時 | 橘色 banner + 前往審批按鈕 |
| 退回驗證 | Modal 中不填意見直接退回 | 警告「退回時請填寫意見回饋」|

---

## 常見狀態說明

| 狀態 | 顏色 | 說明 |
|------|------|------|
| `running` | 藍色 processing | Agent 正在執行 LLM 呼叫 |
| `waiting_approval` | 橘色 | 已暫停，等待人工審批 |
| `completed` | 綠色 success | 全部步驟完成，文件已產出 |
| `failed` | 紅色 error | 某步驟失敗（查看 Worker 日誌）|
| `timeout` | 黃色 warning | 執行時間超過 timeout_minutes 設定 |

---

## 下載產出文件

### 前端操作

1. 進入已完成的工作流程頁面
2. 在「產出物總覽」區塊展開各 Agent 的輸出
3. 每個 Artifact 右側有「下載」按鈕（下載單一 `.docx`）
4. 頁面底部的「下載完整文件」按鈕可下載**所有 Artifact 合併**的 `.docx`

### API 操作

```bash
# 下載單一 artifact
curl -o artifact.docx \
  http://localhost:8000/api/v1/artifacts/<artifact_id>/download \
  -H "Authorization: Bearer $TOKEN"

# 下載專案所有 artifact 合併版
curl -o full_spec.docx \
  http://localhost:8000/api/v1/artifacts/project/<project_id>/download \
  -H "Authorization: Bearer $TOKEN"
```

---

## 人工審批流程

### 觸發條件

當工作流程模板的 `guardrails.require_human_approval` 包含某個步驟 ID，該步驟完成後系統會：
1. 暫停工作流程
2. 設定狀態為 `waiting_approval`
3. 前端顯示橘色審批提示 banner

### 審批決定

**批准流程繼續：**
- 前端：點「前往審批」→「批准，產出文件」
- API：`POST /api/v1/workflows/runs/{run_id}/approve` 帶 `{"approved": true}`

**退回重新修改：**
- 前端：填寫退回意見 → 點「退回修改」
- API：帶 `{"approved": false, "feedback": "你的修改意見"}`
- 退回後：PM Agent 會收到附帶退回意見的上下文，重新撰寫
- 退回次數上限：由 `loop.max_iterations` 控制（預設 3 次）

### 注意事項

- 退回意見**必填**，否則 PM Agent 無法知道要改什麼
- 審批動作只在 `waiting_approval` 狀態有效；其他狀態呼叫會回傳 HTTP 400
- 批准後工作流程自動繼續，無需其他操作

---

## 已知限制與注意事項

### 目前版本限制

1. **M1 Auth（組織/用戶管理）**：目前使用 demo 帳號，尚未完整實作多組織/多用戶管理介面

2. **M4 Knowledge Pack CRUD**：Agent 的 system_prompt 目前從 seed data 載入，尚未開放前端編輯

3. **WebSocket 即時訊息**：前端目前使用輪詢（5 秒），尚未實作 WebSocket 即時推播

4. **MinIO 物件儲存**：Dev 模式下 DOCX 存在本地 `exports/` 目錄，Docker 模式才使用 MinIO

### 效能注意事項

- 每個 Agent 呼叫 LLM 約需 **20~60 秒**（依 model 和需求複雜度而定）
- 完整 5-step 流程預計 **3~8 分鐘**
- 頁面輪詢每 5 秒，不需手動刷新

### LLM Provider 切換

```env
# OpenRouter (推薦，支援多模型)
LLM_PROVIDER=openrouter
LLM_API_KEY=sk-or-...
LLM_MODEL=openrouter/google/gemini-2.0-flash-001

# OpenAI
LLM_PROVIDER=openai
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini

# Anthropic
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-...
LLM_MODEL=claude-haiku-4-5-20251001
```

修改後重啟後端服務即可生效。

---

## 快速診斷腳本

把以下腳本存為 `check_system.sh`，用來快速驗證系統是否正常：

```bash
#!/bin/bash
echo "=== Agent Platform System Check ==="

# 1. API Health
STATUS=$(curl -s http://localhost:8000/health | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','?'))" 2>/dev/null)
echo "API Health: $STATUS"

# 2. Worker
WORKER=$(ps aux | grep "agent_worker" | grep -v grep | wc -l)
echo "Agent Worker processes: $WORKER"

# 3. Redis
REDIS=$(redis-cli ping 2>/dev/null)
echo "Redis: $REDIS"

# 4. Frontend
FE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5173)
echo "Frontend HTTP: $FE"

echo ""
if [ "$STATUS" = "ok" ] && [ "$WORKER" -gt 0 ] && [ "$REDIS" = "PONG" ]; then
    echo "✅ System ready for testing"
else
    echo "❌ Some services are not running"
    echo "   Run: uvicorn app.main:app + python -m agent_worker + npm run dev"
fi
```

```bash
chmod +x check_system.sh && ./check_system.sh
```
