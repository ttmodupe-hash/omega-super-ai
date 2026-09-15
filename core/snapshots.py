"""
OMEGA-LUQI Snapshot Store - append-only, hash-fingerprinted, change-aware.

Adopts the architecture proven in the Spinov health-API review (2026-07-27):
sources rewrite records in place behind stable IDs and answer HTTP 200 for
every reality (current, obsolete, remapped, never-existed). The only durable
defenses:

  1. Key by (source, record_id, version) - NEVER upsert by id alone.
     An id-keyed upsert cannot distinguish "rewritten 7 times" from "never
     touched" - the store destroys the only difference that mattered.
  2. Fingerprint every body (sha256). Same id, new hash -> rewrite detected,
     provable even when the source will not serve old versions.
  3. Record seen_at. The only copy of version 3 you will ever hold is the
     one you took the day it was current - so take it.

In-memory default; swap for Postgres (audit table) when multi-node.

FULL BODIES vs HASHES (the article's open question, made a config): his line -
hashes for everything, full bodies only for sources that have burned him -
was drawn from memory. Here it is drawn deliberately: SNAPSHOT_FULL_BODY_SOURCES
(comma-separated source names) retains bodies for exactly those sources.
Hash-only keeps change detection at ~zero storage; bodies cost real money
(the article measured ~250KB per DailyMed label).
"""
import hashlib
import threading
import time
from typing import Any, Dict, Optional, Tuple

_lock = threading.Lock()
_store: Dict[Tuple[str, str, str], Dict[str, Any]] = {}


def fingerprint_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _keep_bodies(source: str) -> bool:
    """FULL BODIES vs HASHES (the article's open question, made a config):
    hashes for everything, full bodies only for sources listed in
    SNAPSHOT_FULL_BODY_SOURCES (comma-separated) - the deliberate version of
    the line the article's author drew from memory of past incidents."""
    import os
    listed = os.getenv("SNAPSHOT_FULL_BODY_SOURCES", "")
    return source in [s.strip() for s in listed.split(",") if s.strip()]


def record_snapshot(source: str, record_id: str, version: str,
                    body: bytes) -> Dict[str, Any]:
    """Append-only record. Returns change detection, never mutates history.
    Full body retained only for SNAPSHOT_FULL_BODY_SOURCES; hash otherwise."""
    key = (source, record_id, str(version))
    digest = fingerprint_bytes(body)
    keep_body = _keep_bodies(source)
    with _lock:
        existing = _store.get(key)
        if existing is None:
            entry = {"sha256": digest, "seen_at": time.time(), "size": len(body)}
            if keep_body:
                entry["body"] = body
            _store[key] = entry
            return {"keyed_by": "(source, id, version)", "version": str(version),
                    "sha256": digest, "changed": False, "first_seen": True,
                    "previous_sha256": None, "body_retained": keep_body}
        changed = existing["sha256"] != digest
        prev = existing["sha256"]
        if changed:
            existing["sha256"] = digest
            existing["seen_at"] = time.time()
            if keep_body:
                existing["body"] = body
        return {"keyed_by": "(source, id, version)", "version": str(version),
                "sha256": digest, "changed": changed, "first_seen": False,
                "previous_sha256": prev if changed else None,
                "body_retained": keep_body}


def versions_held(source: str, record_id: str) -> int:
    with _lock:
        return len([k for k in _store if k[0] == source and k[1] == record_id])


def rewrites_detected(source: str, record_id: str) -> int:
    """Versions held beyond the first == how many rewrites we witnessed."""
    return max(0, versions_held(source, record_id) - 1)


def assert_history_survives(source: str, record_id: str, expected_versions: int) -> None:
    """A check that can FAIL - not decoration. On an (id, version) store this
    verifies the record of what the source published; on an upserted store it
    names the gap loudly, which is its purpose."""
    kept = versions_held(source, record_id)
    if kept != expected_versions:
        raise AssertionError(
            f"{record_id}: kept {kept} version(s) but the source published "
            f"{expected_versions} - an id-keyed store destroyed the evidence")


def stats() -> Dict[str, Any]:
    with _lock:
        total = len(_store)
        sources = sorted({k[0] for k in _store})
        bodies = sum(1 for v in _store.values() if "body" in v)
    return {"snapshots": total, "sources": sources, "bodies_retained": bodies}
