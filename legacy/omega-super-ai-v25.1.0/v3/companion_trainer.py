"""Omega AI v3 — Companion Trainer
Users can train Luqi-AI, provide feedback, and improve responses over time.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import get_memory_dir
from utils import colorize, Colors, current_timestamp


class CompanionTrainer:
    """Interactive training and feedback system for Luqi-AI."""

    def __init__(self) -> None:
        self._feedback_file = get_memory_dir() / "feedback.jsonl"
        self._knowledge_file = get_memory_dir() / "learned_knowledge.json"

    def enter_training_mode(self) -> None:
        """Interactive CLI training session."""
        print(colorize("\n╔══════════════════════════════════════════╗", Colors.CYAN))
        print(colorize("║     Luqi-AI Companion Training Mode      ║", Colors.CYAN))
        print(colorize("╚══════════════════════════════════════════╝", Colors.CYAN))
        print("Commands: rate <1-5>, fix <correction>, skip, status, export, quit\n")

        pending = self._get_pending_sessions()
        if not pending:
            print("No pending feedback sessions. Use this after getting responses.")
            return

        for session in pending:
            print(f"\nQuery: {colorize(session['query'], Colors.BOLD)}")
            print(f"Response: {session['response'][:300]}...")
            print(f"Module: {session.get('module', 'unknown')}")

            while True:
                cmd = input(colorize("\n[rate/fix/skip/status/export/quit] ", Colors.YELLOW)).strip().lower()
                if cmd.startswith("rate"):
                    try:
                        rating = int(cmd.split()[1])
                        self.record_feedback(session["query"], session["response"], rating, module=session.get("module", ""))
                        print(colorize(f"  ✓ Rated {rating}/5", Colors.GREEN))
                        break
                    except (IndexError, ValueError):
                        print("Usage: rate 4")
                elif cmd.startswith("fix"):
                    correction = cmd[4:].strip()
                    if correction:
                        self.record_feedback(session["query"], session["response"], 3, correction, session.get("module", ""))
                        print(colorize("  ✓ Correction recorded", Colors.GREEN))
                        break
                elif cmd == "skip":
                    break
                elif cmd == "status":
                    print(self.show_training_status())
                elif cmd == "export":
                    print(self.export_knowledge())
                elif cmd == "quit":
                    return

    def record_feedback(self, query: str, answer: str, rating: int, correction: str = "", module: str = "") -> None:
        """Log user feedback."""
        entry: dict[str, Any] = {
            "timestamp": current_timestamp(),
            "query": query,
            "answer_preview": answer[:300],
            "rating": rating,
            "correction": correction,
            "module": module,
        }
        with open(self._feedback_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def learn_from_feedback(self) -> str:
        """Process feedback and generate improvement report."""
        entries = self._get_all_feedback()
        if not entries:
            return "No feedback data available yet."

        ratings = [e["rating"] for e in entries]
        avg = sum(ratings) / len(ratings)
        corrections = [e for e in entries if e.get("correction")]

        by_module: dict[str, list[int]] = {}
        for e in entries:
            mod = e.get("module", "unknown")
            by_module.setdefault(mod, []).append(e["rating"])

        lines = ["## Training Analysis Report\n"]
        lines.append(f"Total feedback entries: {len(entries)}")
        lines.append(f"Average rating: {avg:.1f}/5")
        lines.append(f"Corrections submitted: {len(corrections)}")
        lines.append(f"\nBy Module:")
        for mod, rs in sorted(by_module.items(), key=lambda x: -sum(x[1])/len(x[1])):
            mod_avg = sum(rs) / len(rs)
            status = colorize("✓", Colors.GREEN) if mod_avg >= 4 else colorize("⚠", Colors.YELLOW) if mod_avg >= 3 else colorize("✗", Colors.RED)
            lines.append(f"  {status} {mod:<20} avg: {mod_avg:.1f}/5 ({len(rs)} ratings)")

        if corrections:
            lines.append(f"\nCommon corrections to address:")
            for c in corrections[-5:]:
                lines.append(f"  - {c['correction'][:80]}")

        return "\n".join(lines)

    def show_training_status(self) -> str:
        """Display training statistics."""
        entries = self._get_all_feedback()
        if not entries:
            return "No training data yet. Rate responses to build training data."

        ratings = [e["rating"] for e in entries]
        histogram = {i: ratings.count(i) for i in range(1, 6)}

        lines = ["## Training Status\n"]
        for star, count in histogram.items():
            bar = "█" * count
            lines.append(f"  {star}★: {bar} ({count})")
        lines.append(f"\nAverage: {sum(ratings)/len(ratings):.1f}/5 from {len(ratings)} ratings")
        return "\n".join(lines)

    def export_knowledge(self) -> str:
        """Export learned knowledge."""
        entries = self._get_all_feedback()
        corrections = [e for e in entries if e.get("correction") and e["rating"] >= 4]

        lines = ["# Luqi-AI Learned Knowledge Export\n"]
        lines.append(f"Generated: {current_timestamp()}")
        lines.append(f"Total corrections: {len(corrections)}\n")

        for e in corrections:
            lines.append(f"## Q: {e['query']}")
            lines.append(f"Correction: {e['correction']}")
            lines.append("")

        return "\n".join(lines)

    def get_feedback_history(self) -> list[dict[str, Any]]:
        """List all feedback entries."""
        return self._get_all_feedback()

    def _get_all_feedback(self) -> list[dict[str, Any]]:
        """Read all feedback entries."""
        results = []
        if self._feedback_file.exists():
            with open(self._feedback_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            results.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        return results

    def _get_pending_sessions(self) -> list[dict[str, Any]]:
        """Get sessions awaiting feedback."""
        mem_file = get_memory_dir() / "memory.json"
        if not mem_file.exists():
            return []
        try:
            import json
            data = json.loads(mem_file.read_text())
            return [d for d in data[-10:] if d.get("rating", 0) == 0]
        except Exception:
            return []


if __name__ == "__main__":
    ct = CompanionTrainer()
    ct.record_feedback("What is Bitcoin?", "Bitcoin is a digital currency.", 5, module="deep_research")
    ct.record_feedback("How to file tax?", "Contact SARS.", 3, "Add filing deadlines", "tax")
    print(ct.show_training_status())
    print("\n---\n", ct.learn_from_feedback())
