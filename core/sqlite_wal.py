"""
OMEGA-LUQI SQLite WAL Setup - pilot-cost database mode.

Per the v5.20 review: for the 30-student pilot, SQLite in WAL mode on the
encrypted EBS volume costs $0 vs RDS hourly. When DATABASE_URL starts with
sqlite, init_db applies WAL pragmas (concurrent readers, safe crashes).
Postgres deployments are unaffected. Migration path: tools/migrate_sqlite_to_pg.py.
"""
import os


def configure_sqlite_engine(engine) -> None:
    """Apply WAL pragmas to a SQLite engine. No-op for other dialects."""
    if not engine.url.get_backend_name().startswith("sqlite"):
        return
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
