"""meta_learner.py — The Heart of Self-Improvement for Prometheus Prime.

Implements recursive self-improvement through interaction tracking, conversation
analysis, system-prompt adaptation, capability-gap discovery, and knowledge-graph
construction.
"""

from __future__ import annotations

import asyncio
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

logger = logging.getLogger("prometheus_prime.meta_learner")

DB_PATH_ENV = os.environ.get("PROMETHEUS_DB_PATH", "/mnt/agents/output/project/backend/data/prometheus_prime.db")
EMBEDDING_DIM = 384  # dimension for lightweight local embeddings (simulated)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_db_connection() -> sqlite3.Connection:
    """Return a new SQLite connection with row factory."""
    conn = sqlite3.connect(DB_PATH_ENV, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def _init_db(conn: sqlite3.Connection) -> None:
    """Create required tables if they do not exist."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS interactions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id      TEXT NOT NULL,
            query           TEXT NOT NULL,
            response        TEXT NOT NULL,
            mode            TEXT NOT NULL DEFAULT 'chat',
            duration_ms     INTEGER NOT NULL DEFAULT 0,
            user_feedback   REAL,
            quality_score   REAL NOT NULL DEFAULT 0.0,
            timestamp       REAL NOT NULL DEFAULT (unixepoch()),
            embedding       BLOB
        );

        CREATE INDEX IF NOT EXISTS idx_interactions_session
            ON interactions(session_id);
        CREATE INDEX IF NOT EXISTS idx_interactions_mode
            ON interactions(mode);
        CREATE INDEX IF NOT EXISTS idx_interactions_timestamp
            ON interactions(timestamp);

        CREATE TABLE IF NOT EXISTS conversations (
            session_id      TEXT PRIMARY KEY,
            lessons_learned TEXT,
            knowledge_json  TEXT,
            skill_delta     REAL NOT NULL DEFAULT 0.0,
            created_at      REAL NOT NULL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS capability_scores (
            capability      TEXT PRIMARY KEY,
            score           REAL NOT NULL DEFAULT 0.5,
            total_attempts  INTEGER NOT NULL DEFAULT 0,
            success_count   INTEGER NOT NULL DEFAULT 0,
            last_updated    REAL NOT NULL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS knowledge_graph (
            entity          TEXT NOT NULL,
            relation        TEXT NOT NULL,
            target          TEXT,
            confidence      REAL NOT NULL DEFAULT 0.5,
            source_session  TEXT,
            created_at      REAL NOT NULL DEFAULT (unixepoch()),
            PRIMARY KEY (entity, relation, target)
        );

        CREATE TABLE IF NOT EXISTS system_prompts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            mode        TEXT NOT NULL,
            prompt      TEXT NOT NULL,
            score       REAL NOT NULL DEFAULT 0.0,
            is_active   INTEGER NOT NULL DEFAULT 0,
            generation  INTEGER NOT NULL DEFAULT 0,
            created_at  REAL NOT NULL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS prompt_tests (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt_id       INTEGER NOT NULL REFERENCES system_prompts(id),
            test_case       TEXT NOT NULL,
            result_score    REAL NOT NULL DEFAULT 0.0,
            timestamp       REAL NOT NULL DEFAULT (unixepoch())
        );
        """
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Lightweight embedding helpers (fallback when no external model is available)
# ---------------------------------------------------------------------------

def _compute_embedding(text: str) -> bytes:
    """Compute a deterministic embedding vector for *text*.

    Uses a simple hashing-based approach that produces stable vectors
    suitable for cosine-similarity search.  In production this should
    be swapped for a real sentence-transformer model.
    """
    np.random.seed(hash(text) % (2**31))
    vec = np.random.randn(EMBEDDING_DIM).astype(np.float32)
    vec /= np.linalg.norm(vec) + 1e-9
    return vec.tobytes()


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Return cosine similarity between two 1-D arrays."""
    dot = float(np.dot(a, b))
    norm = float(np.linalg.norm(a) * np.linalg.norm(b))
    return 0.0 if norm == 0 else dot / norm


# ---------------------------------------------------------------------------
# MetaLearner
# ---------------------------------------------------------------------------


class MetaLearner:
    """Meta-learning engine that improves Luqi AI from every conversation.

    This is the core of Prometheus Prime — a system that:
    1. Tracks conversation outcomes (success / failure / satisfaction)
    2. Learns which response strategies work best
    3. Adapts system prompts based on feedback
    4. Discovers new capabilities through pattern recognition
    5. Builds a knowledge graph of what it knows and doesn't know
    """

    # --------------------------------------------------------------------- #
    # Lifecycle
    # --------------------------------------------------------------------- #

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or DB_PATH_ENV
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._conn = _get_db_connection()
        _init_db(self._conn)
        self._lock = threading.RLock()
        logger.info("MetaLearner initialised — DB: %s", self._db_path)

    # --------------------------------------------------------------------- #
    # 1. Interaction recording
    # --------------------------------------------------------------------- #

    def record_interaction(
        self,
        session_id: str,
        query: str,
        response: str,
        mode: str = "chat",
        duration_ms: int = 0,
        user_feedback: float | None = None,
    ) -> None:
        """Record every conversation with metadata.

        Parameters
        ----------
        session_id:
            Unique conversation identifier.
        query:
            User message.
        response:
            Assistant response.
        mode:
            Operating mode — ``chat``, ``research``, ``think``, ``mentor``, …
        duration_ms:
            Wall-clock time to generate the response.
        user_feedback:
            Optional explicit rating (0.0 … 1.0) from the user.

        The method automatically calculates a *quality_score* from:
        * response length (optimal = 300-800 chars)
        * response latency (faster is better)
        * user_feedback if supplied
        * basic sentiment heuristics
        """
        quality = self._calculate_quality_score(query, response, duration_ms, user_feedback)
        embedding_blob = _compute_embedding(query + " " + response)

        with self._lock:
            self._conn.execute(
                """
                INSERT INTO interactions
                    (session_id, query, response, mode, duration_ms,
                     user_feedback, quality_score, timestamp, embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    query,
                    response,
                    mode,
                    duration_ms,
                    user_feedback,
                    quality,
                    time.time(),
                    embedding_blob,
                ),
            )
            self._conn.commit()

        logger.debug(
            "Recorded interaction %s | mode=%s | quality=%.3f",
            session_id, mode, quality,
        )

    def _calculate_quality_score(
        self,
        query: str,
        response: str,
        duration_ms: int,
        user_feedback: float | None,
    ) -> float:
        """Heuristic quality score in [0, 1]."""
        score = 0.5  # baseline

        # Length factor — prefer medium-length responses
        rlen = len(response)
        if 100 <= rlen <= 800:
            score += 0.2
        elif 800 < rlen <= 1500:
            score += 0.1
        elif rlen < 50:
            score -= 0.15
        else:
            score -= 0.05

        # Latency factor — penalise very slow responses
        if duration_ms > 0:
            if duration_ms < 1000:
                score += 0.1
            elif duration_ms > 5000:
                score -= 0.1

        # User feedback dominates if present
        if user_feedback is not None:
            score = 0.4 * score + 0.6 * user_feedback

        # Sentiment heuristics on response
        positive_words = {"great", "excellent", "perfect", "glad", "happy", "success", "achieved"}
        negative_words = {"sorry", "error", "failed", "unable", "cannot", "wrong", "apologise"}
        words = set(response.lower().split())
        pos = len(words & positive_words)
        neg = len(words & negative_words)
        if pos > neg:
            score += 0.05
        elif neg > pos:
            score -= 0.05

        return max(0.0, min(1.0, score))

    # --------------------------------------------------------------------- #
    # 2. Conversation-level learning
    # --------------------------------------------------------------------- #

    def learn_from_conversation(self, session_id: str) -> dict:
        """Analyse a completed conversation, extract lessons and update state.

        Returns
        -------
        dict
            ``{lessons_learned, knowledge_extracted, skill_improved}``
        """
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM interactions WHERE session_id = ? ORDER BY timestamp",
                (session_id,),
            ).fetchall()

        if not rows:
            return {"lessons_learned": [], "knowledge_extracted": [], "skill_improved": None}

        lessons: list[str] = []
        knowledge: list[dict] = []
        skill_changes: dict[str, float] = {}

        avg_quality = float(np.mean([r["quality_score"] for r in rows]))

        # --- Lesson extraction ------------------------------------------------
        if avg_quality < 0.4:
            lessons.append(
                f"Session {session_id} had low average quality ({avg_quality:.2f}); "
                "consider shorter responses or more clarifying questions."
            )
        elif avg_quality > 0.8:
            lessons.append(
                f"Session {session_id} performed well ({avg_quality:.2f}); "
                "response strategy is effective for this query type."
            )

        follow_up_count = len(rows) - 1  # first row is initial query
        if follow_up_count > 3:
            lessons.append(
                f"High follow-up count ({follow_up_count}) suggests the initial "
                "response may have been unclear or incomplete."
            )
        elif follow_up_count == 0 and avg_quality > 0.7:
            lessons.append(
                "Single-turn resolution with high quality — pattern to replicate."
            )

        # --- Knowledge extraction ---------------------------------------------
        for row in rows:
            q, r = row["query"], row["response"]
            # Simple entity extraction: capitalised phrases & noun patterns
            entities = set(re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", q + " " + r))
            for entity in entities:
                knowledge.append({
                    "entity": entity,
                    "relation": "mentioned_in",
                    "target": session_id,
                    "confidence": row["quality_score"],
                })

        # --- Skill tracking ---------------------------------------------------
        mode = rows[0]["mode"]
        mode_score_delta = (avg_quality - 0.5) * 0.1  # small adjustment
        self._update_capability_score(mode, mode_score_delta)
        skill_changes[mode] = mode_score_delta

        # --- Store conversation analysis --------------------------------------
        result = {
            "lessons_learned": lessons,
            "knowledge_extracted": knowledge,
            "skill_improved": skill_changes,
        }
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO conversations
                    (session_id, lessons_learned, knowledge_json, skill_delta, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    json.dumps(lessons),
                    json.dumps(knowledge),
                    mode_score_delta,
                    time.time(),
                ),
            )
            # Persist extracted knowledge into the graph
            for k in knowledge:
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO knowledge_graph
                        (entity, relation, target, confidence, source_session, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (k["entity"], k["relation"], k["target"],
                     k["confidence"], session_id, time.time()),
                )
            self._conn.commit()

        logger.info("Learned from session %s — %d lessons, %d facts", session_id, len(lessons), len(knowledge))
        return result

    def _update_capability_score(self, capability: str, delta: float) -> None:
        """Bump the capability score by *delta*, clamped to [0, 1]."""
        with self._lock:
            row = self._conn.execute(
                "SELECT score, total_attempts FROM capability_scores WHERE capability = ?",
                (capability,),
            ).fetchone()

            if row is None:
                new_score = max(0.0, min(1.0, 0.5 + delta))
                self._conn.execute(
                    "INSERT INTO capability_scores (capability, score, total_attempts) VALUES (?, ?, 1)",
                    (capability, new_score),
                )
            else:
                new_score = max(0.0, min(1.0, row["score"] + delta))
                self._conn.execute(
                    "UPDATE capability_scores SET score = ?, total_attempts = total_attempts + 1, "
                    "last_updated = ? WHERE capability = ?",
                    (new_score, time.time(), capability),
                )
            self._conn.commit()

    # --------------------------------------------------------------------- #
    # 3. System-prompt adaptation
    # --------------------------------------------------------------------- #

    def adapt_system_prompt(self, mode: str) -> str:
        """Analyse historical performance for *mode* and generate an improved prompt.

        Uses OpenAI (when ``OPENAI_API_KEY`` is present) to generate a revised
        system prompt based on accumulated performance data.  Falls back to a
        rule-based rewrite when the API is unavailable.
        """
        with self._lock:
            perf_rows = self._conn.execute(
                "SELECT quality_score, query, response FROM interactions WHERE mode = ? ORDER BY timestamp DESC LIMIT 50",
                (mode,),
            ).fetchall()

        if not perf_rows:
            return self._default_prompt_for_mode(mode)

        avg_quality = float(np.mean([r["quality_score"] for r in perf_rows]))
        low_quality = [r for r in perf_rows if r["quality_score"] < 0.4]

        # Build a critique string
        critiques: list[str] = []
        if avg_quality < 0.5:
            critiques.append(f"Average quality is low ({avg_quality:.2f}); responses need fundamental improvement.")
        if low_quality:
            critiques.append(f"{len(low_quality)} recent interactions rated poorly.")

        # Attempt OpenAI-based rewrite
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            try:
                new_prompt = self._openai_rewrite_prompt(mode, critiques, low_quality)
            except Exception as exc:
                logger.warning("OpenAI prompt rewrite failed: %s; using fallback.", exc)
                new_prompt = self._fallback_rewrite_prompt(mode, critiques)
        else:
            new_prompt = self._fallback_rewrite_prompt(mode, critiques)

        # A/B test against current active prompt
        current_prompt = self._get_active_prompt(mode)
        winner = self._ab_test_prompts(mode, current_prompt, new_prompt, perf_rows)

        # Store winner
        with self._lock:
            self._conn.execute(
                "UPDATE system_prompts SET is_active = 0 WHERE mode = ?",
                (mode,),
            )
            self._conn.execute(
                "INSERT INTO system_prompts (mode, prompt, is_active, generation) VALUES (?, ?, 1, "
                "(SELECT COALESCE(MAX(generation), 0) + 1 FROM system_prompts WHERE mode = ?))",
                (mode, winner, mode),
            )
            self._conn.commit()

        return winner

    def _default_prompt_for_mode(self, mode: str) -> str:
        defaults = {
            "chat": "You are a helpful AI assistant. Answer clearly and concisely.",
            "research": "You are a research assistant. Provide thorough, well-sourced information.",
            "think": "You are a reasoning engine. Think step-by-step and explain your logic.",
            "mentor": "You are a patient mentor. Guide the user to understanding through questions.",
            "code": "You are a coding assistant. Write clean, documented, tested code.",
        }
        return defaults.get(mode, "You are a helpful AI assistant.")

    def _get_active_prompt(self, mode: str) -> str:
        with self._lock:
            row = self._conn.execute(
                "SELECT prompt FROM system_prompts WHERE mode = ? AND is_active = 1 ORDER BY generation DESC LIMIT 1",
                (mode,),
            ).fetchone()
        return row["prompt"] if row else self._default_prompt_for_mode(mode)

    def _openai_rewrite_prompt(
        self, mode: str, critiques: list[str], low_quality: list
    ) -> str:
        """Call OpenAI to rewrite the system prompt based on performance data."""
        try:
            import openai
        except ImportError:
            raise RuntimeError("openai package not installed")

        client = openai.AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

        critique_text = "\n".join(critiques)
        failure_examples = "\n\n".join(
            f"Q: {r['query']}\nA: {r['response']}" for r in low_quality[:3]
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a prompt-engineering expert. Given a mode, critique, and "
                    "failure examples, generate an improved system prompt. Output ONLY "
                    "the new system prompt with no extra commentary."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Mode: {mode}\n"
                    f"Critiques:\n{critique_text}\n\n"
                    f"Failure examples:\n{failure_examples}"
                ),
            },
        ]

        # Synchronous wrapper for async call
        loop = asyncio.new_event_loop()
        try:
            response = loop.run_until_complete(
                client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,  # type: ignore[arg-type]
                    max_tokens=500,
                    temperature=0.7,
                )
            )
        finally:
            loop.close()

        new_prompt = response.choices[0].message.content or self._default_prompt_for_mode(mode)
        return new_prompt.strip()

    def _fallback_rewrite_prompt(self, mode: str, critiques: list[str]) -> str:
        """Rule-based prompt rewrite when OpenAI is unavailable."""
        base = self._default_prompt_for_mode(mode)
        additions: list[str] = []

        if any("low" in c for c in critiques):
            additions.append("Always verify facts before stating them.")
        if any("unclear" in c or "poor" in c for c in critiques):
            additions.append("Structure responses with clear headings and bullet points.")
        if mode == "mentor" and not any("question" in a for a in additions):
            additions.append("Ask clarifying questions when the user's intent is ambiguous.")

        if additions:
            return base + " " + " ".join(additions)
        return base

    def _ab_test_prompts(
        self,
        mode: str,
        current: str,
        candidate: str,
        historical_rows: list,
    ) -> str:
        """Simple simulated A/B test: score each prompt against recent interactions.

        In a full implementation this would run both prompts through an LLM
        evaluator on held-out test cases.  Here we use a fast heuristic.
        """
        current_score = self._score_prompt_heuristic(current, historical_rows)
        candidate_score = self._score_prompt_heuristic(candidate, historical_rows)

        logger.info("A/B test for %s — current=%.3f candidate=%.3f", mode, current_score, candidate_score)

        # Candidate must beat current by a margin to avoid thrashing
        return candidate if candidate_score > current_score + 0.02 else current

    def _score_prompt_heuristic(self, prompt: str, rows: list) -> float:
        """Score a prompt by checking keyword overlap with high-quality responses."""
        prompt_words = set(prompt.lower().split())
        scores: list[float] = []
        for row in rows:
            if row["quality_score"] < 0.5:
                continue
            response_words = set(row["response"].lower().split())
            overlap = len(prompt_words & response_words)
            scores.append(overlap / max(len(prompt_words), 1))
        return float(np.mean(scores)) if scores else 0.0

    # --------------------------------------------------------------------- #
    # 4. Capability-gap discovery
    # --------------------------------------------------------------------- #

    def discover_capability_gaps(self) -> list[dict]:
        """Analyse all failed / poorly-rated interactions and cluster failures.

        Returns a list of gap reports::

            [{pattern, frequency, examples, suggested_fix}, …]
        """
        with self._lock:
            bad_rows = self._conn.execute(
                "SELECT query, response, mode, quality_score FROM interactions "
                "WHERE quality_score < 0.4 ORDER BY timestamp DESC LIMIT 200"
            ).fetchall()

        if not bad_rows:
            return []

        # Simple keyword-based clustering
        clusters: dict[str, list[dict]] = defaultdict(list)
        gap_keywords = {
            "math": {"math", "calculate", "equation", "solve", "number", "sum", "formula"},
            "code": {"code", "program", "function", "bug", "error", "syntax", "python", "javascript"},
            "language": {"translate", "zulu", "afrikaans", "xhosa", "french", "spanish", "chinese"},
            "factual": {"when", "who", "where", "what year", "definition", "meaning"},
            "creative": {"write", "story", "poem", "essay", "creative", "imagine"},
            "technical": {"api", "database", "server", "deploy", "docker", "kubernetes", "cloud"},
        }

        for row in bad_rows:
            query_lower = row["query"].lower()
            matched = False
            for gap_type, keywords in gap_keywords.items():
                if any(kw in query_lower for kw in keywords):
                    clusters[gap_type].append(dict(row))
                    matched = True
                    break
            if not matched:
                clusters["other"].append(dict(row))

        gap_reports: list[dict] = []
        for gap_type, items in sorted(clusters.items(), key=lambda x: -len(x[1])):
            if len(items) < 2:  # ignore singletons
                continue

            top_examples = items[:3]
            suggested_fix = self._suggest_fix_for_gap(gap_type, items)

            gap_reports.append({
                "pattern": f"Poor performance on {gap_type}-related queries",
                "frequency": len(items),
                "percentage": round(len(items) / len(bad_rows) * 100, 1),
                "examples": [
                    {"query": e["query"][:120], "response": e["response"][:120]}
                    for e in top_examples
                ],
                "suggested_fix": suggested_fix,
            })

        return gap_reports

    def _suggest_fix_for_gap(self, gap_type: str, items: list[dict]) -> str:
        """Generate a remediation suggestion for a capability gap."""
        suggestions = {
            "math": "Integrate a symbolic math engine (SymPy) and validate numerical answers.",
            "code": "Add a code execution sandbox and static-analysis linter to verify code suggestions.",
            "language": "Expand multilingual training data and add dedicated translation quality checks.",
            "factual": "Implement retrieval-augmented generation (RAG) with a live knowledge base.",
            "creative": "Fine-tune on high-quality creative writing corpora and add style-guideline templates.",
            "technical": "Build a technical documentation index and add API-schema validation.",
            "other": "Review interactions manually to identify the underlying pattern.",
        }
        return suggestions.get(gap_type, suggestions["other"])

    # --------------------------------------------------------------------- #
    # 5. Knowledge-graph construction
    # --------------------------------------------------------------------- #

    def build_knowledge_graph(self) -> dict:
        """Extract entities and relationships from all conversations.

        Returns::

            {
                entities:        [str, …],
                relationships:   [{source, relation, target, confidence}, …],
                confidence_scores: {entity: float, …},
                knowledge_clusters: [{topic, entities, density}, …],
                gaps:            [str, …]
            }
        """
        with self._lock:
            rows = self._conn.execute(
                "SELECT entity, relation, target, confidence FROM knowledge_graph"
            ).fetchall()

        if not rows:
            return {
                "entities": [],
                "relationships": [],
                "confidence_scores": {},
                "knowledge_clusters": [],
                "gaps": [],
            }

        entities: set[str] = set()
        relationships: list[dict] = []
        entity_confidences: dict[str, list[float]] = defaultdict(list)

        for row in rows:
            e, rel, tgt, conf = row["entity"], row["relation"], row["target"], row["confidence"]
            entities.add(e)
            if tgt:
                entities.add(tgt)
            relationships.append({
                "source": e,
                "relation": rel,
                "target": tgt,
                "confidence": conf,
            })
            entity_confidences[e].append(conf)

        confidence_scores = {
            e: round(float(np.mean(vs)), 3)
            for e, vs in entity_confidences.items()
        }

        # Simple clustering by shared co-occurrence
        clusters = self._cluster_entities(relationships)

        # Identify gaps: low-confidence clusters
        gaps = [
            c["topic"] for c in clusters
            if c["density"] < 0.3
        ]

        return {
            "entities": sorted(entities),
            "relationships": relationships,
            "confidence_scores": confidence_scores,
            "knowledge_clusters": clusters,
            "gaps": gaps,
        }

    def _cluster_entities(self, relationships: list[dict]) -> list[dict]:
        """Build crude topic clusters via connected components."""
        adjacency: dict[str, set[str]] = defaultdict(set)
        for rel in relationships:
            adjacency[rel["source"]].add(rel["target"] or "_self")

        visited: set[str] = set()
        clusters: list[dict] = []

        for entity in adjacency:
            if entity in visited:
                continue
            stack = [entity]
            component: set[str] = set()
            while stack:
                cur = stack.pop()
                if cur in visited:
                    continue
                visited.add(cur)
                component.add(cur)
                for neighbour in adjacency.get(cur, set()):
                    if neighbour not in visited:
                        stack.append(neighbour)

            if len(component) > 1:
                clusters.append({
                    "topic": max(component, key=lambda x: len(adjacency.get(x, set()))),
                    "entities": sorted(component),
                    "density": round(len(component) / max(len(adjacency), 1), 3),
                })

        return sorted(clusters, key=lambda c: -c["density"])

    # --------------------------------------------------------------------- #
    # 6. Improvement report
    # --------------------------------------------------------------------- #

    def get_improvement_report(self) -> str:
        """Generate a comprehensive human-readable report of what was learned.

        Shows before/after metrics, new capabilities, and next priorities.
        """
        with self._lock:
            total_interactions = self._conn.execute(
                "SELECT COUNT(*) as c FROM interactions"
            ).fetchone()["c"]

            avg_quality_row = self._conn.execute(
                "SELECT AVG(quality_score) as avg_q FROM interactions"
            ).fetchone()
            avg_quality = avg_quality_row["avg_q"] or 0.0

            mode_stats = self._conn.execute(
                "SELECT mode, AVG(quality_score) as avg_q, COUNT(*) as cnt "
                "FROM interactions GROUP BY mode ORDER BY avg_q DESC"
            ).fetchall()

            capability_rows = self._conn.execute(
                "SELECT capability, score, total_attempts FROM capability_scores ORDER BY score DESC"
            ).fetchall()

            lessons_rows = self._conn.execute(
                "SELECT lessons_learned, created_at FROM conversations ORDER BY created_at DESC LIMIT 20"
            ).fetchall()

        lines: list[str] = [
            "=" * 60,
            "  PROMETHEUS PRIME — IMPROVEMENT REPORT",
            f"  Generated: {datetime.utcnow().isoformat()} UTC",
            "=" * 60,
            "",
            "## Overall Statistics",
            f"- Total interactions recorded: {total_interactions}",
            f"- Average interaction quality: {avg_quality:.3f}",
            "",
            "## Performance by Mode",
        ]

        for row in mode_stats:
            lines.append(f"- **{row['mode']}**: {row['avg_q']:.3f} avg quality ({row['cnt']} interactions)")

        lines.extend(["", "## Capability Scores"])
        for row in capability_rows:
            bar = "█" * int(row["score"] * 10) + "░" * (10 - int(row["score"] * 10))
            lines.append(f"- **{row['capability']}**: [{bar}] {row['score']:.3f} ({row['total_attempts']} attempts)")

        lines.extend(["", "## Recent Lessons Learned"])
        all_lessons: list[str] = []
        for row in lessons_rows:
            if row["lessons_learned"]:
                all_lessons.extend(json.loads(row["lessons_learned"]))
        for i, lesson in enumerate(all_lessons[:10], 1):
            lines.append(f"{i}. {lesson}")

        # Gap analysis
        gaps = self.discover_capability_gaps()
        if gaps:
            lines.extend(["", "## Identified Capability Gaps"])
            for gap in gaps[:5]:
                lines.append(f"- **{gap['pattern']}** ({gap['frequency']} occurrences, {gap['percentage']}%)")
                lines.append(f"  → Suggested fix: {gap['suggested_fix']}")

        lines.extend(["", "## Next Learning Priorities"])
        if gaps:
            lines.append(f"1. Address '{gaps[0]['pattern']}' gap")
        lines.append("2. Continue prompt evolution for under-performing modes")
        lines.append("3. Expand knowledge graph with verified factual triples")
        lines.append("4. Increase feedback collection coverage")
        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)

    # --------------------------------------------------------------------- #
    # Helpers / utilities
    # --------------------------------------------------------------------- #

    def get_capability_scores(self) -> dict[str, float]:
        """Return current capability scores."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT capability, score FROM capability_scores"
            ).fetchall()
        return {r["capability"]: r["score"] for r in rows}

    def get_recent_interactions(self, limit: int = 20) -> list[dict]:
        """Return recent interactions for inspection."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM interactions ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()
        logger.info("MetaLearner connection closed.")
