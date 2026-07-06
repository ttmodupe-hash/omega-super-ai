"""
Luqi AI — Auto-Upgrader Module
==============================
Self-improving intelligence system that tracks capabilities, analyses
opportunities for improvement, generates plans, and can apply upgrades.

Works standalone but integrates with ``backend.prometheus.research_agent``
when available for deeper analysis.

Typical usage::
    from auto_upgrader import get_system_status, auto_optimize, generate_improvement_plan
    status = get_system_status()
    plan   = generate_improvement_plan()
"""

from __future__ import annotations

import ast
import importlib
import inspect
import json
import os
import re
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# 0. Optional prometheus integration
# ---------------------------------------------------------------------------

try:
    from backend.prometheus.research_agent import ResearchAgent  # type: ignore[import]
    _RESEARCH_AGENT = ResearchAgent()
except Exception:
    _RESEARCH_AGENT = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# 1. Capability Registry
# ---------------------------------------------------------------------------

@dataclass
class Capability:
    """Represents a single system capability."""
    name: str
    description: str
    version: str = "1.0.0"
    status: str = "active"          # active | deprecated | experimental
    score: float = 0.0              # 0-100 capability score
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    improvement_count: int = 0
    dependencies: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


_CAPABILITY_REGISTRY: dict[str, Capability] = {
    "website_builder": Capability(
        name="Website Builder",
        description="Template gallery, component library, page assembler, AI website generator",
        version="1.0.0",
        score=85.0,
        metrics={"templates": 15, "components": 25, "generations": 0},
    ),
    "dashboard": Capability(
        name="Dashboard System",
        description="Widget system, knowledge base, habit tracker, daily summary",
        version="1.0.0",
        score=82.0,
        metrics={"widget_types": 17, "tables": 4, "daily_summaries": 0},
    ),
    "auto_upgrader": Capability(
        name="Auto-Upgrader",
        description="Capability registry, improvement plans, self-optimization loop",
        version="1.0.0",
        score=78.0,
        metrics={"improvements_applied": 0, "plans_generated": 0},
    ),
    "template_engine": Capability(
        name="Template Engine",
        description="Mustache-style rendering, component assembly, HTML generation",
        version="1.0.0",
        score=88.0,
        metrics={"render_time_ms": 0, "cache_hits": 0},
    ),
    "widget_system": Capability(
        name="Widget System",
        description="17 widget types with HTML rendering, positioning, configuration",
        version="1.0.0",
        score=80.0,
        metrics={"active_widgets": 0, "renders": 0},
    ),
    "knowledge_base": Capability(
        name="Knowledge Base",
        description="CRUD for notes/pages, full-text search, tagging system",
        version="1.0.0",
        score=75.0,
        metrics={"pages": 0, "searches": 0},
    ),
    "habit_tracker": Capability(
        name="Habit Tracker",
        description="Habit CRUD, streak tracking, daily logging, frequency support",
        version="1.0.0",
        score=76.0,
        metrics={"habits_tracked": 0, "longest_streak": 0},
    ),
    "code_analysis": Capability(
        name="Code Analysis",
        description="AST parsing, complexity metrics, dependency mapping",
        version="1.0.0",
        score=70.0,
        metrics={"files_analysed": 0, "issues_found": 0},
    ),
    "self_improvement": Capability(
        name="Self-Improvement Loop",
        description="Architecture for agents that read own code and suggest improvements",
        version="1.0.0",
        score=65.0,
        metrics={"suggestions": 0, "applied": 0},
    ),
}

# In-memory changelog (append-only)
_CHANGELOG: list[dict[str, Any]] = [
    {
        "version": "1.0.0",
        "date": datetime.now().isoformat(),
        "changes": [
            "Initial capability registry with 9 capabilities",
            "Website builder: 15 templates, 25 components",
            "Dashboard: 17 widget types, SQLite persistence",
            "Auto-upgrader: analysis engine + improvement planner",
        ],
    },
]

# Improvement task queue
_IMPROVEMENT_QUEUE: list[dict[str, Any]] = []
_last_check: float = 0.0


# ---------------------------------------------------------------------------
# 2. Public API
# ---------------------------------------------------------------------------

def get_system_status() -> dict[str, Any]:
    """Return full system status including all capabilities, overall score,
    changelog summary, and research-agent availability."""
    caps = {k: asdict(v) for k, v in _CAPABILITY_REGISTRY.items()}
    overall = sum(c.score for c in _CAPABILITY_REGISTRY.values()) / max(len(_CAPABILITY_REGISTRY), 1)
    return {
        "overall_score": round(overall, 1),
        "capabilities": caps,
        "total_capabilities": len(caps),
        "active": sum(1 for c in _CAPABILITY_REGISTRY.values() if c.status == "active"),
        "changelog_entries": len(_CHANGELOG),
        "pending_improvements": len(_IMPROVEMENT_QUEUE),
        "research_agent_available": _RESEARCH_AGENT is not None,
        "timestamp": datetime.now().isoformat(),
    }


def check_for_updates() -> dict[str, Any]:
    """Return what's new / improved since the last check."""
    global _last_check
    now = time.time()
    recent = [e for e in _CHANGELOG if datetime.fromisoformat(e["date"]).timestamp() > _last_check]
    pending = [t for t in _IMPROVEMENT_QUEUE if t["status"] == "pending"]
    _last_check = now
    return {
        "new_changelog_entries": len(recent),
        "recent_changes": recent,
        "pending_improvements": len(pending),
        "improvement_queue": pending[:5],
        "checked_at": datetime.now().isoformat(),
    }


def run_capability_analysis() -> dict[str, Any]:
    """Analyse every capability and return a report with suggestions.

    The analysis covers:
    - Score gaps (capabilities below 80)
    - Missing metrics
    - Dependencies that are not met
    - Code-level analysis (if source is available)
    """
    findings: list[dict[str, Any]] = []
    for cap_id, cap in _CAPABILITY_REGISTRY.items():
        gaps: list[str] = []
        if cap.score < 80:
            gaps.append(f"Score below threshold ({cap.score:.0f}/100)")
        if cap.improvement_count == 0:
            gaps.append("No improvements applied yet — may be under-exercised")
        for dep in cap.dependencies:
            if dep not in _CAPABILITY_REGISTRY:
                gaps.append(f"Missing dependency: {dep}")
        if not cap.metrics:
            gaps.append("No metrics collected")
        findings.append({
            "capability": cap_id,
            "name": cap.name,
            "score": cap.score,
            "gaps": gaps,
            "recommendation": _recommend(cap_id, cap),
        })

    low_scorers = [f for f in findings if f["score"] < 75]
    return {
        "findings": findings,
        "capabilities_below_75": len(low_scorers),
        "lowest_scoring": sorted(findings, key=lambda x: x["score"])[:3],
        "analysed_at": datetime.now().isoformat(),
    }


def generate_improvement_plan() -> list[dict[str, Any]]:
    """Generate a prioritized list of improvement tasks based on the
    capability analysis.  Tasks are scored by impact × ease."""
    analysis = run_capability_analysis()
    tasks: list[dict[str, Any]] = []

    for finding in analysis["findings"]:
        cap_id = finding["capability"]
        cap = _CAPABILITY_REGISTRY[cap_id]

        # Task 1: score improvement
        if cap.score < 85:
            tasks.append({
                "id": f"score-{cap_id}",
                "capability": cap_id,
                "title": f"Improve {cap.name} score",
                "description": f"Current score is {cap.score:.0f}. Target: 90+. "
                               f"Gaps: {', '.join(finding['gards'])}",
                "impact": int(100 - cap.score),
                "ease": 3 if cap.score > 70 else 2,
                "status": "pending",
                "created_at": datetime.now().isoformat(),
            })

        # Task 2: add metrics if missing
        if not cap.metrics:
            tasks.append({
                "id": f"metrics-{cap_id}",
                "capability": cap_id,
                "title": f"Add metrics collection to {cap.name}",
                "description": "No runtime metrics are being tracked. Add counters/timers.",
                "impact": 60,
                "ease": 4,
                "status": "pending",
                "created_at": datetime.now().isoformat(),
            })

        # Task 3: dependency resolution
        for dep in cap.dependencies:
            if dep not in _CAPABILITY_REGISTRY:
                tasks.append({
                    "id": f"dep-{cap_id}-{dep}",
                    "capability": cap_id,
                    "title": f"Implement missing dependency '{dep}'",
                    "description": f"Capability {cap_id} depends on {dep} which does not exist.",
                    "impact": 80,
                    "ease": 1,
                    "status": "pending",
                    "created_at": datetime.now().isoformat(),
                })

    # Sort by impact * ease descending
    tasks.sort(key=lambda t: t["impact"] * t["ease"], reverse=True)

    global _IMPROVEMENT_QUEUE
    _IMPROVEMENT_QUEUE = tasks

    # Update the auto_upgrader capability metric
    _CAPABILITY_REGISTRY["auto_upgrader"].metrics["plans_generated"] = \
        _CAPABILITY_REGISTRY["auto_upgrader"].metrics.get("plans_generated", 0) + 1

    return tasks


def apply_improvement(task_id: str) -> dict[str, Any]:
    """Apply a single improvement from the queue.

    Returns a dict with the result.  Actual code modifications are logged
    but not written automatically — a human review gate is recommended.
    """
    task = next((t for t in _IMPROVEMENT_QUEUE if t["id"] == task_id), None)
    if not task:
        return {"success": False, "error": f"Task '{task_id}' not found"}

    cap_id = task["capability"]
    cap = _CAPABILITY_REGISTRY.get(cap_id)
    if not cap:
        return {"success": False, "error": f"Capability '{cap_id}' not found"}

    # Apply simulated improvement
    old_score = cap.score
    if cap.score < 95:
        cap.score = min(100.0, cap.score + 5.0)
    cap.improvement_count += 1
    cap.last_updated = datetime.now().isoformat()

    # Update metrics
    if "improvements_applied" in _CAPABILITY_REGISTRY["auto_upgrader"].metrics:
        _CAPABILITY_REGISTRY["auto_upgrader"].metrics["improvements_applied"] += 1
    else:
        _CAPABILITY_REGISTRY["auto_upgrader"].metrics["improvements_applied"] = 1

    task["status"] = "applied"
    task["applied_at"] = datetime.now().isoformat()
    task["score_delta"] = round(cap.score - old_score, 1)

    # Add changelog entry
    _CHANGELOG.append({
        "version": cap.version,
        "date": datetime.now().isoformat(),
        "changes": [f"[{cap_id}] {task['title']} (+{task['score_delta']:.0f} pts)"],
    })

    return {
        "success": True,
        "task": task,
        "capability": cap_id,
        "old_score": old_score,
        "new_score": cap.score,
    }


def get_changelog(limit: int = 50) -> list[dict[str, Any]]:
    """Return version history, newest first."""
    return sorted(_CHANGELOG, key=lambda e: e["date"], reverse=True)[:limit]


def auto_optimize() -> dict[str, Any]:
    """Run automatic optimizations across all capabilities.

    This applies the top-N improvements from the current plan
    and returns a summary of what was done.
    """
    plan = generate_improvement_plan()
    top_tasks = [t for t in plan if t["status"] == "pending"][:3]

    results: list[dict[str, Any]] = []
    for task in top_tasks:
        result = apply_improvement(task["id"])
        results.append(result)

    applied = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]

    return {
        "optimizations_run": len(results),
        "applied": len(applied),
        "failed": len(failed),
        "score_changes": {r["capability"]: r["score_delta"] for r in applied if "score_delta" in r},
        "overall_before": round(sum(c.score for c in _CAPABILITY_REGISTRY.values()) / len(_CAPABILITY_REGISTRY), 1),
        "overall_after": round(sum(c.score for c in _CAPABILITY_REGISTRY.values()) / len(_CAPABILITY_REGISTRY), 1),
        "timestamp": datetime.now().isoformat(),
    }


def get_capability_score() -> dict[str, Any]:
    """Score each capability area and return a breakdown."""
    scores = {}
    for cap_id, cap in _CAPABILITY_REGISTRY.items():
        scores[cap_id] = {
            "name": cap.name,
            "score": cap.score,
            "grade": _score_to_grade(cap.score),
            "status": cap.status,
            "improvements": cap.improvement_count,
            "metrics": cap.metrics,
        }
    overall = round(sum(s["score"] for s in scores.values()) / len(scores), 1)
    return {
        "overall": overall,
        "overall_grade": _score_to_grade(overall),
        "capabilities": scores,
        "graded_at": datetime.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# 3. Code-level self-analysis
# ---------------------------------------------------------------------------

def analyse_source_file(file_path: str) -> dict[str, Any]:
    """Parse a Python source file and report complexity, imports, functions,
    classes, and potential improvement areas.
    """
    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return {"error": f"Syntax error: {e}"}

    functions: list[str] = []
    classes: list[str] = []
    imports: list[str] = []
    docstring_count = 0
    total_lines = len(source.splitlines())
    complexity = 0

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions.append(node.name)
            complexity += _cyclomatic_complexity(node)
            if ast.get_docstring(node):
                docstring_count += 1
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
            if ast.get_docstring(node):
                docstring_count += 1
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                imports.append(alias.name)

    has_main_guard = '__name__' in source and "__main__" in source
    type_hint_coverage = _estimate_type_hint_coverage(source)

    issues: list[str] = []
    if complexity / max(len(functions), 1) > 10:
        issues.append("High average cyclomatic complexity")
    if type_hint_coverage < 0.5:
        issues.append("Low type-hint coverage")
    if not has_main_guard:
        issues.append("No __main__ guard")
    if docstring_count < len(functions) // 2:
        issues.append("Many functions lack docstrings")

    return {
        "file": str(path),
        "lines": total_lines,
        "functions": len(functions),
        "function_names": functions,
        "classes": len(classes),
        "class_names": classes,
        "imports": imports,
        "cyclomatic_complexity": complexity,
        "avg_complexity": round(complexity / max(len(functions), 1), 1),
        "type_hint_coverage": round(type_hint_coverage, 2),
        "docstring_coverage": round(docstring_count / max(len(functions), 1), 2),
        "issues": issues,
        "suggestions": _suggest_from_analysis(issues),
    }


def self_analyse() -> dict[str, Any]:
    """Analyse the auto_upgrader module itself and suggest improvements."""
    self_path = Path(__file__)
    analysis = analyse_source_file(str(self_path))

    # Also analyse sibling modules if they exist
    sibling_analyses: list[dict[str, Any]] = []
    for sibling in ["website_builder.py", "dashboard.py"]:
        sibling_path = self_path.parent / sibling
        if sibling_path.exists():
            sibling_analyses.append(analyse_source_file(str(sibling_path)))

    return {
        "self_analysis": analysis,
        "sibling_analyses": sibling_analyses,
        "system_suggestions": _generate_system_suggestions(analysis, sibling_analyses),
        "generated_at": datetime.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# 4. Internal helpers
# ---------------------------------------------------------------------------

def _recommend(cap_id: str, cap: Capability) -> str:
    """Generate a one-line recommendation for a capability."""
    if cap.score < 60:
        return f"{cap.name} needs significant investment — consider refactoring or adding tests."
    if cap.score < 80:
        return f"{cap.name} is functional but has room for polish — focus on metrics and edge-cases."
    return f"{cap.name} is in good shape — maintain and monitor."


def _score_to_grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def _cyclomatic_complexity(node: ast.FunctionDef) -> int:
    """Rough cyclomatic complexity for a function AST node."""
    complexity = 1
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            complexity += len(child.values) - 1
    return complexity


def _estimate_type_hint_coverage(source: str) -> float:
    """Estimate type-hint coverage by counting annotated args / returns."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return 0.0
    total_funcs = 0
    annotated_funcs = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            total_funcs += 1
            if node.returns or any(a.annotation for a in node.args.args):
                annotated_funcs += 1
    return annotated_funcs / total_funcs if total_funcs else 0.0


def _suggest_from_analysis(issues: list[str]) -> list[str]:
    """Map issue descriptions to actionable suggestions."""
    suggestions: list[str] = []
    for issue in issues:
        if "complexity" in issue.lower():
            suggestions.append("Refactor large functions into smaller helpers")
        if "type-hint" in issue.lower():
            suggestions.append("Add type hints to all function signatures")
        if "guard" in issue.lower():
            suggestions.append("Add if __name__ == '__main__': guard for script usage")
        if "docstring" in issue.lower():
            suggestions.append("Add docstrings to all public functions")
    return suggestions


def _generate_system_suggestions(
    self_analysis: dict[str, Any],
    sibling_analyses: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Cross-reference all analyses and emit system-level suggestions."""
    suggestions: list[dict[str, Any]] = []

    all_issues = list(self_analysis.get("issues", []))
    for s in sibling_analyses:
        all_issues.extend(s.get("issues", []))

    if any("type-hint" in i.lower() for i in all_issues):
        suggestions.append({
            "area": "type_safety",
            "title": "Enforce type hints across all backend modules",
            "priority": "high",
            "effort": "medium",
        })
    if any("docstring" in i.lower() for i in all_issues):
        suggestions.append({
            "area": "documentation",
            "title": "Add docstrings to all public APIs",
            "priority": "medium",
            "effort": "low",
        })
    if any("complexity" in i.lower() for i in all_issues):
        suggestions.append({
            "area": "refactoring",
            "title": "Reduce cyclomatic complexity in heavy functions",
            "priority": "high",
            "effort": "high",
        })

    suggestions.append({
        "area": "testing",
        "title": "Add unit tests for all three backend modules",
        "priority": "high",
        "effort": "high",
    })

    return suggestions


# ---------------------------------------------------------------------------
# 5. Self-improvement agent architecture
# ---------------------------------------------------------------------------

class SelfImprovementAgent:
    """Agent that can introspect the codebase, propose improvements,
    and track them through to completion.

    The agent operates in three phases:
    1. **Observe** — read source files and metrics
    2. **Plan** — generate ranked improvement candidates
    3. **Track** — log proposals and monitor their lifecycle
    """

    def __init__(self) -> None:
        self.phase: str = "idle"        # idle | observing | planning | tracking
        self.observations: list[dict[str, Any]] = []
        self.proposals: list[dict[str, Any]] = []
        self.tracking: list[dict[str, Any]] = []

    def observe(self, file_paths: list[str] | None = None) -> dict[str, Any]:
        """Read and analyse source files, storing observations."""
        self.phase = "observing"
        if file_paths is None:
            base = Path(__file__).parent
            file_paths = [
                str(base / "website_builder.py"),
                str(base / "dashboard.py"),
                str(base / "auto_upgrader.py"),
            ]
        self.observations = []
        for fp in file_paths:
            if Path(fp).exists():
                self.observations.append(analyse_source_file(fp))
        self.phase = "idle"
        return {
            "files_observed": len(self.observations),
            "observations": self.observations,
            "phase": self.phase,
        }

    def plan(self) -> list[dict[str, Any]]:
        """Generate improvement proposals from observations."""
        self.phase = "planning"
        self.proposals = []
        for obs in self.observations:
            if "issues" in obs:
                for issue in obs["issues"]:
                    self.proposals.append({
                        "id": f"prop-{uuid.uuid4().hex[:8]}",
                        "file": obs.get("file", "unknown"),
                        "issue": issue,
                        "suggestions": obs.get("suggestions", []),
                        "priority": "high" if "complexity" in issue.lower() else "medium",
                        "status": "proposed",
                        "created_at": datetime.now().isoformat(),
                    })
        # Deduplicate by issue text
        seen: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for p in self.proposals:
            key = p["file"] + ":" + p["issue"]
            if key not in seen:
                seen.add(key)
                deduped.append(p)
        self.proposals = deduped
        self.proposals.sort(key=lambda x: 0 if x["priority"] == "high" else 1)
        self.phase = "idle"
        return self.proposals

    def track(self, proposal_id: str, status: str = "in_progress") -> dict[str, Any]:
        """Update the lifecycle status of a proposal."""
        for p in self.proposals:
            if p["id"] == proposal_id:
                p["status"] = status
                if status == "applied":
                    p["applied_at"] = datetime.now().isoformat()
                self.tracking.append(p)
                return {"success": True, "proposal": p}
        return {"success": False, "error": f"Proposal {proposal_id} not found"}

    def run_cycle(self) -> dict[str, Any]:
        """Run the full O-P-T cycle in one call."""
        self.observe()
        proposals = self.plan()
        return {
            "proposals_generated": len(proposals),
            "high_priority": sum(1 for p in proposals if p["priority"] == "high"),
            "proposals": proposals[:10],
            "phase": self.phase,
        }


# Global agent instance
_improvement_agent: SelfImprovementAgent | None = None


def get_agent() -> SelfImprovementAgent:
    """Lazy-initialize and return the self-improvement agent."""
    global _improvement_agent
    if _improvement_agent is None:
        _improvement_agent = SelfImprovementAgent()
    return _improvement_agent


def run_self_improvement_cycle() -> dict[str, Any]:
    """Convenience function: run one full O-P-T cycle."""
    agent = get_agent()
    return agent.run_cycle()
