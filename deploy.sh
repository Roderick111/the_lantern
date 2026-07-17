#!/bin/bash
# =============================================================================
# Deploy Script - The Lantern (web + Telegram gateway)
# =============================================================================
# Usage: ./deploy.sh [server-ip]
#
# 1. Sync project files to the server
# 2. Copy env (never logs secrets)
# 3. docker compose build + up
# 4. Print health + owner webhook steps (does NOT set Telegram webhook)
#
# Kill switches (set in .env.production on server, then recreate telegram):
#   FEATURE_NEW_SESSIONS=false
#   FEATURE_LLM_TURNS=false
#   FEATURE_MINIAPP_MUTATIONS=false

set -e

SERVER_IP="${1:-188.34.196.228}"
SERVER_USER="root"
DEPLOY_DIR="/opt/the-lantern"

echo "Deploying The Lantern to $SERVER_USER@$SERVER_IP"
echo "   Target: $DEPLOY_DIR"
echo ""

FILES=(
    "Dockerfile.backend"
    "Dockerfile.frontend"
    "Dockerfile.telegram"
    "docker-compose.yml"
    "Caddyfile"
    "nginx.conf"
    "nginx-site.conf"
    "nginx-proxy"
    "docs"
    "backend"
    "frontend"
    "telegram"
)

echo "Creating deployment directory..."
ssh "$SERVER_USER@$SERVER_IP" "mkdir -p $DEPLOY_DIR"

echo "Syncing files to server..."
for file in "${FILES[@]}"; do
    if [ ! -e "$file" ]; then
        echo "   skip missing: $file"
        continue
    fi
    echo "   → $file"
    rsync -avz --delete \
        --exclude 'node_modules' \
        --exclude '.venv' \
        --exclude 'venv_linux' \
        --exclude '__pycache__' \
        --exclude '.git' \
        --exclude 'dist' \
        --exclude '*.pyc' \
        --exclude '.DS_Store' \
        --exclude 'saves' \
        --exclude 'telemetry' \
        --exclude 'coverage' \
        --exclude '*.db' \
        --exclude '*.db-*' \
        "$file" "$SERVER_USER@$SERVER_IP:$DEPLOY_DIR/"
done

echo ""
echo "Copying environment configuration..."
if [ -f "backend/.env" ]; then
    echo "   → backend/.env → server .env.production"
    scp "backend/.env" "$SERVER_USER@$SERVER_IP:$DEPLOY_DIR/.env.production"
else
    echo "   WARN: backend/.env not found. Ensure .env.production exists on server."
fi

echo ""
echo "Building and starting containers..."
ssh "$SERVER_USER@$SERVER_IP" "cd $DEPLOY_DIR && docker compose build --no-cache && docker compose up -d"

echo ""
echo "Installing nginx-proxy SSE config (web only)..."
ssh "$SERVER_USER@$SERVER_IP" "cp $DEPLOY_DIR/nginx-proxy/thelantern.institute_location /var/lib/docker/volumes/crowd_due_dill_nginx_vhost/_data/thelantern.institute_location 2>/dev/null && docker restart crowd-due-dill-proxy || true"

echo ""
echo "Container status:"
ssh "$SERVER_USER@$SERVER_IP" "cd $DEPLOY_DIR && docker compose ps"

echo ""
echo "Health checks:"
ssh "$SERVER_USER@$SERVER_IP" "curl -sf http://127.0.0.1:8000/health 2>/dev/null || docker compose -f $DEPLOY_DIR/docker-compose.yml exec -T backend python -c \"import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read().decode())\" 2>/dev/null || echo 'backend health: skip'"
ssh "$SERVER_USER@$SERVER_IP" "docker compose -f $DEPLOY_DIR/docker-compose.yml exec -T telegram bun -e \"fetch('http://127.0.0.1:8080/health').then(async r=>console.log(await r.text())).catch(e=>console.error(e))\" 2>/dev/null || echo 'telegram health: skip (container starting?)'"

echo ""
echo "Deploy complete."
echo "   Web:      https://thelantern.institute"
echo "   Telegram: https://bot.thelantern.institute/health"
echo ""
echo "   Logs: ssh $SERVER_USER@$SERVER_IP 'cd $DEPLOY_DIR && docker compose logs -f telegram'"
echo ""
echo "=== Owner: Telegram webhook (run once; do NOT put bot token in shell history) ==="
echo "See: docs/plans/2026-07-17-telegram-phase5-deploy.md"
echo "1) Put secrets in server .env.production (TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_SECRET, MINIAPP_SESSION_SECRET)"
echo "2) SQL: backend idempotency + telegram gateway (if not applied)"
echo "3) setWebhook via BotFather/API with secret_token (owner machine, not this script)"
echo "4) BotFather: commands, Menu Button → https://bot.thelantern.institute/app/"
echo ""
echo "Rollback telegram only:"
echo "  ssh $SERVER_USER@$SERVER_IP 'cd $DEPLOY_DIR && docker compose stop telegram && docker compose rm -f telegram'"
echo "  # previous image: docker compose up -d telegram  (after retag) or remove service from compose"
echo ""
