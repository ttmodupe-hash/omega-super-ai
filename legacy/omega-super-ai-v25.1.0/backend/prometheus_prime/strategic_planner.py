"""strategic_planner.py — Long-Term Strategic Planning for Prometheus Prime.

Analyses market position, sets SMART goals, creates prioritised roadmaps,
tracks progress, and generates weekly action plans.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from typing import Any

import numpy as np

logger = logging.getLogger("prometheus_prime.strategic_planner")

DB_PATH_ENV = os.environ.get("PROMETHEUS_DB_PATH", "/mnt/agents/output/project/backend/data/prometheus_prime.db")


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH_ENV, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def _init_strategic_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS strategic_goals (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            title           TEXT NOT NULL,
            description     TEXT,
            metric          TEXT,
            target_value    REAL,
            current_value   REAL NOT NULL DEFAULT 0.0,
            deadline        REAL NOT NULL,
            status          TEXT NOT NULL DEFAULT 'active',
            priority        INTEGER NOT NULL DEFAULT 3,
            created_at      REAL NOT NULL DEFAULT (unixepoch()),
            updated_at      REAL NOT NULL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS roadmap_items (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_id         INTEGER REFERENCES strategic_goals(id),
            title           TEXT NOT NULL,
            description     TEXT,
            impact          INTEGER NOT NULL DEFAULT 3,
            effort          INTEGER NOT NULL DEFAULT 3,
            status          TEXT NOT NULL DEFAULT 'todo',
            milestone_date  REAL,
            created_at      REAL NOT NULL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS market_analysis (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_json   TEXT NOT NULL,
            created_at      REAL NOT NULL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS weekly_plans (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start      TEXT NOT NULL UNIQUE,
            plan_text       TEXT NOT NULL,
            goals_json      TEXT,
            created_at      REAL NOT NULL DEFAULT (unixepoch())
        );
        """
    )
    conn.commit()


# ---------------------------------------------------------------------------
# StrategicPlanner
# ---------------------------------------------------------------------------


class StrategicPlanner:
    """Long-term strategic planning for Luqi AI.

    Provides:
    * market-position analysis
    * SMART goal setting
    * prioritised roadmap generation
    * goal-progress tracking
    * weekly action-plan generation
    """

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or DB_PATH_ENV
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._conn = _get_db()
        _init_strategic_tables(self._conn)
        self._lock = threading.RLock()
        logger.info("StrategicPlanner initialised")

    # ------------------------------------------------------------------ #
    # 1. Market-position analysis
    # ------------------------------------------------------------------ #

    def analyze_market_position(self) -> dict:
        """Analyse where Luqi AI stands relative to competitors.

        Returns::

            {
                position: str,
                competitors: [str, …],
                unique_value_proposition: str,
                moats: [str, …],
                threats: [str, …],
                opportunities: [str, …],
                timestamp: str
            }
        """
        # In a production system this would scrape competitor data, analyse
        # market-research APIs, etc.  Here we return a structured framework
        # that is updated by the meta-learner over time.

        analysis = {
            "position": "Emerging AI assistant with strong multilingual and cultural-localisation capabilities",
            "competitors": [
                "ChatGPT (OpenAI)",
                "Claude (Anthropic)",
                "Gemini (Google)",
                "Llama-based local deployments",
            ],
            "unique_value_proposition": (
                "Deep cultural fluency for South African and African markets, "
                "with 11 official languages, local context awareness, and "
                "reciprocal-learning (Prometheus Prime) that improves with every interaction."
            ),
            "moats": [
                "Proprietary meta-learning engine (Prometheus Prime) that self-improves",
                "Cultural and linguistic depth for African languages (isiZulu, isiXhosa, Afrikaans, etc.)",
                "On-device and edge-deployment capability for low-bandwidth environments",
                "Feedback-loop integration that continuously adapts to user needs",
            ],
            "threats": [
                "Well-funded competitors rapidly expanding multilingual support",
                "Open-source models closing the quality gap",
                "Regulatory uncertainty around AI in African markets",
                "Infrastructure limitations (electricity, bandwidth) in target markets",
            ],
            "opportunities": [
                "First-mover advantage in African-language AI assistants",
                "Enterprise demand for culturally-aware customer-service bots",
                "Education sector: multilingual tutoring and mentoring",
                "Government and NGO partnerships for digital inclusion",
                "Mobile-first deployment for feature-phone users",
            ],
            "timestamp": datetime.utcnow().isoformat(),
        }

        with self._lock:
            self._conn.execute(
                "INSERT INTO market_analysis (analysis_json, created_at) VALUES (?, ?)",
                (json.dumps(analysis), time.time()),
            )
            self._conn.commit()

        return analysis

    # ------------------------------------------------------------------ #
    # 2. SMART goal setting
    # ------------------------------------------------------------------ #

    def set_strategic_goals(self) -> list[dict]:
        """Set 90-day SMART goals based on the latest market analysis.

        SMART = Specific, Measurable, Achievable, Relevant, Time-bound.

        Returns the list of active goals.
        """
        now = time.time()
        deadline_90d = now + 90 * 86400

        goals = [
            {
                "title": "Achieve 95% user satisfaction on isiZulu responses",
                "description": "Improve accuracy, cultural relevance, and naturalness of isiZulu language generation.",
                "metric": "average_satisfaction_score_zulu",
                "target_value": 0.95,
                "current_value": 0.72,
                "priority": 1,
            },
            {
                "title": "Reduce average response latency to <1.5 seconds",
                "description": "Optimise inference pipeline, implement response caching, and enable streaming.",
                "metric": "avg_response_latency_ms",
                "target_value": 1500.0,
                "current_value": 3200.0,
                "priority": 1,
            },
            {
                "title": "Deploy self-improving prompt system across all 5 modes",
                "description": "Activate Prometheus Prime prompt evolution for chat, research, think, mentor, and code modes.",
                "metric": "modes_with_active_evolution",
                "target_value": 5.0,
                "current_value": 1.0,
                "priority": 2,
            },
            {
                "title": "Build knowledge graph with 10,000 verified entities",
                "description": "Extract and verify entities from conversations to populate the knowledge graph.",
                "metric": "knowledge_graph_entity_count",
                "target_value": 10000.0,
                "current_value": 1200.0,
                "priority": 2,
            },
            {
                "title": "Achieve 99.5% uptime for core inference API",
                "description": "Implement redundancy, health checks, and automated failover.",
                "metric": "api_uptime_percentage",
                "target_value": 99.5,
                "current_value": 97.8,
                "priority": 1,
            },
            {
                "title": "Expand supported languages to 15 African languages",
                "description": "Add support for Setswana, Sesotho, Tshivenda, Xitsonga, Siswati, isiNdebele, Sepedi, Khoisan, Amharic, Swahili.",
                "metric": "supported_language_count",
                "target_value": 15.0,
                "current_value": 5.0,
                "priority": 3,
            },
        ]

        with self._lock:
            for goal in goals:
                self._conn.execute(
                    """
                    INSERT OR IGNORE INTO strategic_goals
                        (title, description, metric, target_value, current_value, deadline, priority, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        goal["title"],
                        goal["description"],
                        goal["metric"],
                        goal["target_value"],
                        goal["current_value"],
                        deadline_90d,
                        goal["priority"],
                        now,
                        now,
                    ),
                )
            self._conn.commit()

        logger.info("Set %d strategic goals with 90-day horizon", len(goals))
        return goals

    # ------------------------------------------------------------------ #
    # 3. Roadmap creation
    # ------------------------------------------------------------------ #

    def create_roadmap(self) -> dict:
        """Turn goals into a prioritised development roadmap.

        Returns::

            {
                goals: [goal_with_items, …],
                priority_order: [goal_id, …],
                total_items: int,
                timeline_estimate_weeks: int
            }
        """
        with self._lock:
            goal_rows = self._conn.execute(
                "SELECT * FROM strategic_goals WHERE status = 'active' ORDER BY priority ASC, deadline ASC"
            ).fetchall()

        roadmap_goals: list[dict] = []
        all_items: list[dict] = []

        for goal in goal_rows:
            # Derive roadmap items from the goal
            items = self._goal_to_roadmap_items(goal)

            # RICE-style prioritisation: impact / effort
            for item in items:
                item["rice_score"] = round(item["impact"] / max(item["effort"], 1), 2)
                all_items.append(item)

            roadmap_goals.append({
                "goal_id": goal["id"],
                "title": goal["title"],
                "priority": goal["priority"],
                "items": items,
            })

        # Global priority order
        priority_order = sorted(
            roadmap_goals,
            key=lambda g: (g["priority"], -sum(it["rice_score"] for it in g["items"])),
        )

        total_items = sum(len(g["items"]) for g in roadmap_goals)
        timeline_weeks = max(1, total_items // 3)  # rough heuristic

        result = {
            "goals": roadmap_goals,
            "priority_order": [g["goal_id"] for g in priority_order],
            "total_items": total_items,
            "timeline_estimate_weeks": timeline_weeks,
            "generated_at": datetime.utcnow().isoformat(),
        }

        # Persist items
        with self._lock:
            for item in all_items:
                self._conn.execute(
                    """
                    INSERT OR IGNORE INTO roadmap_items
                        (goal_id, title, description, impact, effort, status, milestone_date, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item["goal_id"],
                        item["title"],
                        item["description"],
                        item["impact"],
                        item["effort"],
                        item["status"],
                        item.get("milestone_date"),
                        time.time(),
                    ),
                )
            self._conn.commit()

        return result

    def _goal_to_roadmap_items(self, goal: sqlite3.Row) -> list[dict]:
        """Break a strategic goal into concrete roadmap items."""
        title = goal["title"]
        items: list[dict] = []

        if "Zulu" in title or "language" in title.lower():
            items = [
                {"title": "Audit current isiZulu response quality", "description": "Run 100 test queries and score outputs", "impact": 5, "effort": 2, "status": "todo", "goal_id": goal["id"]},
                {"title": "Collect isiZulu training corpus", "description": "Partner with language institute for verified data", "impact": 5, "effort": 4, "status": "todo", "goal_id": goal["id"]},
                {"title": "Fine-tune model on isiZulu data", "description": "Run fine-tuning pipeline with cultural context", "impact": 5, "effort": 5, "status": "todo", "goal_id": goal["id"]},
                {"title": "Implement isiZulu quality gate", "description": "Add automated evaluation for Zulu outputs", "impact": 4, "effort": 3, "status": "todo", "goal_id": goal["id"]},
            ]
        elif "latency" in title.lower():
            items = [
                {"title": "Profile inference pipeline", "description": "Identify bottlenecks in model serving", "impact": 5, "effort": 2, "status": "todo", "goal_id": goal["id"]},
                {"title": "Implement response caching", "description": "Cache common queries with TTL", "impact": 4, "effort": 3, "status": "todo", "goal_id": goal["id"]},
                {"title": "Enable streaming responses", "description": "Stream tokens as they are generated", "impact": 4, "effort": 3, "status": "todo", "goal_id": goal["id"]},
                {"title": "Deploy edge inference nodes", "description": "Place inference in JHB, CPT, DBN", "impact": 5, "effort": 5, "status": "todo", "goal_id": goal["id"]},
            ]
        elif "prompt" in title.lower():
            items = [
                {"title": "Activate prompt evolution for research mode", "description": "Run genetic algorithm on research prompts", "impact": 4, "effort": 2, "status": "todo", "goal_id": goal["id"]},
                {"title": "Activate prompt evolution for think mode", "description": "Run genetic algorithm on think prompts", "impact": 4, "effort": 2, "status": "todo", "goal_id": goal["id"]},
                {"title": "Activate prompt evolution for mentor mode", "description": "Run genetic algorithm on mentor prompts", "impact": 4, "effort": 2, "status": "todo", "goal_id": goal["id"]},
                {"title": "Activate prompt evolution for code mode", "description": "Run genetic algorithm on code prompts", "impact": 4, "effort": 2, "status": "todo", "goal_id": goal["id"]},
                {"title": "Cross-mode prompt transfer learning", "description": "Transfer improvements across modes", "impact": 3, "effort": 4, "status": "todo", "goal_id": goal["id"]},
            ]
        elif "knowledge graph" in title.lower():
            items = [
                {"title": "Scale entity extraction pipeline", "description": "Process 1000 conversations/day", "impact": 4, "effort": 3, "status": "todo", "goal_id": goal["id"]},
                {"title": "Add entity verification layer", "description": "Cross-reference facts with trusted sources", "impact": 5, "effort": 4, "status": "todo", "goal_id": goal["id"]},
                {"title": "Build knowledge graph visualiser", "description": "Interactive dashboard for knowledge exploration", "impact": 3, "effort": 4, "status": "todo", "goal_id": goal["id"]},
                {"title": "Implement gap-driven learning", "description": "Auto-generate learning tasks from graph gaps", "impact": 5, "effort": 5, "status": "todo", "goal_id": goal["id"]},
            ]
        elif "uptime" in title.lower():
            items = [
                {"title": "Implement health-check endpoints", "description": "Deep health checks for all services", "impact": 5, "effort": 2, "status": "todo", "goal_id": goal["id"]},
                {"title": "Deploy redundant inference workers", "description": "Minimum 3 replicas across zones", "impact": 5, "effort": 4, "status": "todo", "goal_id": goal["id"]},
                {"title": "Set up automated failover", "description": "DNS + load-balancer health-based routing", "impact": 5, "effort": 3, "status": "todo", "goal_id": goal["id"]},
                {"title": "Create incident response runbook", "description": "Documented procedures for common failures", "impact": 3, "effort": 2, "status": "todo", "goal_id": goal["id"]},
            ]
        else:
            items = [
                {"title": f"Research: {title}", "description": "Conduct feasibility analysis", "impact": 3, "effort": 3, "status": "todo", "goal_id": goal["id"]},
                {"title": f"Prototype: {title}", "description": "Build and evaluate a prototype", "impact": 4, "effort": 4, "status": "todo", "goal_id": goal["id"]},
                {"title": f"Deploy: {title}", "description": "Production deployment with monitoring", "impact": 5, "effort": 5, "status": "todo", "goal_id": goal["id"]},
            ]

        # Add milestone dates
        now = time.time()
        for i, item in enumerate(items):
            item["milestone_date"] = now + (i + 1) * 7 * 86400  # weekly milestones

        return items

    # ------------------------------------------------------------------ #
    # 4. Goal-progress tracking
    # ------------------------------------------------------------------ #

    def track_goal_progress(self) -> dict:
        """Track progress on each active strategic goal.

        Returns::

            {
                goals: [{id, title, progress_pct, status, on_track}, …],
                summary: {total, on_track, at_risk, behind, completed}
            }
        """
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM strategic_goals WHERE status IN ('active', 'completed') ORDER BY priority ASC"
            ).fetchall()

        goals: list[dict] = []
        summary = {"total": 0, "on_track": 0, "at_risk": 0, "behind": 0, "completed": 0}

        for row in rows:
            target = row["target_value"] or 1.0
            current = row["current_value"] or 0.0
            progress = min(100.0, max(0.0, (current / target) * 100)) if target else 0.0

            # Determine status based on progress vs time elapsed
            elapsed = time.time() - row["created_at"]
            total_time = row["deadline"] - row["created_at"]
            expected_progress = (elapsed / total_time * 100) if total_time > 0 else 100

            if progress >= 100:
                status_label = "completed"
                summary["completed"] += 1
            elif progress >= expected_progress * 0.8:
                status_label = "on_track"
                summary["on_track"] += 1
            elif progress >= expected_progress * 0.5:
                status_label = "at_risk"
                summary["at_risk"] += 1
            else:
                status_label = "behind"
                summary["behind"] += 1

            goals.append({
                "id": row["id"],
                "title": row["title"],
                "metric": row["metric"],
                "target_value": target,
                "current_value": current,
                "progress_pct": round(progress, 1),
                "expected_progress_pct": round(expected_progress, 1),
                "status": status_label,
                "deadline": datetime.utcfromtimestamp(row["deadline"]).strftime("%Y-%m-%d"),
            })

        summary["total"] = len(goals)
        return {"goals": goals, "summary": summary}

    def update_goal_progress(self, goal_id: int, new_value: float) -> None:
        """Update the current value for a strategic goal."""
        with self._lock:
            self._conn.execute(
                "UPDATE strategic_goals SET current_value = ?, updated_at = ? WHERE id = ?",
                (new_value, time.time(), goal_id),
            )
            self._conn.commit()
        logger.info("Updated goal %d progress to %.2f", goal_id, new_value)

    # ------------------------------------------------------------------ #
    # 5. Weekly plan generation
    # ------------------------------------------------------------------ #

    def generate_weekly_plan(self) -> str:
        """Generate a concrete weekly action plan based on goals and current state.

        Returns a formatted Markdown string.
        """
        progress = self.track_goal_progress()
        now = datetime.utcnow()
        week_start = now - timedelta(days=now.weekday())
        week_start_str = week_start.strftime("%Y-%m-%d")

        # Prioritise behind / at-risk goals
        behind_goals = [g for g in progress["goals"] if g["status"] in ("behind", "at_risk")]
        on_track_goals = [g for g in progress["goals"] if g["status"] == "on_track"]

        lines: list[str] = [
            f"# Weekly Action Plan — Week of {week_start_str}",
            "",
            "## Focus Areas",
        ]

        if behind_goals:
            lines.append(f"**Priority**: {len(behind_goals)} goal(s) need attention:")
            for g in behind_goals:
                lines.append(f"- **{g['title']}** — {g['progress_pct']}% complete (expected: {g['expected_progress_pct']}%)")
        else:
            lines.append("All goals on track. Focus on acceleration and capability expansion.")

        lines.extend(["", "## Research Tasks"])
        for g in behind_goals[:2]:
            lines.append(f"- [ ] Research latest approaches for: {g['title']}")
        lines.append("- [ ] Review competitor releases and feature updates")
        lines.append("- [ ] Survey users for unmet needs")

        lines.extend(["", "## Implementation Tasks"])
        task_count = 1
        for g in behind_goals[:3]:
            lines.append(f"- [ ] {task_count}. Implement improvement for: {g['title']} (target: +10% progress)")
            task_count += 1
        for g in on_track_goals[:2]:
            lines.append(f"- [ ] {task_count}. Accelerate: {g['title']} (stretch goal)")
            task_count += 1

        lines.extend(["", "## Testing Tasks"])
        lines.append("- [ ] Run A/B test on evolved prompts for top 2 modes")
        lines.append("- [ ] Validate knowledge graph accuracy on 50 random facts")
        lines.append("- [ ] Performance test: measure p99 latency under load")
        lines.append("- [ ] User satisfaction survey: target 30 responses")

        lines.extend(["", "## Metrics to Track"])
        for g in progress["goals"]:
            lines.append(f"- {g['metric']}: current={g['current_value']}, target={g['target_value']}")

        lines.extend(["", "---", f"*Generated by Prometheus Prime StrategicPlanner on {now.isoformat()} UTC*"])

        plan_text = "\n".join(lines)

        # Persist
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO weekly_plans (week_start, plan_text, goals_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (week_start_str, plan_text, json.dumps(progress["goals"]), time.time()),
            )
            self._conn.commit()

        return plan_text

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def get_active_goals(self) -> list[dict]:
        """Return all active strategic goals."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM strategic_goals WHERE status = 'active' ORDER BY priority ASC"
            ).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self._conn.close()
        logger.info("StrategicPlanner connection closed.")
