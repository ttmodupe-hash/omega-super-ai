"""
OMEGA-LUQI Sandbox Runner v2 (Issue 32) - tiered isolation + capped self-recalibration.

Tier 1: combined static gate - string patterns (open/import/exec/eval/dunder) AND a
        proper AST visitor (forbidden imports: subprocess/sys/shutil/socket/ctypes;
        forbidden calls: eval/exec/compile/__import__; dunder attribute traversal).
Tier 2: ephemeral Docker container when available (network none, mem/cpu caps, non-root,
        read-only mount, auto-remove, hard timeout) - real kernel-namespace isolation.
Tier 3: subprocess `python -I` fallback with POSIX rlimits (Windows: timeout-only).
Failures return structured {exit_code, stderr} and optionally drive a capped
recalibration loop (stderr -> fixer callback -> retry, bounded) - the self-healing
loop, honest: feedback to the model, never silent auto-patch.
"""
from __future__ import annotations

import ast
import os
import subprocess
import sys
import tempfile
import time

BANNED_STRINGS = ("import", "exec(", "eval(", "open(", "__", "compile(")
FORBIDDEN_IMPORTS = {"subprocess", "sys", "shutil", "socket", "ctypes", "os", "pathlib"}
FORBIDDEN_CALLS = {"eval", "exec", "compile", "__import__", "open", "getattr"}
DEFAULT_TIMEOUT = float(os.getenv("SANDBOX_TIMEOUT_S", "10"))
RLIMIT_MB = int(os.getenv("SANDBOX_RLIMIT_MB", "256"))
DOCKER_IMAGE = os.getenv("SANDBOX_DOCKER_IMAGE", "python:3.11-slim")
DOCKER_ENABLED = os.getenv("SANDBOX_DOCKER", "auto") != "off"

_meter = {"runs": 0, "rejected": 0, "timeouts": 0, "errors": 0, "docker_runs": 0, "recalibrations": 0}


class _ASTVerifier(ast.NodeVisitor):
    def __init__(self):
        self.issues: list[str] = []

    def visit_Import(self, node):
        for a in node.names:
            if a.name.split(".")[0] in FORBIDDEN_IMPORTS:
                self.issues.append(f"forbidden import: {a.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module and node.module.split(".")[0] in FORBIDDEN_IMPORTS:
            self.issues.append(f"forbidden import from: {node.module}")
        self.generic_visit(node)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load) and node.id in FORBIDDEN_CALLS:
            self.issues.append(f"forbidden call: {node.id}")
        self.generic_visit(node)

    def visit_Attribute(self, node):
        if node.attr.startswith("__"):
            self.issues.append(f"dunder access: .{node.attr}")
        self.generic_visit(node)


def static_gate(code: str) -> tuple[bool, str]:
    """Tier 1: string patterns + AST audit. Both must pass."""
    low = code.lower()
    for b in BANNED_STRINGS:
        if b in low:
            return False, f"string gate rejected: {b!r}"
    if len(code) > 20000:
        return False, "code over 20KB cap"
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"syntax error: {e}"
    v = _ASTVerifier()
    v.visit(tree)
    if v.issues:
        return False, "; ".join(v.issues[:5])
    return True, "ok"


def _preexec():
    if os.name == "posix":
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (RLIMIT_MB * 1024 * 1024, -1))


_RUNNER = ("import sys\n"
           "code = open(sys.argv[1], encoding='utf-8').read()\n"
           "ns = {}\n"
           "exec(compile(code, '<worker>', 'exec'), ns)")


def _docker_available() -> bool:
    if not DOCKER_ENABLED or os.name != "posix":
        return False
    try:
        import docker  # type: ignore
        docker.from_env().ping()
        return True
    except Exception:
        return False


async def _run_docker(code: str, timeout: float) -> dict:
    import docker  # type: ignore
    client = docker.from_env()
    with tempfile.TemporaryDirectory() as td:
        sp = os.path.join(td, "payload.py")
        with open(sp, "w", encoding="utf-8") as f:
            f.write(code)
        try:
            logs = client.containers.run(
                image=DOCKER_IMAGE, command="python /app/payload.py",
                volumes={td: {"bind": "/app", "mode": "ro"}},
                network_mode="none", mem_limit=f"{RLIMIT_MB}m", nano_cpus=1_000_000_000,
                user="1000:1000", detach=False, remove=True,
                stdout=True, stderr=True, timeout=int(timeout))
            _meter["docker_runs"] += 1
            return {"ok": True, "stage": "docker", "output": logs.decode()[:4000] if isinstance(logs, bytes) else str(logs)[:4000], "error": None, "exit_code": 0}
        except docker.errors.ContainerError as ce:
            err = ce.stderr.decode() if isinstance(ce.stderr, bytes) else str(ce.stderr or ce)
            _meter["errors"] += 1
            return {"ok": False, "stage": "docker", "output": "", "error": err[-3000:], "exit_code": getattr(ce, "exit_status", -1) or -1}
        except Exception as exc:
            _meter["errors"] += 1
            return {"ok": False, "stage": "docker", "output": "", "error": f"{type(exc).__name__}: {exc}", "exit_code": -1}


async def _run_subprocess(code: str, timeout: float) -> dict:
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code)
            path = f.name
        proc = subprocess.run([sys.executable, "-I", "-c", _RUNNER, path],
                              capture_output=True, text=True, timeout=timeout,
                              preexec_fn=_preexec if os.name == "posix" else None)
        os.unlink(path)
        if proc.returncode == 0:
            _meter["runs"] += 1
            return {"ok": True, "stage": "subprocess", "output": proc.stdout.strip()[:4000], "error": None, "exit_code": 0}
        _meter["errors"] += 1
        return {"ok": False, "stage": "subprocess", "output": proc.stdout.strip()[:1000],
                "error": proc.stderr.strip()[-3000:], "exit_code": proc.returncode}
    except subprocess.TimeoutExpired:
        _meter["timeouts"] += 1
        return {"ok": False, "stage": "timeout", "output": "", "error": f"exceeded {timeout}s", "exit_code": -1}
    except Exception as exc:
        _meter["errors"] += 1
        return {"ok": False, "stage": "sandbox", "output": "", "error": f"{type(exc).__name__}: {exc}", "exit_code": -1}


async def run_python(code: str, timeout: float = DEFAULT_TIMEOUT) -> dict:
    """Tiered execution: gate -> docker (if available) -> isolated subprocess."""
    t0 = time.perf_counter()
    ok, why = static_gate(code)
    if not ok:
        _meter["rejected"] += 1
        return {"ok": False, "stage": "gate", "error": why, "output": "", "exit_code": -2,
                "latency_ms": round((time.perf_counter() - t0) * 1000, 2)}
    result = await _run_docker(code, timeout) if _docker_available() else await _run_subprocess(code, timeout)
    result["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    if not result["ok"] and result.get("stage") in ("docker", "subprocess"):
        await _feedback(result.get("error") or "")   # execution failures -> self-diagnose
    return result


async def run_with_recalibration(code: str, fixer, max_retries: int = 2,
                                 timeout: float = DEFAULT_TIMEOUT) -> dict:
    """The capped self-healing loop: failure -> structured stderr -> fixer(code, err)
    -> retry. Bounded by max_retries; returns the last verdict. Never auto-patches
    anything except via the caller-reviewed fixer callback."""
    current, last = code, None
    for attempt in range(max_retries + 1):
        last = await run_python(current, timeout)
        if last["ok"]:
            return {**last, "attempts": attempt + 1, "recalibrations": _meter["recalibrations"]}
        if attempt < max_retries:
            _meter["recalibrations"] += 1
            try:
                current = await fixer(current, last.get("error", ""))
                if not current or not str(current).strip():
                    break
            except Exception:
                break
    return {**last, "attempts": max_retries + 1, "recalibrations": _meter["recalibrations"]}


async def _feedback(traceback_text: str) -> None:
    try:
        from . import self_diagnose
        result = await self_diagnose._diagnose(traceback_text)
        self_diagnose._log.append({"ts": time.time(), "trace_excerpt": traceback_text[:500],
                                   **result, "auto_applied": False})
        if len(self_diagnose._log) > self_diagnose.MAX_ENTRIES:
            del self_diagnose._log[: len(self_diagnose._log) - self_diagnose.MAX_ENTRIES]
    except Exception:
        pass


def metrics() -> dict:
    return {**_meter, "docker_available": _docker_available()}
