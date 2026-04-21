# Agent Platform — EC2 Deployment SOP

> Based on the real deployment to `agent-platform.aiops-gill.com` on AWS EC2 (Ubuntu 24.04). Default values preserved — replace only the machine-specific and secret parts (`${DOMAIN}`, `${IP}`, `LLM_API_KEY`, SSH key path).

---

## 0. What you get at the end

- `https://<your-subdomain>` serving the full PM Co-pilot UI
- Backend FastAPI on `127.0.0.1:8080` (not exposed directly)
- Nginx reverse-proxy with Let's Encrypt SSL (auto-renews every 90 days)
- systemd-managed backend (auto-restart on crash, auto-start on boot)
- Per-browser anonymous user isolation out of the box
- OpenRouter + `gpt-oss-120b` as the default LLM (change `LLM_MODEL` in `.env` to switch)

---

## 1. Machine Requirements

| Item | Minimum | Notes |
|------|---------|-------|
| OS | Ubuntu 22.04 / 24.04 | Other distros work but paths in this SOP are Debian/Ubuntu |
| CPU | 2 vCPU | `t3.medium` on AWS is fine |
| RAM | 2 GB | 4 GB recommended; backend caps at 600 MB via systemd |
| Disk | 10 GB free | SQLite DB + frontend build + node_modules ~ 1 GB |
| Network | Public IP, ports 80/443 open | Backend 8080 stays on localhost |

---

## 2. Prerequisites (install once)

```bash
sudo apt update
sudo apt install -y \
    python3.12 python3.12-venv python3-pip \
    nginx certbot python3-certbot-nginx \
    git sqlite3 gettext-base

# Node.js 20 (needed to build the frontend; not kept running in prod)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

Verify:
```bash
python3 --version   # 3.12+
node --version      # v20+
nginx -v
certbot --version
```

---

## 3. DNS Setup

Before running the installer, point the target hostname at the server:

1. Go to your domain registrar (GoDaddy, Cloudflare, Route53 — doesn't matter).
2. Add an **A record**:
   - **Name**: `<subdomain>` (e.g., `agent-platform`)
   - **Value**: EC2 public IP
   - **TTL**: 300–600s
3. Verify propagation from **any external machine**:
   ```bash
   dig +short <subdomain>.<yourdomain>.com
   # Should print the EC2 IP
   ```
4. **Don't proceed until DNS resolves.** certbot's HTTP-01 challenge will fail otherwise.

---

## 4. Clone + Configure

Repo URL: `https://github.com/gillggx/agent-platform` (branch: `feat/monitoring` as of this SOP).

```bash
# Pick a deploy target; /opt is a common choice
sudo mkdir -p /opt/agent-platform
sudo chown $USER:$USER /opt/agent-platform
git clone -b feat/monitoring https://github.com/gillggx/agent-platform.git /opt/agent-platform
cd /opt/agent-platform

# Create the backend env file
cp backend/.env.example backend/.env
chmod 600 backend/.env
```

Now edit `backend/.env` — **the only value that MUST change is `LLM_API_KEY`**. Everything else is production-safe defaults. Example minimum config:

```bash
# Required — get your own key from https://openrouter.ai/settings/keys
LLM_API_KEY=sk-or-v1-REPLACE_ME

# Defaults used in production — keep as-is unless you have a reason
LLM_PROVIDER=openrouter
LLM_MODEL=openrouter/openai/gpt-oss-120b
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
DATABASE_URL=sqlite+aiosqlite:////opt/agent-platform/backend/data/app.db
SECRET_KEY=REPLACE_WITH_RANDOM_32_CHARS  # openssl rand -hex 32
```

Generate a fresh `SECRET_KEY`:
```bash
SK=$(openssl rand -hex 32)
sudo sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$SK|" /opt/agent-platform/backend/.env
```

---

## 5. Install & Seed

### 5.1 Backend virtualenv + dependencies

```bash
cd /opt/agent-platform/backend
python3 -m venv .venv
.venv/bin/pip install --upgrade pip --quiet
.venv/bin/pip install -r requirements.txt
```

### 5.2 Create DB schema + seed agents/templates (one-time)

```bash
.venv/bin/python init_db.py
# Expected tail:
#   ✓ Database tables created
#   Created system agent: PM Agent
#   ...
#   Created system template: 標準 Spec 流程
#   ✓ Default system data seeded
```

### 5.3 Run migrations

```bash
for mig in migrations/*.py; do
    .venv/bin/python "$mig"
done
# Safe to re-run — each script is idempotent.
```

### 5.4 Build frontend (static files only — no node server needed in prod)

```bash
cd /opt/agent-platform/frontend
npm ci --silent
npx vite build
# Output: /opt/agent-platform/frontend/dist/
```

> TypeScript errors on unused legacy files (`LoginPage.tsx`, etc.) are OK to skip by calling `npx vite build` directly instead of the `npm run build` script (which includes `tsc`).

---

## 6. systemd Service

Render the template and install:

```bash
export APP_DIR=/opt/agent-platform
export RUN_USER=$USER   # or 'ubuntu' on AWS default AMI
export BACKEND_PORT=8080

envsubst '${APP_DIR} ${RUN_USER} ${BACKEND_PORT}' \
    < /opt/agent-platform/deploy/systemd/agent-platform-backend.service.template \
    | sudo tee /etc/systemd/system/agent-platform-backend.service > /dev/null

sudo systemctl daemon-reload
sudo systemctl enable --now agent-platform-backend
sleep 3
sudo systemctl is-active agent-platform-backend   # "active"
```

Smoke test (localhost only):
```bash
curl -s http://127.0.0.1:8080/health
# {"status":"ok", ... "llm_configured":true}
```

---

## 7. Nginx + Let's Encrypt SSL

### 7.1 Create cert directory + bootstrap HTTP-only server block

```bash
sudo mkdir -p /var/www/certbot

sudo tee /etc/nginx/sites-available/agent-platform > /dev/null <<'EOF'
server {
    listen 80;
    server_name ${DOMAIN};

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 200 'bootstrap';
    }
}
EOF

# Render the ${DOMAIN} placeholder
export DOMAIN=<your-subdomain>.<yourdomain>.com   # e.g. agent-platform.example.com
sudo sed -i "s|\${DOMAIN}|$DOMAIN|g" /etc/nginx/sites-available/agent-platform

sudo ln -sf /etc/nginx/sites-available/agent-platform /etc/nginx/sites-enabled/agent-platform
sudo nginx -t
sudo systemctl reload nginx
```

### 7.2 Obtain SSL certificate

```bash
sudo certbot certonly --webroot -w /var/www/certbot -d $DOMAIN \
    --non-interactive --agree-tos -m <your-email>
# Expected: "Successfully received certificate."
```

Certbot installs a renewal timer automatically. Verify:
```bash
sudo systemctl list-timers | grep certbot
sudo certbot renew --dry-run
```

### 7.3 Replace HTTP-only config with full HTTPS config

Render the full config from the repo template:

```bash
export APP_DIR=/opt/agent-platform
export DOMAIN=<your-subdomain>.<yourdomain>.com
export BACKEND_PORT=8080

envsubst '${DOMAIN} ${APP_DIR} ${BACKEND_PORT}' \
    < /opt/agent-platform/deploy/nginx/agent-platform.conf.template \
    | sudo tee /etc/nginx/sites-available/agent-platform > /dev/null

sudo nginx -t
sudo systemctl reload nginx
```

---

## 8. End-to-End Verification

```bash
DOMAIN=<your-subdomain>.<yourdomain>.com

echo "=== 1. HTTPS health ==="
curl -s https://$DOMAIN/health

echo ""
echo "=== 2. Frontend HTML loads ==="
curl -sI https://$DOMAIN/ | head -3

echo ""
echo "=== 3. Templates API ==="
curl -s https://$DOMAIN/api/v1/workflows/templates \
    | python3 -c "import sys,json; print([t['name'] for t in json.load(sys.stdin)])"

echo ""
echo "=== 4. PM chat SSE ==="
curl -sN -X POST https://$DOMAIN/api/v1/chat/message \
    -H "Content-Type: application/json" \
    -H "X-Client-ID: 00000000-0000-4000-0000-000000000001" \
    -d '{"message":"hi","intake_already_triggered":false}' \
    --max-time 30 | head -5
# Should stream `data: {"type": "delta", "content": "..."}`
```

All four should succeed. Then open `https://$DOMAIN/` in a browser — you'll see the PM Co-pilot chat interface.

---

## 9. Updates After `git pull`

```bash
cd /opt/agent-platform
git pull --ff-only

# Backend: refresh deps + run any new migrations
cd backend
.venv/bin/pip install -r requirements.txt --quiet
for mig in migrations/*.py; do
    .venv/bin/python "$mig"
done

# Frontend: rebuild if files changed under frontend/
cd ../frontend
npx vite build

# Restart backend to pick up code + soul changes
sudo systemctl restart agent-platform-backend
sudo systemctl is-active agent-platform-backend
```

No nginx reload needed unless you change `deploy/nginx/*.template`.

---

## 10. Operations Cheatsheet

```bash
# Live logs (follow)
sudo journalctl -u agent-platform-backend -f

# Last 50 lines
sudo journalctl -u agent-platform-backend -n 50 --no-pager

# Switch LLM model without redeploying
sudo sed -i 's|^LLM_MODEL=.*|LLM_MODEL=openrouter/anthropic/claude-sonnet-4-5|' \
    /opt/agent-platform/backend/.env
sudo systemctl restart agent-platform-backend

# Rotate LLM_API_KEY
sudo sed -i 's|^LLM_API_KEY=.*|LLM_API_KEY=sk-or-NEW|' \
    /opt/agent-platform/backend/.env
sudo systemctl restart agent-platform-backend

# Clear all projects / chat for a fresh demo (DESTRUCTIVE)
sqlite3 /opt/agent-platform/backend/data/app.db \
    "DELETE FROM chat_messages; DELETE FROM projects; DELETE FROM workflow_runs; DELETE FROM artifacts;"

# Backup DB
cp /opt/agent-platform/backend/data/app.db \
   /opt/agent-platform/backend/data/app.db.$(date +%Y%m%d-%H%M%S).bak

# Force SSL renewal test
sudo certbot renew --dry-run
```

---

## 11. Troubleshooting

### `502 Bad Gateway` from nginx
Backend is down or still starting.
```bash
sudo systemctl status agent-platform-backend
sudo journalctl -u agent-platform-backend -n 30
```
Usually: LLM_API_KEY missing/invalid, or port 8080 taken by another service.

### PM chat returns error `Key limit exceeded` / `rate-limited upstream`
OpenRouter key out of credit OR hit the shared Gemini free-tier limit.
- Top up OpenRouter OR
- Switch model: `LLM_MODEL=openrouter/openai/gpt-oss-120b` (less contention)

### Workflow runs but no LLM is called
Check `step_executions._log` in the workflow run — exception gets written there. Common causes:
- `LLM_API_KEY` wrong → check `/health` returns `llm_configured:true`
- Agent definitions missing → re-run `init_db.py`

### Download gives `.md` file that looks like gibberish
Browser cached old frontend. Hard-refresh: **Cmd+Shift+R / Ctrl+Shift+F5**.

### Certbot HTTP-01 challenge fails
DNS hasn't propagated yet. Wait 10–30 min and retry:
```bash
dig +short $DOMAIN   # must show your IP from any external location
```

### Existing nginx configs conflict (`warn: conflicting server name`)
Check `/etc/nginx/sites-enabled/` — backup files with the same `server_name` get auto-loaded. Move them out:
```bash
sudo mv /etc/nginx/sites-enabled/<file>.backup* /etc/nginx/sites-available/
sudo nginx -t && sudo systemctl reload nginx
```

---

## 12. Files This Deployment Touches

| Path | Owner | Purpose |
|------|-------|---------|
| `/opt/agent-platform/` | $USER | Clone of the repo + built artifacts |
| `/opt/agent-platform/backend/.venv/` | $USER | Python virtualenv |
| `/opt/agent-platform/backend/.env` | $USER (0600) | Contains `LLM_API_KEY` — **never commit** |
| `/opt/agent-platform/backend/data/app.db` | $USER | SQLite (users, chats, workflows, artifacts) |
| `/opt/agent-platform/frontend/dist/` | $USER | Static frontend served by nginx |
| `/etc/systemd/system/agent-platform-backend.service` | root | Backend process manager |
| `/etc/nginx/sites-available/agent-platform` | root | Nginx vhost |
| `/etc/nginx/sites-enabled/agent-platform` | root | Symlink to above |
| `/etc/letsencrypt/live/<DOMAIN>/` | root | TLS cert + key |
| `/var/www/certbot/` | root | ACME challenge webroot |

Removing a deployment cleanly:
```bash
sudo systemctl disable --now agent-platform-backend
sudo rm /etc/systemd/system/agent-platform-backend.service
sudo rm /etc/nginx/sites-enabled/agent-platform /etc/nginx/sites-available/agent-platform
sudo certbot delete --cert-name $DOMAIN
sudo systemctl reload nginx
sudo rm -rf /opt/agent-platform
```

---

## 13. Sanity Defaults Snapshot (what's kept across deployments)

These came from the production install and stay as-is unless you have a reason:

- Backend binds to `127.0.0.1:8080` (never directly exposed)
- systemd `MemoryMax=600M`, `Restart=always`, `RestartSec=5`
- Nginx enables HTTP/2, TLS 1.2/1.3, gzip for JSON/JS/CSS
- SSE endpoint (`/api/v1/chat/message`) has `proxy_buffering off` + `proxy_read_timeout 300s` — needed for PM Co-pilot streaming
- SPA fallback: all unmatched paths serve `index.html` so React Router client-side routes work on hard refresh
- Static assets under `/assets/` cached `max-age=31536000, immutable`
- SQLite DB stored at `/opt/agent-platform/backend/data/app.db`
- Workflow template seed files synced from `backend/app/data/default_templates.py` on every backend restart (edits to these files auto-apply on restart)
- Soul files synced from `backend/souls/*.md` on every backend restart (same pattern)

Everything above survives updates via `git pull + restart` without manual intervention.
