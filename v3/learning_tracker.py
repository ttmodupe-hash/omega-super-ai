"""Omega AI v3 — Financial Literacy Learning Tracker
Tracks progress through 36 lessons (12 topics x 3 levels).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


# 12 topics x 3 levels = 36 lessons
_TOPICS = [
    "budgeting", "saving", "investing", "debt", "credit",
    "crypto", "scams", "retirement", "insurance", "tax",
    "entrepreneurship", "banking",
]
_LEVELS = ["beginner", "intermediate", "advanced"]

_TOPIC_MAP: Dict[str, str] = {
    "budgeting": "budgeting", "saving": "saving", "investing": "investing",
    "debt": "debt_management", "credit": "credit_scores", "crypto": "crypto",
    "scams": "scam_protection", "retirement": "retirement", "insurance": "insurance",
    "tax": "tax_basics", "entrepreneurship": "entrepreneurship", "banking": "banking",
}


class LearningTracker:
    """Track progress through financial literacy lessons."""

    def __init__(self) -> None:
        self._file = Path.home() / ".omega_ai" / "learning_progress.json"
        self._file.parent.mkdir(parents=True, exist_ok=True)
        self._progress: Dict[str, str] = {}  # topic:level -> completed ISO timestamp
        self._load()

    def _load(self) -> None:
        if self._file.exists():
            try:
                self._progress = json.loads(self._file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._progress = {}

    def _save(self) -> None:
        self._file.write_text(json.dumps(self._progress, indent=2), encoding="utf-8")

    def _key(self, topic: str, level: str) -> str:
        return f"{topic}:{level}"

    def get_progress(self) -> dict[str, Any]:
        """Return overall progress stats."""
        completed = sum(1 for k in self._progress if k.split(":")[0] in _TOPICS)
        total = len(_TOPICS) * len(_LEVELS)
        by_topic: Dict[str, dict] = {}
        for topic in _TOPICS:
            topic_completed = sum(1 for level in _LEVELS if self._key(topic, level) in self._progress)
            by_topic[topic] = {
                "completed": topic_completed,
                "total": len(_LEVELS),
                "remaining": len(_LEVELS) - topic_completed,
            }
        return {
            "completed": completed,
            "total": total,
            "percentage": round((completed / total) * 100, 1) if total else 0,
            "by_topic": by_topic,
        }

    def mark_completed(self, topic: str, level: str) -> None:
        """Mark a lesson as completed."""
        self._progress[self._key(topic, level)] = datetime.now(timezone.utc).isoformat()
        self._save()

    def get_next_lesson(self) -> dict[str, str] | None:
        """Find the first incomplete lesson."""
        for topic in _TOPICS:
            for level in _LEVELS:
                if self._key(topic, level) not in self._progress:
                    return {"topic": topic, "level": level}
        return None

    def get_lesson_content(self, topic: str, level: str) -> str:
        """Fetch lesson content from FinancialLiteracy."""
        try:
            from financial_literacy import FinancialLiteracy
            fl = FinancialLiteracy()
            mapped_topic = _TOPIC_MAP.get(topic, topic)
            return fl.lesson(mapped_topic, level)
        except Exception as e:
            return f"[Lesson] {topic} ({level}): See FinancialLiteracy module for details. ({e})"

    def format_progress(self) -> str:
        """Pretty ASCII progress bar."""
        p = self.get_progress()
        bar_width = 20
        filled = int(bar_width * p["percentage"] / 100)
        bar = "█" * filled + "░" * (bar_width - filled)
        lines = [
            f"📚 Financial Literacy Progress: {p['completed']}/{p['total']} lessons ({p['percentage']}%)",
            f"[{bar}]",
            "",
        ]
        for topic, stats in p["by_topic"].items():
            icon = "✅" if stats["remaining"] == 0 else "🔄" if stats["completed"] > 0 else "⬜"
            lines.append(f"  {icon} {topic.title():15} ({stats['completed']}/{stats['total']})")
        return "\n".join(lines)

    def reset_progress(self) -> None:
        """Clear all progress."""
        self._progress = {}
        self._save()