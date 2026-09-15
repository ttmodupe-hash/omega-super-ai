# OMEGA-LUQI Architecture Roadmap

## Phase R1 — Decentralized Peer-to-Peer Local Lab Mesh — MOSTLY SHIPPED (v4.8.0)
mesh.js: complete WebRTC handshake + two real signaling transports
(HttpRelaySignalingTransport via /v1/mesh/signal relay; ManualSignalingTransport
for fully offline copy/paste exchange). Remaining: field-test on hotspot hardware.
Integrate WebRTC DataChannels into the PWA client.
In rural settings with no internet, one phone downloads the Luqi-AI package once
(via mobile data) and serves as a local host over a closed Wi-Fi mesh — every
other phone in the classroom runs the 3D labs at zero data cost.

## Phase R2 — Offline-First TinyML Language Core
Bundle an ultra-compact client-side reasoning engine (ONNX Runtime Web running a
quantized small model, compiled to WebAssembly) inside the browser cache.
Basic lab guidance and troubleshooting run fully offline on the student's phone;
external APIs (Kimi / Gemini) are only called for complex architectural problems.
Impact: operational token costs drop dramatically; primary-tier becomes truly free to serve.

## Shipped in v5.31.0
- [x] Migration 004 (persistent dead man's switch + DB heartbeat trigger); honest ops-channel legacy alerts

## Shipped in v5.30.0
- [x] Data portability endpoint (POPIA/GDPR access-request export)
- [x] Digital legacy guard (dead man's switch -> 30% gate, never autonomous)

## Shipped in v5.29.0
- [x] Hume EVI ingestion hooks (HMAC-verified webhooks, distress intervention -> crisis line + mentor alert; client subscription remains)
- [x] Daily context-sync cron workflow (fixed action key, real module runner, daily cadence)

## Shipped in v5.28.1
- [x] Drift alerts (Slack/Discord webhooks; throttled 1/marker/day; delivery failures never break the audit)

## Shipped in v5.28.0
- [x] Context sync auditor (GitHub commits + coverage ledger reconciliation; fixed host; fail-closed token; admin /v1/sync/audit)

## Shipped in v5.27.0
- [x] African languages phrasebook (21 phrases x 10 languages, pronunciation, speech playback, honest no-translator design)
- [x] Load shedding preparedness guide (8-stage reference, persistent checklist, wattage guide, backup options, manual slot countdown; mock 'real-time' claims rejected)

## Shipped in v5.26.0
- [x] Migration 003 (skill tables: FORCE RLS, correct GUC, 3-letter codes, FK; ORM on shared Base); accurate CHANGELOG.md; de-dup governance note

## Shipped in v5.25.1
- [x] Certificate authority (100% live-readiness gate; env salt fail-closed; public verification endpoint; JWT JS client)

## Shipped in v5.25.0
- [x] Skill engine (TVET trade gap analysis + experience roadmaps; heuristic structured-submission checks honestly labeled; credential hashes; versioned trade registry)

## Shipped in v5.24.1
- [x] ApiResponse typed Pydantic model (Generic[T], ISO-8601, honest cached flag); registry.query() unified async dispatch front

## Shipped in v5.24.0
- [x] Centralized free-provider registry (8 providers; uniform envelope; typed ProviderError kinds; concurrent health checks; estimated savings counter)

## Shipped in v5.23.0
- [x] Free knowledge scatter-gather (Wikipedia/Open-Meteo/World Bank/OpenAlex; circuit breakers + token buckets; provenance hashing; no fabricated fallbacks)

## Shipped in v5.22.0
- [x] 20-query golden evaluation set (CI floor 85%; admin /v1/hybrid/eval; civil class added; SQL-injection guardrail)
- [x] Cost telemetry (real call counting, estimated spend vs budget, 80% SMS alarm throttled daily)
- [x] Institutional readiness pack (docs/INSTITUTIONAL_READINESS.md)

## Shipped in v5.21.1
- [x] Full-article lessons: served-version verifier, HTML-200 detector, empty-envelope flag, spl_version never trusted, assert_history_survives, per-source body retention (SNAPSHOT_FULL_BODY_SOURCES)

## Shipped in v5.21.0
- [x] Keyless health data layer (DailyMed/RxNorm/ClinicalTrials/PubChem/openFDA; RxNorm lesson encoded; medical disclaimer on all)
- [x] Snapshot store (append-only (id,version,sha256) - the review's rewrite-proof architecture, replay-tested)

## Shipped in v5.20.0
- [x] Pilot SQLite WAL mode ($0 pilot DB; migration scaffold to pgloader/RDS)
- [x] Automated freeze gate helper (freeze_required) + corrected CI semantics in SRE.md
- [x] PWA live status pill (operational/approvals-pending + active/beta capability counts)
- [x] CloudFront distribution for static assets (/v1/* bypass; honest latency note)

## Shipped in v5.19.0
- [x] Future-phase artifacts: Terraform scaffold (af-south-1, encrypted, hardened SG), feature flags (public read, safety unflaggable), error-budget math + docs/SRE.md

## Shipped in v5.18.1
- [x] Ops metrics (DORA-style: deploy frequency, change failure rate, MTTR; admin events + pure computation)
- [x] Static gate (every core module byte-compiles on PR); SECURITY.md; docs/DEVOPS.md lifecycle map

## Shipped in v5.18.0
- [x] Hybrid engine v2 (tiered per-intent gates; Electrical/Mechanical N4-N6 classes; admin-gated live calibration; latency + pii_redacted telemetry)

## Shipped in v5.17.1
- [x] CORE rate limiting (shared gate, daily quota, 429 message with remaining quota)
- [x] Open-source readiness (MIT LICENSE, CONTRIBUTING.md with good first issues, Hacktoberfest topics)

## Shipped in v5.17.0
- [x] Platform knowledge base (zero-dep TF-IDF over repo docs; grounded excerpts with sources; public /v1/knowledge/ask)
- [x] Engine output contracts (declared key sets per LLM engine; 502 fail-closed on drift)

## Shipped in v5.16.0
- [x] Hybrid AI front door (regex guardrails always-on zero-dep; lazy sklearn ML; confidence fallback; kill-switch; intents wired to real tools)

## Shipped in v5.15.0
- [x] Companion memory layer (per-user, append-only, scrubbed, capped; closes the 'memory systems' gap)
- [x] Feedback loop capture (rated outcomes per engine target, admin aggregates; the future learning loop consumes this)

## Shipped in v5.14.0
- [x] Executable verification harness (VerificationSpec: fixed cases + must-fail negatives, isolated per-case runs; honest success_unverified label)

## Shipped in v5.13.0
- [x] Full free-geocoding family (Photon/FR-BAN/Zippopotam/UK-Postcodes/OpenPLZ/3geonames/ip-api + Nominatim->Photon fallback chain; ip-api terms warning permanent)

## Shipped in v5.12.0
- [x] Free geocoding layer (Nominatim - fixed host, shared rate gate, PII scrub, OSM attribution)
- [x] Tool router (deterministic WHEN-to-use logic: geocode + literature signals, /detect + /auto)

## Shipped in v5.11.0
- [x] Jarvis companion avatar (procedural primitives - deliberately not AI-modelled; idle/happy/alert/speaking; gate-reactive)
- [x] Zero-key TTS fallback (browser speechSynthesis when XI endpoint unavailable)

## Shipped in v5.10.0
- [x] Sovereign research grounding layer (OpenAlex/Crossref/PubMed/arXiv adapters - keyless, SSRF-immune by fixed endpoints, per-source failure isolation)

## Shipped in v5.31.0
- [x] Migration 004 (persistent dead man's switch + DB heartbeat trigger); honest ops-channel legacy alerts

## Shipped in v5.30.0
- [x] Data portability endpoint (POPIA/GDPR access-request export)
- [x] Digital legacy guard (dead man's switch -> 30% gate, never autonomous)

## Shipped in v5.29.0
- [x] Hume EVI ingestion hooks (HMAC-verified webhooks, distress intervention -> crisis line + mentor alert; client subscription remains)
- [x] Daily context-sync cron workflow (fixed action key, real module runner, daily cadence)

## Shipped in v5.28.1
- [x] Drift alerts (Slack/Discord webhooks; throttled 1/marker/day; delivery failures never break the audit)

## Shipped in v5.28.0
- [x] Context sync auditor (GitHub commits + coverage ledger reconciliation; fixed host; fail-closed token; admin /v1/sync/audit)

## Shipped in v5.27.0
- [x] African languages phrasebook (21 phrases x 10 languages, pronunciation, speech playback, honest no-translator design)
- [x] Load shedding preparedness guide (8-stage reference, persistent checklist, wattage guide, backup options, manual slot countdown; mock 'real-time' claims rejected)

## Shipped in v5.26.0
- [x] Migration 003 (skill tables: FORCE RLS, correct GUC, 3-letter codes, FK; ORM on shared Base); accurate CHANGELOG.md; de-dup governance note

## Shipped in v5.25.1
- [x] Certificate authority (100% live-readiness gate; env salt fail-closed; public verification endpoint; JWT JS client)

## Shipped in v5.25.0
- [x] Skill engine (TVET trade gap analysis + experience roadmaps; heuristic structured-submission checks honestly labeled; credential hashes; versioned trade registry)

## Shipped in v5.24.1
- [x] ApiResponse typed Pydantic model (Generic[T], ISO-8601, honest cached flag); registry.query() unified async dispatch front

## Shipped in v5.24.0
- [x] Centralized free-provider registry (8 providers; uniform envelope; typed ProviderError kinds; concurrent health checks; estimated savings counter)

## Shipped in v5.23.0
- [x] Free knowledge scatter-gather (Wikipedia/Open-Meteo/World Bank/OpenAlex; circuit breakers + token buckets; provenance hashing; no fabricated fallbacks)

## Shipped in v5.22.0
- [x] 20-query golden evaluation set (CI floor 85%; admin /v1/hybrid/eval; civil class added; SQL-injection guardrail)
- [x] Cost telemetry (real call counting, estimated spend vs budget, 80% SMS alarm throttled daily)
- [x] Institutional readiness pack (docs/INSTITUTIONAL_READINESS.md)

## Shipped in v5.21.1
- [x] Full-article lessons: served-version verifier, HTML-200 detector, empty-envelope flag, spl_version never trusted, assert_history_survives, per-source body retention (SNAPSHOT_FULL_BODY_SOURCES)

## Shipped in v5.21.0
- [x] Keyless health data layer (DailyMed/RxNorm/ClinicalTrials/PubChem/openFDA; RxNorm lesson encoded; medical disclaimer on all)
- [x] Snapshot store (append-only (id,version,sha256) - the review's rewrite-proof architecture, replay-tested)

## Shipped in v5.20.0
- [x] Pilot SQLite WAL mode ($0 pilot DB; migration scaffold to pgloader/RDS)
- [x] Automated freeze gate helper (freeze_required) + corrected CI semantics in SRE.md
- [x] PWA live status pill (operational/approvals-pending + active/beta capability counts)
- [x] CloudFront distribution for static assets (/v1/* bypass; honest latency note)

## Shipped in v5.19.0
- [x] Future-phase artifacts: Terraform scaffold (af-south-1, encrypted, hardened SG), feature flags (public read, safety unflaggable), error-budget math + docs/SRE.md

## Shipped in v5.18.1
- [x] Ops metrics (DORA-style: deploy frequency, change failure rate, MTTR; admin events + pure computation)
- [x] Static gate (every core module byte-compiles on PR); SECURITY.md; docs/DEVOPS.md lifecycle map

## Shipped in v5.18.0
- [x] Hybrid engine v2 (tiered per-intent gates; Electrical/Mechanical N4-N6 classes; admin-gated live calibration; latency + pii_redacted telemetry)

## Shipped in v5.17.1
- [x] CORE rate limiting (shared gate, daily quota, 429 message with remaining quota)
- [x] Open-source readiness (MIT LICENSE, CONTRIBUTING.md with good first issues, Hacktoberfest topics)

## Shipped in v5.17.0
- [x] Platform knowledge base (zero-dep TF-IDF over repo docs; grounded excerpts with sources; public /v1/knowledge/ask)
- [x] Engine output contracts (declared key sets per LLM engine; 502 fail-closed on drift)

## Shipped in v5.16.0
- [x] Hybrid AI front door (regex guardrails always-on zero-dep; lazy sklearn ML; confidence fallback; kill-switch; intents wired to real tools)

## Shipped in v5.15.0
- [x] Companion memory layer (per-user, append-only, scrubbed, capped; closes the 'memory systems' gap)
- [x] Feedback loop capture (rated outcomes per engine target, admin aggregates; the future learning loop consumes this)

## Shipped in v5.14.0
- [x] Executable verification harness (VerificationSpec: fixed cases + must-fail negatives, isolated per-case runs; honest success_unverified label)

## Shipped in v5.13.0
- [x] Full free-geocoding family (Photon/FR-BAN/Zippopotam/UK-Postcodes/OpenPLZ/3geonames/ip-api + Nominatim->Photon fallback chain; ip-api terms warning permanent)

## Shipped in v5.12.0
- [x] Free geocoding layer (Nominatim - fixed host, shared rate gate, PII scrub, OSM attribution)
- [x] Tool router (deterministic WHEN-to-use logic: geocode + literature signals, /detect + /auto)

## Shipped in v5.11.0
- [x] Jarvis companion avatar (procedural primitives - deliberately not AI-modelled; idle/happy/alert/speaking; gate-reactive)
- [x] Zero-key TTS fallback (browser speechSynthesis when XI endpoint unavailable)

## Shipped in v5.10.0
- [x] Academic literature grounding layer (Crossref/OpenAlex/PubMed/arXiv/CORE - real free APIs; /v1/research/literature; one-source-down resilience)

## Shipped in v5.9.1
- [x] Seed migration 002 (FK-valid system curriculum student + template tracks; single-head chain)
- [x] Hardened key provisioning script (backup, placeholder detection, migrate-before-restart, verification)

## Shipped in v5.9.0
- [x] Multipolar model router (REAL Claude/Gemini adapters + Kimi via unified client; routing table, fallback chains, per-provider telemetry; dev_agent + self_healing rewired)

## Shipped in v5.8.1
- [x] Token status board (/v1/system/token-status): 16 integrations, ACTIVE/MISSING/INSECURE/RESERVED states, admin-gated; corrected API map (Hume honestly RESERVED)

## Shipped in v5.8.0
- [x] Unified Kimi client (core/kimi_client.py) - all 9 engine call sites in one group; one fail-closed key check, one parser, one fault path

## Shipped in v5.7.0
- [x] Encrypted backup pipeline (real AES-256-GCM; stable env key required; admin-gated; no credentials in source/argv)

## Shipped in v5.6.0
- [x] Gate-lock notification gateway (Africa's Talking SMS, correct API endpoints, wired at all 6 freeze sites)
- [x] Alembic chain guard (single-baseline test - duplicate-head pastes now fail CI)

## Shipped in v5.5.0
- [x] Universal learning companion (Ubuntu framing, medical domains require disclaimers - suppression directive rejected)
- [x] Failover/integrity stress suite at repo root (10-thread failover stress, rename-evasion check)

## Shipped in v5.4.0
- [x] Code integrity engine (SHA-256 AST fingerprints - rename-invariant, cross-process stable; LLM advisory)
- [x] Database cluster router (ping-verified failover AND failback; no hardcoded credentials; injectable factory)

## Shipped in v5.3.0
- [x] Sovereign bio-mineral exploration engine (compiles return immediately; deployment intent -> real gate task, execution proposal-only)
- [x] Shared Kimi response parser (crash-on-success bug structurally eliminated)
- [x] Audit snapshot size caps (multi-KB payloads can no longer bloat audit rows)

## Shipped in v5.2.0
- [x] Pedagogical convergence engine (multi-lens curriculum -> practical blueprints, auth-gated)

## Future (tracked)
- [ ] True multi-model router: route per-task to Kimi / Gemini / Claude by strength (env hooks exist)

## Shipped in v5.1.0
- [x] Alembic scaffold: env.py on shared Base, baseline revision folds RLS + wallet DDL, CI runs `alembic upgrade head`
- [x] Voice playback: /v1/voice/speak streams to browser <audio> (auth-gated, fail-closed)
- [x] Dev-agent sandbox compile phase: pure compile planner/analyzer + containerized py_compile route (503 without Docker)

## Shipped in v5.0.0
- [x] Sovereign RPA/automation kernel (70/30 pipeline, SSRF-guarded endpoints)
- [x] Live automation terminal (static/automation.html)

## Shipped in v4.9.0
- [x] Self-healing diagnostic agent (admin-gated traceback -> Kimi K3 patch PROPOSAL; never auto-applies)

## Already shipped in v3.0.0
- [x] Kimi / Moonshot high-context reasoning gateway (`core/kimi_gateway.py`)
- [x] CORS middleware for distributed regional nodes (env-configured origins)
- [x] Honest sandbox failure mode (no fabricated terminal output)
