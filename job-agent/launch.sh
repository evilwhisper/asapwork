#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$DIR/.venv"
MARKER="$DIR/.setup_done"
PORT=8000

echo ""
echo " =========================================="
echo "   Job Agent"
echo " =========================================="
echo ""

# ── Check Python ──────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo " [!] Python 3 not found."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo " Install via: brew install python3"
    else
        echo " Install via: sudo apt install python3 python3-venv python3-pip"
    fi
    exit 1
fi

# ── Create virtualenv ─────────────────────────────────────────────────────────
if [ ! -f "$VENV/bin/activate" ]; then
    echo " [*] Creating virtual environment..."
    python3 -m venv "$VENV"
fi

source "$VENV/bin/activate"

# ── First-time setup ──────────────────────────────────────────────────────────
if [ ! -f "$MARKER" ]; then
    echo " [*] First run — installing dependencies (this takes ~2 min)..."
    pip install -r "$DIR/requirements.txt" -q

    echo " [*] Installing Chromium for scraping..."
    playwright install chromium

    if command -v npm &>/dev/null; then
        echo " [*] Building frontend UI..."
        cd "$DIR/frontend"
        npm install --silent
        npm run build
        cd "$DIR"
    else
        echo " [!] npm not found — UI will not be available."
        echo "     Install Node.js from https://nodejs.org/ then delete .setup_done and re-run."
    fi

    touch "$MARKER"
    echo ""
    echo " [OK] Setup complete!"
    echo ""
fi

# ── Kill anything on the port ─────────────────────────────────────────────────
lsof -ti :$PORT | xargs kill -9 2>/dev/null || true

# ── Start server ──────────────────────────────────────────────────────────────
echo " [*] Starting Job Agent on http://localhost:$PORT ..."
uvicorn backend.main:app --port $PORT --log-level warning &
SERVER_PID=$!

# ── Wait for ready ────────────────────────────────────────────────────────────
for i in $(seq 1 15); do
    sleep 1
    curl -s http://localhost:$PORT/api/health >/dev/null 2>&1 && break
done

# ── Open browser ──────────────────────────────────────────────────────────────
if [[ "$OSTYPE" == "darwin"* ]]; then
    open "http://localhost:$PORT"
else
    xdg-open "http://localhost:$PORT" 2>/dev/null || true
fi

echo " [OK] Job Agent running at http://localhost:$PORT"
echo "      Press Ctrl+C to stop."
echo ""

wait $SERVER_PID
