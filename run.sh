#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "Starting Atlas backend on http://localhost:8000 ..."
uvicorn api:app --port 8000 --workers 1 &
BACKEND_PID=$!

echo "Starting Atlas frontend on http://localhost:3000 ..."
python -m http.server 3000 &
FRONTEND_PID=$!

echo ""
echo "  Atlas frontend → http://localhost:3000"
echo "  Atlas backend  → http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" EXIT INT TERM
wait
