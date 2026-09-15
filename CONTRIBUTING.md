# Contributing to Luqi-AI

Thanks for helping build Africa's sovereign education engine. This repo is
Hacktoberfest-ready: look for issues labeled `good first issue`.

## Ground rules (the house standard)
- **No simulated anything.** Real API calls or fail-closed errors. Tests catch fakes.
- **Fail-closed**: missing keys/secrets -> loud refusal, never fabricated success.
- **Import-safety**: `from core.main import app` must work with only fastapi+pydantic.
  Heavy deps (docker, sqlalchemy, sklearn, redis, cryptography) load lazily.
- **Every freeze at the 30% gate is sacred.** Payments/filings never auto-execute.
- **PII never leaves the VPC unscrubbed.** Use `core.pii_scrub.scrub_pii`.
- **Tests**: pure logic unit-tested offline; suites run with plain `pytest -v`.

## Good first issues (from the roadmap)
1. Field-test the classroom WebRTC mesh (mesh.js) on real hotspot hardware; document results.
2. Vet near-miss telemetry into the hybrid classifier via POST /v1/hybrid/calibrate (admin-gated).
3. Hume EVI integration: wire `HUME_API_KEY` (currently RESERVED) into a voice-emotion endpoint.
4. African-language prompt support: extend prompt_support.py wrappers for isiZulu/Sesotho.
5. Dashboard i18n: language switcher for the ops cockpit.
6. CORE API: wire your free key, tune CORE_RATE_LIMIT_SECONDS from observed 429s.

## Process
1. Fork -> branch -> PR. CI runs 5 suites; all must be green.
2. Alembic for schema changes; never edit `0001_initial_schema` after it ships.
3. No secrets in code, tests, docs, or chat. `.env` only, gitignored.

## De-duplication protocol (governance)
The blueprint chat is a spec source ONLY. Do not port its code: it ships
plausible structure with fabricated verification and lower security baselines.
Interface: one-line ideas -> built here to standard. The canonical CHANGELOG
is CHANGELOG.md - update it with every PR.
