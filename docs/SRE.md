# Luqi-AI SRE Notes (pilot-phase)

## SLOs
| Service | Target | Rationale |
|---|---|---|
| API availability | 99.5% monthly | pilot-tier; raise to 99.9% after first term |
| Gate approval latency (SMS alerted) | < 15 min | the 30% gate must never block a school day |
| PWA install success (low-end Android) | > 95% | the whole model depends on it |

## Error budget
0.5% of a 30-day window = 21,600s (~3.6h) of allowed downtime.
Computed live: core.ops_metrics.error_budget_remaining().
Alert when remaining < 50% of budget before day 15 (fast burn).

## Automated freeze gate (CI)
    python -c "from core.ops_metrics import freeze_required; \
assert not freeze_required(99.5, 30*86400, float('$DOWNTIME_SECONDS')), 'budget exhausted: deploy frozen'"
(The pasted recommendation referenced a 'feature_freeze' key that does not
exist; freeze_required() is the real API. Wire DOWNTIME_SECONDS from your
monitoring; hotfixes excepted by policy.)

## Policy
- Budget exhausted -> feature freeze (no new merges until SLO recovered).
- Safety layers (gate, guardrails, PII scrub) are NEVER flaggable off.
- Every incident -> POST /v1/ops/event (admin) so MTTR is real, not estimated.

## Alerting path
Token board (admin) -> /v1/companion/status (public heartbeat)
-> Africa's Talking SMS via notifications.py for gate freezes.
