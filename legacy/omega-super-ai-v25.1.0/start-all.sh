#!/bin/bash
# Luqi AI v24 — Unified Startup Script
set -e
cd "$(dirname "$0")"
mkdir -p data uploads

echo "=================================="
echo "  🚀 LUQI AI v24 Startup"
echo "=================================="

# Python backend
echo "📦 Starting Python Backend..."
python3 -m uvicorn backend.router:app --host 0.0.0.0 --port 8000 --reload &

# Collab service (if built)
if [ -f collab-service/dist/index.js ]; then
    echo "📡 Starting Collab Service..."
    (cd collab-service && node dist/index.js) &
fi

echo ""
echo "✅ All services starting..."
echo "🌐 Web UI: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo "Press Ctrl+C to stop"
wait
