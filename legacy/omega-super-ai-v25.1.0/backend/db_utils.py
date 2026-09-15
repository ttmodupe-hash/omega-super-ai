#!/usr/bin/env python3
"""
Luqi AI - Safe Database Utilities
==================================
Parameterized SQL query builders with table/column whitelisting.
Prevents SQL injection by never using f-strings for SQL identifiers.

Part of Luqi AI v24.4.0 Security Hardening — Built by Limitless Telecoms
"""

import logging
import re
import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# TABLE WHITELISTS — Per-module allowed tables
# ═══════════════════════════════════════════════════════════════════

_GOVERNMENT_TABLES = frozenset({
    "government_services", "services", "documents", "forms",
    "applications", "permits", "licenses", "registrations",
    "citizens", "appointments", "payments", "notifications",
})

_AGRICULTURE_TABLES = frozenset({
    "crops", "livestock", "farms", "farmers", "plantings",
    "harvests", "expenses", "revenues", "advisories",
    "weather_data", "soil_data", "market_prices",
})

_EDUCATION_TABLES = frozenset({
    "students", "teachers", "courses", "enrollments", "grades",
    "assignments", "submissions", "curricula", "subjects",
    "classrooms", "departments", "institutions",
})

_CORE_TABLES = frozenset({
    "users", "subscriptions", "payments", "api_keys", "sessions",
    "audit_logs", "webhooks", "files", "notifications",
    "messages", "conversations", "projects", "tasks",
})

_SECURITY_TRAINING_TABLES = frozenset({
    "security_courses", "security_modules", "security_lessons",
    "security_labs", "security_quizzes", "quiz_questions",
    "user_progress", "user_certificates", "skill_trees",
    "ctf_challenges", "ctf_submissions", "skill_badges",
})

ALLOWED_TABLES = (
    _GOVERNMENT_TABLES | _AGRICULTURE_TABLES | _EDUCATION_TABLES |
    _CORE_TABLES | _SECURITY_TRAINING_TABLES
)

_MODULE_TABLE_MAP = {
    "government": _GOVERNMENT_TABLES,
    "agriculture": _AGRICULTURE_TABLES,
    "education": _EDUCATION_TABLES,
    "core": _CORE_TABLES,
    "security_training": _SECURITY_TRAINING_TABLES,
}

# ═══════════════════════════════════════════════════════════════════
# COLUMN WHITELISTS
# ═══════════════════════════════════════════════════════════════════

ALLOWED_COLUMNS: Dict[str, frozenset] = {
    "users": frozenset({"id", "email", "username", "password_hash", "role", "created_at", "updated_at", "is_active", "tier"}),
    "government_services": frozenset({"id", "name", "category", "description", "requirements", "processing_time", "fee", "status", "created_at"}),
    "documents": frozenset({"id", "user_id", "service_id", "type", "status", "file_path", "created_at", "updated_at"}),
    "forms": frozenset({"id", "service_id", "title", "fields", "version", "status"}),
    "crops": frozenset({"id", "name", "type", "season", "region", "planting_month", "harvest_month", "water_needs", "fertilizer_needs"}),
    "farmers": frozenset({"id", "user_id", "farm_size", "location", "crops", "livestock", "created_at"}),
    "students": frozenset({"id", "user_id", "grade_level", "subjects", "enrollment_date"}),
    "security_courses": frozenset({"id", "title", "description", "category", "difficulty", "duration_hours", "prerequisites", "created_at"}),
    "user_progress": frozenset({"user_id", "course_id", "module_id", "completed_lessons", "lab_scores", "quiz_scores", "overall_score", "updated_at"}),
}

_SQL_IDENTIFIER_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def _validate_identifier(name: str) -> str:
    if not name or not _SQL_IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return name


def validate_table_name(table: str, module: str = None) -> str:
    name = _validate_identifier(table)
    allowed = _MODULE_TABLE_MAP.get(module, ALLOWED_TABLES)
    if name not in allowed:
        raise ValueError(f"Table {name!r} not allowed for module {module!r}")
    return name


def validate_column_names(columns: List[str], table: str = None) -> List[str]:
    validated = [_validate_identifier(c) for c in columns]
    if table and table in ALLOWED_COLUMNS:
        invalid = [c for c in validated if c not in ALLOWED_COLUMNS[table]]
        if invalid:
            raise ValueError(f"Columns {invalid!r} not allowed for table {table!r}")
    return validated


def safe_query(table: str, columns: List[str] = None, where: Dict[str, Any] = None,
               order_by: str = None, limit: int = None, offset: int = None, module: str = None) -> Tuple[str, tuple]:
    table = validate_table_name(table, module)
    col_str = ", ".join(f'"{c}"' for c in validate_column_names(columns, table)) if columns else "*"
    query = f'SELECT {col_str} FROM "{table}"'
    params = []
    if where:
        conditions = []
        for col, val in where.items():
            col = _validate_identifier(col)
            if isinstance(val, (list, tuple)):
                placeholders = ", ".join("?" * len(val))
                conditions.append(f'"{col}" IN ({placeholders})')
                params.extend(val)
            elif val is None:
                conditions.append(f'"{col}" IS NULL')
            else:
                conditions.append(f'"{col}" = ?')
                params.append(val)
        query += " WHERE " + " AND ".join(conditions)
    if order_by:
        order_col = _validate_identifier(order_by.lstrip("-"))
        direction = "DESC" if order_by.startswith("-") else "ASC"
        query += f' ORDER BY "{order_col}" {direction}'
    if limit is not None:
        query += f" LIMIT {int(limit)}"
    if offset is not None:
        query += f" OFFSET {int(offset)}"
    return query, tuple(params)


def safe_insert(table: str, data: Dict[str, Any], module: str = None) -> Tuple[str, tuple]:
    table = validate_table_name(table, module)
    if not data:
        raise ValueError("No data for INSERT")
    columns = validate_column_names(list(data.keys()), table)
    col_str = ", ".join(f'"{c}"' for c in columns)
    placeholders = ", ".join("?" * len(columns))
    params = tuple(data[c] for c in columns)
    return f'INSERT INTO "{table}" ({col_str}) VALUES ({placeholders})', params


def safe_update(table: str, data: Dict[str, Any], where: Dict[str, Any], module: str = None) -> Tuple[str, tuple]:
    table = validate_table_name(table, module)
    if not data:
        raise ValueError("No data for UPDATE")
    if not where:
        raise ValueError("WHERE required for UPDATE")
    columns = validate_column_names(list(data.keys()), table)
    set_clauses = [f'"{c}" = ?' for c in columns]
    params = [data[c] for c in columns]
    where_conditions = []
    for col, val in where.items():
        col = _validate_identifier(col)
        where_conditions.append(f'"{col}" = ?')
        params.append(val)
    query = f'UPDATE "{table}" SET {", ".join(set_clauses)} WHERE {" AND ".join(where_conditions)}'
    return query, tuple(params)


def safe_delete(table: str, where: Dict[str, Any], module: str = None) -> Tuple[str, tuple]:
    table = validate_table_name(table, module)
    if not where:
        raise ValueError("WHERE required for DELETE")
    conditions = []
    params = []
    for col, val in where.items():
        col = _validate_identifier(col)
        conditions.append(f'"{col}" = ?')
        params.append(val)
    return f'DELETE FROM "{table}" WHERE {" AND ".join(conditions)}', tuple(params)


def safe_count(table: str, where: Dict[str, Any] = None, module: str = None) -> Tuple[str, tuple]:
    table = validate_table_name(table, module)
    query = f'SELECT COUNT(*) FROM "{table}"'
    params = []
    if where:
        conditions = []
        for col, val in where.items():
            col = _validate_identifier(col)
            conditions.append(f'"{col}" = ?')
            params.append(val)
        query += " WHERE " + " AND ".join(conditions)
    return query, tuple(params)


def execute_safe(conn, query: str, params: tuple = ()):
    try:
        return conn.execute(query, params)
    except sqlite3.IntegrityError as e:
        raise ValueError(f"Integrity error: {e}") from e
    except sqlite3.OperationalError as e:
        raise ConnectionError(f"Database error: {e}") from e
    except sqlite3.ProgrammingError as e:
        raise RuntimeError(f"Query error: {e}") from e


def safe_select_by_id(table: str, record_id, columns: List[str] = None, id_column: str = "id", module: str = None):
    return safe_query(table, columns=columns, where={_validate_identifier(id_column): record_id}, module=module)


def safe_select_paginated(table: str, columns: List[str] = None, where: Dict[str, Any] = None,
                          order_by: str = None, page: int = 1, per_page: int = 20, module: str = None):
    offset = (max(1, page) - 1) * max(1, min(per_page, 100))
    return safe_query(table, columns=columns, where=where, order_by=order_by, limit=per_page, offset=offset, module=module)


def is_valid_table(table: str, module: str = None) -> bool:
    try:
        validate_table_name(table, module)
        return True
    except (ValueError, TypeError):
        return False
