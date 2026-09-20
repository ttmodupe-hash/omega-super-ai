"""
OMEGA-LUQI Task State Store

Default backend: thread-safe in-memory dict (single-worker deployments).
Production backend: Redis (set STATE_BACKEND=redis and REDIS_URL) - required
before running uvicorn with --workers > 1, so every worker shares one task
ledger and the 30% gate stays consistent across processes.

Key contract: ALL Redis keys carry the "luqi:task:" prefix. get() and set()
MUST use the same key - a prefix mismatch silently strands every task at the
human gate (get returns None -> 404, gate unreleaseable). Locked by
tests/verify_state_store.py.
"""
import os
import threading
from typing import Optional

from .main_types import LuqiState  # re-exported below to avoid circularity

TASK_KEY_PREFIX = "luqi:task:"


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

    @staticmethod
    def _key(task_id) -> str:
        return f"{TASK_KEY_PREFIX}{task_id}"

    def get(self, task_id) -> Optional[LuqiState]:
        raw = self._r.get(self._key(task_id))
        return LuqiState.model_validate_json(raw) if raw else None

    def set(self, task_id, state: LuqiState) -> None:
        self._r.set(self._key(task_id), state.model_dump_json())

    def all(self) -> list:
        keys = list(self._r.scan_iter(f"{TASK_KEY_PREFIX}*"))
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
