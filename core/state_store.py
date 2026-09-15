"""
OMEGA-LUQI Task State Store

Default backend: thread-safe in-memory dict (single-worker deployments).
Production backend: Redis (set STATE_BACKEND=redis and REDIS_URL) - required
before running uvicorn with --workers > 1, so every worker shares one task
ledger and the 30% gate stays consistent across processes.
"""
import os
import threading
from typing import Optional

from .main_types import LuqiState  # re-exported below to avoid circularity


class InMemoryStateStore:
    def __init__(self):
        self._db: dict = {}
        self._lock = threading.Lock()

    def get(self, task_id) -> Optional[LuqiState]:
        with self._lock:
            return self._db.get(task_id)

    def set(self, task_id, state: LuqiState) -> None:
        with self._lock:
            self._db[task_id] = state

    def all(self) -> list:
        """Snapshot of all tracked tasks (used by the ops cockpit gate queue)."""
        with self._lock:
            return list(self._db.values())


class RedisStateStore:
    def __init__(self, url: str):
        import redis  # optional dependency - only needed for STATE_BACKEND=redis
        self._r = redis.Redis.from_url(url, decode_responses=True)

    def get(self, task_id) -> Optional[LuqiState]:
        raw = self._r.get(str(task_id))
        return LuqiState.model_validate_json(raw) if raw else None

    def set(self, task_id, state: LuqiState) -> None:
        self._r.set(f"luqi:task:{task_id}", state.model_dump_json())

    def all(self) -> list:
        keys = list(self._r.scan_iter("luqi:task:*"))
        if not keys:
            return []
        raw = self._r.mget(keys)
        return [LuqiState.model_validate_json(v) for v in raw if v]


_store = None


def get_state_store():
    global _store
    if _store is None:
        if os.getenv("STATE_BACKEND", "memory") == "redis":
            _store = RedisStateStore(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        else:
            _store = InMemoryStateStore()
    return _store
