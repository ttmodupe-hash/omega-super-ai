"""orchestrator_prime.py — Master Orchestrator for Prometheus Prime.

Ties together MetaLearner, FeedbackLoop, PromptEvolution, and StrategicPlanner
into a single cohesive system with daily / weekly / continuous cycles.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any, Optional

import numpy as np

from .meta_learner import MetaLearner
from .feedback_loop import FeedbackLoop
from .prompt_evolution import PromptEvolution
from .strategic_planner import StrategicPlanner

logger = logging.getLogger("prometheus_prime.orchestrator")

DB_PATH_ENV = os.environ.get("PROMETHEUS_DB_PATH", "/mnt/agents/output/project/backend/data/prometheus_prime.db")


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH_ENV, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def _init_orchestrator_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS orchestrator_cycles (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_type      TEXT NOT NULL,
            cycle_data_json TEXT,
            started_at      REAL NOT NULL,
            completed_at    REAL,
            status          TEXT NOT NULL DEFAULT 'running'
        );

        CREATE TABLE IF NOT EXISTS learning_stats (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            total_interactions  INTEGER NOT NULL DEFAULT 0,
            total_conversations INTEGER NOT NULL DEFAULT 0,
            avg_quality         REAL NOT NULL DEFAULT 0.0,
            total_lessons       INTEGER NOT NULL DEFAULT 0,
            knowledge_entities  INTEGER NOT NULL DEFAULT 0,
            capabilities_count  INTEGER NOT NULL DEFAULT 0,
            last_updated        REAL NOT NULL DEFAULT (unixepoch())
        );
        """
    )
    conn.commit()


# ---------------------------------------------------------------------------
# PrometheusPrime
# ---------------------------------------------------------------------------


class PrometheusPrime:
    """Master orchestrator for the Prometheus Prime meta-learning engine.

    Initialises and coordinates four subsystems:

    * **MetaLearner** — recursive self-improvement from every interaction
    * **FeedbackLoop** — implicit + explicit feedback collection
    * **PromptEvolution** — genetic algorithm for system-prompt optimisation
    * **StrategicPlanner** — long-term goal setting and roadmap tracking

    Provides three operational rhythms:

    * ``continuous_learning()`` — lightweight post-conversation updates
    * ``daily_cycle()`` — daily analysis and adaptation
    * ``weekly_cycle()`` — deep review and strategic alignment
    """

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or DB_PATH_ENV
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)

        # Subsystems
        self.meta = MetaLearner(db_path=self._db_path)
        self.feedback = FeedbackLoop(db_path=self._db_path)
        self.evolution = PromptEvolution(db_path=self._db_path)
        self.planner = StrategicPlanner(db_path=self._db_path)

        # Orchestrator DB
        self._conn = _get_db()
        _init_orchestrator_tables(self._conn)
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="prometheus_")

        # Caches
        self._last_daily_cycle: float = 0.0
        self._last_weekly_cycle: float = 0.0
        self._status_cache: dict | None = None
        self._status_cache_time: float = 0.0

        logger.info("PrometheusPrime orchestrator initialised")

    # ------------------------------------------------------------------ #
    # 1. Daily cycle
    # ------------------------------------------------------------------ #

    def daily_cycle(self) -> dict:
        """Run the daily improvement cycle.

        Steps::

            1. Analyse feedback (implicit + explicit)
            2. Learn from recent conversations
            3. Evolve prompts for under-performing modes
            4. Update strategic goal progress
            5. Generate comprehensive report

        Returns the cycle report dict.
        """
        started_at = time.time()
        logger.info("=== DAILY CYCLE START ===")

        cycle_id = self._start_cycle("daily")
        report: dict[str, Any] = {"cycle_type": "daily", "started_at": datetime.utcnow().isoformat()}

        try:
            # --- Step 1: Feedback analysis ---------------------------------
            feedback_summary = self.feedback.get_feedback_summary(days=1)
            report["feedback_summary"] = feedback_summary
            logger.info("Feedback analysed — %d sessions, avg satisfaction=%.3f",
                        feedback_summary["total_sessions"],
                        feedback_summary.get("implicit_scores", {}).get("average", 0))

            # --- Step 2: Learn from conversations ---------------------------
            recent_sessions = self._get_recent_sessions(limit=50)
            lessons_total = 0
            knowledge_total = 0
            for session_id in recent_sessions:
                result = self.meta.learn_from_conversation(session_id)
                lessons_total += len(result.get("lessons_learned", []))
                knowledge_total += len(result.get("knowledge_extracted", []))

            report["learning"] = {
                "sessions_analysed": len(recent_sessions),
                "lessons_extracted": lessons_total,
                "knowledge_facts": knowledge_total,
            }
            logger.info("Learning complete — %d sessions, %d lessons, %d facts",
                        len(recent_sessions), lessons_total, knowledge_total)

            # --- Step 3: Prompt evolution ----------------------------------
            underperforming = self._identify_underperforming_modes()
            evolved: list[dict] = []
            for mode, score in underperforming:
                new_prompt = self.evolution.evolve_prompt(mode, generations=2)
                evolved.append({"mode": mode, "old_score": score, "prompt_length": len(new_prompt)})
                logger.info("Evolved prompt for '%s' (previous score: %.3f)", mode, score)

            report["prompt_evolution"] = {
                "modes_evaluated": len(underperforming),
                "modes_evolved": len(evolved),
                "details": evolved,
            }

            # --- Step 4: Strategic plan update -----------------------------
            goal_progress = self.planner.track_goal_progress()
            report["goal_progress"] = goal_progress
            logger.info("Strategic goals tracked — %d total, %d on track, %d behind",
                        goal_progress["summary"]["total"],
                        goal_progress["summary"]["on_track"],
                        goal_progress["summary"]["behind"])

            # --- Step 5: Report generation ---------------------------------
            improvement_report = self.meta.get_improvement_report()
            report["improvement_report"] = improvement_report[:2000]  # truncate for JSON

            # --- Update stats ----------------------------------------------
            self._update_learning_stats()

            self._last_daily_cycle = time.time()
            self._complete_cycle(cycle_id, "completed", report)

            logger.info("=== DAILY CYCLE COMPLETE in %.1fs ===", time.time() - started_at)

        except Exception as exc:
            logger.exception("Daily cycle failed: %s", exc)
            self._complete_cycle(cycle_id, "failed", {"error": str(exc)})
            report["status"] = "failed"
            report["error"] = str(exc)

        return report

    # ------------------------------------------------------------------ #
    # 2. Weekly cycle
    # ------------------------------------------------------------------ #

    def weekly_cycle(self) -> dict:
        """Run the full weekly improvement cycle.

        Extends the daily cycle with:

            * Deep failure-pattern analysis
            * Prompt evolution for ALL modes (not just underperforming)
            * Strategic plan review and refresh
            * Weekly action-plan generation
            * Comprehensive weekly report
        """
        started_at = time.time()
        logger.info("=== WEEKLY CYCLE START ===")

        cycle_id = self._start_cycle("weekly")
        report: dict[str, Any] = {"cycle_type": "weekly", "started_at": datetime.utcnow().isoformat()}

        try:
            # --- Step 1: Run full daily cycle -----------------------------
            daily_report = self.daily_cycle()
            report["daily_cycle"] = {k: v for k, v in daily_report.items() if k != "improvement_report"}

            # --- Step 2: Deep failure-pattern analysis ---------------------
            failure_patterns = self.feedback.identify_failure_patterns()
            report["failure_patterns"] = failure_patterns
            logger.info("Identified %d failure patterns", len(failure_patterns))

            # --- Step 3: Prompt evolution for ALL modes --------------------
            modes = ["chat", "research", "think", "mentor", "code"]
            all_evolved: list[dict] = []
            for mode in modes:
                try:
                    new_prompt = self.evolution.evolve_prompt(mode, generations=3)
                    all_evolved.append({"mode": mode, "prompt_length": len(new_prompt)})
                    logger.info("Weekly evolution complete for '%s'", mode)
                except Exception as mode_exc:
                    logger.warning("Evolution failed for '%s': %s", mode, mode_exc)
                    all_evolved.append({"mode": mode, "error": str(mode_exc)})

            report["prompt_evolution"] = {
                "modes_processed": len(modes),
                "results": all_evolved,
            }

            # --- Step 4: Strategic plan review -----------------------------
            market_analysis = self.planner.analyze_market_position()
            goals = self.planner.set_strategic_goals()
            roadmap = self.planner.create_roadmap()
            report["strategic_review"] = {
                "market_position_summary": market_analysis["position"],
                "goals_set": len(goals),
                "roadmap_items": roadmap.get("total_items", 0),
            }

            # --- Step 5: Weekly action plan --------------------------------
            weekly_plan = self.planner.generate_weekly_plan()
            report["weekly_plan"] = weekly_plan[:1500]

            # --- Step 6: Capability-gap report -----------------------------
            gaps = self.meta.discover_capability_gaps()
            report["capability_gaps"] = gaps

            self._last_weekly_cycle = time.time()
            self._complete_cycle(cycle_id, "completed", report)

            elapsed = time.time() - started_at
            logger.info("=== WEEKLY CYCLE COMPLETE in %.1fs ===", elapsed)
            report["elapsed_seconds"] = round(elapsed, 1)

        except Exception as exc:
            logger.exception("Weekly cycle failed: %s", exc)
            self._complete_cycle(cycle_id, "failed", {"error": str(exc)})
            report["status"] = "failed"
            report["error"] = str(exc)

        return report

    # ------------------------------------------------------------------ #
    # 3. Continuous learning (post-conversation)
    # ------------------------------------------------------------------ #

    def continuous_learning(
        self,
        session_id: str,
        query: str,
        response: str,
        mode: str = "chat",
        duration_ms: int = 0,
        user_feedback: float | None = None,
    ) -> dict:
        """Lightweight learning update after every conversation.

        This method is designed to be called synchronously (or in a
        background thread) immediately after a response is sent.  It:

            1. Records the interaction
            2. Extracts implicit feedback signals
            3. Learns from the conversation
            4. Updates the knowledge graph

        Returns a compact status dict.
        """
        try:
            # 1. Record interaction
            self.meta.record_interaction(
                session_id=session_id,
                query=query,
                response=response,
                mode=mode,
                duration_ms=duration_ms,
                user_feedback=user_feedback,
            )

            # 2. Collect implicit feedback
            implicit = self.feedback.collect_implicit_feedback(
                session_id=session_id,
                interaction_data={
                    "response_time_ms": duration_ms,
                    "query_length": len(query),
                    "response_length": len(response),
                },
            )

            # 3. Learn from conversation (lightweight — only if enough data)
            lessons = {"lessons_learned": [], "knowledge_extracted": []}
            # We do full learning only periodically to avoid overhead
            with self._lock:
                count_row = self._conn.execute(
                    "SELECT COUNT(*) as c FROM interactions WHERE session_id = ?",
                    (session_id,),
                ).fetchone()
            if count_row and count_row["c"] >= 3:
                lessons = self.meta.learn_from_conversation(session_id)

            # 4. Update satisfaction if explicit feedback provided
            if user_feedback is not None:
                self.feedback.collect_explicit_feedback(session_id, user_feedback * 5)

            return {
                "status": "ok",
                "session_id": session_id,
                "implicit_score": implicit.get("implicit_score"),
                "lessons": len(lessons["lessons_learned"]),
                "facts": len(lessons["knowledge_extracted"]),
            }

        except Exception as exc:
            logger.warning("Continuous learning error for %s: %s", session_id, exc)
            return {"status": "error", "session_id": session_id, "error": str(exc)}

    # ------------------------------------------------------------------ #
    # 4. System status
    # ------------------------------------------------------------------ #

    def get_status(self) -> dict:
        """Return overall system health and learning statistics.

        Result is cached for 30 seconds to avoid repeated DB queries.
        """
        now = time.time()
        if self._status_cache and (now - self._status_cache_time) < 30:
            return self._status_cache

        with self._lock:
            # Interaction stats
            total_interactions = self._conn.execute(
                "SELECT COUNT(*) as c FROM interactions"
            ).fetchone()["c"]

            total_conversations = self._conn.execute(
                "SELECT COUNT(DISTINCT session_id) as c FROM interactions"
            ).fetchone()["c"]

            avg_quality_row = self._conn.execute(
                "SELECT AVG(quality_score) as avg_q FROM interactions"
            ).fetchone()
            avg_quality = avg_quality_row["avg_q"] or 0.0

            # Capability scores
            cap_rows = self._conn.execute(
                "SELECT capability, score FROM capability_scores ORDER BY score DESC"
            ).fetchall()
            capabilities = {r["capability"]: round(r["score"], 3) for r in cap_rows}

            # Knowledge graph
            entity_count = self._conn.execute(
                "SELECT COUNT(DISTINCT entity) as c FROM knowledge_graph"
            ).fetchone()["c"]

            # Prompt evolution status
            prompt_modes = self._conn.execute(
                "SELECT DISTINCT mode FROM system_prompts WHERE is_active = 1"
            ).fetchall()

            # Cycle history
            last_cycles = self._conn.execute(
                "SELECT cycle_type, status, completed_at FROM orchestrator_cycles "
                "ORDER BY completed_at DESC LIMIT 5"
            ).fetchall()

        status = {
            "system": "Prometheus Prime",
            "version": "1.0.0",
            "status": "healthy",
            "learning_statistics": {
                "total_interactions": total_interactions,
                "total_conversations": total_conversations,
                "average_quality_score": round(avg_quality, 3),
                "knowledge_entities": entity_count,
                "capabilities_tracked": len(capabilities),
            },
            "capability_scores": capabilities,
            "active_prompt_modes": [r["mode"] for r in prompt_modes],
            "last_cycles": [
                {
                    "type": r["cycle_type"],
                    "status": r["status"],
                    "completed_at": datetime.utcfromtimestamp(r["completed_at"]).isoformat()
                    if r["completed_at"] else None,
                }
                for r in last_cycles
            ],
            "uptime_seconds": round(now - self._last_daily_cycle, 1) if self._last_daily_cycle else None,
            "timestamp": datetime.utcnow().isoformat(),
        }

        self._status_cache = status
        self._status_cache_time = now
        return status

    # ------------------------------------------------------------------ #
    # 5. Report generation
    # ------------------------------------------------------------------ #

    def get_report(self, report_type: str = "daily") -> str:
        """Generate various report types.

        Parameters
        ----------
        report_type:
            One of ``daily``, ``weekly``, ``monthly``, ``strategic``.
        """
        if report_type == "daily":
            return self.meta.get_improvement_report()

        if report_type == "weekly":
            parts: list[str] = [
                self.meta.get_improvement_report(),
                "\n\n## Failure Patterns\n",
            ]
            for pat in self.feedback.identify_failure_patterns():
                parts.append(f"- **{pat['pattern']}**: {pat['frequency']} occurrences")
                parts.append(f"  → Fix: {pat['suggested_fix']}")

            parts.extend(["\n## Weekly Plan\n", self.planner.generate_weekly_plan()])
            return "\n".join(parts)

        if report_type == "monthly":
            parts = [
                f"# Monthly Report — {datetime.utcnow().strftime('%B %Y')}",
                "",
                self.meta.get_improvement_report(),
                "",
                "## Strategic Goal Progress",
                json.dumps(self.planner.track_goal_progress(), indent=2, default=str),
                "",
                "## Capability Gaps",
                json.dumps(self.meta.discover_capability_gaps(), indent=2, default=str)[:2000],
            ]
            return "\n".join(parts)

        if report_type == "strategic":
            market = self.planner.analyze_market_position()
            progress = self.planner.track_goal_progress()
            gaps = self.meta.discover_capability_gaps()
            return (
                f"# Strategic Report\n\n"
                f"## Market Position\n{market['position']}\n\n"
                f"## Unique Value Proposition\n{market['unique_value_proposition']}\n\n"
                f"## Goals Progress\n{json.dumps(progress, indent=2, default=str)}\n\n"
                f"## Capability Gaps ({len(gaps)} identified)\n"
                + "\n".join(f"- {g['pattern']}" for g in gaps[:10])
            )

        return f"Unknown report type: {report_type}"

    # ------------------------------------------------------------------ #
    # 6. Async interface
    # ------------------------------------------------------------------ #

    async def daily_cycle_async(self) -> dict:
        """Async wrapper for ``daily_cycle`` (runs in thread pool)."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self.daily_cycle)

    async def weekly_cycle_async(self) -> dict:
        """Async wrapper for ``weekly_cycle`` (runs in thread pool)."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self.weekly_cycle)

    async def continuous_learning_async(
        self,
        session_id: str,
        query: str,
        response: str,
        mode: str = "chat",
        duration_ms: int = 0,
        user_feedback: float | None = None,
    ) -> dict:
        """Async wrapper for ``continuous_learning``."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor,
            self.continuous_learning,
            session_id, query, response, mode, duration_ms, user_feedback,
        )

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _get_recent_sessions(self, limit: int = 50) -> list[str]:
        """Return distinct session IDs from recent interactions."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT DISTINCT session_id FROM interactions ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [r["session_id"] for r in rows]

    def _identify_underperforming_modes(self, threshold: float = 0.5) -> list[tuple[str, float]]:
        """Return modes with average quality below *threshold*."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT mode, AVG(quality_score) as avg_q FROM interactions "
                "GROUP BY mode HAVING avg_q < ? ORDER BY avg_q ASC",
                (threshold,),
            ).fetchall()
        return [(r["mode"], r["avg_q"]) for r in rows]

    def _start_cycle(self, cycle_type: str) -> int:
        """Insert a cycle record and return its ID."""
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO orchestrator_cycles (cycle_type, started_at, status) VALUES (?, ?, 'running')",
                (cycle_type, time.time()),
            )
            self._conn.commit()
            return cur.lastrowid  # type: ignore[return-value]

    def _complete_cycle(self, cycle_id: int, status: str, data: dict) -> None:
        """Mark a cycle as completed/failed."""
        with self._lock:
            self._conn.execute(
                "UPDATE orchestrator_cycles SET status = ?, completed_at = ?, cycle_data_json = ? WHERE id = ?",
                (status, time.time(), json.dumps(data, default=str), cycle_id),
            )
            self._conn.commit()

    def _update_learning_stats(self) -> None:
        """Update the learning statistics snapshot."""
        with self._lock:
            total = self._conn.execute("SELECT COUNT(*) as c FROM interactions").fetchone()["c"]
            convs = self._conn.execute("SELECT COUNT(DISTINCT session_id) as c FROM interactions").fetchone()["c"]
            avg_q = self._conn.execute("SELECT AVG(quality_score) as avg_q FROM interactions").fetchone()["avg_q"] or 0.0
            lessons = self._conn.execute("SELECT COUNT(*) as c FROM conversations").fetchone()["c"]
            entities = self._conn.execute("SELECT COUNT(DISTINCT entity) as c FROM knowledge_graph").fetchone()["c"]
            caps = self._conn.execute("SELECT COUNT(*) as c FROM capability_scores").fetchone()["c"]

            self._conn.execute(
                """
                INSERT OR REPLACE INTO learning_stats
                    (id, total_interactions, total_conversations, avg_quality,
                     total_lessons, knowledge_entities, capabilities_count, last_updated)
                VALUES (
                    (SELECT id FROM learning_stats ORDER BY id DESC LIMIT 1),
                    ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (total, convs, avg_q, lessons, entities, caps, time.time()),
            )
            self._conn.commit()

    # ------------------------------------------------------------------ #
    # Cleanup
    # ------------------------------------------------------------------ #

    def close(self) -> None:
        """Shut down the orchestrator and all subsystems."""
        self._executor.shutdown(wait=True)
        self.meta.close()
        self.feedback.close()
        self.evolution.close()
        self.planner.close()
        self._conn.close()
        logger.info("PrometheusPrime shut down complete.")
