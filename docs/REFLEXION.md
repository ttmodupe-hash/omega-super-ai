# Reflexion Critique Stage (UNIFY-16)

Draft answer → critique (factuality, grounding, policy) → **accept / revise / flag**,
with every run persisted to `reflexion_traces` (migration 006) including the
parsed critique and per-stage latency.

## API

| Endpoint | Purpose |
|---|---|
| `POST /v1/reflexion/answer` | Answer via the pipeline. `force=true|false` overrides routing. |
| `POST /v1/reflexion/ab` | **A/B harness**: same question answered direct (never critiqued) vs full pipeline (always critiqued); both traces share one `ab_group` for side-by-side evaluation. Response includes latency delta and multiplier. |
| `GET /v1/reflexion/traces/{id}` | Fetch the stored critique trace. |
| `GET /v1/reflexion/config` | The routing policy + latency budget (live, inspectable). |

## Latency budget (binding)

| Query class | LLM calls | Added latency |
|---|---|---|
| Simple (not routed) | 1 (draft only) | **0 — critique skipped entirely** |
| Complex/risky, accepted | 2 (draft + critique) | ≤ 1 extra call |
| Complex/risky, revised | 3 (draft + critique + revise) | ≤ 2 extra calls — **structural maximum** |

Hard caps: draft 60 s, critique 45 s, revise 60 s timeouts. Worst case is
therefore bounded at **3× a single call**, never a runaway loop: exactly one
critique pass, at most one revise pass, **no recursive self-reflection** by
design. Simple queries never pay for the stage — that is the documented answer
to "cheap enough not to double latency on simple queries."

## Routing heuristic (deterministic, no LLM)

Route to critique when any of:
- question longer than 280 chars, or
- multi-part (more than one `?`), or
- risk-domain keyword (health, finance, law, statistics/verifiable claims,
  recommendations — see `_RISKY_RE` in `core/reflexion.py`).

`force` on `/answer` overrides either way (used by the A/B harness).

## Fail-closed rules

- Unparseable or invalid critique JSON → verdict `flag` (never ship blind).
- `flag` verdict → user gets an honest "I won't guess" message, not the draft.
- No `KIMI_API_KEY` → 500 (kimi_client contract). Upstream network failure → 503.
- DB down → answer still returned, but `trace_persisted: false` (honest, not silent).

## Observability

Every run writes one `reflexion_traces` row: question, routing decision +
reason, draft, parsed critique JSON, verdict, final answer, and
draft/critique/revise/total milliseconds — the data the A/B harness and the
latency budget are audited against.
