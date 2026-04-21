# Quick Start — 部署白話指引 🚀

> 完整 SOP 看 [EC2_DEPLOYMENT_SOP.md](EC2_DEPLOYMENT_SOP.md)。這份是給**第一次部署、對指令不熟**的人用的速查表。

---

## 你只需要決定 3 件事

### 1️⃣ `LLM_API_KEY` — 你的 AI 金鑰

從 <https://openrouter.ai/settings/keys> 申請，會長這樣：
```
sk-or-v1-abc123...（大約 60 個字元）
```

**⚠️ 絕對不要 commit 到 git！** 永遠只寫在 `.env` 檔裡。

---

### 2️⃣ `DOMAIN` — 你要讓人打的網址

你已經擁有的 domain（例如 `example.com`）前面加一個子名稱即可：

| 想起的網址 | 你要填 |
|------------|--------|
| `agent.example.com` | `DOMAIN=agent.example.com` |
| `pm.example.com` | `DOMAIN=pm.example.com` |
| `dev.example.com` | `DOMAIN=dev.example.com` |
| `test.example.com` | `DOMAIN=test.example.com` |

**配對動作（重要）：**
- 登入你的 domain 管理後台（GoDaddy / Cloudflare / Route53 都行）
- 新增一筆 **A record**：
  - Name = 子名稱（例：`agent`）
  - Value = 你伺服器的公開 IP
  - TTL = 600
- 等 5–15 分鐘，用這個指令確認生效：
  ```bash
  dig +short agent.example.com
  # 應該回傳你的 IP
  ```

---

### 3️⃣ `ADMIN_EMAIL` — 你的聯絡信箱

給 Let's Encrypt 通知 SSL 憑證到期用。**填你自己常用的 Gmail / 公司信箱**即可。憑證有自動續約，基本上不會收到信。

範例：
```
ADMIN_EMAIL=you@gmail.com
```

---

## `SECRET_KEY` — 伺服器自己用的隨機字串（不用你自己想）

這是伺服器內部加密用的鑰匙，你**不會直接用到**，但每台伺服器要不一樣。

### 最快做法：一行指令直接把 `.env` 改好

SSH 到伺服器後，在終端機跑這行（**照抄即可**）：

```bash
sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$(openssl rand -hex 32)|" /opt/agent-platform/backend/.env
```

這行做三件事：
1. 跑 `openssl rand -hex 32` 產一串隨機 64 位元字
2. 把 `.env` 裡 `SECRET_KEY=xxx` 整行換成新的
3. 你不用手動複製貼上，也不會貼錯

### 驗證有寫進去

```bash
grep ^SECRET_KEY /opt/agent-platform/backend/.env
# 應該看到類似：
# SECRET_KEY=04a84d03b5abccf72cd33109d26ef0499c491476439460b4c0954cdc17638714
```

### ⚠️ 不要這樣做

- ❌ 把上面那串 `04a84d03...` 抄進自己的 `.env`（那是文件範例，所有人都看得到）
- ❌ 所有環境共用同一個 `SECRET_KEY`
- ✅ **每一台伺服器都用 `openssl rand -hex 32` 產一個新的**

---

## 最終 `backend/.env` 範本

### 情境 A：用 OpenRouter（雲端，有 API key）

```bash
# ── 必改 ──────────────────────────────
LLM_API_KEY=sk-or-v1-你的OpenRouter金鑰貼這裡

# ── 用指令產、只改一次 ────────────────────────────
# 跑：openssl rand -hex 32
SECRET_KEY=fd6a513efe3c5df1ffcb5a001c281dde15fb13fbfae53016184cf38140aba99b

# ── 下面全部照抄，不用改 ───────────────────────────
LLM_PROVIDER=openrouter
LLM_MODEL=openrouter/openai/gpt-oss-120b
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
DATABASE_URL=sqlite+aiosqlite:////opt/agent-platform/backend/data/app.db
```

### 情境 B：用公司內部 LLM（OpenAI-compatible，沒 API key）

如果你的 GPT-OSS-120B 是跑在公司內網、有一個 endpoint URL、靠 VPN 保護、**沒有 API key** 的情況：

```bash
# ── 必改：填你公司 LLM 的 URL ─────────────────────────
LLM_BASE_URL=https://llm.company.internal/v1
LLM_MODEL=openai/gpt-oss-120b        # 或你公司給的 model 別名
LLM_API_KEY=                          # ← 留空

# ── 用指令產、只改一次 ────────────────────────────
# 跑：openssl rand -hex 32
SECRET_KEY=fd6a513efe3c5df1ffcb5a001c281dde15fb13fbfae53016184cf38140aba99b

# ── 下面全部照抄 ─────────────────────────────────
LLM_PROVIDER=openai
DATABASE_URL=sqlite+aiosqlite:////opt/agent-platform/backend/data/app.db
```

**驗證：** 部署完後跑 `curl https://<your-domain>/health`，應該看到：
```json
{"llm_configured": true, "llm_base_url": "https://llm.company.internal/v1"}
```

> ℹ️ 如果公司 endpoint 其實需要一個 token（不完全 keyless），把 token 填到 `LLM_API_KEY=` 即可，其他不變。

---

## 實際部署到新環境的完整指令（照抄改 3 個值）

```bash
# ═══ 只有這 3 行要改 ═══
export DOMAIN=agent.example.com        # ← 你決定的網址
export ADMIN_EMAIL=you@gmail.com       # ← 你的 email
export APP_DIR=/opt/agent-platform     # ← 裝哪裡（保留預設即可）
# ════════════════════════

# 下面這段照抄就行，不用改任何東西
sudo apt update && sudo apt install -y \
    python3.12 python3.12-venv python3-pip \
    nginx certbot python3-certbot-nginx \
    git sqlite3 gettext-base
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

sudo mkdir -p $APP_DIR && sudo chown $USER:$USER $APP_DIR
git clone -b feat/monitoring https://github.com/gillggx/agent-platform.git $APP_DIR
cd $APP_DIR

cp backend/.env.example backend/.env
chmod 600 backend/.env

# 自動把 LLM_API_KEY 和 SECRET_KEY 填進 .env
# （你要先 export LLM_API_KEY=sk-or-v1-...，或下一步手動編輯 .env）
SK=$(openssl rand -hex 32)
sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$SK|" backend/.env
echo ""
echo "⚠️  現在用編輯器打開 $APP_DIR/backend/.env，把 LLM_API_KEY 填進去"
echo "    範例：vi $APP_DIR/backend/.env"
read -p "按 Enter 繼續..."

# 後端
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python init_db.py
for mig in migrations/*.py; do .venv/bin/python "$mig"; done

# 前端
cd ../frontend
npm ci
npx vite build

# systemd service
cd $APP_DIR
export RUN_USER=$USER
export BACKEND_PORT=8080
envsubst '${APP_DIR} ${RUN_USER} ${BACKEND_PORT}' \
    < deploy/systemd/agent-platform-backend.service.template \
    | sudo tee /etc/systemd/system/agent-platform-backend.service > /dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now agent-platform-backend

# Nginx + SSL（需要 DNS 已生效）
sudo mkdir -p /var/www/certbot
sudo tee /etc/nginx/sites-available/agent-platform > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 200 'bootstrap'; }
}
EOF
sudo ln -sf /etc/nginx/sites-available/agent-platform /etc/nginx/sites-enabled/agent-platform
sudo nginx -t && sudo systemctl reload nginx

sudo certbot certonly --webroot -w /var/www/certbot -d $DOMAIN \
    --non-interactive --agree-tos -m $ADMIN_EMAIL

envsubst '${DOMAIN} ${APP_DIR} ${BACKEND_PORT}' \
    < deploy/nginx/agent-platform.conf.template \
    | sudo tee /etc/nginx/sites-available/agent-platform > /dev/null
sudo nginx -t && sudo systemctl reload nginx

echo ""
echo "✅ 完成！打開 https://$DOMAIN"
```

---

## 驗證跑起來了

```bash
# 1. 伺服器健康
curl -s https://$DOMAIN/health

# 應該看到：
# {"status":"ok", ... "llm_configured":true}

# 2. 瀏覽器打開
open https://$DOMAIN/   # Mac
# 或直接在瀏覽器貼網址
```

---

## 遇到問題？

| 症狀 | 做什麼 |
|------|--------|
| 瀏覽器顯示 `502 Bad Gateway` | `sudo journalctl -u agent-platform-backend -n 30` 看錯誤 |
| PM 聊天回 `Key limit exceeded` | OpenRouter 金鑰用完或打錯 — 重新檢查 `backend/.env` 的 `LLM_API_KEY` |
| `certbot` 失敗說 DNS 沒解析 | 等 15 分鐘讓 DNS 傳播，再跑 `dig +short $DOMAIN` 確認 |
| 工作流程跑但沒回應 | 檢查 `backend/.env` 的 `LLM_API_KEY` 是否正確 |
| 下載檔打開是亂碼 | 瀏覽器快取 — 硬清 `Cmd+Shift+R` / `Ctrl+Shift+F5` |

詳細排錯看 [EC2_DEPLOYMENT_SOP.md § 11](EC2_DEPLOYMENT_SOP.md#11-troubleshooting)。
