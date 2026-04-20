# Deployment Guide

Production deployment using **Nginx + systemd + Let's Encrypt** on a Linux server (tested on Ubuntu 24.04).

> This layout keeps agent-platform independent of any existing services on the box — it runs on its own port, its own systemd unit, and its own Nginx server block.

---

## Prerequisites

On the target machine:

| Requirement | Install |
|-------------|---------|
| Python 3.12+ | `sudo apt install python3.12 python3.12-venv python3-pip` |
| Node.js 18+ | `curl -fsSL https://deb.nodesource.com/setup_20.x \| sudo -E bash - && sudo apt install nodejs` |
| Nginx | `sudo apt install nginx` |
| Certbot | `sudo apt install certbot python3-certbot-nginx` |
| envsubst | `sudo apt install gettext-base` (usually pre-installed) |

On your domain registrar:
- Add an **A record** pointing `${DOMAIN}` → the server's public IP.
- Wait for DNS propagation before running `install.sh` (certbot needs the domain resolving).
  - Verify: `dig +short ${DOMAIN}` should return the server IP.

---

## First Install

```bash
# 1. Clone repo to target dir
sudo mkdir -p /opt/agent-platform
sudo chown $USER:$USER /opt/agent-platform
git clone https://github.com/gillggx/agent-platform.git /opt/agent-platform
cd /opt/agent-platform

# 2. Create backend/.env and fill in LLM_API_KEY
cp backend/.env.example backend/.env
vi backend/.env   # set LLM_API_KEY, adjust LLM_MODEL if needed, randomize SECRET_KEY
chmod 600 backend/.env

# 3. Run the installer (as root — it writes to /etc/nginx and /etc/systemd)
sudo APP_DIR=/opt/agent-platform \
     DOMAIN=agent-platform.example.com \
     ADMIN_EMAIL=you@example.com \
     bash deploy/install.sh
```

The installer will:
1. Create a Python venv and install backend dependencies
2. Seed the DB (`init_db.py`) with default agents + workflow templates
3. Run all migration scripts in `backend/migrations/`
4. Build the frontend (`npm ci && vite build`)
5. Write `/etc/systemd/system/agent-platform-backend.service` and enable it
6. Configure Nginx + obtain an SSL cert via certbot
7. Start the backend service

After it finishes, browse to `https://${DOMAIN}` — the PM Co-pilot should be live.

---

## Updating After `git pull`

```bash
cd /opt/agent-platform
git pull
sudo bash deploy/install.sh --update
```

This skips DNS/SSL/systemd registration (they are already set up) and:
- Reinstalls backend deps
- Runs any new migration scripts
- Rebuilds the frontend
- Restarts the backend service

---

## Environment Variables

See `backend/.env.example` for the full list. Minimum required for first boot:

| Var | Required | Notes |
|-----|----------|-------|
| `LLM_API_KEY` | ✅ | OpenRouter / OpenAI / Anthropic key |
| `LLM_MODEL` | Optional | Defaults to `openrouter/google/gemini-2.0-flash-001` |
| `OPENROUTER_BASE_URL` | Optional | Override for custom proxy/gateway |
| `SECRET_KEY` | Recommended | Randomise in production |

---

## Ports

- **Backend:** binds to `127.0.0.1:8080` only. Not reachable directly — all external traffic goes through Nginx (80 → 301 → 443).
- **Frontend:** served statically by Nginx from `${APP_DIR}/frontend/dist`. No node process running in production.

To change the backend port: set `BACKEND_PORT=9090` (or whatever) when running `install.sh`. It will re-render both the systemd unit and the Nginx config.

---

## Operations Cheatsheet

```bash
# Live logs
sudo journalctl -u agent-platform-backend -f

# Restart after editing .env
sudo systemctl restart agent-platform-backend

# Check status
sudo systemctl status agent-platform-backend

# Check nginx is valid before reloading
sudo nginx -t && sudo systemctl reload nginx

# Cert renewal (certbot auto-installs a timer, but force a renew:)
sudo certbot renew --dry-run

# Switch model without redeploy
sudo sed -i 's|^LLM_MODEL=.*|LLM_MODEL=openrouter/openai/gpt-oss-120b|' \
    /opt/agent-platform/backend/.env
sudo systemctl restart agent-platform-backend
```

---

## Files Written by `install.sh`

| File | Owner | Purpose |
|------|-------|---------|
| `/etc/systemd/system/agent-platform-backend.service` | root | systemd unit (rendered from template) |
| `/etc/nginx/sites-available/agent-platform` | root | Nginx vhost (rendered from template) |
| `/etc/nginx/sites-enabled/agent-platform` | root | symlink to above |
| `/etc/letsencrypt/live/${DOMAIN}/` | root | Let's Encrypt certs |
| `${APP_DIR}/backend/.venv/` | `${RUN_USER}` | Python virtualenv |
| `${APP_DIR}/backend/data/app.db` | `${RUN_USER}` | SQLite database |
| `${APP_DIR}/frontend/dist/` | `${RUN_USER}` | Built frontend assets |

---

## Architecture Notes

### User isolation via anonymous ID
Each browser generates a UUID on first visit, stored in `localStorage['agent_platform_client_id']`, and sent as `X-Client-ID` on every API call. The backend auto-creates a user record bound to that ID. Clearing browser storage creates a fresh user (old data becomes orphaned but is not deleted).

For stronger auth (email login, OAuth), replace `app/api/auth.py::get_current_user`.

### SQLite vs PostgreSQL
SQLite is the default — fine for single-server deployments with moderate concurrency. To switch:
1. Set `DATABASE_URL=postgresql+asyncpg://...` in `.env`
2. The migration scripts handle both engines.
3. Run `init_db.py` against the new DB to seed agents + templates.

### Background LLM tasks
Workflow execution uses `asyncio.create_task()` with strong references (see `workflow_engine.py` — `_background_tasks` set). If you see workflows stuck at "running" with no LLM call, check the backend journal: failures are written to `step_executions._log` and the run status flips to `failed`.
