#!/usr/bin/env python3
"""
Captainship Module for Luqi AI — "Captain Luqi"
================================================

An AI-powered project captain that takes ownership of projects, manages teams,
makes strategic decisions, and ensures success. Combines project management
methodology (Agile, Scrum, Waterfall, Hybrid) with AI-driven analytics.

Modules:
    - ProjectCaptain: Core engine for project leadership
    - TeamCoordinator: Virtual team management and delegation
    - CrisisManager: Emergency and crisis response
    - Strategic Planning: SWOT, decision matrices, scenario planning, OKRs
    - Resource Management: Allocation, time estimation, budget forecasting
    - Stakeholder Management: Status reports, communication plans
    - Database: Persistent SQLite storage for all project data

Target: 2500+ lines of production-quality Python.

Author: Luqi AI Engineering Team
Version: 1.0.0
"""

from __future__ import annotations

import os
import re
import json
import math
import sqlite3
import logging
import hashlib
import datetime
import random
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logger = logging.getLogger("captainship")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setLevel(logging.INFO)
    _formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    _handler.setFormatter(_formatter)
    logger.addHandler(_handler)

# ---------------------------------------------------------------------------
# Constants & Configuration
# ---------------------------------------------------------------------------

DEFAULT_DB_PATH = os.environ.get("LUQI_DB_PATH", "/mnt/agents/output/project/backend/luqi_projects.db")

HEALTH_WEIGHTS = {
    "progress": 0.25,
    "schedule": 0.25,
    "budget": 0.20,
    "quality": 0.15,
    "team_morale": 0.15,
}

PERT_WEIGHTS = {"optimistic": 1, "most_likely": 4, "pessimistic": 1}

RISK_MATRIX = {
    (1, 1): 1, (1, 2): 2, (1, 3): 3,
    (2, 1): 2, (2, 2): 4, (2, 3): 6,
    (3, 1): 3, (3, 2): 6, (3, 3): 9,
}

CRISIS_THRESHOLDS = {
    "none": (0, 0.30),
    "moderate": (0.30, 0.55),
    "severe": (0.55, 0.80),
    "critical": (0.80, 1.01),
}

PHASE_TEMPLATES: Dict[str, List[Dict[str, Any]]] = {
    "software": [
        {"name": "Discovery & Requirements", "duration_days": 14, "tasks": [
            "Stakeholder interviews", "Requirements gathering",
            "Competitive analysis", "Technical feasibility study",
        ]},
        {"name": "Design & Architecture", "duration_days": 21, "tasks": [
            "System architecture design", "UI/UX wireframes",
            "Database schema design", "API specification",
        ]},
        {"name": "Development", "duration_days": 56, "tasks": [
            "Sprint 1: Core features", "Sprint 2: Integration",
            "Sprint 3: Advanced features", "Sprint 4: Polish & bug fixes",
        ]},
        {"name": "Testing & QA", "duration_days": 21, "tasks": [
            "Unit testing", "Integration testing",
            "Performance testing", "User acceptance testing",
        ]},
        {"name": "Deployment & Launch", "duration_days": 14, "tasks": [
            "Production deployment", "Monitoring setup",
            "Documentation finalization", "Post-launch review",
        ]},
    ],
    "marketing": [
        {"name": "Research & Strategy", "duration_days": 10, "tasks": [
            "Market research", "Audience segmentation", "Competitor analysis",
        ]},
        {"name": "Creative Development", "duration_days": 21, "tasks": [
            "Campaign concept", "Asset creation", "Copywriting",
        ]},
        {"name": "Execution", "duration_days": 30, "tasks": [
            "Channel deployment", "Influencer outreach", "Paid media launch",
        ]},
        {"name": "Analysis & Optimization", "duration_days": 14, "tasks": [
            "Performance tracking", "A/B testing", "ROI analysis",
        ]},
    ],
    "consulting": [
        {"name": "Discovery", "duration_days": 7, "tasks": [
            "Client intake", "Current-state assessment", "Gap analysis",
        ]},
        {"name": "Analysis", "duration_days": 21, "tasks": [
            "Data collection", "Root-cause analysis", "Benchmarking",
        ]},
        {"name": "Recommendations", "duration_days": 14, "tasks": [
            "Solution design", "Implementation roadmap", "Business case",
        ]},
        {"name": "Delivery", "duration_days": 7, "tasks": [
            "Final presentation", "Knowledge transfer", "Next steps planning",
        ]},
    ],
}

SWOT_TEMPLATES = {
    "strengths": [
        "Experienced core team with domain expertise",
        "Strong technical infrastructure and tooling",
        "Clear vision and well-defined goals",
        "Adequate budget allocation for the scope",
        "Proven methodology and past successes",
    ],
    "weaknesses": [
        "Tight deadline limiting buffer time",
        "Dependency on external vendors or APIs",
        "Limited team availability during peak periods",
        "Incomplete requirements at project start",
        "Technical debt from previous iterations",
    ],
    "opportunities": [
        "Market timing aligns with product launch",
        "Potential for strategic partnerships",
        "Emerging technologies can accelerate delivery",
        "Customer feedback loop enables rapid iteration",
        "Competitor gaps create differentiation chance",
    ],
    "threats": [
        "Scope creep from evolving stakeholder demands",
        "Key-person risk if critical member departs",
        "Regulatory changes affecting deliverables",
        "Economic downturn impacting budget continuity",
        "Technology obsolescence during development cycle",
    ],
}

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _generate_id(prefix: str = "") -> str:
    """Generate a unique identifier string."""
    raw = f"{prefix}{uuid.uuid4().hex}{random.randint(1000, 9999)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _now_iso() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
    return datetime.datetime.utcnow().isoformat() + "Z"


def _parse_date(date_str: str) -> datetime.date:
    """Parse a date string (YYYY-MM-DD) into a date object."""
    return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()


def _date_add_days(date_str: str, days: int) -> str:
    """Add days to a date string and return new date string."""
    d = _parse_date(date_str) + datetime.timedelta(days=days)
    return d.isoformat()


def _days_between(start: str, end: str) -> int:
    """Return number of days between two date strings."""
    return (_parse_date(end) - _parse_date(start)).days


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a float between low and high."""
    return max(low, min(high, value))


def _db_connect(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open a SQLite connection with row factory."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
