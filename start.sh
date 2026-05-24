#!/usr/bin/env bash
set -e

ROOT_DIR=$(cd "$(dirname "$0")" && pwd)

# Auto-restart loop for backend — max 5 consecutive crashes before giving up
_run_backend() {
    local retries=0
    local max_retries=5
    cd "$ROOT_DIR/backend"
    while [ $retries -lt $max_retries ]; do
        echo "Starting backend (attempt $((retries + 1))/$max_retries)..."
        PYTHONPATH=. uvicorn main:app --reload --reload-include "*.txt" --host 0.0.0.0 --port 8000
        retries=$((retries + 1))
        echo "Backend stopped. Restarting in 3s..."
        sleep 3
    done
    echo "Backend failed $max_retries times. Giving up."
    exit 1
}

_run_backend &
BACKEND_PID=$!

# wait for backend to warm up
sleep 3

# Start frontend
echo "Starting frontend..."
cd "$ROOT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"

echo "ProcureAI started. Backend at http://localhost:8000, frontend at http://localhost:3000"
echo "To stop: kill $BACKEND_PID $FRONTEND_PID"

wait $BACKEND_PID $FRONTEND_PID
