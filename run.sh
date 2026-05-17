#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "Starting Atlas API on http://localhost:8000 ..."
uvicorn api:app --port 8000 --workers 1 &
BACKEND_PID=$!

echo "Serving frontend on http://localhost:3000 ..."
python -m http.server 3000 &
FRONTEND_PID=$!

sleep 1
open "http://localhost:3000/Atlas.html" 2>/dev/null || xdg-open "http://localhost:3000/Atlas.html" 2>/dev/null || true

echo ""
echo "  Atlas UI   → http://localhost:3000/Atlas.html"
echo "  Atlas API  → http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" EXIT INT TERM
wait
