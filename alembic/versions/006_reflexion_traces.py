"""006_reflexion_traces - Reflexion critique stage observability (UNIFY-16).

Postgres DDL mirror of core/reflexion_models.py:
  reflexion_traces - one row per pipeline run (draft/critique/verdict/final,
  per-stage latency, A/B arm).

House conventions preserved:
  - FORCE ROW LEVEL SECURITY (owner bypass closed)
  - country isolation policy scoped TO luqi_app_user
  - NULLIF(current_setting('app.current_user_country', true), '') GUC guard
  - user_id plain UUID, nullable (anonymous requests allowed), NO FK to
    students - the v1 auth registry is in-memory (see 005 note).
"""
from alembic import op

revision = "006_reflexion_traces"
down_revision = "005_companion_system"
branch_labels = None
depends_on = None

_TABLE = "reflexion_traces"


def upgrade() -> None:
    for stmt in (
        """CREATE TABLE IF NOT EXISTS reflexion_traces (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            user_id UUID,
            country_code VARCHAR(3) NOT NULL DEFAULT '',
            ab_group VARCHAR(36),
            ab_arm VARCHAR(10),
            question TEXT NOT NULL,
            routed BOOLEAN NOT NULL,
            route_reason VARCHAR(200) NOT NULL,
            draft TEXT NOT NULL,
            critique JSONB,
            verdict VARCHAR(10) NOT NULL,
            final_answer TEXT NOT NULL,
            draft_ms INT NOT NULL DEFAULT 0,
            critique_ms INT NOT NULL DEFAULT 0,
            revise_ms INT NOT NULL DEFAULT 0,
            total_ms INT NOT NULL DEFAULT 0
        )""",
        "CREATE INDEX IF NOT EXISTS idx_reflexion_traces_user ON reflexion_traces (user_id, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_reflexion_traces_ab ON reflexion_traces (ab_group)",
    ):
        op.execute(stmt)

    op.execute(f"ALTER TABLE {_TABLE} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {_TABLE} FORCE ROW LEVEL SECURITY")
    op.execute(f"DROP POLICY IF EXISTS country_tenant_isolation ON {_TABLE}")
    op.execute(
        f"""CREATE POLICY country_tenant_isolation ON {_TABLE}
            TO luqi_app_user
            USING (country_code = NULLIF(current_setting('app.current_user_country', true), ''))"""
    )


def downgrade() -> None:
    op.execute(f"DROP POLICY IF EXISTS country_tenant_isolation ON {_TABLE}")
    op.execute(f"DROP TABLE IF EXISTS {_TABLE}")
