#!/usr/bin/env bash
# OMEGA-LUQI start wrapper (Railway + any container host).
# Runs the Alembic chain before serving - idempotent, so every deploy keeps
# the schema at head. Without DATABASE_URL the engine boots DB-less by design.
#
# RESILIENCE LAW (v5.35.10): a migration problem must NEVER wall the entire
# engine behind a proxy 404 while the dashboard shows "Online". Migrations
# only run against PostgreSQL URLs (the schema is Postgres-specific: RLS,
# wallet ledger). Non-Postgres URLs or failed migrations -> warn LOUDLY and
# boot DEGRADED: the engine's init_db catches DB errors itself and keeps API
# routes active; wallet settlement stays fail-closed (503 at the gate), so
# degraded mode risks availability of writes, never money.
set -u
if [ -n "${DATABASE_URL:-}" ]; then
  case "${DATABASE_URL}" in
    postgres*|postgresql*)
      echo "[start] DATABASE_URL present - applying migrations (alembic upgrade head)"
      if alembic upgrade head; then
        echo "[start] schema at head"
      else
        echo "[start] WARNING: migrations FAILED - booting DEGRADED (DB-less). Read the alembic output above; /v1/health still answers so monitoring shows the truth."
      fi
      ;;
    *)
      echo "[start] WARNING: DATABASE_URL is not PostgreSQL (scheme: ${DATABASE_URL%%://*}) - skipping migrations, booting DB-less. The engine requires PostgreSQL: attach a PostgreSQL service, not MySQL."
      ;;
  esac
else
  echo "[start] no DATABASE_URL - skipping migrations (engine boots DB-less)"
fi
exec uvicorn core.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers
