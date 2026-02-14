#!/bin/bash
set -e

# Replivo dev runner — starts backend + frontend concurrently

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Load .env
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
fi

export FLASK_ENV=development
export PATH="/opt/homebrew/opt/node@22/bin:$PATH"

# Activate venv
source "$SCRIPT_DIR/.venv/bin/activate"

cleanup() {
    echo "Shutting down..."
    kill 0 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

# Backend
echo "Starting Flask backend..."
cd "$SCRIPT_DIR/backend"
python wsgi.py &

# Frontend
echo "Starting Vite frontend..."
cd "$SCRIPT_DIR/frontend"
npm run dev &

echo ""
echo "Backend:  http://localhost:5000"
echo "Frontend: http://localhost:5173"
echo ""

wait
