"""
OMEGA-LUQI Sovereign Database Cluster Router

Ping-verified failover AND failback between primary and replica engines.

SECURITY: connection URLs come ONLY from environment variables. The pasted
blueprint shipped hardcoded credentials as defaults - never do this; anything
in source is in git history forever. Missing env vars raise at construction.

Not auto-wired into main.py: the app treats the database as optional (lazy
init). When you operate a real replica, construct this router in startup and
assign its engines where app.state.db_engine is used today. Until then this
module is a tested, standalone state machine.

Testing: the engine factory is injectable, so the full failover/failback
state machine runs in unit tests without a database.
"""
import logging
import os
from typing import Callable, Optional

# Lazy import: the core must boot without SQLAlchemy installed (design rule).
try:
    import sqlalchemy as sa
    from sqlalchemy import create_engine
except ImportError:
    sa = None
    create_engine = None

logger = logging.getLogger("LuqiReplicationKernel")

PRIMARY_DB_URL = os.getenv("DATABASE_URL")
BACKUP_DB_URL = os.getenv("DATABASE_URL_BACKUP")


class SovereignDatabaseClusterRouter:
    """Symmetric failover: pings current target, switches only after the
    alternative answers, and fails BACK when the primary recovers."""

    def __init__(self, primary_url: Optional[str] = None, backup_url: Optional[str] = None,
                 engine_factory: Optional[Callable] = None):
        if sa is None and engine_factory is None:
            raise RuntimeError("SQLAlchemy not installed - cluster router unavailable.")
        self._factory = engine_factory or create_engine
        self._urls = {
            "PRIMARY": primary_url or PRIMARY_DB_URL,
            "LOCAL_REPLICA": backup_url or BACKUP_DB_URL,
        }
        if not self._urls["PRIMARY"]:
            raise RuntimeError("DATABASE_URL is required for the cluster router.")
        if not self._urls["LOCAL_REPLICA"]:
            raise RuntimeError("DATABASE_URL_BACKUP is required for the cluster router.")
        self._engines = {"PRIMARY": None, "LOCAL_REPLICA": None}
        self.current_target = "PRIMARY"

    def _engine_for(self, target: str):
        if self._engines[target] is None:
            self._engines[target] = self._factory(self._urls[target], pool_pre_ping=True)
        return self._engines[target]

    def _ping(self, target: str) -> bool:
        try:
            with self._engine_for(target).connect() as conn:
                # sa.text when SQLAlchemy is installed; plain string otherwise
                # (injected test doubles accept both; real engines always have sa)
                conn.execute(sa.text("SELECT 1") if sa else "SELECT 1")
            return True
        except Exception as e:  # any connection-level failure = unhealthy
            logger.debug("Ping %s failed: %s", target, e)
            return False

    def get_healthy_session_connection(self):
        """Return an engine verified reachable RIGHT NOW, with failover/failback."""
        if self._ping(self.current_target):
            # Failback: if we're on the replica, check whether primary recovered
            if self.current_target == "LOCAL_REPLICA" and self._ping("PRIMARY"):
                logger.info("Primary recovered - failing back from replica.")
                self.current_target = "PRIMARY"
            return self._engine_for(self.current_target)

        other = "LOCAL_REPLICA" if self.current_target == "PRIMARY" else "PRIMARY"
        logger.error("Target %s unreachable - attempting verified switch to %s",
                     self.current_target, other)
        if self._ping(other):
            self.current_target = other
            return self._engine_for(other)

        logger.critical("Both database nodes unreachable.")
        raise RuntimeError("Sovereign Storage Cluster Defunct: primary and replica both down.")
