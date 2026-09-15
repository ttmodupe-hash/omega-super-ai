# Luqi-AI Deployment Runbook (v5.27.1)
Ordered, copy-pasteable. Every step references a tested artifact. Go/No-Go gates marked.

## PHASE 0 - Pre-flight (your machine)
1. Rotate any secret ever pasted in any chat (consoles: Moonshot, Google, Anthropic).
2. This tree: add + commit + push (see commands below). CI renders the full atomic
   verdict: 113 tests across 6 suites + Alembic (0001/002/003) + wallet integration
   vs Postgres. **GATE 0: CI green.**
3. Generate two secrets: `openssl rand -hex 32` (x2) - admin + JWT.

## PHASE 0.5 - Choose your host
- AWS path (console + Session Manager): continue below.
- Railway path (fully browser-only): see RAILWAY_DEPLOYMENT.md - no terminal,
  no nginx, no certbot. Same repo, same push.

## PHASE 1 - Provision (~30 min)
4. `cd deploy/terraform`
5. `terraform init && terraform validate`   # scaffold - fix what it flags
6. `TF_VAR_key_name=your-keypair terraform apply`   # start with create_rds=false (SQLite WAL pilot)
7. Note `core_public_ip` from output.

## PHASE 2 - Bootstrap (SSH as ubuntu)
8. `git clone <repo> /opt/luqi-ai && cd /opt/luqi-ai`
9. `sudo pip install -r requirements.txt`  (or venv per DEPLOYMENT.md)
10. `sudo cp deploy/luqi-core.service /etc/systemd/system/ && systemctl daemon-reload`

## PHASE 3 - Secrets (ON THE SERVER ONLY - never in chat)
11. `cp deploy/.env.active_now.template /opt/luqi-ai/.env && chmod 600 .env`
12. Fill Tier 1: KIMI_API_KEY (Moonshot), LUQI_ADMIN_SECRET + JWT_SECRET_SIGNING_KEY
    (from step 3). Tier 2/3 stay commented until those features go live.
    Optional later: CERT_SIGNING_KEY (base64 of 32 bytes) BEFORE issuing certificates.

## PHASE 4 - Database + boot
13. `alembic upgrade head`          # 0001 schema+RLS, 002 seed, 003 skill tables - BEFORE first boot
14. SQLite pilot: default DATABASE_URL is postgres; for the $0 pilot set
    DATABASE_URL=sqlite:////var/backups/luqi-ai/pilot.db (WAL pragmas applied automatically).
    Scale later: tools/migrate_sqlite_to_pg.py prints exact pgloader commands.
15. `systemctl enable --now luqi-core`

## PHASE 5 - Verify
16. `./deploy/VERIFY_STAGING.sh`    # 6 steps; Docker/Redis warn-and-degrade by design
17. `pytest -v test_smoke_backends.py`   # 65 checks, every route's correct posture
18. `curl -H "X-Luqi-Admin-Auth: <secret>" localhost:8000/v1/system/token-status`
    **GATE 1: kimi_k3_brain ACTIVE; admin/jwt INSECURE only if you skipped step 12.**

## PHASE 6 - Edge
19. DNS A record: your domain -> core_public_ip
20. `sudo certbot --nginx -d your.domain`   # deploy/nginx.conf already references the cert path
21. `sudo nginx -t && systemctl reload nginx`

## PHASE 7 - Go/No-Go for STUDENTS (close all before real accounts)
- [ ] RLS proof: cross-country query returns 0 rows (validation protocol Stage 01)
- [ ] Restore drill: one .enc backup decrypted + pg_restored into scratch DB
- [ ] POPIA Information Officer registered
- [ ] Golden set: `curl -X POST -H "X-Luqi-Admin-Auth: <key>" localhost:8000/v1/hybrid/eval` -> 20/20
- [ ] 7 days uptime; freeze_required() stayed false

## PHASE 8 - First week ops
- Watch: /v1/ops/metrics (deploy freq, MTTR), /v1/cost/telemetry (80% SMS alarm), token board.
- Gate latency < 15 min (SMS alerts via notifications.py).
- Token spend vs subsidy model ($0.01/student session).

Rollback: `systemctl stop luqi-core; git checkout <prev-tag>; alembic downgrade -1; restart`.
