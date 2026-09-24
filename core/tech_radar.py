"""INNOV-1 — Technology Radar + daily research daemon for the Luqi-ai engine.

Founder's directive: "Luqi-ai must be a master of innovation and problem
solving — it must know the available technologies and share them with people
who are not aware of them, to solve their problems. And there must always be
an agent doing deep research daily, on how to improve itself, with upgrades
pushed to all users."

What this module is:
  1. TECHNOLOGY RADAR — a curated, sourced catalogue of real free/low-cost
     technologies, each mapped to the problem it solves. Users describe a
     problem in their own words; the radar matches deterministically (no LLM
     needed, no hallucination possible — every answer is a catalogue entry
     with its official source).
  2. DAILY RESEARCH JOURNAL — an env-gated daemon (LUQI_RESEARCH_DAEMON=1)
     that once per day digests world developments (science / technology /
     health) from World Pulse feeds into a dated, cited journal. The engine
     researches and PROPOSES; human founders decide and ship upgrades —
     self-code-changes stay behind the 30% human gate, by law.
  3. UPGRADE PUSH — already the platform's reality: repo commit → Railway
     redeploy → every user worldwide has the upgrade. No app store, no
     waiting. This module's /status surface reports that honestly.

Honesty law: catalogue entries are real technologies with official sources;
the journal stores only what feeds actually returned; a disabled or empty
journal says so plainly.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from collections import deque
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/v1/innovation", tags=["innovation"])

_DATA = Path(__file__).resolve().parent / "data" / "tech_radar.json"
_RADAR = json.loads(_DATA.read_text(encoding="utf-8"))
TECHNOLOGIES: list[dict] = _RADAR["technologies"]
CATALOGUE_VERSION: str = _RADAR["version"]

HONESTY_NOTE = (
    "Every technology here is real and linked to its official source. Costs are "
    "stated honestly, including free tiers. The daily research journal contains "
    "only what live feeds actually returned — Luqi-ai never invents findings."
)

# ---------------------------------------------------------------------------
# Daily research journal (per-process, bounded, honestly labelled)
# ---------------------------------------------------------------------------
JOURNAL_MAX = 30  # keep 30 days
_journal: deque = deque(maxlen=JOURNAL_MAX)
_daemon_started = False


def _journal_append(entry: dict) -> None:
    _journal.appendleft(entry)


def _daemon_state() -> str:
    if _daemon_started:
        return "enabled"
    return "disabled (set LUQI_RESEARCH_DAEMON=1 and redeploy to activate)"


def build_daily_digest() -> dict | None:
    """One day of world developments worth knowing, cited from World Pulse.

    Returns None when no feed produced anything — the journal records
    reality or nothing, never a fabricated digest.
    """
    from . import news_pulse  # lazy import: no module-level cycle

    topics = {}
    for topic in ("science", "technology", "health"):
        payload = news_pulse._gather_topic(topic)
        if payload["count"] > 0:
            topics[topic] = {
                "headlines": payload["items"][:3],
                "feeds_ok": payload["feeds_ok"],
                "feeds_failed": payload["feeds_failed"],
            }
    if not topics:
        return None
    return {
        "date": time.strftime("%Y-%m-%d", time.gmtime()),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "kind": "daily-research-digest",
        "topics": topics,
        "note": (
            "Surfaced by the daily research daemon from cited live feeds. "
            "Engine upgrades ship through the human-gated pipeline: research "
            "proposes, founders decide, Railway redeploy delivers to all users."
        ),
    }


async def run_daily_research_daemon(interval_s: int = 86400) -> None:
    """Runs one digest at boot, then daily. Fail-closed per cycle: a failed
    cycle logs and waits for tomorrow — it never writes an empty entry."""
    global _daemon_started
    _daemon_started = True
    while True:
        try:
            entry = build_daily_digest()
            if entry:
                _journal_append(entry)
                print(f"[INNOV] Daily research digest recorded for {entry['date']}.")
            else:
                print("[INNOV] Daily digest skipped: no feeds produced items today.")
        except Exception as e:  # noqa: BLE001 — the journal must never crash the engine
            print(f"[INNOV] Research digest failed (non-fatal): {e}")
        await asyncio.sleep(interval_s)


# ---------------------------------------------------------------------------
# Deterministic problem → technology matching (no LLM, no hallucination)
# ---------------------------------------------------------------------------
def _haystack(t: dict) -> str:
    return " ".join([
        t["name"], t["category"], t["problem"], t["description"],
        " ".join(t.get("platforms", [])),
    ]).lower()


def solve(problem: str, limit: int = 5) -> list[dict]:
    """Keyword-overlap scoring over the catalogue. Transparent and testable:
    every returned match is a real catalogue entry, score included."""
    words = {w.strip(".,!?;:\"'()") for w in problem.lower().split()}
    words = {w for w in words if len(w) > 2}
    if not words:
        return []
    scored = []
    for t in TECHNOLOGIES:
        hay = _haystack(t)
        hits = sum(1 for w in words if w in hay)
        # a word matching the problem statement itself weighs double
        hits += sum(1 for w in words if w in t["problem"].lower())
        if hits > 0:
            scored.append((hits, t))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"score": s, "technology": t} for s, t in scored[:limit]]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.get("/technologies")
def list_technologies(
    category: str | None = Query(None, description="Filter by category"),
    q: str | None = Query(None, description="Free-text filter"),
) -> dict:
    items = TECHNOLOGIES
    if category:
        items = [t for t in items if t["category"] == category.strip().lower()]
    if q:
        needle = q.strip().lower()
        items = [t for t in items if needle in _haystack(t)]
    return {
        "version": CATALOGUE_VERSION,
        "updated": _RADAR["updated"],
        "count": len(items),
        "categories": _RADAR["categories"],
        "technologies": items,
        "honesty": HONESTY_NOTE,
    }


@router.get("/solve")
def solve_problem(
    problem: str = Query(..., min_length=3, description="Describe the problem in your own words"),
    limit: int = Query(5, ge=1, le=18),
) -> dict:
    """'I have no data but need work' → SAYouth.mobi, and so on. Deterministic
    matching over a sourced catalogue — answers are retrieved, never invented."""
    matches = solve(problem, limit=limit)
    body = {
        "problem": problem,
        "matches": matches,
        "count": len(matches),
        "honesty": HONESTY_NOTE,
    }
    if not matches:
        body["message"] = (
            "No catalogue technology matches that yet — try simpler words, or ask "
            "Luqi-ai in chat for deeper help. The radar grows daily."
        )
    return body


@router.get("/journal")
def research_journal(limit: int = Query(7, ge=1, le=30)) -> dict:
    """The daily research record. Honest when empty, honest when the daemon
    is off — a learning platform that fakes its own research is worthless."""
    entries = list(_journal)[:limit]
    return {
        "daemon": _daemon_state(),
        "entries_available": len(_journal),
        "entries": entries,
        "storage": "per-process, newest 30 days (honest free-tier design)",
        "honesty": HONESTY_NOTE,
    }


@router.get("/status")
def innovation_status() -> dict:
    return {
        "catalogue_version": CATALOGUE_VERSION,
        "catalogue_updated": _RADAR["updated"],
        "technologies": len(TECHNOLOGIES),
        "categories": _RADAR["categories"],
        "research_daemon": _daemon_state(),
        "journal_entries": len(_journal),
        "upgrade_pipeline": (
            "repo commit → Railway redeploy → every user worldwide, instantly. "
            "Research proposes; the 30% human gate decides what ships."
        ),
        "honesty": HONESTY_NOTE,
    }
