# OMEGA-LUQI Pre-Launch System Validation Protocol

Complete every stage before opening the portal to students.

## Stage 01 — Environment Integration
- [ ] `.env` permissions locked down: `chmod 600 .env`
- [ ] `LUQI_ADMIN_SECRET` is randomized (`openssl rand -hex 32`) and appears nowhere in git history
- [ ] Gate audit trail verified: release a test task, confirm a `system_audit_logs` row exists with hashed operator identity and origin IP
- [ ] Database geo-sovereignty rules active
  - **IMPLEMENTED (v4.4.0):** `core/security_rls.sql` - FORCE RLS policies bound to `app.current_user_country`, fail-closed (unset context sees zero rows). Remaining: execute the SQL on the production cluster as `luqi_app_user` role and verify a cross-country query returns zero rows.

## Stage 02 — Hardware Simulation Agent
- [ ] Execute a network-lab shell command via the WebSocket terminal and receive real output
- [ ] Verify container memory ceiling: `docker stats` shows the lab container capped at 512MB
- [ ] Black-box injection test: send `rm -rf /` through the terminal — expect `Execution Denied`
- [ ] Ceiling test: with `MAX_SANDBOX_CONTAINERS=2`, the third spawn request returns the ceiling error (enforced in `docker_sandbox.py` since v3.1.0)

## Stage 03 — Cross-Stream Resiliency
- [ ] `POST /v1/agent/kimi-reason` returns 200 under context stress (requires `KIMI_API_KEY` set; returns 500 when unset — verified by test suite)
- [ ] ElevenLabs voice streams hold without drops on simulated 3G throttling
- [ ] `pytest -v test_orchestrator.py` — all 5 tests green
- [ ] Mock high-risk payment locks instantly at `PENDING_HUMAN_APPROVAL`; unauthorized override returns 403

- [ ] Wallet ledger: `core/wallet_ledger.sql` executed; duplicate reference returns 409/503 without double credit; gate stays locked when DB is down

- [ ] Auth hardening: 6 rapid logins from one IP return 429; logout revokes the token immediately; boot with default secrets under LUQI_ENV=production fails
- [ ] Wallet integration (CI): `test_wallet_integration.py` green against the Postgres service

- [ ] Regional routing: ZAF/KEN/NGA tokens route to PayFast/M-Pesa/Flutterwave respectively; production without live keys returns 503
- [ ] Webhooks: correct HMAC signature accepted; tampered body rejected 403; missing signature 401
- [ ] Free-tier caps: 6th autonomous session in a day returns 429; payments and premium tiers unaffected

- [ ] Mesh: host + student complete a WebRTC handshake via the relay; fully-offline manual transport exchanges SDP via copy/paste
- [ ] Reaper: idle sandbox destroyed after timeout (verify in `docker ps` before/after)

- [ ] Self-heal endpoint: anonymous request rejected; without KIMI_API_KEY returns 500 (fail-closed); with key returns a JSON patch proposal - and ONLY a proposal

- [ ] Automation: unauthenticated trigger rejected; SSRF guard blocks loopback/link-local/private targets; sensitive steps freeze at the gate and appear in the queue

- [ ] Pedagogy: anonymous optimize request rejected; stats endpoint live; successful parse of choices list verified

- [ ] Sovereign: anonymous compile rejected; medical/research disclaimer present in UI and docs; deploy intent appears in gate queue

- [ ] Integrity: anonymous submission rejected; fingerprint stable across restarts (SHA-256, not salted hash); similarity labeled advisory
- [ ] Replication: simulated primary failure fails over to replica and fails back on recovery (unit test)

- [ ] Universal learning: anonymous request rejected; medical-domain outputs flagged disclaimer-required; suppression directive absent from codebase (guard test)
- [ ] Failover stress: 50 concurrent router calls during primary crash - all receive a working engine

- [ ] Notifications: freezing a payment task logs/sends an admin alert; alert failure never blocks the freeze
- [ ] Migrations: `alembic heads` shows exactly one head

- [ ] Backups: anonymous request rejected; without BACKUP_ENCRYPTION_KEY the route fails closed (no unrestorable archives); roundtrip decrypt verified
- [ ] Confirm no credentials appear in source, argv, or git history

- [ ] Token board: anonymous query rejected; default secrets report INSECURE (not ACTIVE); no secret values in response

- [ ] Router: no-key environment fails closed 500; provider outage falls through the chain (unit test); 'Simulated' appears nowhere in the module

- [ ] Research layer: anonymous search rejected; normalization fields present; PubMed two-step flow verified; source failure isolation confirmed

- [ ] Literature: endpoint public read-only; one failed source leaves others intact; parsers verified offline

- [ ] Tool router: location query -> geocode; research query -> literature; combined query fires both; no-signal query routes to LLM engines

- [ ] Verification: compile without a spec reports success_unverified; negative case that wrongly passes is flagged "BUT IT PASSED"

- [ ] Memory/feedback: recall scoped to the requesting user; feedback rating clamped 1-5; summary admin-only

- [ ] Hybrid: emergency/injection rules fire deterministically; OOD input gets Phase 3 fallback (never a guessed intent); engine imports and answers without sklearn

- [ ] Knowledge/contract: doc questions return sourced excerpts; engine missing required keys -> 502

- [ ] Health data: every response disclaimered; RxNorm always paired with historystatus; snapshot store distinguishes rewritten from untouched records

## Sign-off
- [ ] All Stage 01-03 boxes checked (or explicitly deferred with owner named)
- [ ] Rollback plan: previous git tag + systemd unit ready
