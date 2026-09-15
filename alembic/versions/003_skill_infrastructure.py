"""003_skill_infrastructure - persistent skill profiles + certificate ledger.

Corrects the pasted blueprint's four defects:
  - GUC name aligned to the engine's RLS layer: app.current_user_country
    (the pasted blueprint used a different GUC - the guard bans the wrong string)
  - FORCE ROW LEVEL SECURITY (owner bypass closed, same as every other table)
  - country_code VARCHAR(3) matching students.country_code (ZAF/KEN)
  - user_id references students(id) (JWT user_id IS students.id for students;
    enterprise accounts join here once the accounts unification lands)
"""
from alembic import op

revision = "003_skill_infrastructure"
down_revision = "002_seed_sovereign_curriculum"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for stmt in (
        """CREATE TABLE IF NOT EXISTS user_skill_profiles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
            country_code VARCHAR(3) NOT NULL,
            target_trade VARCHAR(100) NOT NULL,
            market_readiness_numeric NUMERIC(3,2) DEFAULT 0.00,
            total_experience_hours INT DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )""",
        """CREATE TABLE IF NOT EXISTS cert_ledger (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
            country_code VARCHAR(3) NOT NULL,
            certificate_serial_id VARCHAR(50) UNIQUE NOT NULL,
            certified_trade VARCHAR(100) NOT NULL,
            cryptographic_signature_hash VARCHAR(64) NOT NULL,
            issued_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )""",
        "ALTER TABLE user_skill_profiles ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE user_skill_profiles FORCE ROW LEVEL SECURITY",
        "ALTER TABLE cert_ledger ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE cert_ledger FORCE ROW LEVEL SECURITY",
        """CREATE POLICY country_tenant_isolation_profile ON user_skill_profiles
           FOR ALL TO luqi_app_user
           USING (country_code = NULLIF(current_setting('app.current_user_country', true), ''))""",
        """CREATE POLICY country_tenant_isolation_ledger ON cert_ledger
           FOR ALL TO luqi_app_user
           USING (country_code = NULLIF(current_setting('app.current_user_country', true), ''))""",
    ):
        op.execute(stmt)


def downgrade() -> None:
    for stmt in (
        "DROP POLICY IF EXISTS country_tenant_isolation_ledger ON cert_ledger",
        "DROP POLICY IF EXISTS country_tenant_isolation_profile ON user_skill_profiles",
        "DROP TABLE cert_ledger",
        "DROP TABLE user_skill_profiles",
    ):
        op.execute(stmt)
