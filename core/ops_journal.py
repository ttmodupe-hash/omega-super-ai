"""
OMEGA-LUQI Ops Journal (Issue 36) - append-only durable record of the ops plane.

Approvals, decisions, and task runs are per-worker memory by design
(numReplicas=1 rule), but memory dies with the worker. The journal appends one
JSON line per event to disk with fsync, so a restart can replay pending state
and humans keep an audit trail that survives redeploys.

Honesty rules: journal failure NEVER blocks an ops action (in-memory state is
authoritative within a worker lifetime; the journal exists for restart recovery
and audit). Write failures are recorded in write_errors and surfaced via the
audit endpoint - never silent. Disable with OPS_JOURNAL=off (tests do this).
"""
from __future__ import annotations

import json
import os
import time

ENABLED = os.getenv("OPS_JOURNAL", "on") != "off"
JOURNAL_PATH = os.getenv(
    "OPS_JOURNAL_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "ops_journal.jsonl"))
MAX_READ = int(os.getenv("OPS_JOURNAL_READ", "1000"))

write_errors: list[str] = []     # surfaced via /audit - never silent


def record(event: dict) -> bool:
    """Append one event. Returns False (and logs) on failure - never raises."""
    if not ENABLED:
        return False
    try:
        os.makedirs(os.path.dirname(JOURNAL_PATH), exist_ok=True)
        line = json.dumps({"ts": time.time(), **event}, default=str)
        with open(JOURNAL_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())
        return True
    except Exception as exc:
        write_errors.append(f"{type(exc).__name__}: {exc}")
        return False


def read_recent(limit: int = 100) -> list[dict]:
    """Newest-bounded read; torn tail lines from crashed writes are skipped."""
    if not os.path.exists(JOURNAL_PATH):
        return []
    try:
        with open(JOURNAL_PATH, encoding="utf-8") as f:
            lines = f.readlines()[-max(1, min(limit, MAX_READ)):]
        out = []
        for line in lines:
            try:
                out.append(json.loads(line))
            except Exception:
                continue
        return out
    except Exception:
        return []


def replay() -> list[dict]:
    """All events in write order (bounded to the MAX_READ tail)."""
    return read_recent(MAX_READ)
