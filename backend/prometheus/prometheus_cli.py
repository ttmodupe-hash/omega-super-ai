"""
Prometheus CLI — Command-line interface for the self-improving engine.

Usage:
    python -m prometheus.prometheus_cli --help
    python -m prometheus.prometheus_cli run-cycle
    python -m prometheus.prometheus_cli status
    python -m prometheus.prometheus_cli findings
    python -m prometheus.prometheus_cli gaps
    python -m prometheus.prometheus_cli improvements
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime

from prometheus.prometheus_orchestrator import PrometheusOrchestrator
from prometheus.config import PrometheusConfig

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def cmd_run_cycle(args: argparse.Namespace) -> int:
    """Run a full Prometheus cycle."""
    config = PrometheusConfig.from_env()
    orchestrator = PrometheusOrchestrator(config=config)
    results = orchestrator.run_daily_cycle()
    print(json.dumps(results, indent=2, default=str))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Show Prometheus status."""
    config = PrometheusConfig.from_env()
    orchestrator = PrometheusOrchestrator(config=config)
    status = orchestrator.get_status()
    print(json.dumps(status, indent=2, default=str))
    return 0


def cmd_findings(args: argparse.Namespace) -> int:
    """Show recent research findings."""
    config = PrometheusConfig.from_env()
    orchestrator = PrometheusOrchestrator(config=config)
    orchestrator.research_agent.run_full_scrape(days=args.days)
    top = orchestrator.research_agent.get_top_findings(n=args.limit)
    for i, finding in enumerate(top, 1):
        print(f"\n--- Finding {i} (relevance: {finding.relevance_score:.2f}) ---")
        print(f"Title: {finding.title}")
        print(f"Source: {finding.source}")
        print(f"Category: {finding.category}")
        print(f"URL: {finding.url}")
        print(f"Summary: {finding.summary[:200]}...")
    return 0


def cmd_gaps(args: argparse.Namespace) -> int:
    """Show capability gaps."""
    config = PrometheusConfig.from_env()
    orchestrator = PrometheusOrchestrator(config=config)
    orchestrator.research_agent.run_full_scrape(days=7)
    findings = orchestrator.research_agent.get_top_findings(n=20)
    gaps = orchestrator.gap_analyzer.analyze(findings)
    for gap in gaps[:args.limit]:
        print(f"\n--- Gap: {gap['category']} (severity: {gap['severity']:.2f}) ---")
        print(f"Description: {gap['description']}")
        print(f"Missing: {', '.join(gap['missing_capabilities'])}")
        print(f"Competitors ahead: {', '.join(gap['competitors_ahead'])}")
    return 0


def cmd_improvements(args: argparse.Namespace) -> int:
    """Show generated improvements."""
    config = PrometheusConfig.from_env()
    orchestrator = PrometheusOrchestrator(config=config)
    orchestrator.research_agent.run_full_scrape(days=7)
    findings = orchestrator.research_agent.get_top_findings(n=20)
    gaps = orchestrator.gap_analyzer.analyze(findings)
    improvements = orchestrator.improvement_engine.generate(gaps[:5])
    for i, imp in enumerate(improvements[:args.limit], 1):
        print(f"\n=== Improvement {i}: {imp['name']} ===")
        print(f"Priority: {imp['priority']}")
        print(f"Effort: {imp['effort_estimate']}")
        print(f"Description: {imp['description']}")
        print(f"Code preview:\n{imp['code_sample'][:500]}...")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="prometheus",
        description="Prometheus Self-Improving Engine CLI",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--db-path", default="./prometheus.db", help="Database path")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # run-cycle
    p_cycle = subparsers.add_parser("run-cycle", help="Run a full improvement cycle")
    p_cycle.set_defaults(func=cmd_run_cycle)

    # status
    p_status = subparsers.add_parser("status", help="Show engine status")
    p_status.set_defaults(func=cmd_status)

    # findings
    p_findings = subparsers.add_parser("findings", help="Show research findings")
    p_findings.add_argument("--days", type=int, default=7, help="Days to look back")
    p_findings.add_argument("--limit", type=int, default=10, help="Max findings")
    p_findings.set_defaults(func=cmd_findings)

    # gaps
    p_gaps = subparsers.add_parser("gaps", help="Show capability gaps")
    p_gaps.add_argument("--limit", type=int, default=10, help="Max gaps")
    p_gaps.set_defaults(func=cmd_gaps)

    # improvements
    p_imp = subparsers.add_parser("improvements", help="Show generated improvements")
    p_imp.add_argument("--limit", type=int, default=5, help="Max improvements")
    p_imp.set_defaults(func=cmd_improvements)

    args = parser.parse_args(argv)
    setup_logging(args.verbose)

    if args.command is None:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
