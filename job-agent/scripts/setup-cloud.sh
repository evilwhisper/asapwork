#!/bin/bash
# One-command Ubuntu VPS setup
# Usage: curl -fsSL https://raw.githubusercontent.com/YOU/job-agent/main/scripts/setup-cloud.sh | bash
set -e

echo "==> Job Agent — Cloud VPS Setup"

# Install Docker
if ! command -v docker &>/dev/null; then
  echo "==> Installing Docker..."
  curl -fsSL https://get.docker.com | sh
  usermod -aG docker "$USER"
fi

# Install Docker Compose plugin
if ! docker compose version &>/dev/null; then
  echo "==> Installing Docker Compose..."
  apt-get install -y docker-compose-plugin
fi

# Clone repo if not already present
if [ ! -d "job-agent" ]; then
  echo "==> Cloning repository..."
  git clone https://github.com/YOUR_USERNAME/job-agent.git
fi

cd job-agent

# Generate .env.cloud
if [ ! -f ".env" ]; then
  cp .env.example .env

  ADMIN_PASS=$(openssl rand -base64 16)
  ADMIN_HASH=$(python3 -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('$ADMIN_PASS'))" 2>/dev/null || echo "")

  {
    echo "DEPLOY_MODE=cloud"
    echo "AUTH_ENABLED=true"
    echo "ADMIN_USER=admin"
    echo "ADMIN_PASS_HASH=$ADMIN_HASH"
  } >> .env

  echo ""
  echo "========================================="
  echo " SAVE THESE CREDENTIALS — shown once only"
  echo "  Username: admin"
  echo "  Password: $ADMIN_PASS"
  echo "========================================="
fi

echo "==> Starting containers..."
docker compose -f docker-compose.yml -f docker-compose.cloud.yml up -d --build

echo ""
echo "✓ Job Agent is running."
echo "  Edit Caddyfile to set your domain, then: docker compose restart caddy"
echo "  Or access via server IP on port 80 (HTTP, no HTTPS until domain is set)"
