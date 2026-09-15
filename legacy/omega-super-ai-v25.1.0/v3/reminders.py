"""Omega AI v3 — Smart Reminders
Deadline and recurring reminder system with natural date parsing.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class ReminderManager:
    """Manage reminders with natural language date parsing."""

    def __init__(self) -> None:
        self._file = Path.home() / ".omega_ai" / "reminders.json"
        self._file.parent.mkdir(parents=True, exist_ok=True)

    def _read(self) -> list[dict]:
        if not self._file.exists():
            return []
        try:
            return json.loads(self._file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    def _write(self, reminders: list) -> None:
        self._file.write_text(json.dumps(reminders, indent=2), encoding="utf-8")

    def _parse_date(self, date_str: str) -> str:
        """Parse natural date to ISO."""
        d = date_str.lower().strip()
        today = datetime.now(timezone.utc)
        if d in ("today", "now"):
            return today.isoformat()[:10]
        if d == "tomorrow":
            return (today + timedelta(days=1)).isoformat()[:10]
        if d == "next week":
            return (today + timedelta(weeks=1)).isoformat()[:10]
        if d in ("next month", "in a month"):
            return (today + timedelta(days=30)).isoformat()[:10]
        # Try DD-MM-YYYY or YYYY-MM-DD
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(d, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return today.isoformat()[:10]

    def add(self, text: str, date_str: str = "", recurring: str = "") -> dict:
        """Add a reminder."""
        due = self._parse_date(date_str) if date_str else datetime.now(timezone.utc).isoformat()[:10]
        reminder = {
            "id": str(uuid.uuid4())[:8],
            "text": text,
            "created": datetime.now(timezone.utc).isoformat(),
            "due_date": due,
            "recurring": recurring,
            "completed": False,
            "snoozed_until": "",
        }
        reminders = self._read()
        reminders.append(reminder)
        self._write(reminders)
        return reminder

    def list(self, show_all: bool = False) -> list[dict]:
        """List reminders."""
        reminders = self._read()
        if not show_all:
            today = datetime.now(timezone.utc).isoformat()[:10]
            reminders = [r for r in reminders if not r.get("completed") and r.get("due_date", "") >= today]
        return reminders

    def check_due(self) -> list[dict]:
        """Return reminders due today or earlier."""
        today = datetime.now(timezone.utc).isoformat()[:10]
        return [r for r in self._read() if not r.get("completed") and r.get("due_date", "") <= today]

    def complete(self, reminder_id: str) -> bool:
        """Mark a reminder as completed."""
        reminders = self._read()
        for r in reminders:
            if r["id"] == reminder_id:
                r["completed"] = True
                # If recurring, schedule next
                if r.get("recurring"):
                    r["due_date"] = self._next_date(r["due_date"], r["recurring"])
                    r["completed"] = False
                self._write(reminders)
                return True
        return False

    def delete(self, reminder_id: str) -> bool:
        """Delete a reminder."""
        self._write([r for r in self._read() if r["id"] != reminder_id])
        return True

    def snooze(self, reminder_id: str, days: int = 1) -> dict | None:
        """Snooze a reminder."""
        reminders = self._read()
        for r in reminders:
            if r["id"] == reminder_id:
                new_date = (datetime.fromisoformat(r["due_date"]) + timedelta(days=days)).isoformat()[:10]
                r["due_date"] = new_date
                self._write(reminders)
                return r
        return None

    def _next_date(self, current: str, pattern: str) -> str:
        """Calculate next occurrence for recurring reminders."""
        dt = datetime.fromisoformat(current)
        p = pattern.lower()
        if p == "daily":
            return (dt + timedelta(days=1)).isoformat()[:10]
        if p == "weekly":
            return (dt + timedelta(weeks=1)).isoformat()[:10]
        if p == "monthly":
            return (dt + timedelta(days=30)).isoformat()[:10]
        if p == "yearly":
            return (dt + timedelta(days=365)).isoformat()[:10]
        # Try "every N days/weeks/months"
        m = re.match(r"every\s+(\d+)\s+(day|week|month)s?", p)
        if m:
            n, unit = int(m.group(1)), m.group(2)
            delta = {"day": timedelta(days=n), "week": timedelta(weeks=n), "month": timedelta(days=n*30)}
            return (dt + delta.get(unit, timedelta(days=1))).isoformat()[:10]
        return current

    def format_list(self, reminders: list[dict]) -> str:
        """Pretty-print reminder list."""
        if not reminders:
            return "No reminders."
        lines = ["📌 Reminders:", "─" * 40]
        today = datetime.now(timezone.utc).isoformat()[:10]
        for r in reminders:
            icon = "✅" if r.get("completed") else "⚠️" if r["due_date"] <= today else "○"
            rec = f" (↻ {r['recurring']})" if r.get("recurring") else ""
            lines.append(f"  {icon} [{r['id']}] {r['due_date']} — {r['text']}{rec}")
        return "\n".join(lines)