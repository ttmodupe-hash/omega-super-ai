"""Scaffold: migrate a pilot SQLite database to PostgreSQL.

Steps (run on the server with both URLs set):
  1. SQLite side: dump schema + data (this tool prints pgloader commands -
     install pgloader, or use sqlalchemy-serializer for custom tables).
  2. Flip create_rds = true in deploy/terraform, apply, then point
     DATABASE_URL at RDS and re-run alembic upgrade head (idempotent).
Honest scope: pgloader does the heavy lifting; this tool generates the exact
command with your env vars so nothing is hand-copied.
"""
import os
import sys

SQLITE_URL = os.getenv("SQLITE_SOURCE_URL", "sqlite:////var/backups/luqi-ai/pilot.db")
PG_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://user:pass@host:5432/luqi_ai")

# pgloader wants plain postgres:// not the +driver form
pg_plain = PG_URL.replace("postgresql+psycopg2://", "postgresql://").replace("postgresql+asyncpg://", "postgresql://")

if __name__ == "__main__":
    print("1) Dry-run migration:")
    print(f"   pgloader --dry-run '{SQLITE_URL}' '{pg_plain}'")
    print("2) If dry-run is clean, run for real (drops target data):")
    print(f"   pgloader '{SQLITE_URL}' '{pg_plain}'")
    print("3) Verify row counts, then: alembic upgrade head")
    print("4) Update .env DATABASE_URL and restart the service.")
    if "--check" in sys.argv:
        for var in ("SQLITE_SOURCE_URL", "DATABASE_URL"):
            print(f"{var}: {'set' if os.getenv(var) else 'MISSING (default used)'}")
