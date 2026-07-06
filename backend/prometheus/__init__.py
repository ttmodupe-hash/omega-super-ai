"""
Prometheus Self-Improving Engine for Luqi AI.

An autonomous system that continuously monitors the AI landscape,
identifies capability gaps, and drives continuous improvement.

Modules:
    config: Configuration constants and settings.
    research_agent: Autonomous research agent for monitoring AI landscape.
    gap_analyzer: Capability gap analyzer for identifying weaknesses.
    improvement_engine: Auto-improvement engine for generating solutions.
    benchmark_runner: Self-benchmarking system for measuring performance.
    prometheus_orchestrator: Main orchestrator tying everything together.
    prometheus_cli: Command-line interface for interacting with Prometheus.

Example:
    from backend.prometheus.prometheus_orchestrator import PrometheusOrchestrator

    orchestrator = PrometheusOrchestrator(db_path="./prometheus.db")
    results = orchestrator.run_daily_cycle()
"""

__version__ = "1.0.0"
__author__ = "Luqi AI Engineering"

from backend.prometheus.prometheus_orchestrator import PrometheusOrchestrator
from backend.prometheus.research_agent import ResearchAgent
from backend.prometheus.gap_analyzer import GapAnalyzer
from backend.prometheus.improvement_engine import ImprovementEngine
from backend.prometheus.benchmark_runner import BenchmarkRunner

__all__ = [
    "PrometheusOrchestrator",
    "ResearchAgent",
    "GapAnalyzer",
    "ImprovementEngine",
    "BenchmarkRunner",
]
