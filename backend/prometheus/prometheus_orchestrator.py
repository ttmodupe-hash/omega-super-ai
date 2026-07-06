"""
Prometheus Orchestrator — Main orchestration module.

Ties together research, gap analysis, improvement generation,
benchmarking, and deployment into a single daily cycle.

Usage:
    orchestrator = PrometheusOrchestrator()
    results = orchestrator.run_daily_cycle()
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.prometheus.config import PrometheusConfig
from backend.prometheus.research_agent import ResearchAgent
from backend.prometheus.gap_analyzer import GapAnalyzer
from backend.prometheus.improvement_engine import ImprovementEngine
from backend.prometheus.benchmark_runner import BenchmarkRunner

logger = logging.getLogger(__name__)


class PrometheusOrchestrator:
    """Main orchestrator for the Prometheus self-improving engine.

    Coordinates the daily cycle of research, analysis, improvement,
    benchmarking, and deployment.

    Attributes:
        config: PrometheusConfig instance.
        db_path: Path to SQLite database for persistence.
        research_agent: ResearchAgent for discovering new developments.
        gap_analyzer: GapAnalyzer for identifying capability gaps.
        improvement_engine: ImprovementEngine for generating solutions.
        benchmark_runner: BenchmarkRunner for measuring performance.
    """

    def __init__(self, config: PrometheusConfig | None = None) -> None:
        """Initialize the orchestrator.

        Args:
            config: Optional configuration. Uses default if not provided.
        """
        self.config = config or PrometheusConfig.from_env()
        self.db_path = self.config.db_path
        self._init_db()

        self.research_agent = ResearchAgent()
        self.gap_analyzer = GapAnalyzer(competitors=self.config.competitors)
        self.improvement_engine = ImprovementEngine()
        self.benchmark_runner = BenchmarkRunner()

        logger.info("PrometheusOrchestrator initialized")

    def _init_db(self) -> None:
        """Initialize SQLite database for persistence."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS cycles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    findings_count INTEGER DEFAULT 0,
                    gaps_count INTEGER DEFAULT 0,
                    improvements_count INTEGER DEFAULT 0,
                    benchmark_score REAL,
                    status TEXT DEFAULT 'running'
                );
                CREATE TABLE IF NOT EXISTS findings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cycle_id INTEGER REFERENCES cycles(id),
                    title TEXT NOT NULL,
                    source TEXT,
                    url TEXT,
                    summary TEXT,
                    relevance_score REAL,
                    category TEXT,
                    date TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS gaps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cycle_id INTEGER REFERENCES cycles(id),
                    category TEXT NOT NULL,
                    severity REAL,
                    description TEXT,
                    missing_capabilities TEXT,
                    competitors_ahead TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS improvements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cycle_id INTEGER REFERENCES cycles(id),
                    name TEXT NOT NULL,
                    priority TEXT,
                    description TEXT,
                    code_sample TEXT,
                    effort_estimate TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)
        logger.info("Database initialized at %s", self.db_path)

    def run_daily_cycle(self) -> dict[str, Any]:
        """Execute a full daily improvement cycle.

        Returns:
            Dictionary with cycle results including findings, gaps,
            improvements, and benchmark scores.
        """
        cycle_id = self._start_cycle()
        results: dict[str, Any] = {"cycle_id": cycle_id, "status": "running"}

        try:
            # Step 1: Research
            logger.info("[Cycle %d] Step 1: Research", cycle_id)
            findings = self.research_agent.run_full_scrape(days=7)
            results["findings_count"] = len(findings)
            self._store_findings(cycle_id, findings)

            # Step 2: Gap Analysis
            logger.info("[Cycle %d] Step 2: Gap Analysis", cycle_id)
            gaps = self.gap_analyzer.analyze(findings)
            results["gaps_count"] = len(gaps)
            self._store_gaps(cycle_id, gaps)

            # Step 3: Generate Improvements
            logger.info("[Cycle %d] Step 3: Generate Improvements", cycle_id)
            improvements = self.improvement_engine.generate(gaps[:self.config.max_candidate_features])
            results["improvements_count"] = len(improvements)
            self._store_improvements(cycle_id, improvements)

            # Step 4: Benchmark
            logger.info("[Cycle %d] Step 4: Benchmark", cycle_id)
            benchmark = self.benchmark_runner.run_all_benchmarks()
            results["benchmark"] = benchmark
            results["overall_score"] = benchmark.get("overall_score", 0.0)

            # Step 5: Finalize
            results["status"] = "completed"
            self._complete_cycle(cycle_id, results)
            logger.info("[Cycle %d] Cycle completed successfully", cycle_id)

        except Exception as e:
            logger.error("[Cycle %d] Cycle failed: %s", cycle_id, e)
            results["status"] = "failed"
            results["error"] = str(e)
            self._fail_cycle(cycle_id, str(e))

        return results

    def _start_cycle(self) -> int:
        """Start a new cycle and return its ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO cycles (started_at, status) VALUES (?, ?)",
                (datetime.now().isoformat(), "running")
            )
            return cursor.lastrowid

    def _complete_cycle(self, cycle_id: int, results: dict[str, Any]) -> None:
        """Mark a cycle as completed."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE cycles SET completed_at = ?, findings_count = ?, gaps_count = ?, improvements_count = ?, benchmark_score = ?, status = ? WHERE id = ?",
                (
                    datetime.now().isoformat(),
                    results.get("findings_count", 0),
                    results.get("gaps_count", 0),
                    results.get("improvements_count", 0),
                    results.get("overall_score", 0.0),
                    "completed",
                    cycle_id,
                )
            )

    def _fail_cycle(self, cycle_id: int, error: str) -> None:
        """Mark a cycle as failed."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE cycles SET completed_at = ?, status = ? WHERE id = ?",
                (datetime.now().isoformat(), f"failed: {error}", cycle_id)
            )

    def _store_findings(self, cycle_id: int, findings: list[Any]) -> None:
        """Store findings in the database."""
        with sqlite3.connect(self.db_path) as conn:
            for finding in findings:
                conn.execute(
                    "INSERT INTO findings (cycle_id, title, source, url, summary, relevance_score, category, date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        cycle_id,
                        getattr(finding, "title", ""),
                        getattr(finding, "source", ""),
                        getattr(finding, "url", ""),
                        getattr(finding, "summary", "")[:1000],
                        getattr(finding, "relevance_score", 0.0),
                        getattr(finding, "category", ""),
                        getattr(finding, "date", ""),
                    )
                )

    def _store_gaps(self, cycle_id: int, gaps: list[dict[str, Any]]) -> None:
        """Store gaps in the database."""
        with sqlite3.connect(self.db_path) as conn:
            for gap in gaps:
                conn.execute(
                    "INSERT INTO gaps (cycle_id, category, severity, description, missing_capabilities, competitors_ahead) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        cycle_id,
                        gap.get("category", ""),
                        gap.get("severity", 0.0),
                        gap.get("description", ""),
                        ", ".join(gap.get("missing_capabilities", [])),
                        ", ".join(gap.get("competitors_ahead", [])),
                    )
                )

    def _store_improvements(self, cycle_id: int, improvements: list[dict[str, Any]]) -> None:
        """Store improvements in the database."""
        with sqlite3.connect(self.db_path) as conn:
            for imp in improvements:
                conn.execute(
                    "INSERT INTO improvements (cycle_id, name, priority, description, code_sample, effort_estimate) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        cycle_id,
                        imp.get("name", ""),
                        imp.get("priority", ""),
                        imp.get("description", ""),
                        imp.get("code_sample", "")[:2000],
                        imp.get("effort_estimate", ""),
                    )
                )

    def get_status(self) -> dict[str, Any]:
        """Get current engine status."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM cycles ORDER BY id DESC LIMIT 10"
            )
            cycles = [dict(row) for row in cursor.fetchall()]

        return {
            "total_cycles": len(cycles),
            "recent_cycles": cycles,
            "config": self.config.to_dict(),
        }
