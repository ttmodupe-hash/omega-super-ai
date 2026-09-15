#!/usr/bin/env bash
# OMEGA-LUQI start wrapper (Railway + any container host).
# Runs the Alembic chain (0001-004) before serving - idempotent, so every
# deploy keeps the schema at head. Without DATABASE_URL the engine boots
# DB-less by design (SQLite default) and migrations are skipped - not failed.
set -e
if [ -n "${DATABASE_URL:-}" ]; then
  echo "[start] DATABASE_URL present - applying migrations (alembic upgrade head)"
  alembic upgrade head
  echo "[start] schema at head"
else
  echo "[start] no DATABASE_URL - skipping migrations (engine boots DB-less)"
fi
exec uvicorn core.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers
