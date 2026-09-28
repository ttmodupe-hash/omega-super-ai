"""
Omega AI v4.0.0 — Autonomous Multi-Agent Memory Orchestration & Lifecycle Engine
Manages long-term data retention, dynamic decay heuristics, and user-consent-based deletion.
"""
from __future__ import annotations

import asyncio
import json
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class RetentionStatus(str, Enum):
    ACTIVE = "active"          # Recently accessed, keep
    AGING = "aging"            # Access rate decaying, monitor
    STALE = "stale"            # High idle time & low utility, propose cleanup
    ORPHANED = "orphaned"      # Belongs to deleted/invalid module
    QUARANTINED = "quarantined" # Marked for deletion, awaiting user consent
    PURGED = "purged"          # Soft-deleted (recoverable for 30 days)


@dataclass
class MemoryEntry:
    """A single tracked memory item with dynamic decay telemetry."""
    entry_id: str
    module: str
    data_type: str
    summary: str
    size_bytes: int
    created_at: float
    last_accessed: float
    access_count: int = 0
    importance: int = 3       # 1-5 scale (5 = critical/permanent, 1 = transient)
    status: str = RetentionStatus.ACTIVE
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def age_days(self) -> float:
        return round((time.time() - self.created_at) / 86400, 2)

    @property
    def idle_days(self) -> float:
        return round((time.time() - self.last_accessed) / 86400, 2)

    def calculate_decay_score(self, half_life_days: float = 14.0) -> float:
        """Calculates retention score based on importance, access frequency, and time decay."""
        if self.importance >= 5:
            return 100.0  # Critical entries never decay
        
        # Exponential decay factor lambda
        decay_lambda = math.log(2) / half_life_days
        time_factor = math.exp(-decay_lambda * self.idle_days)
        frequency_factor = math.log(self.access_count + 1) + 1.0
        
        score = (self.importance * 20.0) * frequency_factor * time_factor
        return round(score, 2)


@dataclass
class PurgeProposal:
    """A proposal to delete memory entries, awaiting user approval."""
    proposal_id: str
    proposed_at: float
    entries: List[str]
    reason: str
    total_size_bytes: int
    approved: Optional[bool] = None
    user_response: str = ""
    executed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 1: THE ARCHIVIST — Asynchronous Ledger & Access Tracker
# ═══════════════════════════════════════════════════════════════════════════════

class ArchivistAgent:
    """Monitors and logs all memory entries asynchronously with thread-safe persistence."""

    def __init__(self, persist_path: str = ".omega_sessions/memory_registry.json") -> None:
        self._persist_path = Path(persist_path)
        self._entries: Dict[str, MemoryEntry] = {}
        self._lock = asyncio.Lock()
        self._load_sync()

    def _load_sync(self) -> None:
        """Initial synchronous load at startup."""
        if self._persist_path.exists():
            try:
                data = json.loads(self._persist_path.read_text(encoding="utf-8"))
                for e in data.get("entries", []):
                    self._entries[e["entry_id"]] = MemoryEntry(**e)
            except Exception:
                pass

    async def save_async(self) -> None:
        """Asynchronously persists memory entries to disk."""
        async with self._lock:
            try:
                self._persist_path.parent.mkdir(parents=True, exist_ok=True)
                payload = {
                    "entries": [e.to_dict() for e in self._entries.values()],
                    "saved_at": time.time(),
                }
                # Non-blocking write via executor
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, 
                    lambda: self._persist_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                )
            except Exception:
                pass

    async def register(self, entry: MemoryEntry) -> None:
        self._entries[entry.entry_id] = entry
        await self.save_async()

    async def record_access(self, entry_id: str) -> None:
        if entry_id in self._entries:
            entry = self._entries[entry_id]
            entry.last_accessed = time.time()
            entry.access_count += 1
            if entry.status in (RetentionStatus.STALE, RetentionStatus.ORPHANED):
                entry.status = RetentionStatus.ACTIVE
            await self.save_async()

    async def set_importance(self, entry_id: str, importance: int) -> None:
        if entry_id in self._entries and 1 <= importance <= 5:
            self._entries[entry_id].importance = importance
            await self.save_async()

    def get(self, entry_id: str) -> Optional[MemoryEntry]:
        return self._entries.get(entry_id)

    def list_all(self, module: str = "", status: str = "") -> List[MemoryEntry]:
        results = list(self._entries.values())
        if module:
            results = [e for e in results if e.module == module]
        if status:
            results = [e for e in results if e.status == status]
        return sorted(results, key=lambda e: e.last_accessed, reverse=True)

    def get_stats(self) -> Dict[str, Any]:
        by_module = defaultdict(int)
        by_status = defaultdict(int)
        by_type = defaultdict(int)
        total_size = 0
        for e in self._entries.values():
            by_module[e.module] += 1
            by_status[e.status] += 1
            by_type[e.data_type] += 1
            total_size += e.size_bytes

        return {
            "total_entries": len(self._entries),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "by_module": dict(by_module),
            "by_status": dict(by_status),
            "by_type": dict(by_type),
        }

    async def update_status(self, entry_id: str, status: str) -> bool:
        if entry_id in self._entries:
            self._entries[entry_id].status = status
            await self.save_async()
            return True
        return False

    async def scan_for_orphans(self, valid_modules: List[str]) -> List[str]:
        orphans = []
        for eid, e in self._entries.items():
            if e.module not in valid_modules and e.status != RetentionStatus.ORPHANED:
                e.status = RetentionStatus.ORPHANED
                orphans.append(eid)
        if orphans:
            await self.save_async()
        return orphans


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 2: THE CURATOR — Heuristic Analytics & Deduplication
# ═══════════════════════════════════════════════════════════════════════════════

class CuratorAgent:
    """Analyzes memory health using decay scores and flags redundant/stale candidates."""

    def __init__(self, archivist: ArchivistAgent) -> None:
        self.archivist = archivist

    def classify(self, entry: MemoryEntry) -> str:
        if entry.status in (RetentionStatus.QUARANTINED, RetentionStatus.PURGED):
            return entry.status
        if entry.status == RetentionStatus.ORPHANED:
            return RetentionStatus.ORPHANED

        score = entry.calculate_decay_score()
        
        if score < 5.0 and entry.importance < 5:
            return RetentionStatus.STALE
        elif score < 20.0 and entry.importance < 4:
            return RetentionStatus.AGING
        else:
            return RetentionStatus.ACTIVE

    async def review_all(self) -> Dict[str, List[str]]:
        changes: Dict[str, List[str]] = {"to_stale": [], "to_aging": [], "to_active": []}
        for eid, entry in list(self.archivist._entries.items()):
            new_status = self.classify(entry)
            if new_status != entry.status and entry.status not in (
                RetentionStatus.QUARANTINED, RetentionStatus.PURGED
            ):
                if new_status == RetentionStatus.STALE:
                    changes["to_stale"].append(eid)
                elif new_status == RetentionStatus.AGING:
                    changes["to_aging"].append(eid)
                elif new_status == RetentionStatus.ACTIVE:
                    changes["to_active"].append(eid)
                await self.archivist.update_status(eid, new_status)
        return changes

    def propose_cleanup(self) -> List[MemoryEntry]:
        candidates = []
        for entry in self.archivist._entries.values():
            if entry.status in (RetentionStatus.STALE, RetentionStatus.ORPHANED):
                if entry.importance < 5 and entry.status not in (
                    RetentionStatus.QUARANTINED, RetentionStatus.PURGED
                ):
                    candidates.append(entry)
        return sorted(candidates, key=lambda e: e.calculate_decay_score())

    def find_redundant_entries(self) -> List[Tuple[str, str]]:
        """Scans for summary overlaps to flag potential duplicates for consolidation."""
        entries = list(self.archivist._entries.values())
        duplicates = []
        for i in range(len(entries)):
            for j in range(i + 1, len(entries)):
                e1, e2 = entries[i], entries[j]
                if e1.module == e2.module and e1.summary.lower() == e2.summary.lower():
                    duplicates.append((e1.entry_id, e2.entry_id))
        return duplicates

    def generate_report(self) -> Dict[str, Any]:
        stats = self.archivist.get_stats()
        stale = len(self.archivist.list_all(status=RetentionStatus.STALE))
        aging = len(self.archivist.list_all(status=RetentionStatus.AGING))
        orphaned = len(self.archivist.list_all(status=RetentionStatus.ORPHANED))
        quarantined = len(self.archivist.list_all(status=RetentionStatus.QUARANTINED))
        purged = len(self.archivist.list_all(status=RetentionStatus.PURGED))
        active = len(self.archivist.list_all(status=RetentionStatus.ACTIVE))

        purgeable_size = sum(
            e.size_bytes for e in self.archivist._entries.values()
            if e.status in (RetentionStatus.STALE, RetentionStatus.ORPHANED) and e.importance < 5
        )

        return {
            "total_entries": stats["total_entries"],
            "total_size_mb": stats["total_size_mb"],
            "active": active,
            "aging": aging,
            "stale": stale,
            "orphaned": orphaned,
            "quarantined": quarantined,
            "purged": purged,
            "purgeable_entries": stale + orphaned,
            "purgeable_size_mb": round(purgeable_size / (1024 * 1024), 2),
            "health_score": max(0, 100 - (stale * 5) - (orphaned * 10) - (quarantined * 2)),
            "recommendation": "cleanup_needed" if (stale + orphaned) > 0 else "healthy",
        }


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 3: THE STEWARD — Consent Governance & Lifecycle Execution
# ═══════════════════════════════════════════════════════════════════════════════

class StewardAgent:
    """Enforces consent policies, manages interactive CLI reviews, and handles soft-deletes."""

    SOFT_DELETE_DAYS = 30

    def __init__(self, archivist: ArchivistAgent, persist_path: str = ".omega_sessions/purge_queue.json") -> None:
        self.archivist = archivist
        self._persist_path = Path(persist_path)
        self._proposals: Dict[str, PurgeProposal] = {}
        self._lock = asyncio.Lock()
        self._load_sync()

    def _load_sync(self) -> None:
        if self._persist_path.exists():
            try:
                data = json.loads(self._persist_path.read_text(encoding="utf-8"))
                for p in data.get("proposals", []):
                    self._proposals[p["proposal_id"]] = PurgeProposal(**p)
            except Exception:
                pass

    async def save_async(self) -> None:
        async with self._lock:
            try:
                self._persist_path.parent.mkdir(parents=True, exist_ok=True)
                payload = {
                    "proposals": [p.to_dict() for p in self._proposals.values()],
                    "saved_at": time.time(),
                }
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self._persist_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                )
            except Exception:
                pass

    async def create_proposal(self, reason: str = "stale/orphaned cleanup") -> Optional[PurgeProposal]:
        curator = CuratorAgent(self.archivist)
        candidates = curator.propose_cleanup()
        if not candidates:
            return None

        proposal = PurgeProposal(
            proposal_id=f"purge_{int(time.time())}_{len(candidates)}",
            proposed_at=time.time(),
            entries=[e.entry_id for e in candidates],
            reason=reason,
            total_size_bytes=sum(e.size_bytes for e in candidates),
        )
        for eid in proposal.entries:
            await self.archivist.update_status(eid, RetentionStatus.QUARANTINED)

        self._proposals[proposal.proposal_id] = proposal
        await self.save_async()
        return proposal

    async def approve(self, proposal_id: str, user_note: str = "") -> Dict[str, Any]:
        proposal = self._proposals.get(proposal_id)
        if not proposal or proposal.approved is not None:
            return {"success": False, "error": "Proposal not found or already decided"}

        proposal.approved = True
        proposal.user_response = user_note
        proposal.executed_at = time.time()

        deleted = 0
        failed = 0
        for eid in proposal.entries:
            if await self.archivist.update_status(eid, RetentionStatus.PURGED):
                deleted += 1
            else:
                failed += 1

        await self.save_async()
        return {
            "success": True,
            "proposal_id": proposal_id,
            "entries_deleted": deleted,
            "entries_failed": failed,
            "total_size_mb": round(proposal.total_size_bytes / (1024 * 1024), 2),
            "recoverable_until": proposal.executed_at + (self.SOFT_DELETE_DAYS * 86400),
        }

    async def deny(self, proposal_id: str, user_note: str = "") -> Dict[str, Any]:
        proposal = self._proposals.get(proposal_id)
        if not proposal or proposal.approved is not None:
            return {"success": False, "error": "Proposal not found or already decided"}

        proposal.approved = False
        proposal.user_response = user_note
        proposal.executed_at = time.time()

        restored = 0
        for eid in proposal.entries:
            if await self.archivist.update_status(eid, RetentionStatus.ACTIVE):
                restored += 1

        await self.save_async()
        return {
            "success": True,
            "proposal_id": proposal_id,
            "entries_restored": restored,
            "message": "All entries restored to active status.",
        }

    async def prompt_user_interactive(self, proposal_id: str) -> Dict[str, Any]:
        """Provides an interactive CLI consent prompt to the user."""
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            return {"success": False, "error": "Proposal not found"}

        print(f"\n[STEWARD CONSENT REQUIRED] Proposal ID: {proposal.proposal_id}")
        print(f"Reason: {proposal.reason} | Entries: {len(proposal.entries)} | Size: {round(proposal.total_size_bytes / 1024, 2)} KB")
        for eid in proposal.entries:
            entry = self.archivist.get(eid)
            if entry:
                print(f"  - [{entry.module}] {entry.summary} (Idle: {entry.idle_days} days)")

        choice = input("\nDo you approve soft-deleting these items? (y/n): ").strip().lower()
        note = input("Add optional note: ").strip()

        if choice in ('y', 'yes'):
            return await self.approve(proposal_id, note or "Approved via CLI prompt")
        else:
            return await self.deny(proposal_id, note or "Denied via CLI prompt")


# ═══════════════════════════════════════════════════════════════════════════════
# UNIFIED MEMORY MANAGER COORDINATOR
# ═══════════════════════════════════════════════════════════════════════════════

class MemoryManager:
    """Unified Orchestrator for the 3-Agent Memory Management Engine."""

    VALID_MODULES = [
        "core_brain", "api_server", "db_engine", "cache_manager",
        "knowledge_base", "conversation_state", "scheduler", "error_repair"
    ]

    def __init__(self) -> None:
        self.archivist = ArchivistAgent()
        self.curator = CuratorAgent(self.archivist)
        self.steward = StewardAgent(self.archivist)

    async def register_entry(self, entry: MemoryEntry) -> None:
        await self.archivist.register(entry)

    async def record_access(self, entry_id: str) -> None:
        await self.archivist.record_access(entry_id)

    async def review(self) -> Dict[str, Any]:
        changes = await self.curator.review_all()
        orphans = await self.archivist.scan_for_orphans(self.VALID_MODULES)
        changes["orphaned"] = orphans
        return changes

    async def propose_cleanup(self) -> Optional[PurgeProposal]:
        return await self.steward.create_proposal()

    def get_report(self) -> Dict[str, Any]:
        return self.curator.generate_report()


# ── Global Singleton Access ──

_memory_manager_instance: Optional[MemoryManager] = None

def get_memory_manager() -> MemoryManager:
    global _memory_manager_instance
    if _memory_manager_instance is None:
        _memory_manager_instance = MemoryManager()
    return _memory_manager_instance
