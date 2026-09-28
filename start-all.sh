#!/usr/bin/env bash
# Luqi AI v24 — Unified Asynchronous Service Controller
set -euo pipefail

# ── Environment & Directory Setup ─────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

mkdir -p data uploads logs

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
COLLAB_PORT="${COLLAB_PORT:-3000}"
NODE_ENV="${NODE_ENV:-development}"

# Colors
BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

PIDS=()

# ── Signal Handling & Cleanup ──────────────────────────────────────────────────
cleanup() {
  echo -e "\n${YELLOW}───── Shutting down Luqi AI services... ─────${NC}"
  for pid in "${PIDS[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      echo -e "Stopping process PID $pid..."
      kill -TERM "$pid" 2>/dev/null || true
    fi
  done

  # Wait briefly for graceful shutdown, then enforce termination if needed
  sleep 2
  for pid in "${PIDS[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      echo -e "${RED}Force killing unresponsive process PID $pid...${NC}"
      kill -9 "$pid" 2>/dev/null || true
    fi
  done
  echo -e "${GREEN}✓ All services stopped gracefully.${NC}"
  exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# ── Port Availability Check ───────────────────────────────────────────────────
check_port() {
  local port=$1
  if command -v lsof >/dev/null 2>&1; then
    if lsof -i:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
      echo -e "${RED}Error: Port $port is already in use.${NC}"
      exit 1
    fi
  elif command -v nc >/dev/null 2>&1; then
    if nc -z localhost "$port" 2>/dev/null; then
      echo -e "${RED}Error: Port $port is already in use.${NC}"
      exit 1
    fi
  fi
}

# ── Startup Execution ────────────────────────────────────────────────────────
echo -e "${BOLD}==================================================${NC}"
echo -e "${BOLD}   🚀 LUQI AI v24 — Unified Service Controller    ${NC}"
echo -e "${BOLD}==================================================${NC}"

check_port "$PORT"

# 1. Start Python FastAPI Backend
echo -e "\n📦 ${BOLD}Starting Python Backend (Uvicorn)...${NC}"
python3 -m uvicorn backend.router:app \
  --host "$HOST" \
  --port "$PORT" \
  --reload \
  --log-level info &
PIDS+=($!)

# 2. Start Collab Node.js Service (if compiled)
COLLAB_DIST="collab-service/dist/index.js"
if [ -f "$COLLAB_DIST" ]; then
  check_port "$COLLAB_PORT"
  echo -e "📡 ${BOLD}Starting Collaboration Service...${NC}"
  (
    cd collab-service
    NODE_ENV="$NODE_ENV" node dist/index.js
  ) &
  PIDS+=($!)
else
  echo -e "${YELLOW}⚠️  Collab Service build not found at $COLLAB_DIST (Skipping)${NC}"
fi

# ── Health Output & Process Monitoring ───────────────────────────────────────
echo -e "\n${GREEN}==================================================${NC}"
echo -e "${GREEN}  ✅ All requested services are running!          ${NC}"
echo -e "${GREEN}==================================================${NC}"
echo -e " 🌐 ${BOLD}Web UI / Router:${NC} http://localhost:${PORT}"
echo -e " 📚 ${BOLD}API Docs:${NC}       http://localhost:${PORT}/docs"
echo -e " 🪵 ${BOLD}Logs Location:${NC}  ${SCRIPT_DIR}/logs/"
echo -e " Press ${BOLD}Ctrl+C${NC} to stop all services cleanly.\n"

# Block and wait for all background background processes
wait
