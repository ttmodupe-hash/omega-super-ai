#!/usr/bin/env bash
# ==============================================================================
# LUQI-AI STAGING ENVIRONMENT VERIFICATION (v5.3)
# Run on a clean Ubuntu node BEFORE exposing the service to users.
# Every step degrades gracefully and says what it verified - no silent passes.
# ==============================================================================
set -u

echo "[0/6] Python runtime"
python3 --version | grep -qE "3\.(11|12|13)" \
  && echo "  ok: supported Python" \
  || { echo "  FAIL: Python 3.11+ required"; exit 1; }

echo "[1/6] Environment vault"
if [ ! -f .env ]; then
  echo "  FAIL: .env missing - copy .env.production.example and fill real values"; exit 1
fi
PERMS=$(stat -c '%a' .env)
if [ "$PERMS" != "600" ]; then
  echo "  warn: .env perms are $PERMS - tightening to 600"
  chmod 600 .env
else
  echo "  ok: .env readable only by owner"
fi

echo "[2/6] Docker daemon socket"
if [ ! -S /var/run/docker.sock ]; then
  echo "  FAIL: /var/run/docker.sock missing - lab terminals and compiles will 503"
  exit 1
fi
[ -w /var/run/docker.sock ] \
  && echo "  ok: socket present and writable" \
  || echo "  warn: socket present but not writable by this user - check docker group membership"

echo "[3/6] Redis (optional - memory fallback active without it)"
if command -v redis-cli &> /dev/null; then
  redis-cli ping 2>/dev/null | grep -q PONG \
    && echo "  ok: Redis reachable (STATE_BACKEND=redis usable)" \
    || echo "  warn: redis-cli present but no PONG - revocation falls back to in-memory"
else
  echo "  warn: redis-cli not installed - revocation uses in-memory denylist"
fi

echo "[4/6] Database migrations"
if [ -n "${DATABASE_URL:-}" ]; then
  alembic upgrade head && echo "  ok: schema at head" \
    || { echo "  FAIL: migrations did not apply cleanly"; exit 1; }
else
  echo "  warn: DATABASE_URL unset - skipping migrations (dev mode)"
fi

echo "[5/6] Service health"
if curl -fsS http://localhost:8000/v1/health >/dev/null 2>&1; then
  echo "  ok: /v1/health operational"
else
  echo "  warn: health endpoint not responding (service not started yet?)"
fi

echo "[6/6] Full quality gate"
# test_wallet_integration skips itself without a database - expected locally.
pytest -v
echo "Staging verification complete."
