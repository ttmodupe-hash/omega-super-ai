"""004_dead_man_switch_registry - persistent legacy guard + heartbeat trigger.

Persists the v5.30.0 in-memory dead man's switch into Postgres so directives
survive restarts, and adds a DB-level heartbeat: any UPDATE on
user_skill_profiles stamps last_heartbeat on the registry (application-level
login touch from v5.30.0 complements this).

FIXED from the pasted blueprint:
  - current_setting wrapped with NULLIF(..., '') + missing_ok, matching the
    engine's RLS layer (bare current_setting raises when the GUC is unset)
  - policy scoped TO luqi_app_user (house convention)
  - FORCE RLS kept; downgrade drops trigger -> function -> table in order
"""
from alembic import op

revision = "004_dead_man_switch_registry"
down_revision = "003_skill_infrastructure"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for stmt in (
        """CREATE TABLE dead_man_switch_registry (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
            country_code VARCHAR(3) NOT NULL,
            inactivity_threshold_days INT DEFAULT 90,
            trusted_contact VARCHAR(255) NOT NULL,
            execution_directive VARCHAR(100) DEFAULT 'NOTIFY_TRUSTED_CONTACT',
            last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            is_triggered BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )""",
        "ALTER TABLE dead_man_switch_registry ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE dead_man_switch_registry FORCE ROW LEVEL SECURITY",
        """CREATE POLICY country_tenant_isolation_dms ON dead_man_switch_registry
           FOR ALL TO luqi_app_user
           USING (country_code = NULLIF(current_setting('app.current_user_country', true), ''))""",
        """CREATE OR REPLACE FUNCTION update_user_heartbeat_on_activity()
           RETURNS TRIGGER AS $fn$
           BEGIN
               UPDATE dead_man_switch_registry
               SET last_heartbeat = NOW()
               WHERE user_id = NEW.user_id
                 AND country_code = NULLIF(current_setting('app.current_user_country', true), '');
               RETURN NEW;
           END;
           $fn$ LANGUAGE plpgsql""",
        """CREATE TRIGGER tr_user_activity_heartbeat
           AFTER UPDATE ON user_skill_profiles
           FOR EACH ROW
           EXECUTE FUNCTION update_user_heartbeat_on_activity()""",
    ):
        op.execute(stmt)


def downgrade() -> None:
    for stmt in (
        "DROP TRIGGER IF EXISTS tr_user_activity_heartbeat ON user_skill_profiles",
        "DROP FUNCTION IF EXISTS update_user_heartbeat_on_activity()",
        "DROP TABLE dead_man_switch_registry",
    ):
        op.execute(stmt)
