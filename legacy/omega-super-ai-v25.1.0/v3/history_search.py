"""Omega AI v3 — Conversation History Manager
Search, list, filter, and clear conversation history.
"""
from __future__ import annotations

import fnmatch
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class HistoryManager:
    """Manage conversation history with full-text search."""

    def __init__(self) -> None:
        self._mem_dir = Path.home() / ".omega_ai"

    def _read_store(self) -> list[dict]:
        """Read all interactions from memory.json."""
        mem_file = self._mem_dir / "memory.json"
        if not mem_file.exists():
            return []
        try:
            data = json.loads(mem_file.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Full-text search across query + response text."""
        entries = self._read_store()
        query_lower = query.lower()
        scored = []
        for entry in entries:
            text = f"{entry.get('query', '')} {entry.get('response_preview', entry.get('response', ''))}".lower()
            score = 0
            if query_lower in text:
                score += 10
            for word in query_lower.split():
                if word in text:
                    score += 2
            if score > 0:
                scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:limit]]

    def list_recent(self, limit: int = 20) -> list[dict]:
        """List most recent conversations."""
        entries = self._read_store()
        return sorted(entries, key=lambda e: e.get("timestamp", ""), reverse=True)[:limit]

    def get_by_module(self, module: str, limit: int = 10) -> list[dict]:
        """Filter by module name."""
        entries = self._read_store()
        filtered = [e for e in entries if e.get("module") == module or e.get("category") == module]
        return filtered[:limit]

    def get_by_date_range(self, start: str, end: str) -> list[dict]:
        """Filter by ISO date range."""
        entries = self._read_store()
        return [e for e in entries if start <= e.get("timestamp", "")[:10] <= end]

    def clear_all(self) -> bool:
        """Clear all conversation history."""
        mem_file = self._mem_dir / "memory.json"
        if mem_file.exists():
            mem_file.write_text("[]", encoding="utf-8")
        return True

    def format_results(self, results: list[dict]) -> str:
        """Pretty-print search results."""
        if not results:
            return "No results found."
        lines = [f"Found {len(results)} conversation(s):\n"]
        for i, r in enumerate(results, 1):
            ts = r.get("timestamp", "")[:16].replace("T", " ")
            mod = r.get("module", r.get("category", "general"))
            q = r.get("query", "")[:60]
            resp = r.get("response_preview", r.get("response", ""))[:80]
            lines.append(f"  {i}. [{mod}] {ts}")
            lines.append(f"     Q: {q}")
            lines.append(f"     R: {resp}...\n")
        return "\n".join(lines)

    def stats(self) -> dict[str, Any]:
        """Return usage statistics."""
        entries = self._read_store()
        if not entries:
            return {"total": 0, "by_module": {}, "by_date": {}, "avg_rating": 0, "period": "N/A"}
        modules: dict[str, int] = {}
        dates: dict[str, int] = {}
        ratings = []
        for e in entries:
            mod = e.get("module", e.get("category", "unknown"))
            modules[mod] = modules.get(mod, 0) + 1
            date = e.get("timestamp", "")[:10]
            dates[date] = dates.get(date, 0) + 1
            if e.get("rating"):
                ratings.append(e["rating"])
        return {
            "total": len(entries),
            "by_module": modules,
            "by_date": dates,
            "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0,
            "period": f"{min(dates)} to {max(dates)}" if dates else "N/A",
        }