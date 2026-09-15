"""
OMEGA-LUQI Memory Layer - persistent per-user memory for the companion.

Closes the 'memory systems' gap: tasks have always persisted (state store),
but students/companions did not. Append-only, per-user, PII-scrubbed on
write, capped per user. In-memory default (same pattern as the state store);
swap for Redis/Postgres when multi-node.

Honest scope: this is RECALL, not learning. Retrieval of what was said.
"""
import threading
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .auth import LuqiAuthManager, UserSessionProfile
from .pii_scrub import scrub_pii

router = APIRouter(prefix="/v1/memory", tags=["Companion Memory"])

_MAX_PER_USER = 100
_store: Dict[str, List[Dict[str, Any]]] = {}
_lock = threading.Lock()


class MemoryNote(BaseModel):
    topic: str
    fact: str


def add_memory(user_id: str, topic: str, fact: str) -> Dict[str, Any]:
    note = {"topic": scrub_pii(topic)[:100], "fact": scrub_pii(fact)[:1000],
            "at": time.time()}
    with _lock:
        bucket = _store.setdefault(user_id, [])
        bucket.append(note)
        if len(bucket) > _MAX_PER_USER:  # cap: drop oldest
            del bucket[0:len(bucket) - _MAX_PER_USER]
        return {"stored": True, "total": len(bucket)}


def get_memories(user_id: str, topic: Optional[str] = None) -> List[Dict[str, Any]]:
    with _lock:
        notes = list(_store.get(user_id, []))
    if topic:
        t = topic.lower()
        notes = [n for n in notes if t in n["topic"].lower()]
    return notes


@router.post("/remember")
async def remember(note: MemoryNote,
                   user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token)):
    return add_memory(str(user.user_id), note.topic, note.fact)


@router.get("/recall")
async def recall(topic: Optional[str] = None,
                 user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token)):
    return {"memories": get_memories(str(user.user_id), topic)}
