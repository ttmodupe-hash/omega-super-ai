"""
Prometheus metrics endpoint — engine-native observability (backlog: v18 /api/prometheus gap)

GET /metrics — Prometheus text exposition format (v0.0.4), scrape-ready.

HONESTY LAW: every sample is fed by a REAL engine counter or gauge that
already exists — no invented metrics, no placeholder zeros dressed as data:

  luqi_http_requests_total      middleware counter (method, route family, status)
  luqi_http_request_duration_*  middleware latency histogram (route family)
  luqi_gate_pending             live 30%-gate queue depth (state store)
  luqi_llm_calls_total          unified-client call counts per provider (cost telemetry)
  luqi_llm_est_cost_usd         ESTIMATED spend per provider (chars/4 estimate, labeled)
  luqi_cost_budget_pct          estimated spend vs MONTHLY_TOKEN_BUDGET_USD
  luqi_ops_deployments_7d       DORA window counters (ops_metrics event log)
  luqi_ops_incidents_open       open incidents in the 7d window
  luqi_uptime_seconds           process uptime
  luqi_build_info               version stamp (always 1)

Secret-free by design: counts and gauges only, never payload data — same
philosophy as /v1/companion/status. Scrape endpoint is unauthenticated so a
standard Prometheus/Grafana agent can reach it; it exposes nothing sensitive.
"""
import threading
import time
from typing import Callable, Dict, Optional

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

router = APIRouter(tags=["Observability"])

_STARTED_AT = time.time()

# ── Middleware counters (real, incremented per request) ──────────────────
_lock = threading.Lock()
_http_counts: Dict[tuple, int] = {}        # (method, family, status) -> count
_http_durations: Dict[str, list] = {}      # family -> [seconds, ...] (bounded)
_DURATION_KEEP = 2048                      # per-family ring bound
_DURATION_BUCKETS = (0.005, 0.025, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)

_SKIP_FAMILIES = {"/metrics"}              # never count the scrape itself


def _route_family(request: Request, status: int) -> str:
    """Low-cardinality path label: the matched route template, else a family
    of static asset roots, else 'unmatched'."""
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    if path:
        return path
    raw = request.url.path
    return raw if raw in _SKIP_FAMILIES else "unmatched"


async def metrics_middleware(request: Request, call_next: Callable):
    """Count every request + record latency. Failure here must NEVER break
    the business path — observability is best-effort by law."""
    start = time.perf_counter()
    try:
        response = await call_next(request)
        status = response.status_code
    except Exception:
        status = 500
        raise
    finally:
        try:
            family = _route_family(request, status)
            if family not in _SKIP_FAMILIES:
                elapsed = time.perf_counter() - start
                with _lock:
                    key = (request.method, family, status)
                    _http_counts[key] = _http_counts.get(key, 0) + 1
                    buf = _http_durations.setdefault(family, [])
                    buf.append(elapsed)
                    if len(buf) > _DURATION_KEEP:
                        del buf[: len(buf) - _DURATION_KEEP]
        except Exception:
            pass
    return response


# ── Exposition rendering (pure, offline-testable) ────────────────────────

def _esc(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _line(name: str, value: float, labels: Optional[Dict[str, str]] = None) -> str:
    if labels:
        inner = ",".join(f'{k}="{_esc(str(v))}"' for k, v in labels.items())
        return f"{name}{{{inner}}} {value}"
    return f"{name} {value}"


def render_prometheus(
    http_counts: Dict[tuple, int],
    http_durations: Dict[str, list],
    gate_pending: Optional[int],
    cost_telemetry: Dict,
    ops: Dict,
    version: str,
    now: Optional[float] = None,
) -> str:
    """Render the full exposition. Pure function — all state passed in."""
    now = now if now is not None else time.time()
    out = []

    out += ['# HELP luqi_http_requests_total HTTP requests by method, route family and status.',
            '# TYPE luqi_http_requests_total counter']
    for (method, family, status), count in sorted(http_counts.items()):
        out.append(_line("luqi_http_requests_total", count,
                         {"method": method, "route": family, "status": str(status)}))

    out += ['# HELP luqi_http_request_duration_seconds Request latency by route family.',
            '# TYPE luqi_http_request_duration_seconds histogram']
    for family, samples in sorted(http_durations.items()):
        total = sum(samples)
        for b in _DURATION_BUCKETS:
            le = "+Inf" if b == _DURATION_BUCKETS[-1] else str(b)
            n = sum(1 for s in samples if s <= b) if b != _DURATION_BUCKETS[-1] else len(samples)
            out.append(_line("luqi_http_request_duration_seconds_bucket", n,
                             {"route": family, "le": le}))
        out.append(_line("luqi_http_request_duration_seconds_bucket", len(samples),
                         {"route": family, "le": "+Inf"}))
        out.append(_line("luqi_http_request_duration_seconds_sum", round(total, 6),
                         {"route": family}))
        out.append(_line("luqi_http_request_duration_seconds_count", len(samples),
                         {"route": family}))

    out += ['# HELP luqi_gate_pending Tasks halted at the 30% human gate right now.',
            '# TYPE luqi_gate_pending gauge']
    if gate_pending is not None:
        out.append(_line("luqi_gate_pending", gate_pending))

    out += ['# HELP luqi_llm_calls_total Unified-client LLM calls per provider.',
            '# TYPE luqi_llm_calls_total counter',
            '# HELP luqi_llm_est_cost_usd ESTIMATED LLM spend per provider (chars/4 estimate; reconcile with invoices).',
            '# TYPE luqi_llm_est_cost_usd gauge']
    for provider, agg in sorted(cost_telemetry.get("by_provider", {}).items()):
        out.append(_line("luqi_llm_calls_total", agg.get("calls", 0), {"provider": provider}))
        out.append(_line("luqi_llm_est_cost_usd", round(agg.get("est_cost_usd", 0.0), 6),
                         {"provider": provider}))

    out += ['# HELP luqi_cost_budget_pct Estimated spend as % of MONTHLY_TOKEN_BUDGET_USD.',
            '# TYPE luqi_cost_budget_pct gauge']
    out.append(_line("luqi_cost_budget_pct", cost_telemetry.get("pct_of_budget", 0.0)))

    out += ['# HELP luqi_ops_deployments_7d Deployments logged in the 7-day DORA window.',
            '# TYPE luqi_ops_deployments_7d gauge',
            '# HELP luqi_ops_incidents_open Incidents started but not resolved in the window.',
            '# TYPE luqi_ops_incidents_open gauge']
    out.append(_line("luqi_ops_deployments_7d", ops.get("deployments", 0)))
    out.append(_line("luqi_ops_incidents_open", ops.get("open_incidents", 0)))

    out += ['# HELP luqi_uptime_seconds Engine process uptime.',
            '# TYPE luqi_uptime_seconds gauge']
    out.append(_line("luqi_uptime_seconds", round(now - _STARTED_AT, 1)))

    out += ['# HELP luqi_build_info Engine version stamp (always 1).',
            '# TYPE luqi_build_info gauge']
    out.append(_line("luqi_build_info", 1, {"version": version}))

    return "\n".join(out) + "\n"


# ── Scrape endpoint ──────────────────────────────────────────────────────

@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics(request: Request) -> PlainTextResponse:
    from .main_types import TaskStatus
    from .state_store import get_state_store
    from . import cost_telemetry as _cost
    from . import ops_metrics as _ops

    gate_pending = None
    try:
        gate_pending = sum(1 for t in get_state_store().all()
                           if t.status == TaskStatus.PENDING_HUMAN_APPROVAL)
    except Exception:
        pass  # gauge omitted rather than faked

    with _lock:
        counts = dict(_http_counts)
        durations = {k: list(v) for k, v in _http_durations.items()}

    body = render_prometheus(
        http_counts=counts,
        http_durations=durations,
        gate_pending=gate_pending,
        cost_telemetry=_cost.telemetry(),
        ops=_ops.compute_metrics(_ops._events),
        version=request.app.version,
    )
    return PlainTextResponse(body, media_type="text/plain; version=0.0.4; charset=utf-8")
