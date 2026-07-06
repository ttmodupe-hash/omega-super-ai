#!/usr/bin/env python3
"""
Prometheus Prime — Command-Line Interface

Unified CLI for managing the self-improving AI engine. Provides commands
for learning, testing, deploying, monitoring, and reporting.

Usage::

    $ python -m prometheus_prime.prime_cli status
    $ python -m prometheus_prime.prime_cli generate "Add sentiment analysis"
    $ python -m prometheus_prime.prime_cli learn --session-id abc123
    $ python -m prometheus_prime.prime_cli test --all
    $ python -m prometheus_prime.prime_cli deploy --strategy canary
    $ python -m prometheus_prime.prime_cli monitor --start
    $ python -m prometheus_prime.prime_cli report --type weekly
    $ python -m prometheus_prime.prime_cli evolve-prompt --mode chat
    $ python -m prometheus_prime.prime_cli feedback --session-id abc123 --rating 5
    $ python -m prometheus_prime.prime_cli gaps
    $ python -m prometheus_prime.prime_cli roadmap
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure the parent package is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.prometheus_prime.orchestrator_prime import PrometheusPrime
from backend.prometheus_prime.code_generator import CodeGenerator
from backend.prometheus_prime.safe_experiment import SafeExperiment
from backend.prometheus_prime.test_harness import TestHarness
from backend.prometheus_prime.deployment_manager import DeploymentManager
from backend.prometheus_prime.self_repair import SelfRepair

logger = logging.getLogger("prometheus_prime.cli")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_prime(db_path: str | None = None) -> PrometheusPrime:
    return PrometheusPrime(db_path=db_path)


def _print_json(data: dict) -> None:
    print(json.dumps(data, indent=2, default=str))


def _print_table(headers: list[str], rows: list[list[str]]) -> None:
    """Print a simple ASCII table."""
    widths = [max(len(str(h)), max((len(str(r[i])) for r in rows), default=0)) for i, h in enumerate(headers)]
    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    header_row = "|" + "|".join(f" {h:^{widths[i]}} " for i, h in enumerate(headers)) + "|"

    print(sep)
    print(header_row)
    print(sep)
    for row in rows:
        print("|" + "|".join(f" {str(row[i]):^{widths[i]}} " for i in range(len(headers))) + "|")
    print(sep)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_status(args: argparse.Namespace) -> int:
    """Show Prometheus Prime system status."""
    prime = _init_prime(args.db_path)
    status = prime.get_status()

    if args.json:
        _print_json(status)
        return 0

    print(f"\n{'='*60}")
    print(f"  PROMETHEUS PRIME — SYSTEM STATUS")
    print(f"  {status['timestamp']}")
    print(f"{'='*60}\n")

    stats = status["learning_statistics"]
    print(f"  Total interactions:      {stats['total_interactions']:,}")
    print(f"  Total conversations:     {stats['total_conversations']:,}")
    print(f"  Avg quality score:       {stats['average_quality_score']:.3f}")
    print(f"  Knowledge entities:      {stats['knowledge_entities']:,}")
    print(f"  Capabilities tracked:    {stats['capabilities_count']}")
    print(f"\n  Active prompt modes:     {', '.join(status['active_prompt_modes']) or 'None'}")

    print(f"\n  {'Capability Scores:'}")
    for cap, score in status.get("capability_scores", {}).items():
        bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
        print(f"    {cap:20s} [{bar}] {score:.3f}")

    if status.get("last_cycles"):
        print(f"\n  Recent Cycles:")
        for c in status["last_cycles"]:
            print(f"    {c['type']:10s} — {c['status']:12s} — {c.get('completed_at', 'N/A')}")

    print(f"\n{'='*60}\n")
    prime.close()
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    """Generate code for a feature requirement."""
    print(f"Generating code for: {args.requirement}")
    cg = CodeGenerator(project_root=args.project_root)
    spec = cg.generate_feature_spec(args.requirement)
    code_files = cg.generate_code(spec)

    if args.output_dir:
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        for rel_path, source in code_files.items():
            dest = out_dir / rel_path.replace("/", "_")
            dest.write_text(source, encoding="utf-8")
            print(f"  Written: {dest}")
    else:
        for rel_path, source in code_files.items():
            print(f"\n--- {rel_path} ---\n{source[:500]}...")

    # Review
    if args.review:
        for rel_path, source in code_files.items():
            review = cg.review_code(source)
            print(f"\nReview for {rel_path}: {'PASS' if review.passed else 'FAIL'} (score: {review.score:.2f})")
            for issue in review.issues:
                print(f"  [{issue['severity']}] {issue['category']}: {issue['message']}")

    return 0


def cmd_experiment(args: argparse.Namespace) -> int:
    """Run a safe experiment."""
    se = SafeExperiment()

    if args.list:
        experiments = se.list_experiments()
        if experiments:
            _print_table(["ID", "Status", "Created"],
                         [[e["id"], e["status"], e["created_at"]] for e in experiments])
        else:
            print("No experiments found.")
        return 0

    if args.experiment_id:
        results = se.get_experiment_results(args.experiment_id)
        if "error" in results:
            print(f"Error: {results['error']}")
            return 1
        _print_json(results)
        return 0

    # Create and run a new experiment from feature code
    if not args.feature_file:
        print("Error: --feature-file is required (unless using --list or --experiment-id)")
        return 1

    feature_code = Path(args.feature_file).read_text(encoding="utf-8")
    test_code = Path(args.test_file).read_text(encoding="utf-8") if args.test_file else "# No tests\n"

    eid = se.create_experiment(feature_code, test_code)
    print(f"Experiment created: {eid}")

    results = se.run_experiment(eid)
    print(f"\nResults: {'PASSED' if results.passed else 'FAILED'}")
    print(f"Metrics: {json.dumps(results.metrics, indent=2)}")

    if results.passed and args.canary:
        status = se.canary_deploy(eid, rollout_percent=args.canary_percent)
        print(f"Canary: {status.status} at {status.rollout_percent}% (health: {status.health_score:.2f})")

    return 0 if results.passed else 1


def cmd_test(args: argparse.Namespace) -> int:
    """Run the test suite."""
    harness = TestHarness(project_root=args.project_root)

    if args.all:
        results = harness.run_all_tests()
    elif args.unit:
        results = TestResults()
        results.unit_tests = harness.run_unit_tests(args.unit)
        results.overall_passed = results.unit_tests.get("failed", 0) == 0
    elif args.integration:
        results = TestResults()
        results.integration_tests = harness.run_integration_tests(args.integration)
        results.overall_passed = results.integration_tests.get("failed", 0) == 0
    elif args.benchmarks:
        results = TestResults()
        results.benchmarks = harness.run_benchmarks()
        results.overall_passed = all(b.passed for b in results.benchmarks)
    else:
        results = harness.run_all_tests()

    if args.json:
        print(results.to_json())
    else:
        print(f"\nOverall: {'PASSED' if results.overall_passed else 'FAILED'}")
        print(f"Duration: {results.duration_seconds}s")
        if results.unit_tests:
            u = results.unit_tests
            print(f"Unit: {u.get('passed', 0)} passed, {u.get('failed', 0)} failed")
        if results.integration_tests:
            i = results.integration_tests
            print(f"Integration: {i.get('passed', 0)} passed, {i.get('failed', 0)} failed")
        if results.regression_tests:
            r = results.regression_tests
            print(f"Regression: {r.get('passed', 0)} passed, {r.get('failed', 0)} failed")
        if results.benchmarks:
            print(f"Benchmarks: {len(results.benchmarks)} run")
            for b in results.benchmarks:
                status = "OK" if b.passed else f"FAIL ({b.error})"
                print(f"  {b.test_name}: mean={b.mean_ms}ms p95={b.p95_ms}ms [{status}]")
        if results.errors:
            print(f"\nErrors: {'; '.join(results.errors)}")

    if args.report:
        report_path = harness.generate_report(results)
        print(f"\nReport saved to: {report_path}")

    return 0 if results.overall_passed else 1


def cmd_deploy(args: argparse.Namespace) -> int:
    """Deploy code changes."""
    dm = DeploymentManager(project_root=args.project_root)

    if args.history:
        history = dm.get_deployment_history(limit=args.limit)
        if history:
            _print_table(["ID", "Strategy", "Status", "Started"],
                         [[h.get("deploy_id", "")[:12], h.get("strategy", ""),
                           h.get("status", ""), h.get("started_at", "")[:19]] for h in history])
        else:
            print("No deployment history.")
        return 0

    if args.rollback_id:
        record = dm.rollback(args.rollback_id)
        if record:
            print(f"Rolled back: {record.deploy_id} → {record.status.value}")
        else:
            print(f"Deployment not found: {args.rollback_id}")
            return 1
        return 0

    if not args.files:
        print("Error: --files is required (unless using --history or --rollback-id)")
        return 1

    # Read files
    files: dict[str, str] = {}
    for file_path in args.files:
        p = Path(file_path)
        if not p.exists():
            print(f"Error: File not found: {file_path}")
            return 1
        rel = p.name  # use basename as relative path
        files[rel] = p.read_text(encoding="utf-8")

    record = dm.deploy(
        files=files,
        strategy=args.strategy,
        rollout_percent=args.canary_percent,
    )
    print(f"Deployment: {record.deploy_id}")
    print(f"Strategy: {record.strategy}")
    print(f"Status: {record.status.value}")
    print(f"Files: {len(record.files_deployed)}")

    if record.status == DeploymentStatus.FAILED:
        print(f"Error: {record.error_message}")
        return 1
    return 0


def cmd_monitor(args: argparse.Namespace) -> int:
    """Start/stop health monitoring."""
    repair = SelfRepair()

    if args.start:
        repair.start_monitoring()
        print("Health monitoring started.")
        if args.duration:
            print(f"Running for {args.duration} seconds...")
            time.sleep(args.duration)
            repair.stop_monitoring()
            print("Monitoring stopped.")
        else:
            print("Press Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                repair.stop_monitoring()
                print("\nMonitoring stopped.")

    elif args.stop:
        repair.stop_monitoring()
        print("Health monitoring stopped.")

    elif args.status:
        summary = repair.get_status_summary()
        _print_json(summary)

    elif args.check:
        status = repair.check_health()
        _print_json({"health": {
            "overall_score": status.overall_score,
            "cpu_percent": status.cpu_percent,
            "memory_percent": status.memory_percent,
            "disk_percent": status.disk_percent,
            "error_rate": status.error_rate,
            "uptime_seconds": status.uptime_seconds,
        }})

    else:
        summary = repair.get_status_summary()
        health = summary["health"]
        print(f"\nOverall Score: {health['overall_score']:.2f}/1.00")
        print(f"  CPU: {health['cpu_percent']:.1f}%")
        print(f"  Memory: {health['memory_percent']:.1f}%")
        print(f"  Disk: {health['disk_percent']:.1f}%")
        print(f"  Error Rate: {health['error_rate']:.4f}")
        print(f"  Uptime: {health['uptime_seconds']:.0f}s")
        print(f"\nAnomalies: {summary['anomalies']['total_detected']} detected, {summary['anomalies']['open']} open")
        print(f"Repairs: {summary['repairs']['successful']}/{summary['repairs']['total']} successful")

    return 0


def cmd_report(args: argparse.Namespace) -> int:
    """Generate and display a report."""
    prime = _init_prime(args.db_path)
    report = prime.get_report(args.type)

    if args.output:
        out = Path(args.output)
        out.write_text(report, encoding="utf-8")
        print(f"Report saved to: {out}")
    else:
        print(report)

    prime.close()
    return 0


def cmd_learn(args: argparse.Namespace) -> int:
    """Trigger learning from a session."""
    prime = _init_prime(args.db_path)

    result = prime.continuous_learning(
        session_id=args.session_id,
        query=args.query or "",
        response=args.response or "",
        mode=args.mode,
        duration_ms=args.duration_ms,
    )

    if args.json:
        _print_json(result)
    else:
        print(f"Learning result: {result['status']}")
        print(f"  Lessons: {result['lessons']}")
        print(f"  Facts: {result['facts']}")

    prime.close()
    return 0 if result["status"] == "ok" else 1


def cmd_feedback(args: argparse.Namespace) -> int:
    """Submit explicit user feedback."""
    prime = _init_prime(args.db_path)
    prime.feedback.collect_explicit_feedback(
        session_id=args.session_id,
        rating=args.rating,
        comment=args.comment,
    )
    satisfaction = prime.feedback.calculate_satisfaction_score(args.session_id)
    print(f"Feedback recorded: {args.rating}/5 stars")
    print(f"Satisfaction score: {satisfaction:.3f}")
    prime.close()
    return 0


def cmd_gaps(args: argparse.Namespace) -> int:
    """Show capability gaps."""
    prime = _init_prime(args.db_path)
    gaps = prime.meta.discover_capability_gaps()

    if args.json:
        _print_json({"gaps": gaps})
    else:
        print(f"\n{'='*60}")
        print(f"  CAPABILITY GAPS — {len(gaps)} found")
        print(f"{'='*60}\n")
        for gap in gaps:
            print(f"  Pattern: {gap['pattern']}")
            print(f"  Frequency: {gap['frequency']} ({gap['percentage']}%)")
            print(f"  Fix: {gap['suggested_fix']}")
            if gap.get('examples'):
                print(f"  Examples:")
                for ex in gap['examples'][:2]:
                    print(f"    Q: {ex['query'][:80]}...")
            print()

    prime.close()
    return 0


def cmd_roadmap(args: argparse.Namespace) -> int:
    """Show strategic roadmap."""
    prime = _init_prime(args.db_path)
    roadmap = prime.planner.create_roadmap()

    if args.json:
        _print_json(roadmap)
    else:
        print(f"\n{'='*60}")
        print(f"  STRATEGIC ROADMAP")
        print(f"  {roadmap.get('generated_at', 'N/A')}")
        print(f"  Total items: {roadmap['total_items']} | Est. timeline: {roadmap['timeline_estimate_weeks']} weeks")
        print(f"{'='*60}\n")

        for goal in roadmap.get("goals", []):
            print(f"  Goal #{goal['goal_id']}: {goal['title']}")
            print(f"  Priority: {goal['priority']}")
            for item in goal.get("items", []):
                print(f"    - [{item.get('status', 'todo')}] {item['title']} (impact={item['impact']}, effort={item['effort']})")
            print()

    prime.close()
    return 0


def cmd_evolve_prompt(args: argparse.Namespace) -> int:
    """Evolve a system prompt for a given mode."""
    prime = _init_prime(args.db_path)
    print(f"Evolving prompt for mode: {args.mode}")
    new_prompt = prime.evolution.evolve_prompt(args.mode, generations=args.generations)
    print(f"New prompt ({{len(new_prompt)}} chars):")
    print(f"  {{new_prompt[:200]}}...")
    prime.close()
    return 0


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="prime",
        description="Prometheus Prime — Self-Improving AI Engine CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  %(prog)s status                          Show system status
  %(prog)s generate "Add sentiment analysis"  Generate code for a feature
  %(prog)s test --all                      Run full test suite
  %(prog)s deploy --strategy canary --files file1.py file2.py
  %(prog)s monitor --start                 Start health monitoring
  %(prog)s report --type weekly            Generate weekly report
  %(prog)s gaps                            Show capability gaps
  %(prog)s roadmap                         Show strategic roadmap
        """,
    )
    parser.add_argument("--db-path", default=None, help="Path to the Prometheus Prime SQLite DB")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- status ---
    subparsers.add_parser("status", help="Show system status")

    # --- generate ---
    gen_parser = subparsers.add_parser("generate", help="Generate code for a feature")
    gen_parser.add_argument("requirement", help="Feature requirement description")
    gen_parser.add_argument("--output-dir", default=None, help="Directory to write generated files")
    gen_parser.add_argument("--review", action="store_true", help="Run code review on generated code")

    # --- experiment ---
    exp_parser = subparsers.add_parser("experiment", help="Run a safe experiment")
    exp_parser.add_argument("--feature-file", help="Path to feature code file")
    exp_parser.add_argument("--test-file", help="Path to test code file")
    exp_parser.add_argument("--list", action="store_true", help="List all experiments")
    exp_parser.add_argument("--experiment-id", help="Show results for a specific experiment")
    exp_parser.add_argument("--canary", action="store_true", help="Run canary deployment after success")
    exp_parser.add_argument("--canary-percent", type=int, default=5, help="Canary rollout percentage")

    # --- test ---
    test_parser = subparsers.add_parser("test", help="Run test suite")
    test_parser.add_argument("--all", action="store_true", help="Run all tests")
    test_parser.add_argument("--unit", help="Run unit tests in specified directory")
    test_parser.add_argument("--integration", help="Run integration tests in specified directory")
    test_parser.add_argument("--benchmarks", action="store_true", help="Run benchmarks only")
    test_parser.add_argument("--report", action="store_true", help="Generate HTML report")

    # --- deploy ---
    deploy_parser = subparsers.add_parser("deploy", help="Deploy code changes")
    deploy_parser.add_argument("--strategy", default="canary", choices=["immediate", "canary", "blue_green"])
    deploy_parser.add_argument("--files", nargs="+", help="Files to deploy")
    deploy_parser.add_argument("--canary-percent", type=int, default=10)
    deploy_parser.add_argument("--history", action="store_true", help="Show deployment history")
    deploy_parser.add_argument("--rollback-id", help="Rollback a deployment")
    deploy_parser.add_argument("--limit", type=int, default=20, help="History limit")

    # --- monitor ---
    mon_parser = subparsers.add_parser("monitor", help="Health monitoring")
    mon_parser.add_argument("--start", action="store_true", help="Start monitoring")
    mon_parser.add_argument("--stop", action="store_true", help="Stop monitoring")
    mon_parser.add_argument("--status", action="store_true", help="Show monitoring status")
    mon_parser.add_argument("--check", action="store_true", help="Run one-shot health check")
    mon_parser.add_argument("--duration", type=int, default=0, help="Monitoring duration in seconds")

    # --- report ---
    report_parser = subparsers.add_parser("report", help="Generate reports")
    report_parser.add_argument("--type", default="daily", choices=["daily", "weekly", "monthly", "strategic"])
    report_parser.add_argument("--output", help="Save report to file")

    # --- learn ---
    learn_parser = subparsers.add_parser("learn", help="Trigger learning from a session")
    learn_parser.add_argument("--session-id", required=True)
    learn_parser.add_argument("--query", default="")
    learn_parser.add_argument("--response", default="")
    learn_parser.add_argument("--mode", default="chat")
    learn_parser.add_argument("--duration-ms", type=int, default=0)

    # --- feedback ---
    fb_parser = subparsers.add_parser("feedback", help="Submit user feedback")
    fb_parser.add_argument("--session-id", required=True)
    fb_parser.add_argument("--rating", type=float, required=True, help="Rating 0-5")
    fb_parser.add_argument("--comment", default=None)

    # --- gaps ---
    subparsers.add_parser("gaps", help="Show capability gaps")

    # --- roadmap ---
    subparsers.add_parser("roadmap", help="Show strategic roadmap")

    # --- evolve-prompt ---
    evolve_parser = subparsers.add_parser("evolve-prompt", help="Evolve system prompt")
    evolve_parser.add_argument("--mode", default="chat", help="Operating mode")
    evolve_parser.add_argument("--generations", type=int, default=3, help="Number of GA generations")

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    command_map = {
        "status": cmd_status,
        "generate": cmd_generate,
        "experiment": cmd_experiment,
        "test": cmd_test,
        "deploy": cmd_deploy,
        "monitor": cmd_monitor,
        "report": cmd_report,
        "learn": cmd_learn,
        "feedback": cmd_feedback,
        "gaps": cmd_gaps,
        "roadmap": cmd_roadmap,
        "evolve-prompt": cmd_evolve_prompt,
    }

    handler = command_map.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
