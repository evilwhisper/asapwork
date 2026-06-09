#!/bin/bash
set -e

echo "==> Job Agent — Local Native Setup"

echo "==> Installing Python deps..."
pip install -r requirements.txt

echo "==> Installing Playwright Chromium..."
playwright install chromium

echo "==> Installing Node deps..."
npm install
cd frontend && npm install && cd ..

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env — ENCRYPTION_KEY will be auto-generated on first run."
fi

echo ""
echo "✓ Setup complete. Start the app with:"
echo "  npm run dev"
