"""0001_initial_schema - OMEGA-LUQI baseline.

Creates every table in the shared Base metadata (students, lab_progress,
payment_transactions, sovereign_enterprises, tender_tracking, system_audit_logs,
wallet_ledgers, wallet_transactions), then applies the FORCE RLS policies
(security_rls.sql) and the wallet ledger DDL (wallet_ledger.sql).

Baseline approach: metadata.create_all on the migration bind - exact and
idempotent for a fresh cluster. All FUTURE schema changes go through
`alembic revision --autogenerate` with hand-reviewed op operations.

Downgrade drops policies then all tables (reverse dependency order).
"""
from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

from core.models import Base          # noqa: E402
from core import enterprise_models    # noqa: E402,F401


def _read_ddl(rel: str) -> str:
    import os
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        "core", rel)
    with open(path) as f:
        return f.read()


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind)
    # Ensure the app role exists before RLS policies bind to it (CI/fresh-cluster
    # bootstrap; production creates it with a vault password first - DO-block skips if present).
    op.execute("DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'luqi_app_user') THEN CREATE ROLE luqi_app_user NOLOGIN; END IF; END $$")
    # Security + wallet DDL: FORCE RLS policies, unique reference index
    for rel in ("security_rls.sql", "wallet_ledger.sql"):
        for raw in _read_ddl(rel).split(";"):
            stmt = raw.strip()
            if not stmt:
                continue
            # skip comment-only fragments (SQL headers): psycopg2 refuses empty queries
            if all(not ln.strip() or ln.strip().startswith("--") for ln in stmt.splitlines()):
                continue
            op.execute(stmt)


def downgrade() -> None:
    for stmt in (
        "DROP POLICY IF EXISTS tx_geo_isolation_policy ON wallet_transactions",
        "DROP POLICY IF EXISTS ledger_geo_isolation_policy ON wallet_ledgers",
        "DROP POLICY IF EXISTS enterprise_geo_isolation_policy ON sovereign_enterprises",
        "DROP POLICY IF EXISTS payment_geo_isolation_policy ON payment_transactions",
        "DROP POLICY IF EXISTS progress_geo_isolation_policy ON lab_progress",
        "DROP POLICY IF EXISTS student_geo_isolation_policy ON students",
    ):
        op.execute(stmt)
    bind = op.get_bind()
    Base.metadata.drop_all(bind)
