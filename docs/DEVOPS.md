# Luqi-AI DevOps Lifecycle Map

Our artifacts mapped to the standard 8-stage lifecycle (external reference:
Hyperlink InfoSystem DevOps guide, reviewed 2026-09-14).

| Stage | Luqi-AI artifact |
|---|---|
| Plan | Roadmap (docs/OMEGA-LUQI_Roadmap.md), pilot definition |
| Code | CONTRIBUTING.md standards; static gate test (every core module compiles) |
| Build | Dockerfile (lab image); GitHub Actions `omega_luqi_sync.yml` |
| Test | 6 suites, 100+ tests; wallet integration vs CI Postgres; alembic chain guard |
| Release | Alembic migrations (0001 baseline + 002 seed); versioned zips |
| Deploy | systemd unit + boot guards; deploy/inject_secrets.sh; nginx TLS 1.3 |
| Operate | VERIFY_STAGING.sh; token-status board; ops metrics (DORA-style) |
| Monitor | /v1/monitor/telemetry, /v1/ops/metrics (deploy freq, failure rate, MTTR), audit logs |

## KPIs we track (per the guide's measurement principle)
- deployment_frequency_per_week, change_failure_rate_pct, mttr_hours -> GET /v1/ops/metrics
- pending gate depth, sandbox counts, per-provider call/failure -> telemetry board
- token cost per student session -> docs/OMEGA-LUQI_Subsidy_Model.md

## DevSecOps posture
See SECURITY.md. Security shifted left: guards at boot, contracts at engine
boundaries, HMAC at webhooks, RLS at the database.
