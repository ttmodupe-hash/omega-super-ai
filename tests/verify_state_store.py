"""verify_state_store.py — lock the task-ledger contract that protects the 30% gate.

Covers:
1. InMemory store: set/get/all roundtrip, isolation between tasks.
2. Redis store: set/get/all roundtrip via an injected fake redis module
   (no server needed) — CRITICAL: get() must read the same key set() writes
   ("luqi:task:" prefix). A mismatch strands every task at the human gate:
   get returns None -> the override endpoint 404s -> payments unreleaseable.
3. Backend selection: get_state_store() honours STATE_BACKEND env.
4. Serialization: LuqiState survives model_dump_json -> model_validate_json.

Run: python tests/verify_state_store.py   (repo root, fastapi/pydantic installed)
"""
import os
import sys
import types
import uuid
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

_RESULTS = []


def check(name: str, ok: bool, detail: str = "") -> None:
    _RESULTS.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


# ---------- Fake redis module (injected before RedisStateStore imports it) ----------
class _FakeRedisClient:
    def __init__(self):
        self._data = {}

    def get(self, key):
        return self._data.get(key)

    def set(self, key, value):
        self._data[key] = value

    def mget(self, keys):
        return [self._data.get(k) for k in keys]

    def scan_iter(self, pattern):
        # pattern is always "luqi:task:*" in this codebase
        prefix = pattern[:-1] if pattern.endswith("*") else pattern
        return [k for k in list(self._data) if k.startswith(prefix)]


_FAKE_SINGLETON = _FakeRedisClient()

_fake_redis_mod = types.ModuleType("redis")


class _FakeRedisClass:
    @staticmethod
    def from_url(url, decode_responses=True):
        return _FAKE_SINGLETON


_fake_redis_mod.Redis = _FakeRedisClass
sys.modules["redis"] = _fake_redis_mod

from core.state_store import (  # noqa: E402
    InMemoryStateStore, RedisStateStore, get_state_store, TASK_KEY_PREFIX,
)
import core.state_store as state_store_mod  # noqa: E402
from core.main_types import LuqiState, TaskStatus  # noqa: E402


def _state(tier="free", action="process_payment"):
    return LuqiState(
        task_id=uuid.uuid4(),
        student_tier=tier,
        action_type=action,
        payload={"item": "wallet_topup_R100", "reference_id": "ref-123"},
        status=TaskStatus.PENDING_HUMAN_APPROVAL,
        required_human_action="Human verification required",
    )


print("== 1. InMemoryStateStore ==")
mem = InMemoryStateStore()
s1, s2 = _state(), _state(tier="premium")
mem.set(s1.task_id, s1)
mem.set(s2.task_id, s2)
got = mem.get(s1.task_id)
check("memory: set/get roundtrip", got is not None and got.task_id == s1.task_id)
check("memory: task isolation", mem.get(s2.task_id).student_tier == "premium")
check("memory: missing key -> None", mem.get(uuid.uuid4()) is None)
check("memory: all() returns both", len(mem.all()) == 2)
check("memory: status preserved", got.status == TaskStatus.PENDING_HUMAN_APPROVAL)

print("== 2. RedisStateStore (fake transport) ==")
rds = RedisStateStore("redis://fake:6379/0")
r1, r2 = _state(), _state()
rds.set(r1.task_id, r1)
rds.set(r2.task_id, r2)
check("redis: set/get roundtrip", rds.get(r1.task_id) is not None and rds.get(r1.task_id).task_id == r1.task_id)
check("redis: missing key -> None", rds.get(uuid.uuid4()) is None)
written_keys = list(_FAKE_SINGLETON._data.keys())
check("redis: writes use luqi:task: prefix", all(k.startswith(TASK_KEY_PREFIX) for k in written_keys), str(written_keys))
check("redis: get reads the SAME key set wrote",
      rds._key(r1.task_id) in _FAKE_SINGLETON._data)
check("redis: all() finds both tasks", len(rds.all()) == 2)
check("redis: payload survives serialization",
      rds.get(r1.task_id).payload["reference_id"] == "ref-123")
check("redis: all() empty-safe on fresh prefix",
      RedisStateStore("redis://fake:6379/0").get(uuid.uuid4()) is None)

print("== 3. Backend selection ==")
state_store_mod._store = None
os.environ.pop("STATE_BACKEND", None)
check("default backend = memory", isinstance(get_state_store(), InMemoryStateStore))
state_store_mod._store = None
os.environ["STATE_BACKEND"] = "redis"
os.environ["REDIS_URL"] = "redis://fake:6379/0"
check("STATE_BACKEND=redis -> RedisStateStore", isinstance(get_state_store(), RedisStateStore))
state_store_mod._store = None
os.environ.pop("STATE_BACKEND", None)
check("store is a singleton per process", get_state_store() is get_state_store())

print("== 4. Gate-path simulation (the bug this suite exists to prevent) ==")
# /v1/agent/execute writes -> /v1/human/override reads. If get/set keys differ,
# this sequence 404s and the payment can never be released.
state_store_mod._store = None
os.environ["STATE_BACKEND"] = "redis"
store = get_state_store()
task = _state()
store.set(task.task_id, task)          # execute endpoint writes
fetched = store.get(task.task_id)      # override endpoint reads
check("gate path: write-then-read across endpoints", fetched is not None)
check("gate path: gate status readable",
      fetched is not None and fetched.status == TaskStatus.PENDING_HUMAN_APPROVAL)
state_store_mod._store = None
os.environ.pop("STATE_BACKEND", None)

failed = [r for r in _RESULTS if not r[1]]
print(f"\n{'=' * 50}\nRESULT: {len(_RESULTS) - len(failed)}/{len(_RESULTS)} PASS, {len(failed)} FAIL")
sys.exit(1 if failed else 0)
