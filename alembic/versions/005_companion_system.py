"""005_companion_system - persistent trainable companion (UNIFY-12).

Postgres DDL mirror of core/companion_models.py:
  profiles / memories / feedback / directives / training_log

House conventions preserved:
  - FORCE ROW LEVEL SECURITY on every table (owner bypass closed)
  - country isolation policy scoped TO luqi_app_user
  - NULLIF(current_setting('app.current_user_country', true), '') GUC guard
  - user_id is a plain UUID (NO FK to students): the v1 auth registry is
    in-memory, so authenticated user_ids are not student rows - a hard FK
    would 500 every real user until the accounts unification lands.
"""
from alembic import op

revision = "005_companion_system"
down_revision = "004_dead_man_switch_registry"
branch_labels = None
depends_on = None

_TABLES = (
    "companion_profiles",
    "companion_memories",
    "companion_feedback",
    "companion_directives",
    "companion_training_log",
)


def upgrade() -> None:
    for stmt in (
        """CREATE TABLE IF NOT EXISTS companion_profiles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL UNIQUE,
            country_code VARCHAR(3) NOT NULL,
            companion_name VARCHAR(60) NOT NULL DEFAULT 'Luqi',
            personality JSONB NOT NULL DEFAULT '{}'::jsonb,
            level VARCHAR(20) NOT NULL DEFAULT 'beginner',
            trust_score NUMERIC(4,3) NOT NULL DEFAULT 0.100,
            interaction_count INT NOT NULL DEFAULT 0,
            streak_days INT NOT NULL DEFAULT 0,
            last_interaction_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )""",
        "CREATE INDEX IF NOT EXISTS ix_companion_profiles_user_id ON companion_profiles (user_id)",
        """CREATE TABLE IF NOT EXISTS companion_memories (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL,
            country_code VARCHAR(3) NOT NULL,
            topic VARCHAR(100) NOT NULL,
            fact TEXT NOT NULL,
            importance INT NOT NULL DEFAULT 3,
            recall_count INT NOT NULL DEFAULT 0,
            last_recalled_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )""",
        "CREATE INDEX IF NOT EXISTS idx_companion_mem_user_topic ON companion_memories (user_id, topic)",
        """CREATE TABLE IF NOT EXISTS companion_feedback (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL,
            country_code VARCHAR(3) NOT NULL,
            mode VARCHAR(20) NOT NULL DEFAULT 'chat',
            rating INT NOT NULL,
            comment TEXT NOT NULL DEFAULT '',
            consumed BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )""",
        "CREATE INDEX IF NOT EXISTS idx_companion_fb_user_consumed ON companion_feedback (user_id, consumed)",
        """CREATE TABLE IF NOT EXISTS companion_directives (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL,
            country_code VARCHAR(3) NOT NULL,
            knob VARCHAR(40) NOT NULL,
            value VARCHAR(60) NOT NULL,
            source VARCHAR(20) NOT NULL DEFAULT 'feedback',
            evidence_count INT NOT NULL DEFAULT 1,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            CONSTRAINT uq_companion_directive_user_knob UNIQUE (user_id, knob)
        )""",
        "CREATE INDEX IF NOT EXISTS ix_companion_directives_user_id ON companion_directives (user_id)",
        """CREATE TABLE IF NOT EXISTS companion_training_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL,
            country_code VARCHAR(3) NOT NULL,
            knob VARCHAR(40) NOT NULL,
            old_value VARCHAR(60),
            new_value VARCHAR(60) NOT NULL,
            feedback_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )""",
        "CREATE INDEX IF NOT EXISTS idx_companion_trainlog_user ON companion_training_log (user_id, created_at)",
    ):
        op.execute(stmt)

    for table in _TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""CREATE POLICY country_tenant_isolation_{table} ON {table}
                FOR ALL TO luqi_app_user
                USING (country_code = NULLIF(current_setting('app.current_user_country', true), ''))"""
        )


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.execute(f"DROP POLICY IF EXISTS country_tenant_isolation_{table} ON {table}")
        op.execute(f"DROP TABLE IF EXISTS {table}")
