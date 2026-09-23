"""008_site_stats - anonymous aggregate audience pulse (PRIDE-1).

Postgres DDL mirror of core/site_stats_models.py:
  site_heartbeats - one row per anonymous rotating session id:
    sid (PK), first_seen, last_seen, heartbeats.

House conventions applied:
  - FORCE ROW LEVEL SECURITY (owner bypass closed)
  - DOCUMENTED GLOBAL EXCEPTION (007_i18n precedent): this table holds
    ZERO PII - no IPs, no cookies, no user agents, only rotating anonymous
    ids + timestamps + counters - and exists to power ONE global audience
    pulse on the landing page. Country isolation would break that pulse,
    so the policy grants luqi_app_user full row access (USING/WITH CHECK
    true), exactly like the shared i18n reference table.
  - Rows older than 24h are pruned by the API on every heartbeat: a pulse,
    not a tracker (see core/site_stats.py).
"""
from alembic import op

revision = "008_site_stats"
down_revision = "007_i18n"
branch_labels = None
depends_on = None

_TABLE = "site_heartbeats"


def upgrade() -> None:
    op.execute(
        """CREATE TABLE IF NOT EXISTS site_heartbeats (
            sid VARCHAR(64) NOT NULL,
            first_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            heartbeats INTEGER NOT NULL DEFAULT 1,
            CONSTRAINT pk_site_heartbeats PRIMARY KEY (sid)
        )"""
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_site_heartbeats_last_seen ON site_heartbeats (last_seen)")
    op.execute(f"ALTER TABLE {_TABLE} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {_TABLE} FORCE ROW LEVEL SECURITY")
    op.execute(f"DROP POLICY IF EXISTS site_pulse_global ON {_TABLE}")
    op.execute(
        f"""CREATE POLICY site_pulse_global ON {_TABLE}
            TO luqi_app_user
            USING (true)
            WITH CHECK (true)"""
    )


def downgrade() -> None:
    op.execute(f"DROP POLICY IF EXISTS site_pulse_global ON {_TABLE}")
    op.execute(f"DROP TABLE IF EXISTS {_TABLE}")
