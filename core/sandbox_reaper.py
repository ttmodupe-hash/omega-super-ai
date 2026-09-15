"""
OMEGA-LUQI Sandbox Idle Reaper

Free-tier Docker containers cost continuous RAM. The reaper tracks per-session
last-activity (touched on every terminal packet) and destroys containers idle
past the timeout. Pure collect function is unit-testable without Docker.

Config: SANDBOX_IDLE_TIMEOUT_MINUTES (default 15), SANDBOX_REAPER_INTERVAL_SECONDS (60).
"""
import os
import asyncio
import time
from typing import Dict, List, Optional


def collect_idle_sessions(last_activity: Dict[str, float],
                          timeout_seconds: float,
                          now: Optional[float] = None) -> List[str]:
    """Sessions with no terminal traffic for longer than timeout."""
    now = now if now is not None else time.time()
    return [sid for sid, ts in last_activity.items() if now - ts > timeout_seconds]


async def reaper_loop(connection_manager, sandbox_manager,
                      timeout_minutes: Optional[float] = None,
                      interval_seconds: Optional[float] = None) -> None:
    """Background task: teardown idle sandboxes forever. Swallows errors."""
    timeout = (timeout_minutes if timeout_minutes is not None
               else float(os.getenv("SANDBOX_IDLE_TIMEOUT_MINUTES", "15"))) * 60.0
    interval = interval_seconds or float(os.getenv("SANDBOX_REAPER_INTERVAL_SECONDS", "60"))
    while True:
        await asyncio.sleep(interval)
        try:
            for session_id in collect_idle_sessions(connection_manager.last_activity, timeout):
                # session_id = "{student_id}-{container_name}"
                container_name = session_id.split("-", 1)[1] if "-" in session_id else session_id
                sandbox_manager.destroy_environment(container_name)
                connection_manager.disconnect(session_id)
                print(f"[Reaper] Idle sandbox recycled: {container_name}")
        except Exception as e:
            print(f"[Reaper] Cycle error (non-fatal): {e}")
