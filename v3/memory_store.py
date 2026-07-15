"""Omega AI v3 — Persistent Memory Store
Thread-safe JSON storage for interactions, feedback, and learning.
"""
from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import get_memory_dir
from utils import safe_json_loads, current_timestamp


class MemoryStore:
    """Thread-safe persistent memory using JSON file storage."""

    def __init__(self) -> None:
        self._mem_dir = get_memory_dir()
        self._memory_file = self._mem_dir / "memory.json"
        self._feedback_file = self._mem_dir / "feedback.jsonl"
        self._lock = threading.Lock()
        self._ensure_files()

    def _ensure_files(self) -> None:
        """Create storage files if they don't exist."""
        if not self._memory_file.exists():
            self._memory_file.write_text("[]", encoding="utf-8")
        if not self._feedback_file.exists():
            self._feedback_file.write_text("", encoding="utf-8")

    def save_interaction(self, query: str, response: str, module: str = "general",
                         rating: int = 0, feedback: str = "", sources: list | None = None) -> None:
        """Save an interaction to memory."""
        entry: dict[str, Any] = {
            "timestamp": current_timestamp(),
            "query": query,
            "response_preview": response[:500],
            "module": module,
            "rating": rating,
            "feedback": feedback,
            "sources": sources or [],
        }
        with self._lock:
            data = self._load_memory()
            data.append(entry)
            if len(data) > 1000:
                data = data[-1000:]
            self._save_memory(data)

    def get_history(self, limit: int = 50) -> list[dict]:
        """Get recent interaction history."""
        data = self._load_memory()
        return data[-limit:]

    def get_stats(self) -> dict[str, Any]:
        """Get usage statistics."""
        data = self._load_memory()
        if not data:
            return {"total": 0, "modules": {}, "avg_rating": 0, "period": "N/A"}

        modules: dict[str, int] = {}
        ratings: list[int] = []
        for entry in data:
            mod = entry.get("module", "unknown")
            modules[mod] = modules.get(mod, 0) + 1
            if entry.get("rating"):
                ratings.append(entry["rating"])

        return {
            "total": len(data),
            "modules": modules,
            "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0,
            "period": f"{data[0].get('timestamp', 'N/A')[:10]} to {data[-1].get('timestamp', 'N/A')[:10]}",
        }

    def search_memory(self, query: str) -> list[dict]:
        """Simple keyword search through past interactions."""
        data = self._load_memory()
        keywords = query.lower().split()
        results = []
        for entry in data:
            text = f"{entry.get('query', '')} {entry.get('response_preview', '')}".lower()
            if any(kw in text for kw in keywords):
                results.append(entry)
        return results[-20:]

    def record_feedback(self, query: str, answer: str, rating: int, correction: str = "", module: str = "") -> None:
        """Record user feedback as JSONL."""
        entry: dict[str, Any] = {
            "timestamp": current_timestamp(),
            "query": query,
            "answer_preview": answer[:300],
            "rating": rating,
            "correction": correction,
            "module": module,
        }
        with self._lock:
            with open(self._feedback_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")

    def get_feedback_history(self) -> list[dict]:
        """Read all feedback entries."""
        results = []
        if self._feedback_file.exists():
            with open(self._feedback_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        results.append(json.loads(line))
        return results

    def _load_memory(self) -> list[dict]:
        """Load memory file."""
        try:
            text = self._memory_file.read_text(encoding="utf-8")
            return safe_json_loads(text) if text.strip() else []
        except Exception:
            return []

    def _save_memory(self, data: list[dict]) -> None:
        """Atomically save memory file."""
        tmp = self._memory_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self._memory_file)


if __name__ == "__main__":
    store = MemoryStore()
    store.save_interaction("What is Bitcoin?", "Bitcoin is a digital currency...", "deep_research", rating=5)
    store.save_interaction("How do I pay tax in SA?", "SARS requires...", "tax", rating=4)
    print("Stats:", store.get_stats())
    print("Search 'bitcoin':", len(store.search_memory("bitcoin")))
