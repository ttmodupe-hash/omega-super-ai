"""007_i18n - unified i18n engine layer: translation-memory store (UNIFY-14).

Postgres DDL mirror of core/i18n_models.py:
  i18n_strings - (key, locale) -> text + provenance. Shared reference data
  (UI catalogue seeds + machine-translation memory) for web/ and cli/.

House conventions adapted:
  - FORCE ROW LEVEL SECURITY (owner bypass closed)
  - SHARED data, not per-country user data: policy grants read/write to
    luqi_app_user across rows (USING true) — country isolation would break
    a shared dictionary. Documented exception, see core/i18n_models.py.
"""
from alembic import op

revision = "007_i18n"
down_revision = "006_reflexion_traces"
branch_labels = None
depends_on = None

_TABLE = "i18n_strings"


def upgrade() -> None:
    op.execute(
        """CREATE TABLE IF NOT EXISTS i18n_strings (
            key VARCHAR(200) NOT NULL,
            locale VARCHAR(10) NOT NULL,
            text TEXT NOT NULL,
            source VARCHAR(10) NOT NULL DEFAULT 'seed',
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            CONSTRAINT pk_i18n_strings PRIMARY KEY (key, locale)
        )"""
    )
    op.execute(f"ALTER TABLE {_TABLE} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {_TABLE} FORCE ROW LEVEL SECURITY")
    op.execute(f"DROP POLICY IF EXISTS shared_reference_read ON {_TABLE}")
    op.execute(
        f"""CREATE POLICY shared_reference_read ON {_TABLE}
            TO luqi_app_user
            USING (true)"""
    )


def downgrade() -> None:
    op.execute(f"DROP POLICY IF EXISTS shared_reference_read ON {_TABLE}")
    op.execute(f"DROP TABLE IF EXISTS {_TABLE}")
