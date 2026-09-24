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

## Current engine surfaces (as of 2026-09-24, omega @ 4b257583)
The chat front door is `core/hybrid_ai.py`. Five layers, no dead ends in ANY mode:
- Phase 1: compiled-regex guardrails (zero deps, always on, fire FIRST).
- Phase 1.6: deterministic knowledge router when sklearn is ABSENT.
- Phase 2: TF-IDF + LogisticRegression intent classifier (lazy sklearn;
  pinned quintet in requirements.txt: numpy 2.2.5 / scipy 1.16.2 /
  scikit-learn 1.7.2 / joblib 1.5.2 / threadpoolctl 3.6.0).
- Phase 2.5: sklearn PRESENT but sub-gate confidence -> router consulted
  BEFORE escalating (a sourced surface answer beats a refusal).
- Phase 3: confidence gate -> honest guided escalation (/v1/deep-research
  opt-in). Never a static refusal, never fabricated content.
Router surfaces (all sourced, all lazy-imported, each wrapped in try/except):
- Scam Shield: `core/finlit.py` (pattern catalogue, severity bands).
- World Pulse: `core/news_pulse.py` -> /v1/news/topics, /v1/news/headlines
  (7 topics, 9 zero-cost feeds, 10-min cache, fail-closed honesty).
- Technology Radar: `core/tech_radar.py` + `core/data/tech_radar.json`
  (19 sourced technologies) -> /v1/innovation/*; env-gated daily research
  daemon (LUQI_RESEARCH_DAEMON=1), cited digests, human-gated upgrades.
- Everyday Services: `core/everyday_services.py` (SASSA/SARS/UIF/NSFAS...).
- African History Archive: `core/african_history.py` (29 entries).
- Wikipedia backstop: `core/free_knowledge.py` (live lookup, URL shown).
Pack matching law: rarity-weighted (1/doc-count) + TITLE ANCHORING - a pack
answers only when a query word names the entry title/id (anchors>=2, or
score>=0.4, or single-word title match). Prose-only overlap never hijacks.
Test batteries (run before ANY push; CI is the gate):
- tests/verify_hybrid_fallback.py - 41 checks (ML-off + stubbed-ML sub-gate).
- tests/verify_news.py - 29 checks. tests/verify_innovation.py - ~80 checks.
- Golden set: POST /v1/hybrid/eval (admin) - 20/20 floor enforced at 0.9.
Byte-verification law: every pushed file is fetched back from
raw.githubusercontent.com at the pinned commit SHA and sha256-diffed against
local ground truth; a failed fetch is retried, NEVER treated as a mismatch.

## Working rules
- Ideas from external chats arrive as ONE-LINE ideas; implementations are built
  here to standard. Never port code unseen (see coverage ledger's rejected list).
- Secrets live in `.env` only, never in code/tests/docs/chats.
- Alembic for schema changes; never edit shipped migrations.
