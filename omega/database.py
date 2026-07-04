"""SQLite persistence layer for Omega Super AI.

Provides database initialization, CRUD operations for conversations,
search cache, long-term memory, learning progress, and scam reports.
"""

import json
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_DB_PATH: str = "omega_memory.db"
_local = threading.local()

_LOCK = threading.RLock()
_INITIALIZED: bool = False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _connection() -> sqlite3.Connection:
    """Return a thread-local SQLite connection (creates one if needed)."""
    conn: sqlite3.Connection | None = getattr(_local, "connection", None)
    if conn is None:
        conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        _local.connection = conn
    return conn


def _now_iso() -> str:
    """Return current UTC timestamp as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _hash_query(query: str) -> str:
    """Return a stable SHA-256 hex digest for *query* (cache key)."""
    import hashlib

    return hashlib.sha256(query.strip().lower().encode()).hexdigest()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def init_db(db_path: str | None = None) -> None:
    """Create all tables and indices if they do not already exist.

    This function is safe to call multiple times — it uses a module-level
    guard so subsequent invocations are no-ops in the same process.

    Args:
        db_path: Absolute or relative path to the SQLite database file.
            If ``None``, the previously configured path (or default) is used.
    """
    global _DB_PATH, _INITIALIZED

    if db_path is not None:
        _DB_PATH = db_path
        # Reset thread-local connections so the new path is picked up
        _local.connection = None

    with _LOCK:
        if _INITIALIZED:
            return

        conn = _connection()
        cursor = conn.cursor()

        # ---- conversations --------------------------------------------------
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT    NOT NULL DEFAULT '',
                session_id  TEXT    NOT NULL DEFAULT '',
                user_query  TEXT    NOT NULL DEFAULT '',
                response    TEXT    NOT NULL DEFAULT '',
                intent      TEXT    NOT NULL DEFAULT '',
                sources_json TEXT   NOT NULL DEFAULT '[]'
            );
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_conv_timestamp ON conversations(timestamp);"
        )

        # ---- search_cache ---------------------------------------------------
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS search_cache (
                query_hash   TEXT PRIMARY KEY,
                query        TEXT    NOT NULL,
                results_json TEXT    NOT NULL DEFAULT '[]',
                timestamp    TEXT    NOT NULL
            );
            """
        )

        # ---- memory ---------------------------------------------------------
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS memory (
                key       TEXT PRIMARY KEY,
                value     TEXT    NOT NULL,
                category  TEXT    NOT NULL DEFAULT 'general',
                timestamp TEXT    NOT NULL
            );
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_category ON memory(category);"
        )

        # ---- learning_progress ----------------------------------------------
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS learning_progress (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                topic               TEXT    NOT NULL,
                level               TEXT    NOT NULL DEFAULT 'beginner',
                completed_lessons_json TEXT NOT NULL DEFAULT '[]',
                timestamp           TEXT    NOT NULL
            );
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_learning_topic ON learning_progress(topic);"
        )

        # ---- scam_reports ---------------------------------------------------
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS scam_reports (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                scam_type    TEXT    NOT NULL,
                description  TEXT    NOT NULL DEFAULT '',
                indicators_json TEXT NOT NULL DEFAULT '[]',
                timestamp    TEXT    NOT NULL
            );
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_scam_type ON scam_reports(scam_type);"
        )

        conn.commit()
        _INITIALIZED = True


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------


def save_conversation(
    session_id: str,
    user_query: str,
    response: str,
    intent: str = "",
    sources: list[dict[str, Any]] | None = None,
) -> int:
    """Persist a single conversation turn.

    Args:
        session_id: Unique session identifier.
        user_query: The user's raw input text.
        response: Assistant's generated response.
        intent: Classified intent label (e.g. ``"research"``).
        sources: Optional list of source dictionaries to JSON-serialise.

    Returns:
        The auto-increment ``id`` of the newly inserted row.
    """
    init_db()
    conn = _connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO conversations (timestamp, session_id, user_query, response, intent, sources_json)
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        (
            _now_iso(),
            session_id,
            user_query,
            response,
            intent,
            json.dumps(sources or [], ensure_ascii=False),
        ),
    )
    conn.commit()
    return cursor.lastrowid  # type: ignore[return-value]


def get_history(
    session_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Retrieve conversation history, optionally filtered by session.

    Args:
        session_id: If provided, only rows for that session are returned.
        limit: Maximum rows to return.
        offset: Number of rows to skip (for pagination).

    Returns:
        List of conversation dictionaries ordered by *timestamp* DESC.
    """
    init_db()
    conn = _connection()
    cursor = conn.cursor()

    if session_id:
        cursor.execute(
            """
            SELECT id, timestamp, session_id, user_query, response, intent, sources_json
            FROM conversations
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?;
            """,
            (session_id, limit, offset),
        )
    else:
        cursor.execute(
            """
            SELECT id, timestamp, session_id, user_query, response, intent, sources_json
            FROM conversations
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?;
            """,
            (limit, offset),
        )

    rows = cursor.fetchall()
    return [
        {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "session_id": row["session_id"],
            "user_query": row["user_query"],
            "response": row["response"],
            "intent": row["intent"],
            "sources": json.loads(row["sources_json"]),
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Search cache
# ---------------------------------------------------------------------------


def save_cache(query: str, results: list[dict[str, Any]]) -> None:
    """Store (or overwrite) cached search results for *query*.

    Args:
        query: Raw search query string.
        results: List of result dictionaries to JSON-serialise.
    """
    init_db()
    conn = _connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO search_cache (query_hash, query, results_json, timestamp)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(query_hash) DO UPDATE SET
            query        = excluded.query,
            results_json = excluded.results_json,
            timestamp    = excluded.timestamp;
        """,
        (
            _hash_query(query),
            query,
            json.dumps(results, ensure_ascii=False),
            _now_iso(),
        ),
    )
    conn.commit()


def get_cache(
    query: str, ttl_hours: int = 24
) -> list[dict[str, Any]] | None:
    """Fetch cached results for *query* if they exist and are fresh.

    Args:
        query: Raw search query string.
        ttl_hours: Maximum age of cached entry in hours.

    Returns:
        Deserialised list of result dictionaries, or ``None`` if no
        fresh cache entry exists.
    """
    init_db()
    conn = _connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT results_json, timestamp FROM search_cache
        WHERE query_hash = ?;
        """,
        (_hash_query(query),),
    )
    row = cursor.fetchone()

    if row is None:
        return None

    # Expiration check
    try:
        cached_dt = datetime.fromisoformat(row["timestamp"])
        age_hours = (datetime.now(timezone.utc) - cached_dt).total_seconds() / 3600
        if age_hours > ttl_hours:
            return None
    except (ValueError, TypeError):
        return None

    return json.loads(row["results_json"])


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------


def save_memory(
    key: str, value: str, category: str = "general"
) -> None:
    """Persist a key/value memory entry (upsert semantics).

    Args:
        key: Unique lookup key.
        value: Arbitrary string value.
        category: Logical grouping tag (default ``"general"``).
    """
    init_db()
    conn = _connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO memory (key, value, category, timestamp)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value     = excluded.value,
            category  = excluded.category,
            timestamp = excluded.timestamp;
        """,
        (key, value, category, _now_iso()),
    )
    conn.commit()


def get_memory(key: str | None = None, category: str | None = None) -> dict[str, str] | list[dict[str, Any]] | None:
    """Retrieve memory entries.

    Args:
        key: Exact key to look up. If given, a single dict (or ``None``)
            is returned.
        category: If *key* is omitted, filter by this category.

    Returns:
        - Single ``{key, value, category, timestamp}`` dict when *key* is given.
        - List of dicts when only *category* is given (or neither).
        - ``None`` when *key* is given but not found.
    """
    init_db()
    conn = _connection()
    cursor = conn.cursor()

    if key:
        cursor.execute(
            "SELECT key, value, category, timestamp FROM memory WHERE key = ?;",
            (key,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return {
            "key": row["key"],
            "value": row["value"],
            "category": row["category"],
            "timestamp": row["timestamp"],
        }

    if category:
        cursor.execute(
            "SELECT key, value, category, timestamp FROM memory WHERE category = ? ORDER BY timestamp DESC;",
            (category,),
        )
    else:
        cursor.execute(
            "SELECT key, value, category, timestamp FROM memory ORDER BY timestamp DESC;"
        )

    rows = cursor.fetchall()
    return [
        {
            "key": row["key"],
            "value": row["value"],
            "category": row["category"],
            "timestamp": row["timestamp"],
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Learning progress
# ---------------------------------------------------------------------------


def save_learning(
    topic: str,
    level: str = "beginner",
    completed_lessons: list[str] | None = None,
) -> int:
    """Record learning progress for a topic (upsert by topic name).

    Args:
        topic: Topic or course name.
        level: Proficiency level (e.g. ``"beginner"``, ``"advanced"``).
        completed_lessons: List of completed lesson identifiers.

    Returns:
        The ``id`` of the upserted row.
    """
    init_db()
    conn = _connection()
    cursor = conn.cursor()

    # Check for existing entry
    cursor.execute("SELECT id FROM learning_progress WHERE topic = ?;", (topic,))
    row = cursor.fetchone()

    lessons_json = json.dumps(completed_lessons or [], ensure_ascii=False)
    now = _now_iso()

    if row:
        cursor.execute(
            """
            UPDATE learning_progress
            SET level = ?, completed_lessons_json = ?, timestamp = ?
            WHERE topic = ?;
            """,
            (level, lessons_json, now, topic),
        )
        conn.commit()
        return row["id"]

    cursor.execute(
        """
        INSERT INTO learning_progress (topic, level, completed_lessons_json, timestamp)
        VALUES (?, ?, ?, ?);
        """,
        (topic, level, lessons_json, now),
    )
    conn.commit()
    return cursor.lastrowid  # type: ignore[return-value]


def get_learning(topic: str | None = None) -> dict[str, Any] | list[dict[str, Any]]:
    """Fetch learning progress records.

    Args:
        topic: Exact topic name. If provided, a single dict is returned;
            otherwise all records are returned.

    Returns:
        Single progress dict or list of dicts.  Empty list when no records
        match.
    """
    init_db()
    conn = _connection()
    cursor = conn.cursor()

    if topic:
        cursor.execute(
            """
            SELECT id, topic, level, completed_lessons_json, timestamp
            FROM learning_progress WHERE topic = ?;
            """,
            (topic,),
        )
        row = cursor.fetchone()
        if row is None:
            return []
        return {
            "id": row["id"],
            "topic": row["topic"],
            "level": row["level"],
            "completed_lessons": json.loads(row["completed_lessons_json"]),
            "timestamp": row["timestamp"],
        }

    cursor.execute(
        """
        SELECT id, topic, level, completed_lessons_json, timestamp
        FROM learning_progress ORDER BY timestamp DESC;
        """
    )
    rows = cursor.fetchall()
    return [
        {
            "id": row["id"],
            "topic": row["topic"],
            "level": row["level"],
            "completed_lessons": json.loads(row["completed_lessons_json"]),
            "timestamp": row["timestamp"],
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Scam reports
# ---------------------------------------------------------------------------


def save_scam_report(
    scam_type: str,
    description: str,
    indicators: list[str] | None = None,
) -> int:
    """Store a scam analysis report.

    Args:
        scam_type: Category of scam (e.g. ``"phishing"``).
        description: Human-readable description of the scam.
        indicators: List of red-flag indicators.

    Returns:
        The auto-increment ``id`` of the inserted row.
    """
    init_db()
    conn = _connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO scam_reports (scam_type, description, indicators_json, timestamp)
        VALUES (?, ?, ?, ?);
        """,
        (
            scam_type,
            description,
            json.dumps(indicators or [], ensure_ascii=False),
            _now_iso(),
        ),
    )
    conn.commit()
    return cursor.lastrowid  # type: ignore[return-value]


def get_scam_reports(
    scam_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Retrieve scam reports with optional filtering.

    Args:
        scam_type: Filter by scam category.
        limit: Maximum rows to return.
        offset: Pagination offset.

    Returns:
        List of scam-report dicts ordered by timestamp DESC.
    """
    init_db()
    conn = _connection()
    cursor = conn.cursor()

    if scam_type:
        cursor.execute(
            """
            SELECT id, scam_type, description, indicators_json, timestamp
            FROM scam_reports
            WHERE scam_type = ?
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?;
            """,
            (scam_type, limit, offset),
        )
    else:
        cursor.execute(
            """
            SELECT id, scam_type, description, indicators_json, timestamp
            FROM scam_reports
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?;
            """,
            (limit, offset),
        )

    rows = cursor.fetchall()
    return [
        {
            "id": row["id"],
            "scam_type": row["scam_type"],
            "description": row["description"],
            "indicators": json.loads(row["indicators_json"]),
            "timestamp": row["timestamp"],
        }
        for row in rows
    ]


def close_db() -> None:
    """Close the thread-local database connection (if open)."""
    conn: sqlite3.Connection | None = getattr(_local, "connection", None)
    if conn is not None:
        conn.close()
        _local.connection = None
