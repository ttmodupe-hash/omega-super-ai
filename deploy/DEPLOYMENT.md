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

    
    
