#!/usr/bin/env python3
"""
Prometheus Prime — Automated Testing Harness

Runs unit tests, integration tests, regression tests, and performance
benchmarks.  Designed to be invoked automatically after every code-change
cycle so that broken code never reaches production.
"""

from __future__ import annotations

__all__ = [
    "TestHarness",
    "TestResults",
    "BenchmarkMetrics",
]

import ast
import hashlib
import importlib
import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import warnings
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger("prometheus_prime.test_harness")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPORT_DIR = Path(".prometheus_prime/reports").resolve()

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class BenchmarkMetrics:
    """Performance metrics for a single benchmark run."""

    test_name: str
    mean_ms: float
    median_ms: float
    p95_ms: float
    p99_ms: float
    stddev_ms: float
    min_ms: float
    max_ms: float
    iterations: int
    passed: bool = True
    error: str = ""


@dataclass
class TestResults:
    """Aggregated results from the full test suite."""

    overall_passed: bool = False
    unit_tests: dict[str, Any] = field(default_factory=dict)
    integration_tests: dict[str, Any] = field(default_factory=dict)
    regression_tests: dict[str, Any] = field(default_factory=dict)
    benchmarks: list[BenchmarkMetrics] = field(default_factory=list)
    duration_seconds: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    errors: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, default=str)


# ---------------------------------------------------------------------------
# TestHarness
# ---------------------------------------------------------------------------


class TestHarness:
    """Automated test runner and benchmark suite.

    Usage::

        harness = TestHarness(project_root="/path/to/luqi")
        results = harness.run_all_tests()
        if not results.overall_passed:
            harness.generate_report(results)
    """

    def __init__(self, project_root: str | Path = ".") -> None:
        self.project_root = Path(project_root).resolve()
        self.report_dir = Path(REPORT_DIR)
        self.report_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1. Unit tests
    # ------------------------------------------------------------------

    def run_unit_tests(self, test_dir: str | Path | None = None) -> dict[str, Any]:
        """Execute pytest on the unit-test directory.

        Parameters
        ----------
        test_dir:
            Directory containing ``test_*.py`` files.  Defaults to
            ``<project_root>/tests/unit``.

        Returns
        -------
        dict
            ``{"passed": int, "failed": int, "skipped": int, "duration_ms": float,
            "output": str, "test_files": [str, …]}``
        """
        test_dir = Path(test_dir) if test_dir else self.project_root / "tests" / "unit"
        if not test_dir.exists():
            logger.warning("Unit test directory not found: %s", test_dir)
            return {"passed": 0, "failed": 0, "skipped": 0, "duration_ms": 0, "output": "", "test_files": []}

        logger.info("Running unit tests in %s ...", test_dir)
        start = time.perf_counter()

        cmd = [
            sys.executable, "-m", "pytest",
            str(test_dir),
            "-v", "--tb=short", "--no-header", "-q",
        ]

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            return {"passed": 0, "failed": 1, "skipped": 0, "duration_ms": 300_000,
                    "output": "Timeout after 300s", "test_files": []}

        duration_ms = (time.perf_counter() - start) * 1000
        output = proc.stdout + proc.stderr

        passed = failed = skipped = 0
        for line in output.splitlines():
            if "passed" in line:
                parts = line.split(", ")
                for p in parts:
                    if "passed" in p:
                        passed = int(p.split()[0])
                    elif "failed" in p:
                        failed = int(p.split()[0])
                    elif "skipped" in p:
                        skipped = int(p.split()[0])

        test_files = sorted(p.name for p in test_dir.glob("test_*.py"))

        result = {
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "duration_ms": round(duration_ms, 2),
            "output": output,
            "test_files": test_files,
        }
        logger.info("Unit tests — passed=%d, failed=%d, skipped=%d", passed, failed, skipped)
        return result

    # ------------------------------------------------------------------
    # 2. Integration tests
    # ------------------------------------------------------------------

    def run_integration_tests(self, test_dir: str | Path | None = None) -> dict[str, Any]:
        """Execute integration / end-to-end tests.

        Integration tests live in ``<project_root>/tests/integration`` by default.
        """
        test_dir = Path(test_dir) if test_dir else self.project_root / "tests" / "integration"
        if not test_dir.exists():
            logger.warning("Integration test directory not found: %s", test_dir)
            return {"passed": 0, "failed": 0, "skipped": 0, "duration_ms": 0, "output": "", "test_files": []}

        logger.info("Running integration tests in %s ...", test_dir)
        start = time.perf_counter()

        cmd = [
            sys.executable, "-m", "pytest",
            str(test_dir),
            "-v", "--tb=short", "--no-header", "-q",
        ]

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        except subprocess.TimeoutExpired:
            return {"passed": 0, "failed": 1, "skipped": 0, "duration_ms": 600_000,
                    "output": "Timeout after 600s", "test_files": []}

        duration_ms = (time.perf_counter() - start) * 1000
        output = proc.stdout + proc.stderr

        passed = failed = skipped = 0
        for line in output.splitlines():
            if "passed" in line:
                parts = line.split(", ")
                for p in parts:
                    if "passed" in p:
                        passed = int(p.split()[0])
                    elif "failed" in p:
                        failed = int(p.split()[0])
                    elif "skipped" in p:
                        skipped = int(p.split()[0])

        test_files = sorted(p.name for p in test_dir.glob("test_*.py"))

        result = {
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "duration_ms": round(duration_ms, 2),
            "output": output,
            "test_files": test_files,
        }
        logger.info("Integration tests — passed=%d, failed=%d, skipped=%d", passed, failed, skipped)
        return result

    # ------------------------------------------------------------------
    # 3. Regression tests
    # ------------------------------------------------------------------

    def run_regression_tests(self, baseline_file: str | Path | None = None) -> dict[str, Any]:
        """Detect regressions by comparing current output against a baseline.

        Reads the baseline from *baseline_file* (JSON).  Each entry should be::

            {"test_name": str, "input": Any, "expected_output": Any}

        The function under test is discovered by matching the module path
        derived from *test_name*.

        Returns
        -------
        dict
            ``{"passed": int, "failed": int, "regressions": [str, …]}``
        """
        baseline_file = Path(baseline_file) if baseline_file else self.report_dir / "baseline.json"
        if not baseline_file.exists():
            logger.warning("No baseline file found at %s; skipping regression tests", baseline_file)
            return {"passed": 0, "failed": 0, "regressions": [], "message": "No baseline"}

        baseline = json.loads(baseline_file.read_text(encoding="utf-8"))
        logger.info("Running regression tests (%d cases) ...", len(baseline))

        passed = failed = 0
        regressions: list[str] = []

        for case in baseline:
            test_name = case.get("test_name", "unknown")
            test_input = case.get("input")
            expected = case.get("expected_output")

            try:
                # Try to find and call the function
                module_name, func_name = test_name.rsplit(".", 1) if "." in test_name else ("__main__", test_name)
                module = importlib.import_module(module_name)
                func = getattr(module, func_name)
                actual = func(test_input)

                if actual == expected:
                    passed += 1
                else:
                    failed += 1
                    regressions.append(
                        f"{{test_name}}: expected {{expected!r}}, got {{actual!r}}"
                    )
            except Exception as exc:
                failed += 1
                regressions.append(f"{{test_name}}: exception {{exc}}")

        logger.info("Regression tests — passed=%d, failed=%d", passed, failed)
        return {"passed": passed, "failed": failed, "regressions": regressions}

    # ------------------------------------------------------------------
    # 4. Performance benchmarks
    # ------------------------------------------------------------------

    def run_benchmarks(
        self,
        benchmark_cases: list[dict[str, Any]] | None = None,
        warmup_iterations: int = 2,
        measured_iterations: int = 10,
    ) -> list[BenchmarkMetrics]:
        """Run micro-benchmarks for critical hot paths.

        Parameters
        ----------
        benchmark_cases:
            Each dict must contain ``name`` and ``callable`` keys.  Optionally
            ``args`` and ``kwargs`` for the callable.
        warmup_iterations:
            Number of untimed warmup runs (JIT warm-up, cache priming).
        measured_iterations:
            Number of timed iterations to collect statistics from.

        Returns
        -------
        list[BenchmarkMetrics]
        """
        if benchmark_cases is None:
            benchmark_cases = self._default_benchmarks()

        results: list[BenchmarkMetrics] = []

        for case in benchmark_cases:
            name = case["name"]
            func = case["callable"]
            args = case.get("args", ())
            kwargs = case.get("kwargs", {})

            logger.info("Benchmarking '%s' (%d iters) ...", name, measured_iterations)

            # Warmup
            for _ in range(warmup_iterations):
                try:
                    func(*args, **kwargs)
                except Exception:
                    pass  # ignore warmup errors

            # Measure
            times: list[float] = []
            for _ in range(measured_iterations):
                start = time.perf_counter()
                try:
                    func(*args, **kwargs)
                    times.append((time.perf_counter() - start) * 1000)
                except Exception as exc:
                    results.append(BenchmarkMetrics(
                        test_name=name,
                        mean_ms=0, median_ms=0, p95_ms=0, p99_ms=0,
                        stddev_ms=0, min_ms=0, max_ms=0,
                        iterations=0, passed=False, error=str(exc),
                    ))
                    break
            else:
                times_sorted = sorted(times)
                n = len(times_sorted)
                mean = sum(times_sorted) / n
                median = times_sorted[n // 2] if n % 2 else (times_sorted[n // 2 - 1] + times_sorted[n // 2]) / 2
                p95_idx = int(n * 0.95)
                p99_idx = int(n * 0.99)
                results.append(BenchmarkMetrics(
                    test_name=name,
                    mean_ms=round(mean, 3),
                    median_ms=round(median, 3),
                    p95_ms=round(times_sorted[min(p95_idx, n - 1)], 3),
                    p99_ms=round(times_sorted[min(p99_idx, n - 1)], 3),
                    stddev_ms=round((sum((t - mean) ** 2 for t in times_sorted) / n) ** 0.5, 3),
                    min_ms=round(times_sorted[0], 3),
                    max_ms=round(times_sorted[-1], 3),
                    iterations=n,
                    passed=True,
                ))

        return results

    def _default_benchmarks(self) -> list[dict[str, Any]]:
        """Return sensible default benchmarks for a typical ML API service."""
        return [
            {
                "name": "string_concat_1k",
                "callable": lambda: "x" * 1000,
                "args": (),
                "kwargs": {},
            },
            {
                "name": "dict_lookup_10k",
                "callable": lambda: {str(i): i for i in range(10000)}.get("5000"),
                "args": (),
                "kwargs": {},
            },
            {
                "name": "json_encode_decode",
                "callable": lambda: json.loads(json.dumps({"key": "value", "nested": {"a": 1, "b": [1, 2, 3]}})),
                "args": (),
                "kwargs": {},
            },
            {
                "name": "regex_match",
                "callable": lambda: __import__("re").match(r"\w+@\w+\.\w+", "user@example.com"),
                "args": (),
                "kwargs": {},
            },
            {
                "name": "list_sort_10k",
                "callable": lambda: sorted(__import__("random").sample(range(100000), 10000)),
                "args": (),
                "kwargs": {},
            },
        ]

    # ------------------------------------------------------------------
    # 5. Orchestrator: run everything
    # ------------------------------------------------------------------

    def run_all_tests(self) -> TestResults:
        """Execute the full test suite (unit + integration + regression + benchmarks).

        Returns a consolidated :class:`TestResults` object.
        """
        start = time.perf_counter()
        logger.info("=== FULL TEST SUITE START ===")

        results = TestResults()

        # Unit
        results.unit_tests = self.run_unit_tests()

        # Integration
        results.integration_tests = self.run_integration_tests()

        # Regression
        results.regression_tests = self.run_regression_tests()

        # Benchmarks
        results.benchmarks = self.run_benchmarks()

        # Aggregate
        unit_ok = results.unit_tests.get("failed", 0) == 0
        int_ok = results.integration_tests.get("failed", 0) == 0
        reg_ok = results.regression_tests.get("failed", 0) == 0
        bench_ok = all(b.passed for b in results.benchmarks)

        results.overall_passed = unit_ok and int_ok and reg_ok and bench_ok
        results.duration_seconds = round(time.perf_counter() - start, 2)

        if not results.overall_passed:
            if not unit_ok:
                results.errors.append("Unit tests failed")
            if not int_ok:
                results.errors.append("Integration tests failed")
            if not reg_ok:
                results.errors.append("Regression tests detected failures")
            if not bench_ok:
                failed_benches = [b.test_name for b in results.benchmarks if not b.passed]
                results.errors.append(f"Benchmarks failed: {failed_benches}")

        logger.info(
            "=== FULL TEST SUITE COMPLETE in %.2fs — passed=%s ===",
            results.duration_seconds,
            results.overall_passed,
        )
        return results

    # ------------------------------------------------------------------
    # 6. Report generation
    # ------------------------------------------------------------------

    def generate_report(self, results: TestResults) -> Path:
        """Write an HTML + JSON report to *REPORT_DIR*.

        Returns the path to the JSON report file.
        """
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        json_path = self.report_dir / f"test_report_{{ts}}.json"
        html_path = self.report_dir / f"test_report_{{ts}}.html"

        # JSON
        json_path.write_text(results.to_json(), encoding="utf-8")

        # HTML
        unit = results.unit_tests
        integ = results.integration_tests
        reg = results.regression_tests

        html = f"""\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Prometheus Prime Test Report — {{ts}}</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; }}
  h1 {{ color: #333; }}
  .pass {{ color: #16a34a; font-weight: bold; }}
  .fail {{ color: #dc2626; font-weight: bold; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
  th, td {{ border: 1px solid #ddd; padding: 0.5rem; text-align: left; }}
  th {{ background: #f3f4f6; }}
  pre {{ background: #f3f4f6; padding: 1rem; overflow-x: auto; font-size: 0.85rem; }}
</style>
</head>
<body>
<h1>Prometheus Prime Test Report</h1>
<p>Generated: {{results.timestamp}}</p>
<p>Overall: <span class="{{'pass' if results.overall_passed else 'fail'}}">
  {{'PASSED' if results.overall_passed else 'FAILED'}}
</span></p>
<p>Duration: {{results.duration_seconds}}s</p>

<h2>Unit Tests</h2>
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>Passed</td><td>{{unit.get('passed', 0)}}</td></tr>
<tr><td>Failed</td><td>{{unit.get('failed', 0)}}</td></tr>
<tr><td>Skipped</td><td>{{unit.get('skipped', 0)}}</td></tr>
<tr><td>Duration</td><td>{{unit.get('duration_ms', 0)}}ms</td></tr>
</table>

<h2>Integration Tests</h2>
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>Passed</td><td>{{integ.get('passed', 0)}}</td></tr>
<tr><td>Failed</td><td>{{integ.get('failed', 0)}}</td></tr>
<tr><td>Skipped</td><td>{{integ.get('skipped', 0)}}</td></tr>
<tr><td>Duration</td><td>{{integ.get('duration_ms', 0)}}ms</td></tr>
</table>

<h2>Regression Tests</h2>
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>Passed</td><td>{{reg.get('passed', 0)}}</td></tr>
<tr><td>Failed</td><td>{{reg.get('failed', 0)}}</td></tr>
<tr><td>Regressions</td><td>{{len(reg.get('regressions', []))}}</td></tr>
</table>

<h2>Benchmarks</h2>
<table>
<tr><th>Test</th><th>Mean (ms)</th><th>P95 (ms)</th><th>P99 (ms)</th><th>Status</th></tr>
"""
        for b in results.benchmarks:
            status_class = "pass" if b.passed else "fail"
            status_text = "PASS" if b.passed else f"FAIL: {{b.error}}"
            html += f"""\
<tr>
  <td>{{b.test_name}}</td>
  <td>{{b.mean_ms}}</td>
  <td>{{b.p95_ms}}</td>
  <td>{{b.p99_ms}}</td>
  <td class="{{status_class}}">{{status_text}}</td>
</tr>
"""

        html += """\
</table>

<h2>Errors</h2>
<pre>{{'\\n'.join(results.errors) or "None"}}</pre>
</body>
</html>
"""
        html_path.write_text(html, encoding="utf-8")

        logger.info("Test report written to %s and %s", json_path, html_path)
        return json_path

    # ------------------------------------------------------------------
    # 7. Baseline management
    # ------------------------------------------------------------------

    def save_baseline(self, baseline_cases: list[dict[str, Any]]) -> Path:
        """Save a new baseline for regression testing.

        Parameters
        ----------
        baseline_cases:
            List of ``{{"test_name": str, "input": Any, "expected_output": Any}}``.

        Returns the path to the saved baseline file.
        """
        baseline_path = self.report_dir / "baseline.json"
        baseline_path.write_text(json.dumps(baseline_cases, indent=2, default=str), encoding="utf-8")
        logger.info("Baseline saved with %d cases to %s", len(baseline_cases), baseline_path)
        return baseline_path

    def compare_with_baseline(self, current_results: TestResults) -> dict[str, Any]:
        """Compare current test results against the stored baseline.

        Returns a dict with regression / improvement flags.
        """
        baseline_path = self.report_dir / "baseline.json"
        if not baseline_path.exists():
            return {"has_baseline": False}

        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        comparison = {"has_baseline": True, "regressions": [], "improvements": []}

        # Compare unit test counts
        unit_base = sum(1 for c in baseline if "unit" in c.get("test_name", ""))
        unit_curr = current_results.unit_tests.get("passed", 0) + current_results.unit_tests.get("failed", 0)
        if unit_curr < unit_base:
            comparison["regressions"].append(f"Unit test count dropped: {{unit_base}} → {{unit_curr}}")
        elif unit_curr > unit_base:
            comparison["improvements"].append(f"Unit test count increased: {{unit_base}} → {{unit_curr}}")

        # Compare benchmark performance
        for bench in current_results.benchmarks:
            for base_case in baseline:
                if base_case.get("test_name") == bench.test_name:
                    base_time = base_case.get("expected_duration_ms", 0)
                    if base_time > 0 and bench.mean_ms > base_time * 1.2:
                        comparison["regressions"].append(
                            f"{{bench.test_name}} slowed: {{base_time}}ms → {{bench.mean_ms}}ms"
                        )
                    elif base_time > 0 and bench.mean_ms < base_time * 0.8:
                        comparison["improvements"].append(
                            f"{{bench.test_name}} improved: {{base_time}}ms → {{bench.mean_ms}}ms"
                        )

        return comparison
