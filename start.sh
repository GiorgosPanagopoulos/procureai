#!/usr/bin/env bash
set -e

ROOT_DIR=$(cd "$(dirname "$0")" && pwd)

# Start backend first
echo "Starting backend..."
cd "$ROOT_DIR/backend"
PYTHONPATH=. uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
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
