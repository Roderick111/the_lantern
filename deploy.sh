#!/bin/bash
# =============================================================================
# Deploy Script - The Lantern
# =============================================================================
# Usage: ./deploy.sh [server-ip]
# 
# This script:
# 1. Syncs project files to the server
# 2. Copies local .env to server
# 3. SSHs and runs docker compose

set -e

# Configuration
SERVER_IP="${1:-188.34.196.228}"
SERVER_USER="root"
DEPLOY_DIR="/opt/the-lantern"

echo "🚀 Deploying The Lantern to $SERVER_USER@$SERVER_IP"
echo "   Target directory: $DEPLOY_DIR"
echo ""

# Files to deploy
FILES=(
    "Dockerfile.backend"
    "Dockerfile.frontend"
    "docker-compose.yml"
    "Caddyfile"
    "nginx.conf"
    "nginx-site.conf"
    ".env.production.example"
    "backend"
    "frontend"
)

# Create deployment directory on server
echo "📁 Creating deployment directory..."
ssh "$SERVER_USER@$SERVER_IP" "mkdir -p $DEPLOY_DIR"

# Sync files
echo "📦 Syncing files to server..."
for file in "${FILES[@]}"; do
    echo "   → $file"
    rsync -avz --delete \
        --exclude 'node_modules' \
        --exclude '.venv' \
        --exclude '__pycache__' \
        --exclude '.git' \
        --exclude 'dist' \
        --exclude '*.pyc' \
        --exclude '.DS_Store' \
        "$file" "$SERVER_USER@$SERVER_IP:$DEPLOY_DIR/"
done

# Copy backend/.env to server as .env.production
echo ""
echo "🔐 Copying environment configuration..."
if [ -f "backend/.env" ]; then
    echo "   → Found backend/.env, copying to server as .env.production"
    scp "backend/.env" "$SERVER_USER@$SERVER_IP:$DEPLOY_DIR/.env.production"
else
    echo "   ⚠️  backend/.env not found! Please ensure .env.production exists on server."
fi

# Build and deploy (--no-cache ensures all file changes are picked up)
echo ""
echo "🐳 Building and starting containers..."
ssh "$SERVER_USER@$SERVER_IP" "cd $DEPLOY_DIR && docker compose build --no-cache && docker compose up -d"

# Show status
echo ""
echo "📊 Container status:"
ssh "$SERVER_USER@$SERVER_IP" "cd $DEPLOY_DIR && docker compose ps"

echo ""
echo "✅ Deployment complete!"
echo "   🌐 https://the-lantern.beautiful-apps.com"
echo ""
echo "   View logs: ssh $SERVER_USER@$SERVER_IP 'cd $DEPLOY_DIR && docker compose logs -f'"
