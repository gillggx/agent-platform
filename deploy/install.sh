#!/usr/bin/env bash
# agent-platform — idempotent install / update script
#
# Usage (first install):
#   sudo APP_DIR=/opt/agent-platform DOMAIN=agent-platform.example.com \
#        ADMIN_EMAIL=you@example.com bash deploy/install.sh
#
# Usage (update after git pull):
#   sudo bash deploy/install.sh --update
#
# Environment variables (first install):
#   APP_DIR        (default /opt/agent-platform)
#   DOMAIN         (required)
#   ADMIN_EMAIL    (required — used for certbot)
#   RUN_USER       (default ubuntu)
#   BACKEND_PORT   (default 8080)
#
# What it does:
#   1. Renders nginx config + systemd service from templates
#   2. Installs backend Python deps + runs migrations
#   3. Builds frontend
#   4. Obtains SSL cert via certbot (webroot)
#   5. Reloads nginx + restarts backend service

set -euo pipefail

UPDATE_ONLY=${1:-}

# Defaults
: "${APP_DIR:=/opt/agent-platform}"
: "${RUN_USER:=ubuntu}"
: "${BACKEND_PORT:=8080}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[install] APP_DIR=$APP_DIR  RUN_USER=$RUN_USER  BACKEND_PORT=$BACKEND_PORT"

# ---- 1. Backend: venv + deps + migrations ---------------------------------
echo "[install] Installing backend..."
cd "$APP_DIR/backend"
if [ ! -d .venv ]; then
    sudo -u "$RUN_USER" python3 -m venv .venv
fi
sudo -u "$RUN_USER" .venv/bin/pip install --upgrade pip --quiet
sudo -u "$RUN_USER" .venv/bin/pip install -r requirements.txt --quiet

if [ ! -f .env ]; then
    echo "[install] WARN: $APP_DIR/backend/.env does not exist."
    echo "           Copy .env.example and fill LLM_API_KEY before starting the service."
    cp .env.example .env
    chown "$RUN_USER:$RUN_USER" .env
    chmod 600 .env
fi

# First install: seed DB. Update: run migration.
if [ -z "$UPDATE_ONLY" ]; then
    echo "[install] Seeding database..."
    sudo -u "$RUN_USER" .venv/bin/python init_db.py
fi
echo "[install] Running migrations..."
for mig in migrations/*.py; do
    if [ -f "$mig" ]; then
        echo "  → $mig"
        sudo -u "$RUN_USER" .venv/bin/python "$mig"
    fi
done

# ---- 2. Frontend: build ---------------------------------------------------
echo "[install] Building frontend..."
cd "$APP_DIR/frontend"
sudo -u "$RUN_USER" npm ci --silent
sudo -u "$RUN_USER" npx vite build

# ---- 3. Systemd service ---------------------------------------------------
if [ -z "$UPDATE_ONLY" ]; then
    echo "[install] Installing systemd service..."
    export APP_DIR RUN_USER BACKEND_PORT
    envsubst '${APP_DIR} ${RUN_USER} ${BACKEND_PORT}' \
        < "$SCRIPT_DIR/systemd/agent-platform-backend.service.template" \
        > /etc/systemd/system/agent-platform-backend.service
    systemctl daemon-reload
    systemctl enable agent-platform-backend
fi

# ---- 4. Nginx + SSL -------------------------------------------------------
if [ -z "$UPDATE_ONLY" ]; then
    : "${DOMAIN:?DOMAIN env var is required for first install}"
    : "${ADMIN_EMAIL:?ADMIN_EMAIL env var is required for first install}"

    echo "[install] Configuring nginx for $DOMAIN..."
    mkdir -p /var/www/certbot

    # Temporary HTTP-only config so certbot can do the webroot challenge
    cat > /etc/nginx/sites-available/agent-platform <<EOF
server {
    listen 80;
    server_name $DOMAIN;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 200 'bootstrap'; }
}
EOF
    ln -sf /etc/nginx/sites-available/agent-platform /etc/nginx/sites-enabled/agent-platform
    nginx -t
    systemctl reload nginx

    echo "[install] Obtaining SSL cert via certbot..."
    certbot certonly --webroot -w /var/www/certbot -d "$DOMAIN" \
        --non-interactive --agree-tos -m "$ADMIN_EMAIL"

    echo "[install] Rendering final nginx config..."
    export DOMAIN APP_DIR BACKEND_PORT
    envsubst '${DOMAIN} ${APP_DIR} ${BACKEND_PORT}' \
        < "$SCRIPT_DIR/nginx/agent-platform.conf.template" \
        > /etc/nginx/sites-available/agent-platform
    nginx -t
    systemctl reload nginx
fi

# ---- 5. Start / restart backend ------------------------------------------
echo "[install] Restarting backend..."
systemctl restart agent-platform-backend
sleep 2
systemctl is-active agent-platform-backend

if [ -z "$UPDATE_ONLY" ]; then
    echo ""
    echo "✓ Installed. Visit https://$DOMAIN"
else
    echo ""
    echo "✓ Update complete."
fi
