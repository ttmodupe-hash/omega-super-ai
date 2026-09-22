# Changelog

## [5.36.0] - 2026-09-22
### Added
- African History Archive v1.0.0: 26 sourced entries, /v1/history endpoints, BCE-aware timeline, >=2 sources enforced at load, UNESCO base, 28-check verification battery (shipped in the 5.35.8-5.35.10 line; changelog drift corrected here).
- Everyday Services Pack v1.0.0: SASSA/SRD/SARS/UIF/NSFAS guides, /v1/services endpoints, official sources only, scam warning in every entry, 190-check verification battery (same drift correction).
### Fixed
- Test gate campaign (Issue 17) closed: orchestrator admin tests now follow the live LUQI_ADMIN_SECRET env (root cause of the 5 "403-on-authorized" failures - the hardcoded test secret never matched CI's env value; the human-session theory was disproven by direct probe: admin header alone returns 200).
- Anonymous gate-release attempts assert 403, matching the real engine contract (FastAPI APIKeyHeader auto_error refuses missing credentials with 403; the earlier 401 edits were made from theory, not observation, and are reverted).
- Router wiring audit verified green as evolved (glob discovery + suffix matching + dormant whitelist); the predicted app.mount() blind spot does not exist - all API routers mount via include_router.
- Version drift closed: engine 5.35.10 -> 5.36.0, aligned with changelog head (drift tests green again).
- requirements.txt: cryptography restored (AES-256-GCM backup pipeline, core/db_backup.py lazy import) - its removal as 'unused' broke test_backup_cipher_roundtrip on clean CI installs; reproduced on Python 3.11 + exact CI pins, fixed and re-proven (197/197 with live Postgres 16).
### CI
- Feature verification batteries (tests/verify_history.py, tests/verify_services.py) staged for the CI gate as a dedicated step - they are standalone scripts, not pytest modules, so appending them to the pytest line would collect zero checks. NOTE: the workflow edit itself is PENDING - the pushing token lacks the workflow scope; apply the 5-line step via the GitHub web editor.

## [5.35.7] - 2026-09-15
### Fixed
- test determinism campaign: autouse env-isolation fixture (26 failures -> 5, 192/197 passing locally on the six CI files, exact env + real Postgres 5433).
- WAL test uses a file-based SQLite DB (WAL is impossible on :memory:); wiring audit gains a dormant-router whitelist + suffix matching (None-safe); INSECURE test forces its own default-secret condition.
### Known remaining (Issue 17)
- 5 orchestrator failures: with a live DB the engine correctly requires an authenticated HUMAN SESSION for gate releases (403 on admin-header-only). Tests previously passed only against the DB-less degraded path. Fix = register/login fixture presenting a user JWT.
- 1 wiring-audit gap: engine mounts surface via app.mount(); audit metric cannot see inside mounts (rework: compare against app.openapi() paths).


## [5.35.6] - 2026-09-15
### Fixed
- alembic 0001: DDL path resolves repo root (was alembic/core -> FileNotFoundError); skips comment-only SQL fragments; bootstraps luqi_app_user role (idempotent DO-block).
- models: Text import for curriculum_lessons.content_body; curriculum_lessons + vocational_modules added; lab_progress timestamps get server_default=func.now().
- 002 seed: tier PRIMARY (TierType contract) with is_active + created_at; bulk construct declares all three.
- 003/004: CREATE TABLE IF NOT EXISTS (ORM mirrors already create user_skill_profiles, cert_ledger, dead_man_switch_registry).
- Proven locally: alembic upgrade head passes 0001->004 on fresh Postgres 16; engine boots with Database layer initialised.


## [5.35.0] - 2026-09-15
- Spatial telemetry: server-side physics for client-rendered 3D labs (pure load evaluation,
  safety envelope). Passing simulations earn real skill credit via the engine (unlocks, certificates).

## [5.34.0] - 2026-09-15

## [5.35.1] - 2026-09-15
### Fixed

## [5.35.5] - 2026-09-15
### Fixed
- core/models.py: added curriculum_lessons + vocational_modules tables (Text import included) - migration 002 bulk-inserts into both, and neither existed in Base.metadata, so alembic upgrade head failed at 002 with 'relation does not exist' after 0001 finally passed.

## [5.35.4] - 2026-09-15
### Fixed
- alembic 0001: skip empty/comment-only SQL fragments before op.execute. security_rls.sql's header comment ends with a semicolon (the commented-out CREATE ROLE ... PASSWORD line), so split(';') yielded a comment-only fragment and psycopg2 raised 'can't execute an empty query' (CI run 4). Both SQL files re-verified: no PL/pgSQL $$ bodies; remaining statements are clean DDL.

## [5.35.3] - 2026-09-15
### Fixed
- alembic 0001: _read_ddl now resolves the repo root correctly (two dirnames landed in alembic/ -> FileNotFoundError on core/security_rls.sql, killing the CI migration step sub-second on every run).
- alembic 0001: bootstrap the luqi_app_user role (idempotent DO-block, NOLOGIN) before the RLS policies bind to it - the SQL files reference TO luqi_app_user but never create the role.

## [5.35.2] - 2026-09-15
### Fixed
- enterprise_models: ACTUALLY added the missing Integer import. v5.35.1's guard matched the word 'Integer' elsewhere in the file and skipped the edit; the import line is verified by direct inspection in this release.
- core/enterprise_models.py: added missing Integer import (NameError crashed alembic
  upgrade head on CI and would crash the app on boot; unblocks CI and Railway).
- Tags: removed mis-pointed v5.29.1 / v5.31.0 (both pointed at July commits).
- Submission consensus: three independent checks (validator, structural quality, safety) must agree;
  disagreement routes to human review. No hardcoded skills, JWT auth, works across all trades.

## [5.33.0] - 2026-09-15
- Certificate dashboard (static/credentials.html): skills, hours, certificates with public verify links.
- GET /v1/skills/certificates (per-user listing).
- Real-time unlock alerts: WhatsApp via Twilio (env-gated) with SMS fallback; never blocks the unlock.

## [5.32.0] - 2026-09-15
- Public credential verification: GET /v1/credentials/verify/{serial} checks the real cert ledger
  (employer-facing, read-only). External provider registry listed honestly as PENDING_INTEGRATION.

## [5.31.5] - 2026-09-15
- Cross-artifact consistency audits: router wiring (no orphaned APIRouters in core/,
  30+ mounted) and secret inventory (every *_KEY/*_SECRET/*_TOKEN in the env template
  is represented on the token board).

## [5.31.4] - 2026-09-15
- Production smoke advanced: stale-deploy detection (live /v1/health version must equal the pushed
  commit's version) and GitHub-Secrets admin auth (PROD_ADMIN_SECRET).

## [5.31.3] - 2026-09-15
- Production smoke workflow (prod_smoke.yml + tools/prod_smoke.py): runs the route matrix against a
  live deployment on demand. Rejected the pasted "deployment broker" (syntax error, broken API host,
  created a new Railway project per push; Railway auto-deploys natively).

## [5.31.2] - 2026-09-15
- start.sh boot wrapper: Alembic migrations run automatically before serving (conditional on
  DATABASE_URL, loud failure on real migration errors). Railway deployments need no manual migration step.

## [5.31.1] - 2026-09-15
- Railway deployment layer: railway.toml (Nixpacks override of the lab Dockerfile, uvicorn start,
  /v1/health check), RAILWAY_DEPLOYMENT.md (browser-only runbook: Postgres plugin, variables,
  migration one-shot, custom domain), runbook host-choice pointer.

## [5.31.0] - 2026-09-15
- Migration 004: dead_man_switch_registry persisted to Postgres (FORCE RLS, corrected GUC, heartbeat trigger on user_skill_profiles); ORM on shared Base.
- Ops-channel legacy alerts via the existing throttled broadcaster - honest wording (gate task registered, no execution claimed).

## [5.30.0] - 2026-09-15
- Data portability: GET /v1/user/export compiles the caller's own data (POPIA s23 / GDPR Art.20 access-request package, JSON download).
- Digital legacy guard (dead man's switch): inactivity tracking wired to login, trusted-contact configuration, admin /check registers 30%-gate tasks + SMS alerts on breach. No autonomous action - the gate applies to death too.
- Corrected false external claims: no GitHub push has occurred (repo HEAD verified unchanged since July); archive at 310/351 at time of writing.

## [5.29.2] - 2026-09-15
- AGENTS.md assistant-onboarding blueprint at repo root (repo-as-source-of-truth for any future AI session).

## [5.29.1] - 2026-09-15
- Monolith consolidation: original omega-super-ai repo (v25.1.0, 351 files) archived at
  legacy/omega-super-ai-v25.1.0/; capability gap analysis published
  (docs/OMEGA_SUPERAI_GAP_ANALYSIS.md) with ranked port candidates
  (dead_mans_switch, data_portability, accessibility_deaf lead).

All notable changes to the OMEGA-LUQI engine. One line per version: what it
lets you do that you couldn't before.

## [5.29.0] - 2026-09-15
- Hume EVI ingestion hooks: HMAC-verified webhooks, distress intervention routes to the real crisis line + mentor alert. Client subscription remains the integration step.
- Daily context-sync cron workflow (fixed action key, `python -m core.context_sync` runner, daily cadence).

## [5.28.1] - 2026-09-15
- Drift alerts: Slack/Discord webhooks, throttled one per marker per day, delivery failures never break the audit.

## [5.28.0] - 2026-09-15
- Context sync auditor: GitHub commits + coverage-ledger reconciliation; corrected API host; fail-closed token; admin `/v1/sync/audit`.

## [5.27.1] - 2026-09-15
- Languages phrasebook: Emergency category with crisis lines; ISO-639-3 codes displayed. Deployment runbook restored + guarded.

## [5.27.0] - 2026-09-15
- African languages phrasebook (22 phrases x 10 languages, pronunciation, speech playback, honest no-translator design).
- Load shedding preparedness guide (stage reference, persistent checklist, wattage guide, backup options, manual-slot countdown).

## [5.26.0] - 2026-09-15
- Migration 003: persistent skill tables (FORCE RLS, correct GUC, 3-letter country codes, FK to students) + ORM on shared Base.
- Accurate CHANGELOG.md; de-duplication governance protocol in CONTRIBUTING.md.

## [5.25.1] - 2026-09-15
- Shareable skill certificates: 100% live-readiness gate, env-only signing salt (fail-closed), public verification endpoint, JWT JS client.

## [5.25.0] - 2026-09-15
- Skill engine: TVET trade gap analysis with experience roadmaps; heuristic structured-submission checks (honestly labeled); credential hashes; versioned trade registry.

## [5.24.1] - 2026-09-15
- `ApiResponse` typed Pydantic model (ISO-8601, honest cached flag); `registry.query()` unified async dispatch front for the 8 keyless providers.

## [5.24.0] - 2026-09-15
- Centralized free-provider registry: uniform envelope, typed ProviderError kinds, concurrent health checks, estimated savings counter.

## [5.23.0] - 2026-09-15
- Free knowledge scatter-gather: Wikipedia/Open-Meteo/World Bank + OpenAlex behind circuit breakers and token buckets; per-query provenance hashing; SANS 10400 weather-safety note.

## [5.22.0] - 2026-09-15
- 20-query golden evaluation set (CI floor 90%, drove corpus + gate calibration); cost telemetry with 80% SMS budget alarm; institutional readiness pack; civil-engineering intent class.

## [5.21.1] - 2026-09-15
- Full health-API lessons encoded: served-version verifier, HTML-200 detector, empty-envelope flag, spl_version never trusted, assert_history_survives, per-source snapshot body retention.

## [5.21.0] - 2026-09-15
- Keyless health data layer (DailyMed/RxNorm/ClinicalTrials/PubChem/openFDA); append-only (id, version, sha256) snapshot store.

## [5.20.0] - 2026-09-15
- SQLite WAL pilot mode + pgloader migration scaffold; automated freeze gate helper; PWA live status pill; CloudFront static-asset distribution (APIs bypassed).

## [5.19.0] - 2026-09-15
- Terraform scaffold for af-south-1; feature flags (safety unflaggable); error-budget math + docs/SRE.md.

## [5.18.1] - 2026-09-15
- DORA-style ops metrics (deploy frequency, change failure rate, MTTR); static gate (every core module compiles on PR); SECURITY.md + docs/DEVOPS.md.

## [5.18.0] - 2026-09-15
- Hybrid engine v2: tiered per-intent confidence gates, Electrical/Mechanical N4-N6 classes, admin-gated live calibration, latency + pii_redacted telemetry.

## [5.17.1] - 2026-09-15
- CORE rate limiting (shared gate, daily quota, 429 honesty); open-source readiness: MIT LICENSE, CONTRIBUTING.md, Hacktoberfest topics.

## [5.17.0] - 2026-09-15
- Zero-dep knowledge base over repo docs (EULA included, sourced excerpts); engine output contracts (502 fail-closed on drift).

## [5.16.0] - 2026-09-15
- Hybrid AI front door: always-on regex guardrails (zero-dep), lazy sklearn ML, calibrated tiered thresholds, kill switch, 7 TVET intent classes.

## [5.15.0] - 2026-09-15
- Companion memory layer (per-user recall, scrubbed, capped); feedback loop capture with admin aggregates.

## [5.14.0] - 2026-09-15
- Executable verification harness: fixed cases + must-fail negatives run in-sandbox; honest `success_unverified` labeling.

## [5.13.0] - 2026-09-15
- Full keyless geocoding family (8 sources) with Nominatim→Photon fallback chain; extended tool-router signals (postcode, IP, health).

## [5.12.0] - 2026-09-15
- Nominatim geocoding (policy-compliant rate gate); deterministic tool router (when-to-use logic for free APIs).

## [5.11.0] - 2026-09-15
- Jarvis companion avatar (procedural, gate-reactive, four states); zero-key browser TTS fallback; public companion status endpoint.

## [5.10.0] - 2026-09-15
- Academic literature grounding: Crossref/OpenAlex/PubMed/arXiv (+CORE in .1), keyless, one-source-down resilience.

## [5.9.x] - 2026-09-14
- Multipolar model router (real Claude/Gemini adapters, Kimi fallback chains); seed migration 002; hardened secrets provisioning; corrected API map (Hume RESERVED); minimal .env active-set template.

## [5.8.x] - 2026-09-14
- All 9 Kimi engines unified behind core/kimi_client.py (one group); token status board (16 integrations, INSECURE/RESERVED states).

## [5.7.x] - 2026-09-14
- AES-256-GCM backup pipeline (stable key required, admin-gated); literature free-API family begins; import-safe db replication router (failover + failback).

## [5.6.x] - 2026-09-14
- Gate-lock SMS alerts (correct Africa's Talking endpoints) wired at all six freeze sites; Alembic single-head chain guard.

## [5.5.x] - 2026-09-14
- Ops cockpit + live dashboards; hardened nginx (HTTP/2, rate zones, streaming voice route); paste-overwrite guards; Terraform begins.

## [5.4.x] - 2026-09-14
- Code integrity engine (SHA-256 AST fingerprints); 100-thread failover stress suite; universal-learning companion with mandatory medical disclaimers.

## [5.3.x] - 2026-09-14
- Sovereign bio-mineral compiles (deployment intent gates at 30%); shared Kimi parser (crash bug eliminated structurally); audit snapshot size caps.

## [5.2.x] - 2026-09-14
- Pedagogical convergence engine; failover/integrity stress suite at root; content-policy guard test (medical disclaimer locked in).

## [5.1.x] - 2026-09-14
- Alembic scaffold (baseline folds RLS + wallet DDL); voice playback endpoint; dev-agent sandbox compile phase.

## [5.0.0] - 2026-09-14
- Sovereign RPA kernel with SSRF guard; live automation terminal; unified engine milestone.

## [4.x] - 2026-09-14
- Auth (fail-closed JWT, pbkdf2, revocation, rate limits); production boot guards; Redis state store; wallet ledger with idempotent credit hook; multi-gateway routing; webhooks HMAC; free-tier caps; sandbox reaper; self-healing diagnostics.

## [3.x] - 2026-09-14
- Consumer shield, tax estimation engine (real 30% gate), consumer/medical EULA alignment, core consolidation.

## [2.x] - 2026-09-14
- Orchestrator + ironclad 30% human gate with audit trail; Docker sandbox; WebSocket terminal; PWA + offline layer; persistence schema.

## [1.x] - 2026-09-14
- OMEGA-LUQI merge: the OMEGA AI baseline unified with the Project Bug Fixes stream into the sovereign engine.
