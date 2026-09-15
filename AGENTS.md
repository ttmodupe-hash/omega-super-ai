# AGENTS.md - Assistant Onboarding (repo-as-source-of-truth)

Every AI assistant session starts here. This file exists so no assistant ever
needs chat history: the repository IS the memory.

## First actions for any assistant
1. Read `docs/OMEGA_STREAM_COVERAGE.md` - the ledger of everything merged from
   the upstream stream, everything deliberately rejected (with reasons), and
   everything still open.
2. Read `docs/OMEGA_SUPERAI_GAP_ANALYSIS.md` - the monolith capability map:
   SUPERSEDED (never port), PARTIAL (port review), MISSING (ranked port list:
   dead man's switch, data portability, deaf accessibility lead).
3. Read `CHANGELOG.md` - version history; `core/main.py` version must match its head.
4. Read `DEPLOYMENT_RUNBOOK.md` before suggesting anything operational.

## The house standard (non-negotiable)
- No simulated anything: real API calls or fail-closed errors. Tests catch fakes.
- Fail-closed: missing keys/secrets -> loud refusal, never fabricated success.
- Import-safety: `from core.main import app` works with only fastapi+pydantic;
  heavy deps (docker, sqlalchemy, sklearn, redis, cryptography) load lazily.
- The 30% Human Gate is sacred: payments/filings/deployments never auto-execute.
- PII never leaves the VPC unscrubbed (`core/pii_scrub.py`).
- One engine, one process: no standalone microservices, no second FastAPI apps.
- Safety is unflaggable (`core/feature_flags.py`): gate, guardrails, PII scrub.
- Every PR: tests green (6 suites), CHANGELOG entry, version == changelog head.

## Working rules
- Ideas from external chats arrive as ONE-LINE ideas; implementations are built
  here to standard. Never port code unseen (see coverage ledger's rejected list).
- Secrets live in `.env` only, never in code/tests/docs/chats.
- Alembic for schema changes; never edit shipped migrations.
