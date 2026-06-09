#!/bin/bash
set -e

echo "==> Installing Python deps..."
pip install -r requirements.txt

echo "==> Installing Playwright Chromium..."
playwright install chromium --with-deps

echo "==> Installing Node deps..."
npm install
cd frontend && npm install && cd ..

echo "==> Setting up .env..."
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

echo ""
echo "✓ Job Agent dev environment ready."
echo "  Run: npm run dev"
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8000/docs"
