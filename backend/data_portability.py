"""
Data Portability Module for Luqi AI
====================================

Provides GDPR-compliant data export, import, deletion, and scheduled export
capabilities. All user data can be exported in JSON, Markdown, CSV, or ZIP
formats. Import validates data integrity before writing. Deletion requires
explicit confirmation for safety.

Author: Luqi AI Backend Team
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import os
import sqlite3
import tempfile
import uuid
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants & configuration
# ---------------------------------------------------------------------------

DEFAULT_DB_DIR = "./data"
SUBSCRIPTIONS_DB = os.path.join(DEFAULT_DB_DIR, "subscriptions.db")
DASHBOARD_DB = os.path.join(DEFAULT_DB_DIR, "dashboard.db")
MEMORY_DB = os.path.join(DEFAULT_DB_DIR, "memory.db")
VOICE_CLONES_DIR = os.path.join(DEFAULT_DB_DIR, "voice_clones")
EXPORT_DIR = os.path.join(DEFAULT_DB_DIR, "exports")
SCHEDULED_EXPORTS_DB = os.path.join(DEFAULT_DB_DIR, "scheduled_exports.db")

ALLOWED_EXPORT_FORMATS = {"json", "zip", "markdown"}
ALLOWED_IMPORT_VERSIONS = {"1.0", "2.0"}
SENSITIVE_KEYS = {
    "api_key", "password", "secret", "token", "auth",
    "credit_card", "payment_token", "private_key",
}

GDPR_CONFIRMATION_PHRASE = "DELETE ALL MY DATA PERMANENTLY"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_dir(path: str) -> None:
    """Create directory if it doesn't exist."""
    Path(path).mkdir(parents=True, exist_ok=True)


def _db_cursor(db_path: str) -> Optional[sqlite3.Cursor]:
    """Return a cursor for the given DB, or None if DB does not exist."""
    if not os.path.isfile(db_path):
        return None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn.cursor()
    except sqlite3.Error as exc:
        logger.warning("Cannot open %s: %s", db_path, exc)
        return None


def _safe_query(
    cursor: sqlite3.Cursor,
    query: str,
    params: tuple = (),
) -> List[sqlite3.Row]:
    """Execute query safely, returning empty list on error."""
    try:
        cursor.execute(query, params)
        return cursor.fetchall()
    except sqlite3.Error as exc:
        logger.warning("Query failed: %s | params=%s | error=%s", query, params, exc)
        return []


def _rows_to_dicts(rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
    """Convert sqlite3.Row objects to plain dictionaries."""
    return [dict(row) for row in rows]


def _strip_sensitive(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove or mask sensitive fields from a dictionary."""
    if not isinstance(data, dict):
        return data
    cleaned: Dict[str, Any] = {}
    for key, value in data.items():
        lk = key.lower()
        if any(sk in lk for sk in SENSITIVE_KEYS):
            cleaned[key] = "***REDACTED***"
        elif isinstance(value, dict):
            cleaned[key] = _strip_sensitive(value)
        elif isinstance(value, list):
            cleaned[key] = [
                _strip_sensitive(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            cleaned[key] = value
    return cleaned


def _generate_export_filename(user_id: str, fmt: str) -> str:
    """Generate a unique, descriptive filename for an export."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    short_uid = hashlib.sha256(user_id.encode()).hexdigest()[:8]
    ext = "zip" if fmt == "zip" else fmt
    return f"luqi_export_{short_uid}_{timestamp}.{ext}"


def _generate_file_path(user_id: str, fmt: str) -> str:
    """Generate full file path for an export."""
    _ensure_dir(EXPORT_DIR)
    filename = _generate_export_filename(user_id, fmt)
    return os.path.join(EXPORT_DIR, filename)


# ---------------------------------------------------------------------------
# Internal data collection
# ---------------------------------------------------------------------------

def _collect_all_user_data(user_id: str) -> Dict[str, Any]:
    """Collect all user data from every known database.

    Queries subscriptions, dashboard, memory, and voice-clone stores for
    rows belonging to *user_id*.  Missing databases or tables are skipped
    gracefully so the function never raises.

    Returns
    -------
    dict
        Unified data structure with keys:
        ``user_id``, ``export_version``, ``exported_at``,
        ``subscription``, ``usage_log``, ``api_log``,
        ``widgets``, ``knowledge_base``, ``habits``,
        ``conversations``, ``voice_clones``.
    """
    result: Dict[str, Any] = {
        "user_id": hashlib.sha256(user_id.encode()).hexdigest(),
        "export_version": "2.0",
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "subscription": [],
        "usage_log": [],
        "api_log": [],
        "widgets": [],
        "knowledge_base": [],
        "habits": [],
        "conversations": [],
        "voice_clones": [],
    }

    # --- subscriptions.db ---
    cur = _db_cursor(SUBSCRIPTIONS_DB)
    if cur is not None:
        result["subscription"] = _rows_to_dicts(
            _safe_query(cur, "SELECT * FROM subscription WHERE user_id = ?", (user_id,))
        )
        result["usage_log"] = _rows_to_dicts(
            _safe_query(cur, "SELECT * FROM usage_log WHERE user_id = ?", (user_id,))
        )
        result["api_log"] = _rows_to_dicts(
            _safe_query(cur, "SELECT * FROM api_log WHERE user_id = ?", (user_id,))
        )
        try:
            cur.connection.close()
        except Exception:
            pass

    # --- dashboard.db ---
    cur = _db_cursor(DASHBOARD_DB)
    if cur is not None:
        result["widgets"] = _rows_to_dicts(
            _safe_query(cur, "SELECT * FROM widgets WHERE user_id = ?", (user_id,))
        )
        result["knowledge_base"] = _rows_to_dicts(
            _safe_query(cur, "SELECT * FROM knowledge_base WHERE user_id = ?", (user_id,))
        )
        result["habits"] = _rows_to_dicts(
            _safe_query(cur, "SELECT * FROM habits WHERE user_id = ?", (user_id,))
        )
        try:
            cur.connection.close()
        except Exception:
            pass

    # --- memory.db (conversations) ---
    cur = _db_cursor(MEMORY_DB)
    if cur is not None:
        result["conversations"] = _rows_to_dicts(
            _safe_query(cur, "SELECT * FROM conversations WHERE user_id = ?", (user_id,))
        )
        # Also fetch messages per conversation
        for conv in result["conversations"]:
            session_id = conv.get("session_id") or conv.get("id")
            if session_id:
                conv["messages"] = _rows_to_dicts(
                    _safe_query(
                        cur,
                        "SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp",
                        (session_id,),
                    )
                )
        try:
            cur.connection.close()
        except Exception:
            pass

    # --- voice clones (filesystem) ---
    user_voice_dir = os.path.join(VOICE_CLONES_DIR, user_id)
    if os.path.isdir(user_voice_dir):
        result["voice_clones"] = [
            {
                "file_name": fname,
                "file_path": os.path.join(user_voice_dir, fname),
                "size_bytes": os.path.getsize(os.path.join(user_voice_dir, fname)),
                "modified": datetime.utcfromtimestamp(
                    os.path.getmtime(os.path.join(user_voice_dir, fname))
                ).isoformat()
                + "Z",
            }
            for fname in os.listdir(user_voice_dir)
            if os.path.isfile(os.path.join(user_voice_dir, fname))
        ]

    return _strip_sensitive(result)


def _summarize_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Produce a human-readable summary of collected data."""
    summary: Dict[str, Any] = {
        "export_version": data.get("export_version"),
        "exported_at": data.get("exported_at"),
        "record_counts": {},
        "total_records": 0,
        "voice_clone_files": len(data.get("voice_clones", [])),
        "voice_clone_total_bytes": sum(
            vc.get("size_bytes", 0) for vc in data.get("voice_clones", [])
        ),
    }
    for key in (
        "subscription", "usage_log", "api_log", "widgets",
        "knowledge_base", "habits", "conversations",
    ):
        count = len(data.get(key, []))
        summary["record_counts"][key] = count
        summary["total_records"] += count
    return summary


# ---------------------------------------------------------------------------
# Export functions
# ---------------------------------------------------------------------------

def export_user_data(user_id: str, format: str = "json") -> Dict[str, Any]:
    """Export all data for a user in the specified format.

    Parameters
    ----------
    user_id : str
        The unique identifier of the user.
    format : str, optional
        One of ``"json"``, ``"zip"``, or ``"markdown"``.  Default is ``"json"``.

    Returns
    -------
    dict
        ``{file_path, file_name, size, format, data_summary}``
    """
    if format not in ALLOWED_EXPORT_FORMATS:
        raise ValueError(f"Unsupported format '{format}'. Choose from {ALLOWED_EXPORT_FORMATS}")

    data = _collect_all_user_data(user_id)
    summary = _summarize_data(data)
    file_path = _generate_file_path(user_id, format)

    if format == "json":
        content = to_json(data, indent=2)
        with open(file_path, "w", encoding="utf-8") as fh:
            fh.write(content)

    elif format == "markdown":
        content = to_markdown(data)
        with open(file_path, "w", encoding="utf-8") as fh:
            fh.write(content)

    elif format == "zip":
        zip_info = create_zip_export(user_id)
        file_path = zip_info["file_path"]

    size = os.path.getsize(file_path)

    return {
        "file_path": file_path,
        "file_name": os.path.basename(file_path),
        "size": size,
        "format": format,
        "data_summary": summary,
    }


def export_conversations(user_id: str, format: str = "json") -> Dict[str, Any]:
    """Export chat conversations for a user.

    Returns
    -------
    dict
        ``{conversations: [{session_id, messages, timestamp, ...}]}``
    """
    cur = _db_cursor(MEMORY_DB)
    conversations: List[Dict[str, Any]] = []
    if cur is not None:
        rows = _safe_query(
            cur, "SELECT * FROM conversations WHERE user_id = ?", (user_id,)
        )
        for row in rows:
            conv = dict(row)
            session_id = conv.get("session_id") or conv.get("id")
            if session_id:
                conv["messages"] = _rows_to_dicts(
                    _safe_query(
                        cur,
                        "SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp",
                        (session_id,),
                    )
                )
            conversations.append(conv)
        try:
            cur.connection.close()
        except Exception:
            pass

    result = {"conversations": _strip_sensitive(conversations)}

    if format == "json":
        result["json"] = to_json(result, indent=2)
    elif format == "markdown":
        result["markdown"] = _conversations_to_markdown(conversations)

    return result


def export_knowledge_base(user_id: str) -> Dict[str, Any]:
    """Export knowledge-base pages for a user.

    Returns
    -------
    dict
        ``{pages: [{id, title, content, created_at, ...}]}``
    """
    cur = _db_cursor(DASHBOARD_DB)
    pages: List[Dict[str, Any]] = []
    if cur is not None:
        pages = _rows_to_dicts(
            _safe_query(cur, "SELECT * FROM knowledge_base WHERE user_id = ?", (user_id,))
        )
        try:
            cur.connection.close()
        except Exception:
            pass
    return {"pages": _strip_sensitive(pages)}


def export_habits(user_id: str) -> Dict[str, Any]:
    """Export habit-tracking data for a user.

    Returns
    -------
    dict
        ``{habits: [{id, name, streak, ...}], completions: [...]}``
    """
    cur = _db_cursor(DASHBOARD_DB)
    habits: List[Dict[str, Any]] = []
    completions: List[Dict[str, Any]] = []
    if cur is not None:
        habits = _rows_to_dicts(
            _safe_query(cur, "SELECT * FROM habits WHERE user_id = ?", (user_id,))
        )
        habit_ids = [h.get("id") for h in habits if h.get("id")]
        if habit_ids:
            placeholders = ",".join("?" * len(habit_ids))
            completions = _rows_to_dicts(
                _safe_query(
                    cur,
                    f"SELECT * FROM habit_completions WHERE habit_id IN ({placeholders})",
                    tuple(habit_ids),
                )
            )
        try:
            cur.connection.close()
        except Exception:
            pass
    return {"habits": _strip_sensitive(habits), "completions": _strip_sensitive(completions)}


def export_usage_report(user_id: str, days: int = 30) -> Dict[str, Any]:
    """Export a detailed usage report for a given period.

    Returns
    -------
    dict
        ``{summary, daily_breakdown, endpoint_breakdown, messages_per_day}``
    """
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    cur = _db_cursor(SUBSCRIPTIONS_DB)

    usage_rows: List[Dict[str, Any]] = []
    api_rows: List[Dict[str, Any]] = []
    msg_rows: List[Dict[str, Any]] = []

    if cur is not None:
        usage_rows = _rows_to_dicts(
            _safe_query(
                cur,
                "SELECT * FROM usage_log WHERE user_id = ? AND timestamp >= ?",
                (user_id, since),
            )
        )
        api_rows = _rows_to_dicts(
            _safe_query(
                cur,
                "SELECT * FROM api_log WHERE user_id = ? AND timestamp >= ?",
                (user_id, since),
            )
        )
        try:
            cur.connection.close()
        except Exception:
            pass

    # conversations / messages from memory.db
    cur = _db_cursor(MEMORY_DB)
    if cur is not None:
        msg_rows = _rows_to_dicts(
            _safe_query(
                cur,
                """
                SELECT m.* FROM messages m
                JOIN conversations c ON m.session_id = c.session_id
                WHERE c.user_id = ? AND m.timestamp >= ?
                """,
                (user_id, since),
            )
        )
        try:
            cur.connection.close()
        except Exception:
            pass

    # --- daily breakdown ---
    daily: Dict[str, Dict[str, int]] = {}
    for row in usage_rows:
        day = (row.get("timestamp") or "")[:10]
        if day:
            daily.setdefault(day, {"requests": 0, "tokens": 0, "messages": 0})
            daily[day]["requests"] += 1
            daily[day]["tokens"] += row.get("tokens_used", 0) or 0

    for row in msg_rows:
        day = (row.get("timestamp") or "")[:10]
        if day:
            daily.setdefault(day, {"requests": 0, "tokens": 0, "messages": 0})
            daily[day]["messages"] += 1

    daily_breakdown = [
        {"date": d, **counts} for d, counts in sorted(daily.items())
    ]

    # --- endpoint breakdown ---
    endpoint_counts: Dict[str, int] = {}
    for row in api_rows:
        ep = row.get("endpoint") or "unknown"
        endpoint_counts[ep] = endpoint_counts.get(ep, 0) + 1
    endpoint_breakdown = [
        {"endpoint": ep, "count": c} for ep, c in sorted(endpoint_counts.items(), key=lambda x: -x[1])
    ]

    # --- messages per day ---
    messages_per_day = [
        {"date": d, "count": c["messages"]}
        for d, c in sorted(daily.items())
    ]

    total_requests = sum(d["requests"] for d in daily_breakdown)
    total_tokens = sum(d["tokens"] for d in daily_breakdown)
    total_messages = sum(d["messages"] for d in daily_breakdown)

    return {
        "summary": {
            "period_days": days,
            "total_requests": total_requests,
            "total_tokens": total_tokens,
            "total_messages": total_messages,
            "unique_endpoints": len(endpoint_breakdown),
        },
        "daily_breakdown": daily_breakdown,
        "endpoint_breakdown": endpoint_breakdown,
        "messages_per_day": messages_per_day,
    }


# ---------------------------------------------------------------------------
# Import system
# ---------------------------------------------------------------------------

def validate_import_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate import data structure before writing.

    Returns
    -------
    dict
        ``{valid: bool, errors: list, warnings: list}``
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(data, dict):
        errors.append("Root data must be a JSON object (dict).")
        return {"valid": False, "errors": errors, "warnings": warnings}

    version = data.get("export_version")
    if version is None:
        warnings.append("Missing 'export_version' field; assuming 1.0.")
    elif str(version) not in ALLOWED_IMPORT_VERSIONS:
        errors.append(f"Unsupported export_version '{version}'.")

    expected_keys = {
        "user_id", "export_version", "exported_at",
        "subscription", "usage_log", "api_log",
        "widgets", "knowledge_base", "habits",
        "conversations", "voice_clones",
    }
    present_keys = set(data.keys())
    missing = expected_keys - present_keys
    if missing:
        warnings.append(f"Missing expected top-level keys: {sorted(missing)}")

    # Validate array fields are lists
    for key in ("subscription", "usage_log", "api_log", "widgets",
                "knowledge_base", "habits", "conversations", "voice_clones"):
        value = data.get(key)
        if value is not None and not isinstance(value, list):
            errors.append(f"Field '{key}' must be a list, got {type(value).__name__}.")

    # Check for sensitive data leakage
    raw = json.dumps(data)
    for sk in SENSITIVE_KEYS:
        if f'"{sk}"' in raw.lower() and "***REDACTED***" not in raw:
            warnings.append(f"Potential unredacted sensitive field '{sk}' detected.")

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


def import_user_data(user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Import previously exported data for a user.

    Validates structure before writing.  Returns per-collection counts.

    Returns
    -------
    dict
        ``{imported, skipped, errors, counts}``
    """
    validation = validate_import_data(data)
    if not validation["valid"]:
        return {"imported": False, "skipped": 0, "errors": validation["errors"], "counts": {}}

    counts: Dict[str, int] = {}
    errors: List[str] = []

    # Import conversations first (no FK dependencies)
    conv_result = import_conversations(user_id, data.get("conversations", []))
    counts["conversations"] = conv_result.get("imported", 0)
    errors.extend(conv_result.get("errors", []))

    # Knowledge base
    kb_result = import_knowledge_base(user_id, data.get("knowledge_base", []))
    counts["knowledge_base"] = kb_result.get("imported", 0)
    errors.extend(kb_result.get("errors", []))

    # Habits
    habits_result = import_habits(user_id, data.get("habits", []))
    counts["habits"] = habits_result.get("imported", 0)
    errors.extend(habits_result.get("errors", []))

    total_imported = sum(counts.values())
    return {
        "imported": True,
        "skipped": 0,
        "errors": errors,
        "counts": counts,
        "total_imported": total_imported,
        "validation_warnings": validation.get("warnings", []),
    }


def import_conversations(user_id: str, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Import chat conversations.

    Returns
    -------
    dict
        ``{imported, errors}``
    """
    if not conversations:
        return {"imported": 0, "errors": []}

    inserted = 0
    errors: List[str] = []
    cur = _db_cursor(MEMORY_DB)
    if cur is None:
        return {"imported": 0, "errors": ["memory.db not available"]}

    try:
        for conv in conversations:
            try:
                session_id = conv.get("session_id") or conv.get("id") or str(uuid.uuid4())
                timestamp = conv.get("timestamp") or conv.get("created_at") or datetime.utcnow().isoformat()
                title = conv.get("title", "Imported conversation")

                # Upsert conversation
                cur.execute(
                    """
                    INSERT OR REPLACE INTO conversations (session_id, user_id, title, timestamp)
                    VALUES (?, ?, ?, ?)
                    """,
                    (session_id, user_id, title, timestamp),
                )

                # Insert messages
                for msg in conv.get("messages", []):
                    cur.execute(
                        """
                        INSERT OR REPLACE INTO messages (session_id, role, content, timestamp)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            session_id,
                            msg.get("role", "user"),
                            msg.get("content", ""),
                            msg.get("timestamp") or timestamp,
                        ),
                    )
                inserted += 1
            except sqlite3.Error as exc:
                errors.append(str(exc))
        cur.connection.commit()
    except Exception as exc:
        errors.append(str(exc))
    finally:
        try:
            cur.connection.close()
        except Exception:
            pass

    return {"imported": inserted, "errors": errors}


def import_knowledge_base(user_id: str, pages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Import knowledge-base pages.

    Returns
    -------
    dict
        ``{imported, errors}``
    """
    if not pages:
        return {"imported": 0, "errors": []}

    inserted = 0
    errors: List[str] = []
    cur = _db_cursor(DASHBOARD_DB)
    if cur is None:
        return {"imported": 0, "errors": ["dashboard.db not available"]}

    try:
        for page in pages:
            try:
                cur.execute(
                    """
                    INSERT OR REPLACE INTO knowledge_base
                    (id, user_id, title, content, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        page.get("id") or str(uuid.uuid4()),
                        user_id,
                        page.get("title", "Untitled"),
                        page.get("content", ""),
                        page.get("created_at") or datetime.utcnow().isoformat(),
                        page.get("updated_at") or datetime.utcnow().isoformat(),
                    ),
                )
                inserted += 1
            except sqlite3.Error as exc:
                errors.append(str(exc))
        cur.connection.commit()
    except Exception as exc:
        errors.append(str(exc))
    finally:
        try:
            cur.connection.close()
        except Exception:
            pass

    return {"imported": inserted, "errors": errors}


def import_habits(user_id: str, habits: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Import habits and their completions.

    Returns
    -------
    dict
        ``{imported, errors}``
    """
    if not habits:
        return {"imported": 0, "errors": []}

    inserted = 0
    errors: List[str] = []
    cur = _db_cursor(DASHBOARD_DB)
    if cur is None:
        return {"imported": 0, "errors": ["dashboard.db not available"]}

    try:
        for habit in habits:
            try:
                habit_id = habit.get("id") or str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT OR REPLACE INTO habits
                    (id, user_id, name, description, frequency, streak, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        habit_id,
                        user_id,
                        habit.get("name", "Unnamed habit"),
                        habit.get("description", ""),
                        habit.get("frequency", "daily"),
                        habit.get("streak", 0),
                        habit.get("created_at") or datetime.utcnow().isoformat(),
                    ),
                )

                # Import completions if present
                for comp in habit.get("completions", []):
                    cur.execute(
                        """
                        INSERT OR REPLACE INTO habit_completions
                        (habit_id, completed_at, notes)
                        VALUES (?, ?, ?)
                        """,
                        (
                            habit_id,
                            comp.get("completed_at") or datetime.utcnow().isoformat(),
                            comp.get("notes", ""),
                        ),
                    )
                inserted += 1
            except sqlite3.Error as exc:
                errors.append(str(exc))
        cur.connection.commit()
    except Exception as exc:
        errors.append(str(exc))
    finally:
        try:
            cur.connection.close()
        except Exception:
            pass

    return {"imported": inserted, "errors": errors}


# ---------------------------------------------------------------------------
# Format converters
# ---------------------------------------------------------------------------

def to_json(data: Dict[str, Any], indent: int = 2) -> str:
    """Convert data to a formatted JSON string.

    Handles datetime objects and other non-serialisable types gracefully.
    """
    class _Encoder(json.JSONEncoder):
        def default(self, o: Any) -> Any:
            if isinstance(o, datetime):
                return o.isoformat()
            if isinstance(o, bytes):
                return o.decode("utf-8", errors="replace")
            return super().default(o)

    return json.dumps(data, indent=indent, ensure_ascii=False, cls=_Encoder)


def to_csv(data: List[Dict[str, Any]], headers: Optional[List[str]] = None) -> str:
    """Convert a list of dictionaries to CSV format.

    Parameters
    ----------
    data : list
        List of dictionaries with uniform keys.
    headers : list, optional
        Explicit column order.  If omitted, keys from the first row are used.

    Returns
    -------
    str
        CSV content as a string.
    """
    if not data:
        return ""
    if headers is None:
        headers = list(data[0].keys())
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for row in data:
        writer.writerow(row)
    return output.getvalue()


def to_markdown(data: Dict[str, Any]) -> str:
    """Convert a full user-data export to a human-readable Markdown report.

    Returns
    -------
    str
        Markdown document containing all user data sections.
    """
    lines: List[str] = []
    lines.append("# Luqi AI – Data Export Report")
    lines.append("")
    lines.append(f"- **User hash**: {data.get('user_id', 'N/A')}")
    lines.append(f"- **Export version**: {data.get('export_version', 'N/A')}")
    lines.append(f"- **Exported at**: {data.get('exported_at', 'N/A')}")
    lines.append("")

    # Subscriptions
    lines.append("## Subscriptions")
    subs = data.get("subscription", [])
    if subs:
        lines.append("| Plan | Status | Start | End |")
        lines.append("|------|--------|-------|-----|")
        for s in subs:
            lines.append(
                f"| {s.get('plan','')} | {s.get('status','')} "
                f"| {s.get('start_date','')} | {s.get('end_date','')} |"
            )
    else:
        lines.append("_No subscription records found._")
    lines.append("")

    # Usage log
    lines.append("## Usage Log")
    usage = data.get("usage_log", [])
    if usage:
        lines.append(f"_{len(usage)} usage records._")
        lines.append("| Timestamp | Tokens | Endpoint |")
        lines.append("|-----------|--------|----------|")
        for u in usage[:50]:
            lines.append(
                f"| {u.get('timestamp','')} | {u.get('tokens_used',0)} "
                f"| {u.get('endpoint','')} |"
            )
        if len(usage) > 50:
            lines.append(f"_... and {len(usage) - 50} more records._")
    else:
        lines.append("_No usage records found._")
    lines.append("")

    # API log
    lines.append("## API Log")
    api = data.get("api_log", [])
    if api:
        lines.append(f"_{len(api)} API log records._")
    else:
        lines.append("_No API log records found._")
    lines.append("")

    # Knowledge base
    lines.append("## Knowledge Base")
    kb = data.get("knowledge_base", [])
    if kb:
        for page in kb:
            lines.append(f"### {page.get('title', 'Untitled')}")
            lines.append(f"_Created: {page.get('created_at', 'N/A')}_")
            lines.append("")
            content = page.get("content", "")
            if content:
                lines.append(content[:2000])
                if len(content) > 2000:
                    lines.append("_... (truncated)_")
            lines.append("")
    else:
        lines.append("_No knowledge base pages found._")
    lines.append("")

    # Habits
    lines.append("## Habits")
    habits = data.get("habits", [])
    if habits:
        lines.append("| Name | Frequency | Streak | Created |")
        lines.append("|------|-----------|--------|----------|")
        for h in habits:
            lines.append(
                f"| {h.get('name','')} | {h.get('frequency','')} "
                f"| {h.get('streak',0)} | {h.get('created_at','')} |"
            )
    else:
        lines.append("_No habits found._")
    lines.append("")

    # Conversations
    lines.append("## Conversations")
    convs = data.get("conversations", [])
    if convs:
        for conv in convs:
            lines.append(f"### {conv.get('title', 'Conversation')}")
            lines.append(f"_Session: {conv.get('session_id', 'N/A')}_")
            messages = conv.get("messages", [])
            for msg in messages[:20]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                lines.append(f"**{role}**: {content[:500]}")
                if len(content) > 500:
                    lines.append("_... (truncated)_")
            if len(messages) > 20:
                lines.append(f"_... and {len(messages) - 20} more messages._")
            lines.append("")
    else:
        lines.append("_No conversations found._")
    lines.append("")

    # Voice clones
    lines.append("## Voice Clones")
    clones = data.get("voice_clones", [])
    if clones:
        lines.append("| File | Size (bytes) | Modified |")
        lines.append("|------|-------------|----------|")
        for vc in clones:
            lines.append(
                f"| {vc.get('file_name','')} | {vc.get('size_bytes',0)} "
                f"| {vc.get('modified','')} |"
            )
    else:
        lines.append("_No voice clones found._")
    lines.append("")

    lines.append("---")
    lines.append("_End of export report.  Generated by Luqi AI Data Portability Module._")
    return "\n".join(lines)


def _conversations_to_markdown(conversations: List[Dict[str, Any]]) -> str:
    """Convert conversations list to a standalone Markdown document."""
    lines: List[str] = []
    lines.append("# Chat Conversations Export")
    lines.append("")
    for conv in conversations:
        lines.append(f"## {conv.get('title', 'Conversation')}")
        lines.append(f"- **Session ID**: {conv.get('session_id', 'N/A')}")
        lines.append(f"- **Timestamp**: {conv.get('timestamp', 'N/A')}")
        lines.append("")
        for msg in conv.get("messages", []):
            role = msg.get("role", "user")
            content = msg.get("content", "")
            ts = msg.get("timestamp", "")
            lines.append(f"**{role}** ({ts}):")
            lines.append(f"> {content}")
            lines.append("")
    return "\n".join(lines)


def create_zip_export(user_id: str) -> Dict[str, Any]:
    """Create a ZIP archive with all user data in multiple formats.

    The archive contains:
    - ``data.json``      – full structured export
    - ``conversations.md`` – chat history in Markdown
    - ``kb.md``          – knowledge base pages
    - ``habits.csv``     – habit tracking data
    - ``usage.csv``      – usage log summary

    Returns
    -------
    dict
        ``{file_path, file_name, size}``
    """
    data = _collect_all_user_data(user_id)
    file_path = _generate_file_path(user_id, "zip")

    with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # data.json
        zf.writestr("data.json", to_json(data, indent=2))

        # conversations.md
        conversations = data.get("conversations", [])
        zf.writestr("conversations.md", _conversations_to_markdown(conversations))

        # kb.md
        kb_pages = data.get("knowledge_base", [])
        kb_lines = ["# Knowledge Base Export\n"]
        for page in kb_pages:
            kb_lines.append(f"## {page.get('title', 'Untitled')}\n")
            kb_lines.append(f"_Created: {page.get('created_at', 'N/A')}_\n")
            kb_lines.append(page.get("content", "") + "\n\n")
        zf.writestr("kb.md", "\n".join(kb_lines))

        # habits.csv
        habits = data.get("habits", [])
        if habits:
            zf.writestr("habits.csv", to_csv(habits, ["name", "frequency", "streak", "created_at"]))
        else:
            zf.writestr("habits.csv", "name,frequency,streak,created_at\n")

        # usage.csv
        usage = data.get("usage_log", [])
        if usage:
            zf.writestr("usage.csv", to_csv(usage, ["timestamp", "tokens_used", "endpoint"]))
        else:
            zf.writestr("usage.csv", "timestamp,tokens_used,endpoint\n")

        # README
        zf.writestr(
            "README.txt",
            "Luqi AI Data Export\n"
            "===================\n"
            "This archive contains your personal data exported from Luqi AI.\n"
            "Files:\n"
            "  - data.json        : Full structured export (machine-readable)\n"
            "  - conversations.md : Chat history (human-readable)\n"
            "  - kb.md            : Knowledge base pages\n"
            "  - habits.csv       : Habit tracking data\n"
            "  - usage.csv        : Usage log summary\n"
            f"\nExported at: {datetime.utcnow().isoformat()}Z\n",
        )

    size = os.path.getsize(file_path)
    return {"file_path": file_path, "file_name": os.path.basename(file_path), "size": size}


# ---------------------------------------------------------------------------
# GDPR – Data deletion & anonymisation
# ---------------------------------------------------------------------------

def delete_all_user_data(user_id: str, confirmation: str = "") -> Dict[str, Any]:
    """Delete **all** data for a user (GDPR right to erasure).

    Requires the exact confirmation string to prevent accidental deletion.

    Returns
    -------
    dict
        ``{deleted, from_sources, confirmation_required}``
    """
    if confirmation != GDPR_CONFIRMATION_PHRASE:
        return {
            "deleted": False,
            "from_sources": {},
            "confirmation_required": True,
            "required_phrase": GDPR_CONFIRMATION_PHRASE,
            "message": (
                "Deletion requires explicit confirmation. "
                f"Pass confirmation='{GDPR_CONFIRMATION_PHRASE}' to proceed."
            ),
        }

    deleted_from: Dict[str, int] = {}

    # subscriptions.db
    cur = _db_cursor(SUBSCRIPTIONS_DB)
    if cur is not None:
        for table in ("subscription", "usage_log", "api_log"):
            try:
                cur.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))
                deleted_from[f"subscriptions.{table}"] = cur.rowcount
            except sqlite3.Error as exc:
                logger.error("Failed to delete from %s: %s", table, exc)
        try:
            cur.connection.commit()
            cur.connection.close()
        except Exception:
            pass

    # dashboard.db
    cur = _db_cursor(DASHBOARD_DB)
    if cur is not None:
        for table in ("widgets", "knowledge_base", "habits"):
            try:
                cur.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))
                deleted_from[f"dashboard.{table}"] = cur.rowcount
            except sqlite3.Error as exc:
                logger.error("Failed to delete from %s: %s", table, exc)
        # Habit completions via habit_id join
        try:
            cur.execute(
                """
                DELETE FROM habit_completions
                WHERE habit_id IN (SELECT id FROM habits WHERE user_id = ?)
                """,
                (user_id,),
            )
            deleted_from["dashboard.habit_completions"] = cur.rowcount
        except sqlite3.Error as exc:
            logger.error("Failed to delete habit_completions: %s", exc)
        try:
            cur.connection.commit()
            cur.connection.close()
        except Exception:
            pass

    # memory.db
    cur = _db_cursor(MEMORY_DB)
    if cur is not None:
        try:
            cur.execute(
                """
                DELETE FROM messages
                WHERE session_id IN (SELECT session_id FROM conversations WHERE user_id = ?)
                """,
                (user_id,),
            )
            deleted_from["memory.messages"] = cur.rowcount
        except sqlite3.Error as exc:
            logger.error("Failed to delete messages: %s", exc)
        try:
            cur.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
            deleted_from["memory.conversations"] = cur.rowcount
        except sqlite3.Error as exc:
            logger.error("Failed to delete conversations: %s", exc)
        try:
            cur.connection.commit()
            cur.connection.close()
        except Exception:
            pass

    # Voice clones (filesystem)
    user_voice_dir = os.path.join(VOICE_CLONES_DIR, user_id)
    if os.path.isdir(user_voice_dir):
        count = 0
        for fname in os.listdir(user_voice_dir):
            fpath = os.path.join(user_voice_dir, fname)
            try:
                os.remove(fpath)
                count += 1
            except OSError as exc:
                logger.error("Failed to delete voice clone %s: %s", fpath, exc)
        deleted_from["voice_clones.files"] = count
        try:
            os.rmdir(user_voice_dir)
        except OSError:
            pass

    total_deleted = sum(deleted_from.values())
    logger.info("GDPR deletion for user %s: %d records removed", user_id, total_deleted)

    return {
        "deleted": True,
        "from_sources": deleted_from,
        "confirmation_required": False,
        "total_deleted": total_deleted,
    }


def anonymize_user_data(user_id: str) -> Dict[str, Any]:
    """Anonymize user data instead of deleting it.

    Replaces personal identifiers with deterministic SHA-256 hashes so
    the data can still be used for aggregated analytics while being
    unlinkable to the original user.

    Returns
    -------
    dict
        ``{anonymized, sources}``
    """
    hashed_id = hashlib.sha256(user_id.encode()).hexdigest()
    sources: Dict[str, int] = {}

    # subscriptions.db
    cur = _db_cursor(SUBSCRIPTIONS_DB)
    if cur is not None:
        for table in ("subscription", "usage_log", "api_log"):
            try:
                cur.execute(
                    f"UPDATE {table} SET user_id = ? WHERE user_id = ?",
                    (hashed_id, user_id),
                )
                sources[f"subscriptions.{table}"] = cur.rowcount
            except sqlite3.Error as exc:
                logger.error("Failed to anonymize %s: %s", table, exc)
        try:
            cur.connection.commit()
            cur.connection.close()
        except Exception:
            pass

    # dashboard.db
    cur = _db_cursor(DASHBOARD_DB)
    if cur is not None:
        for table in ("widgets", "knowledge_base", "habits"):
            try:
                cur.execute(
                    f"UPDATE {table} SET user_id = ? WHERE user_id = ?",
                    (hashed_id, user_id),
                )
                sources[f"dashboard.{table}"] = cur.rowcount
            except sqlite3.Error as exc:
                logger.error("Failed to anonymize %s: %s", table, exc)
        try:
            cur.connection.commit()
            cur.connection.close()
        except Exception:
            pass

    # memory.db
    cur = _db_cursor(MEMORY_DB)
    if cur is not None:
        try:
            cur.execute(
                "UPDATE conversations SET user_id = ? WHERE user_id = ?",
                (hashed_id, user_id),
            )
            sources["memory.conversations"] = cur.rowcount
        except sqlite3.Error as exc:
            logger.error("Failed to anonymize conversations: %s", exc)
        try:
            cur.connection.commit()
            cur.connection.close()
        except Exception:
            pass

    total = sum(sources.values())
    logger.info("Anonymized user %s -> %s (%d records)", user_id, hashed_id, total)

    return {"anonymized": True, "sources": sources, "total_anonymized": total, "hashed_id": hashed_id}


# ---------------------------------------------------------------------------
# Scheduled exports
# ---------------------------------------------------------------------------

class ScheduledExportManager:
    """Manage scheduled / automated data exports.

    Uses a small SQLite database to persist schedules and tracks
    last-run timestamps so that due exports can be executed
    idempotently.

    Example
    -------
    >>> mgr = ScheduledExportManager()
    >>> mgr.schedule_export("u-123", "weekly", "json", "user@example.com")
    >>> mgr.run_due_exports()
    """

    def __init__(self, db_path: str = SCHEDULED_EXPORTS_DB) -> None:
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Create the scheduled-exports table if it doesn't exist."""
        _ensure_dir(os.path.dirname(self.db_path))
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scheduled_exports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    frequency TEXT NOT NULL,
                    format TEXT NOT NULL,
                    email TEXT,
                    created_at TEXT NOT NULL,
                    last_run TEXT,
                    next_run TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            conn.commit()

    def schedule_export(
        self,
        user_id: str,
        frequency: str,
        format: str,
        email: str = "",
    ) -> Dict[str, Any]:
        """Create a new scheduled export.

        Parameters
        ----------
        user_id : str
            Target user.
        frequency : str
            ``"daily"``, ``"weekly"``, or ``"monthly"``.
        format : str
            One of the :data:`ALLOWED_EXPORT_FORMATS`.
        email : str, optional
            Address to notify when export is ready.

        Returns
        -------
        dict
            ``{schedule_id, user_id, frequency, format, next_run}``
        """
        if frequency not in {"daily", "weekly", "monthly"}:
            raise ValueError("frequency must be one of: daily, weekly, monthly")
        if format not in ALLOWED_EXPORT_FORMATS:
            raise ValueError(f"format must be one of: {ALLOWED_EXPORT_FORMATS}")

        now = datetime.utcnow()
        if frequency == "daily":
            next_run = now + timedelta(days=1)
        elif frequency == "weekly":
            next_run = now + timedelta(weeks=1)
        else:  # monthly
            next_run = now + timedelta(days=30)

        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO scheduled_exports
                (user_id, frequency, format, email, created_at, next_run)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    frequency,
                    format,
                    email,
                    now.isoformat(),
                    next_run.isoformat(),
                ),
            )
            schedule_id = cur.lastrowid
            conn.commit()

        return {
            "schedule_id": schedule_id,
            "user_id": user_id,
            "frequency": frequency,
            "format": format,
            "next_run": next_run.isoformat() + "Z",
        }

    def list_scheduled(self, user_id: str) -> List[Dict[str, Any]]:
        """Return all active scheduled exports for a user."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM scheduled_exports
                WHERE user_id = ? AND active = 1
                ORDER BY created_at DESC
                """,
                (user_id,),
            ).fetchall()
            return [_strip_sensitive(dict(row)) for row in rows]

    def cancel_schedule(self, schedule_id: int) -> Dict[str, Any]:
        """Deactivate a scheduled export.

        Returns
        -------
        dict
            ``{cancelled, schedule_id}``
        """
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "UPDATE scheduled_exports SET active = 0 WHERE id = ?",
                (schedule_id,),
            )
            conn.commit()
            return {"cancelled": cur.rowcount > 0, "schedule_id": schedule_id}

    def run_due_exports(self) -> List[Dict[str, Any]]:
        """Check for and execute any exports whose ``next_run`` has passed.

        Returns
        -------
        list
            One result dict per executed export.
        """
        now = datetime.utcnow().isoformat()
        results: List[Dict[str, Any]] = []

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM scheduled_exports
                WHERE active = 1 AND next_run <= ?
                """,
                (now,),
            ).fetchall()

            for row in rows:
                sched = dict(row)
                user_id = sched["user_id"]
                fmt = sched["format"]
                schedule_id = sched["id"]

                try:
                    export_result = export_user_data(user_id, fmt)
                    results.append({
                        "schedule_id": schedule_id,
                        "user_id": user_id,
                        "format": fmt,
                        "status": "success",
                        "file": export_result,
                    })
                except Exception as exc:
                    logger.exception("Scheduled export failed for %s", user_id)
                    results.append({
                        "schedule_id": schedule_id,
                        "user_id": user_id,
                        "format": fmt,
                        "status": "error",
                        "error": str(exc),
                    })

                # Update last_run and next_run
                last_run = datetime.utcnow()
                frequency = sched["frequency"]
                if frequency == "daily":
                    next_run = last_run + timedelta(days=1)
                elif frequency == "weekly":
                    next_run = last_run + timedelta(weeks=1)
                else:
                    next_run = last_run + timedelta(days=30)

                conn.execute(
                    """
                    UPDATE scheduled_exports
                    SET last_run = ?, next_run = ?
                    WHERE id = ?
                    """,
                    (last_run.isoformat(), next_run.isoformat(), schedule_id),
                )

            conn.commit()

        return results


# ---------------------------------------------------------------------------
# Module-level convenience helpers
# ---------------------------------------------------------------------------

__all__ = [
    "export_user_data",
    "export_conversations",
    "export_knowledge_base",
    "export_habits",
    "export_usage_report",
    "import_user_data",
    "import_conversations",
    "import_knowledge_base",
    "import_habits",
    "validate_import_data",
    "create_zip_export",
    "delete_all_user_data",
    "anonymize_user_data",
    "ScheduledExportManager",
    "to_json",
    "to_markdown",
    "to_csv",
]
