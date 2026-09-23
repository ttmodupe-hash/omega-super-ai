# OMEGA-LUQI AI Unified Engine v5.9.0

Merged repository: OMEGA AI Build baseline + Project Bug Fixes stream
(multi-agent orchestration, 30% Human-in-the-Loop gate, Docker lab execution,
Mandela/Winnie voice synthesis, WebAssembly PWA, payment router slots).

    omega-luqi-ai-engine/
    ├── .github/workflows/omega_luqi_sync.yml   # CI: tests + lab image build + deploy gate
    ├── static/                  # PWA client (Three.js 3D/4D viewport, offline SW, manifest)
    │   └── icons/
    ├── core/                    # Backend package (import-safe: fastapi+pydantic only)
    │   ├── main.py              # FastAPI hub + human gate + CORS + static serving
│   ├── kimi_gateway.py      # Moonshot high-context reasoning endpoint
│   ├── kimi_plugins.py      # Kimi $web_search deep-research plugin router
│   ├── prompt_support.py    # Student prompt optimization (Ubuntu philosophy wrapper)
│   ├── action_engine.py     # Sovereign tender/business scan (Kimi $web_search)
│   ├── dev_agent.py         # Ground-up software generation matrix (Docker compile = Phase 2)
│   ├── consumer_shield.py   # Ombudsman complaint files (CPA 68/2008 routing, works offline)
│   ├── tax_matrix.py        # SARS-baseline tax engine, filings locked at the 30% gate
│   ├── state_store.py       # Task ledger: memory (default) or Redis (multi-worker)
│   ├── main_types.py        # Shared orchestrator types (TaskStatus, LuqiState)
    │   ├── term_websocket.py    # Real-time sandbox terminal channel
    │   ├── docker_sandbox.py    # Multi-track container allocator
    │   ├── voice_service.py     # Madiba/Nomzamo audio synthesis interface
    │   └── models.py            # SQLAlchemy v2 schemas (POPIA/DPA-aligned)
    ├── deploy/                  # systemd unit, production env template, ops manual
│   └── terraform/           # af-south-1 IaC scaffold (EC2 + SG + encrypted backups)
    ├── docs/                    # Pitch deck, script, grant proposal, API directory, launch checklist
    ├── lab/Dockerfile           # Student lab sandbox image (luqi-lab-base)
    ├── test_orchestrator.py     # 12-test safety gate suite (all passing)
├── test_security_gates.py   # 100-thread tax-gate stress suite (all passing)
├── test_auth_hardening.py   # Production guards + rate limiter + revocation (all passing)
├── test_failover.py         # Failover stress + integrity scenarios (CI)
├── test_backup_and_gate.py # Backup cipher + edge proxy + PII guards (CI)
├── test_wallet_integration.py  # Full money path vs Postgres (CI)
    ├── requirements.txt
    └── .env.example

## Run

    pip install -r requirements.txt
    uvicorn core.main:app --host 0.0.0.0 --port 8000 --reload

PWA: http://localhost:8000/   API docs: http://localhost:8000/docs

## Open source
MIT-licensed (see LICENSE). Hacktoberfest-ready: contributing guide and good
first issues in CONTRIBUTING.md. Suggested repo topics: `hacktoberfest`,
`education`, `fastapi`, `ai`, `africa`, `pwa`.

## Test

    pytest -v test_orchestrator.py test_security_gates.py   # auth tests need: pip install pyjwt

## Scale rule
Default state backend is in-memory (single worker). For multi-worker deployments:
    export STATE_BACKEND=redis
    export REDIS_URL=redis://localhost:6379/0
    uvicorn core.main:app --workers 4
All workers then share one task ledger and the 30% gate stays consistent.
