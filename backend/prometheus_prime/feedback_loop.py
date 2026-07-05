"""feedback_loop.py — Continuous Feedback Integration for Prometheus Prime.

Collects implicit behavioural signals and explicit user ratings, then derives
an overall satisfaction score and surfaces recurring failure patterns.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import threading
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Optional

import numpy as np

logger = logging.getLogger("prometheus_prime.feedback_loop")

DB_PATH_ENV = os.environ.get("PROMETHEUS_DB_PATH", "/mnt/agents/output/project/backend/data/prometheus_prime.db")


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH_ENV, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def _init_feedback_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS explicit_feedback (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id      TEXT NOT NULL,
            rating          REAL NOT NULL CHECK(rating >= 0 AND rating <= 5),
            comment         TEXT,
            timestamp       REAL NOT NULL DEFAULT (unixepoch())
        );

        CREATE INDEX IF NOT EXISTS idx_explicit_session ON explicit_feedback(session_id);
        CREATE INDEX IF NOT EXISTS idx_explicit_time ON explicit_feedback(timestamp);

        CREATE TABLE IF NOT EXISTS implicit_feedback (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id          TEXT NOT NULL,
            follow_up_count     INTEGER NOT NULL DEFAULT 0,
            response_time_ms    INTEGER NOT NULL DEFAULT 0,
            user_corrected      INTEGER NOT NULL DEFAULT 0,
            response_copied     INTEGER NOT NULL DEFAULT 0,
            session_duration_s  REAL,
            query_length        INTEGER NOT NULL DEFAULT 0,
            response_length     INTEGER NOT NULL DEFAULT 0,
            timestamp           REAL NOT NULL DEFAULT (unixepoch())
        );

        CREATE INDEX IF NOT EXISTS idx_implicit_session ON implicit_feedback(session_id);
        CREATE INDEX IF NOT EXISTS idx_implicit_time ON implicit_feedback(timestamp);

        CREATE TABLE IF NOT EXISTS failure_patterns (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern         TEXT NOT NULL UNIQUE,
            frequency       INTEGER NOT NULL DEFAULT 1,
            examples_json   TEXT,
            suggested_fix   TEXT,
            first_seen      REAL NOT NULL DEFAULT (unixepoch()),
            last_seen       REAL NOT NULL DEFAULT (unixepoch())
        );
        """
    )
    conn.commit()


# ---------------------------------------------------------------------------
# FeedbackLoop
# ---------------------------------------------------------------------------


class FeedbackLoop:
    """Continuous feedback integration for Prometheus Prime.

    Captures **implicit** behavioural signals (latency, follow-ups, copy
    actions, corrections) and **explicit** star ratings + free-form comments.
    The two streams are fused into a single ``[0, 1]`` satisfaction score.
    """

    # --- lifecycle -------------------------------------------------------- #

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or DB_PATH_ENV
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._conn = _get_db()
        _init_feedback_tables(self._conn)
        self._lock = threading.RLock()
        logger.info("FeedbackLoop initialised — DB: %s", self._db_path)

    # --- 1. Implicit feedback --------------------------------------------- #

    def collect_implicit_feedback(
        self,
        session_id: str,
        interaction_data: dict[str, Any],
    ) -> dict:
        """Derive satisfaction signals from behavioural data.

        Parameters
        ----------
        session_id:
            Conversation identifier.
        interaction_data:
            Dictionary that may contain any of the following keys::

                follow_up_count   – number of user follow-up turns
                response_time_ms  – last response latency
                user_corrected    – 1 if user said the response was wrong
                response_copied   – 1 if user copied the response
                session_duration_s – total conversation wall time
                query_length      – character length of user query
                response_length   – character length of assistant response

        Returns
        -------
        dict
            Normalised signal values and a preliminary *implicit_score*.
        """
        follow_up_count = int(interaction_data.get("follow_up_count", 0))
        response_time_ms = int(interaction_data.get("response_time_ms", 0))
        user_corrected = int(interaction_data.get("user_corrected", 0))
        response_copied = int(interaction_data.get("response_copied", 0))
        session_duration_s = float(interaction_data.get("session_duration_s", 0.0) or 0.0)
        query_length = int(interaction_data.get("query_length", 0))
        response_length = int(interaction_data.get("response_length", 0))

        # --- Normalise individual signals ----------------------------------

        # Follow-ups: 0 is best; >3 is bad
        follow_up_score = max(0.0, 1.0 - follow_up_count * 0.25)

        # Response time: <1s excellent; >8s poor
        if response_time_ms <= 0:
            time_score = 0.5
        elif response_time_ms < 1000:
            time_score = 1.0
        elif response_time_ms < 3000:
            time_score = 0.8
        elif response_time_ms < 8000:
            time_score = 0.5
        else:
            time_score = 0.2

        # Corrections are a strong negative signal
        correction_score = 0.0 if user_corrected else 1.0

        # Copy is a positive signal
        copy_score = 1.0 if response_copied else 0.5

        # Session duration sweet spot: 30s-5min
        if 30 <= session_duration_s <= 300:
            duration_score = 1.0
        elif session_duration_s < 10:
            duration_score = 0.3  # bounced
        else:
            duration_score = 0.7

        # Response length proportion (don't want novels for short queries)
        if query_length > 0:
            ratio = response_length / query_length
            if 1 <= ratio <= 10:
                proportion_score = 1.0
            elif 10 < ratio <= 20:
                proportion_score = 0.7
            else:
                proportion_score = 0.4
        else:
            proportion_score = 0.5

        # Weighted aggregate
        implicit_score = float(np.average(
            [follow_up_score, time_score, correction_score, copy_score, duration_score, proportion_score],
            weights=[0.25, 0.20, 0.25, 0.10, 0.10, 0.10],
        ))

        record = {
            "session_id": session_id,
            "follow_up_count": follow_up_count,
            "response_time_ms": response_time_ms,
            "user_corrected": user_corrected,
            "response_copied": response_copied,
            "session_duration_s": session_duration_s,
            "query_length": query_length,
            "response_length": response_length,
            "timestamp": time.time(),
        }

        with self._lock:
            self._conn.execute(
                """
                INSERT INTO implicit_feedback
                    (session_id, follow_up_count, response_time_ms, user_corrected,
                     response_copied, session_duration_s, query_length, response_length, timestamp)
                VALUES (:session_id, :follow_up_count, :response_time_ms, :user_corrected,
                        :response_copied, :session_duration_s, :query_length, :response_length, :timestamp)
                """,
                record,
            )
            self._conn.commit()

        logger.debug("Implicit feedback for %s — score=%.3f", session_id, implicit_score)
        return {**record, "implicit_score": round(implicit_score, 3)}

    # --- 2. Explicit feedback --------------------------------------------- #

    def collect_explicit_feedback(
        self,
        session_id: str,
        rating: float,
        comment: str | None = None,
    ) -> None:
        """Store an explicit user rating (1–5 stars) and optional comment.

        Parameters
        ----------
        session_id:
            Conversation identifier.
        rating:
            Star rating from 0.0 to 5.0.
        comment:
            Free-form user feedback (optional).
        """
        clamped = max(0.0, min(5.0, float(rating)))
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO explicit_feedback (session_id, rating, comment, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, clamped, comment, time.time()),
            )
            self._conn.commit()

        logger.info("Explicit feedback for %s — %.1f/5 stars", session_id, clamped)

    # --- 3. Satisfaction fusion ------------------------------------------- #

    def calculate_satisfaction_score(self, session_id: str) -> float:
        """Combine implicit + explicit signals into a single ``[0, 1]`` score.

        Returns 0.0 when no data exists for the session.
        """
        with self._lock:
            implicit_row = self._conn.execute(
                "SELECT * FROM implicit_feedback WHERE session_id = ? ORDER BY timestamp DESC LIMIT 1",
                (session_id,),
            ).fetchone()

            explicit_rows = self._conn.execute(
                "SELECT AVG(rating) as avg_rating FROM explicit_feedback WHERE session_id = ?",
                (session_id,),
            ).fetchall()

        # Derive implicit component
        if implicit_row is None:
            implicit_score = None
        else:
            follow_up = implicit_row["follow_up_count"]
            time_ms = implicit_row["response_time_ms"]
            corrected = implicit_row["user_corrected"]
            copied = implicit_row["response_copied"]
            duration = implicit_row["session_duration_s"] or 0.0

            follow_up_score = max(0.0, 1.0 - follow_up * 0.25)
            time_score = 1.0 if time_ms < 1000 else 0.7 if time_ms < 3000 else 0.4 if time_ms < 8000 else 0.2
            correction_score = 0.0 if corrected else 1.0
            copy_score = 1.0 if copied else 0.5
            duration_score = 1.0 if 30 <= duration <= 300 else 0.3 if duration < 10 else 0.7

            implicit_score = float(np.average(
                [follow_up_score, time_score, correction_score, copy_score, duration_score],
                weights=[0.30, 0.20, 0.30, 0.10, 0.10],
            ))

        # Derive explicit component
        explicit_avg = None
        if explicit_rows and explicit_rows[0]["avg_rating"] is not None:
            explicit_avg = float(explicit_rows[0]["avg_rating"]) / 5.0  # normalise to [0, 1]

        # Fuse
        if implicit_score is not None and explicit_avg is not None:
            return round(0.4 * implicit_score + 0.6 * explicit_avg, 3)
        elif implicit_score is not None:
            return round(implicit_score, 3)
        elif explicit_avg is not None:
            return round(explicit_avg, 3)
        return 0.0

    # --- 4. Failure-pattern identification -------------------------------- #

    def identify_failure_patterns(self) -> list[dict]:
        """Find recurring patterns in low-satisfaction interactions.

        Returns a list of pattern dicts::

            [{pattern, frequency, examples, suggested_fix}, …]
        """
        with self._lock:
            # Pull low-quality sessions
            rows = self._conn.execute(
                """
                SELECT i.session_id, i.query, i.response, i.mode, i.quality_score,
                       e.avg_rating
                FROM interactions i
                LEFT JOIN (
                    SELECT session_id, AVG(rating) as avg_rating
                    FROM explicit_feedback
                    GROUP BY session_id
                ) e ON i.session_id = e.session_id
                WHERE i.quality_score < 0.4
                   OR (e.avg_rating IS NOT NULL AND e.avg_rating < 2.5)
                ORDER BY i.timestamp DESC
                LIMIT 200
                """
            ).fetchall()

        if not rows:
            return []

        # Cluster by keywords (same heuristic as MetaLearner)
        keyword_map = {
            "math_error": {"calculate", "math", "equation", "sum", "formula", "number"},
            "code_bug": {"code", "bug", "error", "syntax", "function", "script"},
            "unclear_response": {"confusing", "unclear", "don't understand", "what do you mean"},
            "wrong_fact": {"wrong", "incorrect", "that's not", "actually", "fact"},
            "too_slow": {"slow", "taking too long", "hurry", "timeout"},
            "hallucination": {"hallucinat", "made up", "not real", "doesn't exist"},
        }

        clusters: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            text = f"{row['query']} {row['response']}".lower()
            matched = False
            for pattern_name, keywords in keyword_map.items():
                if any(kw in text for kw in keywords):
                    clusters[pattern_name].append(dict(row))
                    matched = True
                    break
            if not matched:
                clusters["general_dissatisfaction"].append(dict(row))

        results: list[dict] = []
        fix_map = {
            "math_error": "Integrate a math verification layer (e.g., SymPy) before returning numeric answers.",
            "code_bug": "Add a code-execution sandbox + linter to validate snippets before presenting them.",
            "unclear_response": "Require structured output (headings / bullet points) and add a clarity self-check.",
            "wrong_fact": "Enable retrieval-augmented generation with a live knowledge-base lookup.",
            "too_slow": "Optimise model pipeline or add streaming; investigate slow response root cause.",
            "hallucination": "Implement citation requirements and confidence-threshold filtering.",
            "general_dissatisfaction": "Review full conversation logs and conduct human analysis.",
        }

        for pattern_name, items in sorted(clusters.items(), key=lambda x: -len(x[1])):
            if len(items) < 2:
                continue
            results.append({
                "pattern": pattern_name,
                "frequency": len(items),
                "examples": [
                    {"query": it["query"][:120], "response": it["response"][:120]}
                    for it in items[:3]
                ],
                "suggested_fix": fix_map.get(pattern_name, fix_map["general_dissatisfaction"]),
            })

        # Persist newly discovered patterns
        with self._lock:
            for pat in results:
                self._conn.execute(
                    """
                    INSERT INTO failure_patterns (pattern, frequency, examples_json, suggested_fix, last_seen)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(pattern) DO UPDATE SET
                        frequency = excluded.frequency,
                        examples_json = excluded.examples_json,
                        suggested_fix = excluded.suggested_fix,
                        last_seen = excluded.last_seen
                    """,
                    (pat["pattern"], pat["frequency"], json.dumps(pat["examples"]),
                     pat["suggested_fix"], time.time()),
                )
            self._conn.commit()

        return results

    # --- 5. Feedback summary ---------------------------------------------- #

    def get_feedback_summary(self, days: int = 7) -> dict:
        """Return a summary of feedback over the last *days*.

        Returns::

            {
                period_days: int,
                total_sessions: int,
                explicit_ratings: {count, average, distribution},
                implicit_scores: {average, distribution},
                satisfaction_trend: [{date, score}, …],
                top_complaints: [str, …],
                top_praises: [str, …],
                recommendations: [str, …]
            }
        """
        since = time.time() - days * 86400

        with self._lock:
            explicit_rows = self._conn.execute(
                """
                SELECT rating, comment, timestamp FROM explicit_feedback
                WHERE timestamp > ? ORDER BY timestamp DESC
                """,
                (since,),
            ).fetchall()

            implicit_rows = self._conn.execute(
                """
                SELECT session_id, follow_up_count, response_time_ms, user_corrected,
                       response_copied, session_duration_s, timestamp
                FROM implicit_feedback
                WHERE timestamp > ? ORDER BY timestamp DESC
                """,
                (since,),
            ).fetchall()

        # --- Explicit stats -------------------------------------------------
        explicit_count = len(explicit_rows)
        explicit_avg = float(np.mean([r["rating"] for r in explicit_rows])) if explicit_rows else 0.0
        explicit_distribution = Counter(round(r["rating"]) for r in explicit_rows)

        # --- Implicit stats -------------------------------------------------
        implicit_scores: list[float] = []
        for row in implicit_rows:
            follow_up = row["follow_up_count"]
            time_ms = row["response_time_ms"]
            corrected = row["user_corrected"]
            copied = row["response_copied"]
            duration = row["session_duration_s"] or 0.0

            scores = [
                max(0.0, 1.0 - follow_up * 0.25),
                1.0 if time_ms < 1000 else 0.7 if time_ms < 3000 else 0.4 if time_ms < 8000 else 0.2,
                0.0 if corrected else 1.0,
                1.0 if copied else 0.5,
                1.0 if 30 <= duration <= 300 else 0.3 if duration < 10 else 0.7,
            ]
            implicit_scores.append(float(np.average(scores, weights=[0.30, 0.20, 0.30, 0.10, 0.10])))

        implicit_avg = float(np.mean(implicit_scores)) if implicit_scores else 0.0

        # --- Trend by day ---------------------------------------------------
        daily_scores: dict[str, list[float]] = defaultdict(list)
        for row in explicit_rows:
            day = datetime.utcfromtimestamp(row["timestamp"]).strftime("%Y-%m-%d")
            daily_scores[day].append(row["rating"] / 5.0)
        for row, score in zip(implicit_rows, implicit_scores):
            day = datetime.utcfromtimestamp(row["timestamp"]).strftime("%Y-%m-%d")
            daily_scores[day].append(score)

        trend = sorted(
            [{"date": d, "score": round(float(np.mean(vs)), 3)} for d, vs in daily_scores.items()],
            key=lambda x: x["date"],
        )

        # --- Complaints & praises from comments -----------------------------
        complaint_keywords = {"bad", "wrong", "slow", "poor", "terrible", "useless", "confusing", "error"}
        praise_keywords = {"good", "great", "excellent", "amazing", "helpful", "perfect", "love", "fast"}

        complaints: list[str] = []
        praises: list[str] = []
        for row in explicit_rows:
            if not row["comment"]:
                continue
            lowered = row["comment"].lower()
            if any(kw in lowered for kw in complaint_keywords):
                complaints.append(row["comment"])
            elif any(kw in lowered for kw in praise_keywords):
                praises.append(row["comment"])

        # --- Recommendations ------------------------------------------------
        recommendations: list[str] = []
        if implicit_avg < 0.5:
            recommendations.append("Response latency is hurting satisfaction — optimise pipeline.")
        if explicit_avg < 3.0:
            recommendations.append("Explicit ratings are low — investigate quality issues.")
        if not recommendations:
            recommendations.append("Satisfaction is stable — focus on capability expansion.")

        return {
            "period_days": days,
            "total_sessions": len(set(r["session_id"] for r in implicit_rows)),
            "explicit_ratings": {
                "count": explicit_count,
                "average": round(explicit_avg, 2),
                "distribution": dict(explicit_distribution),
            },
            "implicit_scores": {
                "average": round(implicit_avg, 3),
                "count": len(implicit_scores),
            },
            "satisfaction_trend": trend,
            "top_complaints": complaints[:5],
            "top_praises": praises[:5],
            "recommendations": recommendations,
        }

    # --- helpers ---------------------------------------------------------- #

    def close(self) -> None:
        self._conn.close()
        logger.info("FeedbackLoop connection closed.")
