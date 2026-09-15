"""
OMEGA-LUQI Executable Verification Harness

Implements the post's core insight: generation is cheap, verification is
expensive - so 'done' must be EXECUTABLE, not readable. A green py_compile
proves syntax only; this harness proves behavior.

VerificationSpec (supplied with the compile request, derived from the
REQUIREMENT - never from the same generation pass that wrote the code,
or the test encodes the same misunderstanding as the code and passes
while proving nothing):

  command        shell command to run (receives case input on stdin)
  cases          [{name, input, expected_output}]  - diffed exactly
  negative_cases [{name, input}]                  - MUST fail (non-zero exit)

Runner heuristics from the post:
  - each case runs in ISOLATION, so a flaky case can be re-run alone to
    tell whether the fault is the step or the environment
  - outputs are diffed against what the command ACTUALLY produced in the
    container (the shipped schema), not what was assumed
"""
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class VerifyCase(BaseModel):
    name: str
    input: str = ""
    expected_output: str = ""


class NegativeCase(BaseModel):
    name: str
    input: str = ""


class VerificationSpec(BaseModel):
    command: str = Field(min_length=1)
    cases: List[VerifyCase] = []
    negative_cases: List[NegativeCase] = []


# ---------------- pure evaluation logic (offline-tested) ----------------

def evaluate_case(name: str, actual: str, expected: str, exit_code: int) -> Dict[str, Any]:
    """A positive case passes iff exit 0 AND output matches exactly."""
    passed = (exit_code == 0 and actual.strip() == expected.strip())
    return {"name": name, "passed": passed, "exit_code": exit_code,
            "expected": expected.strip(), "actual": actual.strip(),
            "diff": ("" if passed else _first_diff_line(expected, actual))}


def evaluate_negative_case(name: str, exit_code: int) -> Dict[str, Any]:
    """A negative case passes iff the command FAILS (non-zero exit)."""
    passed = exit_code != 0
    return {"name": name, "passed": passed, "exit_code": exit_code,
            "note": "must-fail" + ("" if passed else " BUT IT PASSED - bug not caught")}


def _first_diff_line(expected: str, actual: str) -> str:
    for i, (a, b) in enumerate(zip(expected.splitlines(), actual.splitlines())):
        if a != b:
            return f"line {i + 1}: expected {a!r}, got {b!r}"
    return "length mismatch"


def verification_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    return {"total": total, "passed": passed, "failed": total - passed,
            "verified": total > 0 and passed == total}


# ---------------- container runner ----------------

def run_verification(container, spec: VerificationSpec) -> Dict[str, Any]:
    """Execute the spec inside an ALREADY-RUNNING compile container.
    Each case is exec'd in isolation. Returns the full report."""
    results: List[Dict[str, Any]] = []

    def run_one(shell: str, stdin_text: str):
        import base64  # base64 pipe avoids ALL shell-quoting breakage
        b64 = base64.b64encode(stdin_text.encode()).decode()
        cmd = f"/bin/sh -c 'echo {b64} | base64 -d | {shell}'"
        exit_code, output = container.exec_run(cmd, user="luqistudent")
        return exit_code, output.decode("utf-8", errors="replace")

    for case in spec.cases:
        exit_code, actual = run_one(spec.command, case.input)
        results.append(evaluate_case(case.name, actual, case.expected_output, exit_code))
    for case in spec.negative_cases:
        exit_code, _ = run_one(spec.command, case.input)
        results.append(evaluate_negative_case(case.name, exit_code))
    return {"results": results, **verification_summary(results)}
