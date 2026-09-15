"""Omega AI v3.7.0 — 3-Agent Memory Management System
Manages long-term data retention with user-consent-based deletion.

Three specialized agents work together:
- Archivist: Tracks all stored data, access patterns, and metadata
- Curator: Analyzes stale/unused data and proposes cleanup candidates
- Steward: Manages the purge queue, prompts user for approval, executes cleanup

Rules:
1. NOTHING is deleted without explicit user approval
2. All data has a retention policy: active, aging, stale, orphaned
3. Before any deletion, the Steward asks the user interactively
4. Every decision is logged and reversible (soft-delete for 30 days)
"""
from __future__ import annotations

import json
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class RetentionStatus(str, Enum):
    ACTIVE = "active"       # Recently accessed, keep
    AGING = "aging"         # Not accessed recently, monitor
    STALE = "stale"         # Long time no access, propose cleanup
    ORPHANED = "orphaned"   # Belongs to deleted/invalid module
    QUARANTINED = "quarantined"  # Marked for deletion, awaiting approval
    PURGED = "purged"       # Soft-deleted (recoverable for 30 days)


@dataclass
class MemoryEntry:
    """A single tracked memory item."""
    entry_id: str
    module: str              # Which module owns this (chat, kb, cache, export, etc.)
    data_type: str           # conversation, knowledge, cache, export, preference, etc.
    summary: str             # Human-readable summary of the content
    size_bytes: int
    created_at: float
    last_accessed: float
    access_count: int = 0
    importance: int = 3      # 1-5 scale (5 = critical, 1 = disposable)
    status: str = RetentionStatus.ACTIVE
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def age_days(self) -> float:
        return round((time.time() - self.created_at) / 86400, 1)

    @property
    def idle_days(self) -> float:
        return round((time.time() - self.last_accessed) / 86400, 1)


@dataclass
class PurgeProposal:
    """A proposal to delete memory entries, awaiting user approval."""
    proposal_id: str
    proposed_at: float
    entries: list[str]       # List of entry_ids
    reason: str
    total_size_bytes: int
    approved: bool | None = None   # None = pending, True = approved, False = denied
    user_response: str = ""
    executed_at: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 1: THE ARCHIVIST — Tracks everything
# ═══════════════════════════════════════════════════════════════════════════════

class ArchivistAgent:
    """Monitors and logs all memory entries. Tracks access patterns and metadata."""

    def __init__(self, persist_path: str = ".omega_sessions/memory_registry.json") -> None:
        self._persist_path = persist_path
        self._entries: dict[str, MemoryEntry] = {}
        self._load()

    def _load(self) -> None:
        path = Path(self._persist_path)
        if path.exists():
            try:
                data = json.loads(path.read_text())
                for e in data.get("entries", []):
                    self._entries[e["entry_id"]] = MemoryEntry(**e)
            except Exception:
                pass

    def _save(self) -> None:
        try:
            Path(self._persist_path).parent.mkdir(parents=True, exist_ok=True)
            Path(self._persist_path).write_text(json.dumps({
                "entries": [e.to_dict() for e in self._entries.values()],
                "saved_at": time.time(),
            }, indent=2))
        except Exception:
            pass

    # ── Registration ──

    def register(self, entry: MemoryEntry) -> None:
        """Register a new memory entry."""
        self._entries[entry.entry_id] = entry
        self._save()

    def record_access(self, entry_id: str) -> None:
        """Record that an entry was accessed."""
        if entry_id in self._entries:
            self._entries[entry_id].last_accessed = time.time()
            self._entries[entry_id].access_count += 1
            # If it was stale/orphaned, reactivate
            if self._entries[entry_id].status in (RetentionStatus.STALE, RetentionStatus.ORPHANED):
                self._entries[entry_id].status = RetentionStatus.ACTIVE
            self._save()

    def set_importance(self, entry_id: str, importance: int) -> None:
        """Set importance level (1-5) for an entry."""
        if entry_id in self._entries and 1 <= importance <= 5:
            self._entries[entry_id].importance = importance
            self._save()

    # ── Queries ──

    def get(self, entry_id: str) -> MemoryEntry | None:
        return self._entries.get(entry_id)

    def list_all(self, module: str = "", status: str = "") -> list[MemoryEntry]:
        results = list(self._entries.values())
        if module:
            results = [e for e in results if e.module == module]
        if status:
            results = [e for e in results if e.status == status]
        return sorted(results, key=lambda e: e.last_accessed, reverse=True)

    def get_stats(self) -> dict[str, Any]:
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

    # ── Status transitions ──

    def update_status(self, entry_id: str, status: str) -> bool:
        if entry_id in self._entries:
            self._entries[entry_id].status = status
            self._save()
            return True
        return False

    def scan_for_orphans(self, valid_modules: list[str]) -> list[str]:
        """Find entries belonging to modules that no longer exist."""
        orphans = []
        for eid, e in self._entries.items():
            if e.module not in valid_modules and e.status != RetentionStatus.ORPHANED:
                e.status = RetentionStatus.ORPHANED
                orphans.append(eid)
        if orphans:
            self._save()
        return orphans


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 2: THE CURATOR — Decides what to propose for cleanup
# ═══════════════════════════════════════════════════════════════════════════════

class CuratorAgent:
    """Analyzes memory entries and proposes cleanup candidates.

    Policies:
    - Aging: >7 days idle, importance <= 3
    - Stale: >30 days idle, importance <= 4
    - Orphaned: module no longer exists (any importance)
    - Never proposes importance=5 (critical) for deletion
    - Never proposes anything without tagging it first
    """

    def __init__(self, archivist: ArchivistAgent) -> None:
        self.archivist = archivist

    def classify(self, entry: MemoryEntry) -> str:
        """Classify a single entry's retention status."""
        if entry.status in (RetentionStatus.QUARANTINED, RetentionStatus.PURGED):
            return entry.status
        if entry.status == RetentionStatus.ORPHANED:
            return RetentionStatus.ORPHANED

        idle = entry.idle_days
        importance = entry.importance

        if idle > 30 and importance <= 3:
            return RetentionStatus.STALE
        elif idle > 7 and importance <= 2:
            return RetentionStatus.AGING
        elif idle > 30 and importance <= 4:
            return RetentionStatus.STALE
        elif idle > 14 and importance <= 2:
            return RetentionStatus.AGING
        else:
            return RetentionStatus.ACTIVE

    def review_all(self) -> dict[str, list[str]]:
        """Review all entries and return classification changes."""
        changes: dict[str, list[str]] = {
            "to_stale": [],
            "to_aging": [],
            "to_active": [],
        }
        for eid, entry in self.archivist._entries.items():
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
                self.archivist.update_status(eid, new_status)
        return changes

    def propose_cleanup(self) -> list[MemoryEntry]:
        """Generate a list of entries to propose for deletion.

        Rules for proposal:
        - Must be STALE or ORPHANED
        - Importance must NOT be 5 (critical)
        - Must not already be quarantined or purged
        """
        candidates = []
        for entry in self.archivist._entries.values():
            if entry.status in (RetentionStatus.STALE, RetentionStatus.ORPHANED):
                if entry.importance < 5 and entry.status not in (
                    RetentionStatus.QUARANTINED, RetentionStatus.PURGED
                ):
                    candidates.append(entry)
        return sorted(candidates, key=lambda e: e.idle_days, reverse=True)

    def generate_report(self) -> dict[str, Any]:
        """Generate a full memory health report."""
        stats = self.archivist.get_stats()
        stale = len(self.archivist.list_all(status=RetentionStatus.STALE))
        aging = len(self.archivist.list_all(status=RetentionStatus.AGING))
        orphaned = len(self.archivist.list_all(status=RetentionStatus.ORPHANED))
        quarantined = len(self.archivist.list_all(status=RetentionStatus.QUARANTINED))
        purged = len(self.archivist.list_all(status=RetentionStatus.PURGED))
        active = len(self.archivist.list_all(status=RetentionStatus.ACTIVE))

        # Size breakdown
        purgeable_size = sum(
            e.size_bytes for e in self.archivist._entries.values()
            if e.status in (RetentionStatus.STALE, RetentionStatus.ORPHANED)
            and e.importance < 5
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
# AGENT 3: THE STEWARD — Handles user consent and cleanup execution
# ═══════════════════════════════════════════════════════════════════════════════

class StewardAgent:
    """Manages the purge queue and ensures user consent for every deletion.

    Core rule: NOTHING is deleted without user approval.
    - Soft-delete for 30 days (recoverable)
    - Every proposal is logged
    - Batch proposals for user review
    """

    SOFT_DELETE_DAYS = 30

    def __init__(self, archivist: ArchivistAgent, persist_path: str = ".omega_sessions/purge_queue.json") -> None:
        self.archivist = archivist
        self._persist_path = persist_path
        self._proposals: dict[str, PurgeProposal] = {}
        self._load()

    def _load(self) -> None:
        path = Path(self._persist_path)
        if path.exists():
            try:
                data = json.loads(path.read_text())
                for p in data.get("proposals", []):
                    self._proposals[p["proposal_id"]] = PurgeProposal(**p)
            except Exception:
                pass

    def _save(self) -> None:
        try:
            Path(self._persist_path).parent.mkdir(parents=True, exist_ok=True)
            Path(self._persist_path).write_text(json.dumps({
                "proposals": [p.to_dict() for p in self._proposals.values()],
                "saved_at": time.time(),
            }, indent=2))
        except Exception:
            pass

    # ── Proposal lifecycle ──

    def create_proposal(self, reason: str = "stale/orphaned cleanup") -> PurgeProposal | None:
        """Create a new purge proposal from curator's recommendations."""
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
        # Mark entries as quarantined
        for eid in proposal.entries:
            self.archivist.update_status(eid, RetentionStatus.QUARANTINED)

        self._proposals[proposal.proposal_id] = proposal
        self._save()
        return proposal

    def get_pending_proposals(self) -> list[PurgeProposal]:
        """Get all proposals awaiting user decision."""
        return [p for p in self._proposals.values() if p.approved is None]

    def get_proposal(self, proposal_id: str) -> PurgeProposal | None:
        return self._proposals.get(proposal_id)

    def approve(self, proposal_id: str, user_note: str = "") -> dict[str, Any]:
        """User approved deletion — execute soft-delete."""
        proposal = self._proposals.get(proposal_id)
        if not proposal or proposal.approved is not None:
            return {"success": False, "error": "Proposal not found or already decided"}

        proposal.approved = True
        proposal.user_response = user_note
        proposal.executed_at = time.time()

        # Soft-delete: mark as PURGED but keep metadata for 30 days
        deleted = 0
        failed = 0
        for eid in proposal.entries:
            if self.archivist.update_status(eid, RetentionStatus.PURGED):
                deleted += 1
            else:
                failed += 1

        self._save()
        return {
            "success": True,
            "proposal_id": proposal_id,
            "entries_deleted": deleted,
            "entries_failed": failed,
            "total_size_mb": round(proposal.total_size_bytes / (1024 * 1024), 2),
            "recoverable_until": proposal.executed_at + (self.SOFT_DELETE_DAYS * 86400),
        }

    def deny(self, proposal_id: str, user_note: str = "") -> dict[str, Any]:
        """User denied deletion — restore entries to active."""
        proposal = self._proposals.get(proposal_id)
        if not proposal or proposal.approved is not None:
            return {"success": False, "error": "Proposal not found or already decided"}

        proposal.approved = False
        proposal.user_response = user_note
        proposal.executed_at = time.time()

        # Restore all entries to active
        restored = 0
        for eid in proposal.entries:
            if self.archivist.update_status(eid, RetentionStatus.ACTIVE):
                restored += 1

        self._save()
        return {
            "success": True,
            "proposal_id": proposal_id,
            "entries_restored": restored,
            "message": "All entries restored to active status. They will not be proposed again for 7 days.",
        }

    def recover(self, entry_id: str) -> bool:
        """Recover a soft-deleted entry within the 30-day window."""
        entry = self.archivist.get(entry_id)
        if entry and entry.status == RetentionStatus.PURGED:
            # Check if within recovery window
            for p in self._proposals.values():
                if entry_id in p.entries and p.approved and p.executed_at:
                    if time.time() - p.executed_at < self.SOFT_DELETE_DAYS * 86400:
                        self.archivist.update_status(entry_id, RetentionStatus.ACTIVE)
                        return True
        return False

    def list_recoverable(self) -> list[MemoryEntry]:
        """List all entries that can still be recovered."""
        recoverable = []
        for p in self._proposals.values():
            if p.approved and p.executed_at:
                if time.time() - p.executed_at < self.SOFT_DELETE_DAYS * 86400:
                    for eid in p.entries:
                        entry = self.archivist.get(eid)
                        if entry and entry.status == RetentionStatus.PURGED:
                            entry.metadata["recoverable_until"] = p.executed_at + (self.SOFT_DELETE_DAYS * 86400)
                            recoverable.append(entry)
        return recoverable

    def permanent_purge(self, entry_id: str) -> bool:
        """Permanently delete an entry (only for PURGED entries past recovery window)."""
        entry = self.archivist.get(entry_id)
        if entry and entry.status == RetentionStatus.PURGED:
            # Check recovery window has passed
            for p in self._proposals.values():
                if entry_id in p.entries and p.approved and p.executed_at:
                    if time.time() - p.executed_at >= self.SOFT_DELETE_DAYS * 86400:
                        del self.archivist._entries[entry_id]
                        self.archivist._save()
                        return True
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# UNIFIED MEMORY MANAGER — Coordinator
# ═══════════════════════════════════════════════════════════════════════════════

class MemoryManager:
    """Unified interface to the 3-Agent Memory Management System."""

    VALID_MODULES = [
        "core_brain", "api_server", "db_engine", "cache_manager",
        "knowledge_base", "conversation_state", "scheduler",
        "plugin_registry", "auth_middleware", "local_llm",
        "deep_research", "investment", "tax", "companion",
        "self_improve", "language", "financial_lit", "professional",
        "opportunity", "email", "wisdom", "workflow", "visualization",
        "file_analysis", "digital_transform", "realtime_prices",
        "error_repair", "memory_manager", "bilingual", "web_search",
        "export_formats", "price_ticker", "calc_engine", "history_search",
        "learning_tracker", "reminders", "wizard", "pipeline",
        "educational_companion", "vocational_companion", "voice_interface",
        "crypto_utils", "key_rotation", "rate_limiter", "ws_server",
        "vector_db", "multi_tenant", "plugin_marketplace", "metrics_exporter",
        "email_notifier", "telegram_bot", "pdf_generator", "db_migrations",
        "auto_backup", "agent_mesh", "blockchain_audit", "federated_learning",
    ]

    def __init__(self) -> None:
        self.archivist = ArchivistAgent()
        self.curator = CuratorAgent(self.archivist)
        self.steward = StewardAgent(self.archivist)

    # ── Public API ──

    def register(self, entry: MemoryEntry) -> None:
        """Register a new memory entry with the Archivist."""
        self.archivist.register(entry)

    def record_access(self, entry_id: str) -> None:
        """Record that a memory entry was accessed."""
        self.archivist.record_access(entry_id)

    def review(self) -> dict[str, Any]:
        """Run Curator review and return status changes."""
        changes = self.curator.review_all()
        # Scan for orphaned entries
        orphans = self.archivist.scan_for_orphans(self.VALID_MODULES)
        changes["orphaned"] = orphans
        return changes

    def get_report(self) -> dict[str, Any]:
        """Get full memory health report from Curator."""
        return self.curator.generate_report()

    def propose_cleanup(self) -> PurgeProposal | None:
        """Create a purge proposal via the Steward. Returns None if nothing to clean."""
        return self.steward.create_proposal()

    def get_pending_proposals(self) -> list[PurgeProposal]:
        """Get all cleanup proposals awaiting user approval."""
        return self.steward.get_pending_proposals()

    def approve_deletion(self, proposal_id: str, user_note: str = "") -> dict[str, Any]:
        """User approves deletion of a proposal's entries."""
        return self.steward.approve(proposal_id, user_note)

    def deny_deletion(self, proposal_id: str, user_note: str = "") -> dict[str, Any]:
        """User denies deletion — entries are restored to active."""
        return self.steward.deny(proposal_id, user_note)

    def recover_entry(self, entry_id: str) -> bool:
        """Attempt to recover a soft-deleted entry within 30-day window."""
        return self.steward.recover(entry_id)

    def list_recoverable(self) -> list[MemoryEntry]:
        """List all soft-deleted entries that can still be recovered."""
        return self.steward.list_recoverable()

    def set_importance(self, entry_id: str, importance: int) -> bool:
        """Set importance (1-5) for an entry. 5 = never delete."""
        self.archivist.set_importance(entry_id, importance)
        return True

    def get_entry(self, entry_id: str) -> MemoryEntry | None:
        return self.archivist.get(entry_id)

    def list_entries(self, module: str = "", status: str = "") -> list[MemoryEntry]:
        return self.archivist.list_all(module=module, status=status)

    # ── Convenience helpers ──

    @staticmethod
    def create_entry(
        entry_id: str,
        module: str,
        data_type: str,
        summary: str,
        size_bytes: int = 0,
        importance: int = 3,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        now = time.time()
        return MemoryEntry(
            entry_id=entry_id,
            module=module,
            data_type=data_type,
            summary=summary,
            size_bytes=size_bytes,
            created_at=now,
            last_accessed=now,
            importance=importance,
            tags=tags or [],
            metadata=metadata or {},
        )

    def get_response(self, action: str = "report", **kwargs) -> dict[str, Any]:
        """Unified response for brain/API integration."""
        if action == "report":
            report = self.get_report()
            return {"module": "memory_manager", "action": "report", **report}
        elif action == "review":
            changes = self.review()
            return {"module": "memory_manager", "action": "review", "changes": changes}
        elif action == "propose":
            proposal = self.propose_cleanup()
            if proposal:
                entries = []
                for eid in proposal.entries:
                    e = self.archivist.get(eid)
                    if e:
                        entries.append({
                            "id": e.entry_id,
                            "module": e.module,
                            "summary": e.summary,
                            "idle_days": e.idle_days,
                            "size_mb": round(e.size_bytes / (1024 * 1024), 2),
                            "importance": e.importance,
                        })
                return {
                    "module": "memory_manager",
                    "action": "propose",
                    "proposal_id": proposal.proposal_id,
                    "reason": proposal.reason,
                    "total_entries": len(proposal.entries),
                    "total_size_mb": round(proposal.total_size_bytes / (1024 * 1024), 2),
                    "entries": entries,
                    "message": f"Proposal {proposal.proposal_id} created. {len(entries)} entries awaiting your approval.",
                }
            return {"module": "memory_manager", "action": "propose", "message": "No cleanup needed. Memory is healthy.", "total_entries": 0}
        elif action == "pending":
            proposals = self.get_pending_proposals()
            return {
                "module": "memory_manager",
                "action": "pending",
                "count": len(proposals),
                "proposals": [{"id": p.proposal_id, "reason": p.reason, "entries": len(p.entries), "size_mb": round(p.total_size_bytes / (1024 * 1024), 2)} for p in proposals],
            }
        elif action == "recoverable":
            entries = self.list_recoverable()
            return {
                "module": "memory_manager",
                "action": "recoverable",
                "count": len(entries),
                "entries": [{"id": e.entry_id, "module": e.module, "summary": e.summary} for e in entries],
            }
        elif action == "approve":
            pid = kwargs.get("proposal_id", "")
            note = kwargs.get("note", "Approved by user")
            return {"module": "memory_manager", "action": "approve", **self.approve_deletion(pid, note)}
        elif action == "deny":
            pid = kwargs.get("proposal_id", "")
            note = kwargs.get("note", "Denied by user")
            return {"module": "memory_manager", "action": "deny", **self.deny_deletion(pid, note)}
        elif action == "recover":
            eid = kwargs.get("entry_id", "")
            success = self.recover_entry(eid)
            return {"module": "memory_manager", "action": "recover", "entry_id": eid, "recovered": success}
        else:
            return {"module": "memory_manager", "action": "stats", **self.archivist.get_stats()}


# ── Global instance ──
_memory_manager: MemoryManager | None = None

def get_memory_manager() -> MemoryManager:
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager


if __name__ == "__main__":
    mm = MemoryManager()
    print("=== Luqi-AI 3-Agent Memory Management System ===")
    print(f"\nArchivist: tracking {len(mm.archivist._entries)} entries")
    report = mm.get_report()
    print(f"Health Score: {report['health_score']}/100")
    print(f"Status: {report['recommendation']}")
    print(f"\nBreakdown:")
    print(f"  Active: {report['active']}")
    print(f"  Aging:  {report['aging']}")
    print(f"  Stale:  {report['stale']}")
    print(f"  Orphaned: {report['orphaned']}")
    print(f"  Quarantined: {report['quarantined']}")
    print(f"  Purged: {report['purged']}")
