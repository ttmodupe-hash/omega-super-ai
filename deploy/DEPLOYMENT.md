"""
Dead Man's Switch Engine (core/dead_man_switch.py)
Monitors user vitality, manages trust contacts, and handles escalation state locks.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger("core.dead_man_switch")

class DeadManSwitchEngine:
    def __init__(self, db_session=None):
        self.db = db_session

    async def record_heartbeat(self, user_id: str, trigger_source: str = "login") -> Dict[str, Any]:
        """Record an explicit user activity signal."""
        now = datetime.now(timezone.utc)
        logger.info("Heartbeat recorded for user=%s source=%s at=%s", user_id, trigger_source, now.isoformat())
        return {
            "user_id": user_id,
            "status": "active",
            "last_heartbeat": now.isoformat(),
            "source": trigger_source
        }

    async def evaluate_user_status(
        self,
        user_id: str,
        last_seen: datetime,
        inactivity_limit_days: int = 30,
        grace_period_days: int = 7
    ) -> Dict[str, Any]:
        """
        Evaluates inactivity thresholds and triggers escalation tiers:
        - Active: within inactivity limit
        - Warning: exceeded limit, inside grace period (triggers SMS/Email)
        - Breached: exceeded grace period (engages 30% gate / state lock)
        """
        now = datetime.now(timezone.utc)
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)

        elapsed = now - last_seen
        warning_threshold = timedelta(days=inactivity_limit_days)
        breach_threshold = warning_threshold + timedelta(days=grace_period_days)

        if elapsed >= breach_threshold:
            return {
                "user_id": user_id,
                "state": "BREACHED",
                "gate_task_required": True,
                "action": "LOCK_ACCOUNT_AND_DISPATCH_LEGACY_AUDIT",
                "elapsed_days": elapsed.days
            }
        elif elapsed >= warning_threshold:
            return {
                "user_id": user_id,
                "state": "WARNING",
                "gate_task_required": False,
                "action": "DISPATCH_HEALTH_CHECK_NOTIFICATION",
                "days_remaining_in_grace": (breach_threshold - elapsed).days
            }

        return {
            "user_id": user_id,
            "state": "ACTIVE",
            "gate_task_required": False,
            "days_until_warning": (warning_threshold - elapsed).days
        }

    """
Data Portability Core (core/data_portability.py)
Pulls user data packages (POPIA/GDPR compliant) with automated PII redaction.
"""

import re
from typing import Dict, Any, List

class PIIScrubber:
    # Regex patterns for common sensitive indicators
    EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    PHONE_PATTERN = re.compile(r"(\+?27|0)\s?\d{2}\s?\d{3}\s?\d{4}")
    ID_PATTERN = re.compile(r"\b\d{13}\b")  # Standard 13-digit national ID

    @classmethod
    def scrub_text(cls, text: str) -> str:
        if not text:
            return text
        text = cls.EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)
        text = cls.PHONE_PATTERN.sub("[REDACTED_PHONE]", text)
        text = cls.ID_PATTERN.sub("[REDACTED_ID]", text)
        return text

    @classmethod
    def scrub_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        cleaned = {}
        for key, value in data.items():
            if isinstance(value, str):
                cleaned[key] = cls.scrub_text(value)
            elif isinstance(value, dict):
                cleaned[key] = cls.scrub_dict(value)
            elif isinstance(value, list):
                cleaned[key] = [
                    cls.scrub_dict(item) if isinstance(item, dict)
                    else (cls.scrub_text(item) if isinstance(item, str) else item)
                    for item in value
                ]
            else:
                cleaned[key] = value
        return cleaned


class DataPortabilityExporter:
    def __init__(self, user_id: str):
        self.user_id = user_id

    async def generate_export_package(self, raw_user_records: Dict[str, Any]) -> Dict[str, Any]:
        """Compiles user profile, telemetry, and activity logs into a scrubbed JSON payload."""
        scrubbed_records = PIIScrubber.scrub_dict(raw_user_records)
        return {
            "version": "1.0",
            "compliance_standard": "POPIA_SECTION_23_GDPR_ART20",
            "user_id": self.user_id,
            "export_data": scrubbed_records
        }
"""
Verification Battery (tests/verify_superai_upgrades.py)
Runs test assertions for v5.37.0 modules.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from core.dead_man_switch import DeadManSwitchEngine
from core.data_portability import PIIScrubber

async def run_tests():
    print("=== STARTING SUPERAI VERIFICATION BATTERY ===")
    
    # 1. Test PII Scrubber
    sample_text = "Contact user at test@example.com or phone 0821234567 with ID 8708195000088."
    scrubbed = PIIScrubber.scrub_text(sample_text)
    assert "[REDACTED_EMAIL]" in scrubbed
    assert "[REDACTED_PHONE]" in scrubbed
    assert "[REDACTED_ID]" in scrubbed
    print("✓ PII Scrubbing Tests Passed.")

    # 2. Test Dead Man's Switch Evaluation
    dms = DeadManSwitchEngine()
    now = datetime.now(timezone.utc)
    
    # Active case
    res_active = await dms.evaluate_user_status("usr_1", last_seen=now - timedelta(days=10))
    assert res_active["state"] == "ACTIVE"
    
    # Warning case
    res_warn = await dms.evaluate_user_status("usr_1", last_seen=now - timedelta(days=32))
    assert res_warn["state"] == "WARNING"
    
    # Breached case
    res_breach = await dms.evaluate_user_status("usr_1", last_seen=now - timedelta(days=40))
    assert res_breach["state"] == "BREACHED"
    assert res_breach["gate_task_required"] is True
    print("✓ Dead Man's Switch Logic Tests Passed.")

    print("\n=== ALL CHECKS PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    asyncio.run(run_tests())

"""dead_man_switch_registry and force RLS policies

Revision ID: 0004_dead_man_switch
Revises: 0003_skill_engine_tables
Create Date: 2026-09-15 11:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0004_dead_man_switch'
down_revision: Union[str, None] = '0003_skill_engine_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create dead_man_switch_registry table
    op.execute("""
    CREATE TABLE IF NOT EXISTS dead_man_switch_registry (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        inactivity_limit_days INT NOT NULL DEFAULT 30,
        grace_period_days INT NOT NULL DEFAULT 7,
        last_heartbeat TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, WARNING, BREACHED
        trusted_contacts JSONB DEFAULT '[]'::jsonb,
        gate_task_id VARCHAR(64) NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT uq_dms_user UNIQUE (user_id)
    );
    """)

    # 2. Enable and Force Row Level Security (RLS)
    op.execute("ALTER TABLE dead_man_switch_registry ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE dead_man_switch_registry FORCE ROW LEVEL SECURITY;")

    # 3. Apply Tenant Isolation RLS Policy
    # Utilizes app.current_user_id GUC set by the request context middleware
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_policies 
            WHERE tablename = 'dead_man_switch_registry' 
            AND policyname = 'dms_user_isolation_policy'
        ) THEN
            CREATE POLICY dms_user_isolation_policy ON dead_man_switch_registry
                FOR ALL
                TO luqi_app_user
                USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
                WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid);
        END IF;
    END
    $$;
    """)

    # 4. Create trigger function to auto-update last_heartbeat on profile activity
    op.execute("""
    CREATE OR REPLACE FUNCTION update_dms_heartbeat_on_activity()
    RETURNS TRIGGER AS $$
    BEGIN
        INSERT INTO dead_man_switch_registry (user_id, last_heartbeat, status, updated_at)
        VALUES (NEW.user_id, NOW(), 'ACTIVE', NOW())
        ON CONFLICT (user_id) 
        DO UPDATE SET 
            last_heartbeat = NOW(),
            status = 'ACTIVE',
            updated_at = NOW();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    # 5. Attach activity trigger to user_skill_profiles updates
    op.execute("""
    DROP TRIGGER IF EXISTS trg_dms_heartbeat_skill_profile ON user_skill_profiles;
    CREATE TRIGGER trg_dms_heartbeat_skill_profile
        AFTER INSERT OR UPDATE ON user_skill_profiles
        FOR EACH ROW
        EXECUTE FUNCTION update_dms_heartbeat_on_activity();
    """)


def downgrade() -> None:
    # Drop trigger and function
    op.execute("DROP TRIGGER IF EXISTS trg_dms_heartbeat_skill_profile ON user_skill_profiles;")
    op.execute("DROP FUNCTION IF EXISTS update_dms_heartbeat_on_activity();")

    # Drop RLS policy
    op.execute("DROP POLICY IF EXISTS dms_user_isolation_policy ON dead_man_switch_registry;")

    # Drop table
    op.execute("DROP TABLE IF EXISTS dead_man_switch_registry CASCADE;")    
    
"""
core/models.py (Excerpt)

SQLAlchemy ORM models for the OMEGA-LUQI engine database persistence layer.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Any, Dict

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

# Import shared Base declaration
from core.database import Base


class DeadManSwitchRegistry(Base):
    """
    Persists user vitality tracking thresholds, trusted contacts, 
    and 30% gate escalation state locks.
    """
    __tablename__ = "dead_man_switch_registry"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False, 
        unique=True
    )
    inactivity_limit_days: Mapped[int] = mapped_column(
        Integer, 
        default=30, 
        nullable=False
    )
    grace_period_days: Mapped[int] = mapped_column(
        Integer, 
        default=7, 
        nullable=False
    )
    last_heartbeat: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), 
        default="ACTIVE", 
        nullable=False
    )  # ACTIVE, WARNING, BREACHED
    
    # List of trusted contacts: [{"name": "Jane", "email": "jane@example.com", "phone": "+27820000000"}]
    trusted_contacts: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB, 
        server_default="[]", 
        nullable=True
    )
    gate_task_id: Mapped[Optional[str]] = mapped_column(
        String(64), 
        nullable=True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(), 
        nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="dead_man_switch")

    def __repr__(self) -> str:
        return (
            f"<DeadManSwitchRegistry(user_id={self.user_id}, "
            f"status='{self.status}', last_heartbeat={self.last_heartbeat})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert ORM instance to clean dictionary payload."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "inactivity_limit_days": self.inactivity_limit_days,
            "grace_period_days": self.grace_period_days,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "status": self.status,
            "trusted_contacts": self.trusted_contacts or [],
            "gate_task_id": self.gate_task_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
