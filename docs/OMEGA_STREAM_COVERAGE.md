# Omega AI Build & Sync Stream - Coverage Ledger
Audit date: 2026-09-15. Question answered: "is everything from that stream in the repo?"

METHOD NOTE (updated 2026-09-15): the stream's ACTUAL source repository was
located and archived: ttmodupe-hash/omega-super-ai (v25.1.0 lineage, 351 files)
is preserved byte-for-byte at legacy/omega-super-ai-v25.1.0/. Capability mapping
against the engine lives in docs/OMEGA_SUPERAI_GAP_ANALYSIS.md. The de-dup protocol (CONTRIBUTING.md) exists precisely so the
stream's future output arrives as one-line ideas, making this ledger complete
by construction going forward.

## MERGED (idea -> where it lives)
| Stream item | Engine destination |
|---|---|
| Multi-agent blueprint, HITL gate, sandbox, terminal, PWA, mesh, voice matrix | v1.x-v2.x core: core/main.py, term_websocket.py, docker_sandbox.py, static/* |
| Payment stubs, RLS, webhooks, wallet, caps | v4.x: payment_hub/routers, security_rls.sql, wallet_service, resource_caps |
| Auth + JWT fail-closed | v4.3: core/auth.py |
| Kimi engines (9x), unified client | v3.x-v5.8: kimi_gateway/plugins/action_engine/dev_agent/pedagogy/sovereign/universal/integrity/self_healing + kimi_client.py |
| Multipolar router | v5.9: model_router.py (real Claude/Gemini adapters) |
| Token board, corrected API map | v5.8.1: token_status.py, docs map (Hume honestly RESERVED) |
| Notifications (Africa's Talking) | v5.6: notifications.py (endpoints corrected) |
| Backups AES-256-GCM | v5.7: db_backup.py |
| Hybrid AI front door + upgrades | v5.16-v5.18: hybrid_ai.py (tiered gates, 8 classes, golden-calibrated) |
| Golden set + money telemetry | v5.22: golden_set.py, cost_telemetry.py |
| Scatter-gather + circuit breakers | v5.23: free_knowledge.py |
| Provider registry | v5.24.x: api_registry.py (typed ApiResponse, dispatch front) |
| Skill engine + certificates | v5.25.x: skill_engine.py (gap analysis, validators, cert authority) |
| Pedagogy / sovereign / universal / medical | v5.2-v5.5 (disclaimers mandatory, suppression directives rejected) |
| DevOps/KPIs/IaC/SRE freeze flags | v5.18.1-v5.20: ops_metrics, terraform, feature_flags, SRE.md |
| Free APIs (academic 5, geocoding 8, health 5) | v5.10-v5.21: academic_sources, free_geo_apis, health_sources, snapshots |
| React pages (load shedding, languages) | v5.27.x: static/loadshedding.html + static/languages.html (honest ports; React mocks rejected) |
| Deployment manual + secrets provisioning | deploy/: runbook, VERIFY_STAGING.sh, inject_secrets.sh, MULTI_PROVIDER_SETUP.md |
| Subsidy model, readiness pack, grant/pitch docs | docs/ (Subsidy_Model, INSTITUTIONAL_READINESS, API_Integration_Map) |

## DELIBERATELY NOT TAKEN (with reason)
- Simulated responses of any kind ("Mock Sandbox Response", fake metrics, fabricated schedules/translations) - fail-closed policy.
- Second FastAPI instances / standalone microservices - everything folds into one engine.
- Hardcoded credentials, template salts, placeholder keys - env-only secrets.
- kimi_k3.py, auth_redis.py, sandbox_recycler.py, seed_data.py - never existed; features live under tested names.
- Suppression directives (medical "never warn"), "RFC 6598" citation, invented latency/percentage figures.
- Duplicate/older re-implementations of already-merged modules (multiple occurrences).
- React app itself - separate repo; content ported to PWA at higher standard.

## OPEN / UNRESOLVED from that stream (tracked, not merged)
- Hume EVI: ingestion hooks SHIPPED (v5.29.0, HMAC-verified, distress intervention wired to crisis line + mentor alert). The EVI client subscription (student->Hume sessions) remains the integration step.
- Voice persona estate engagement (Mandela/Winnie cadence): legal prerequisite, tracked in EULA + roadmap.
- "Drive Intelligent" integration: clarification requested, never answered - three interpretations documented (student storage / platform export / repo sync). Awaiting decision.
- Live market-feed for skill trade registry: documented future work (admin reload endpoint exists). No keyless job-platform API exists - polling without a real source would be fabrication.
- Digital legacy (dead man's switch): SHIPPED v5.30.0 at the 30% gate.
- Data portability (POPIA export): SHIPPED v5.30.0 (/v1/user/export).
- Enterprise accounts unification (students vs enterprises parent table): noted at wallet build; deferred until enterprise onboarding.

## VERIFICATION
Any future stream item can be checked against this ledger; CONTRIBUTING.md carries
the one-line-idea protocol that keeps this list complete by construction.
