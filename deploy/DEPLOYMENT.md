# Luqi-AI Production System Administration Manual

## 1. Environment Configuration
Copy `deploy/.env.production.example` to `/opt/omega-luqi-ai-engine/.env` and fill in real values.
Generate a strong admin gate key: `openssl rand -hex 32`
Verify the `DATABASE_URL` has a real hostname, port, and database name — a malformed URL crashes startup.

## 2. Service User Setup (run once)
    useradd -r -s /usr/sbin/nologin luqi
    usermod -aG docker luqi
    mkdir -p /opt/omega-luqi-ai-engine && chown -R luqi:luqi /opt/omega-luqi-ai-engine

## 3. Install the systemd service
    cp deploy/luqi-core.service /etc/systemd/system/luqi-core.service
    systemctl daemon-reload
    systemctl enable luqi-core.service
    systemctl start luqi-core.service

## 4. Verify
    systemctl status luqi-core.service
    journalctl -u luqi-core.service -f                 # live logs
    curl http://localhost:8000/v1/health               # expect {"status":"operational"}

## 3c. Edge proxy (Nginx + TLS 1.3)
Config lives at deploy/nginx.conf. Install:
    sudo cp deploy/nginx.conf /etc/nginx/sites-available/luqi-ai.conf
    sudo ln -s /etc/nginx/sites-available/luqi-ai.conf /etc/nginx/sites-enabled/
    sudo nginx -t && sudo systemctl reload nginx
Hardening included: HTTP/2, edge rate limits (2 r/s auth zone, 10 r/s API zone),
10MB body cap, OCSP stapling, websocket upgrade route with 1h keepalive,
buffering disabled on /v1/voice/ for immediate audio streaming.
CSP keeps 'unsafe-inline' for current dashboard pages - see comment in the config.

## 3d. Key provisioning
Minimal live set: deploy/.env.active_now.template (Tier 1 = 3 keys to go active).
Full set: .env.production.example. Script: ./deploy/inject_secrets.sh
See MULTI_PROVIDER_SETUP.md (console-fresh tokens only - never from chats)
and ./deploy/inject_secrets.sh.
    ./deploy/inject_secrets.sh [ENV_FILE] [SERVICE]
Backs up .env, replaces multipolar keys, migrates BEFORE restarting, then
verifies health + token board. Placeholder strings are detected and flagged.

## 4a. Staging verification
Run `./deploy/VERIFY_STAGING.sh` on a clean node before go-live.
Six steps: Python version -> .env perms -> Docker socket -> Redis (optional)
-> Alembic migrations -> health check -> full test gate. Every step either
verifies, degrades with a stated fallback, or fails loudly.

## 4b. Boot-time security guards
With LUQI_ENV=production the engine REFUSES TO START if:
  - LUQI_ADMIN_SECRET or JWT_SECRET_SIGNING_KEY is unset or a template default
  - PAYSTACK_SECRET_KEY is a test key (sk_test_)
This is a hard RuntimeError at startup - fix the secret or the service stays down.

## 4c. Database migrations (Alembic)
Fresh cluster:     alembic upgrade head
New schema change: alembic revision --autogenerate -m "describe_change", review, apply.
The baseline revision (0001_initial_schema) creates all tables plus the FORCE RLS
policies and wallet ledger DDL - create_all is no longer the production path.

## 5. Scaling rule (read before adding workers)
The orchestrator's task state (`STATE_DB`) lives in process memory. With `--workers 1`
this is safe. Before raising workers above 1, migrate state to Redis or Postgres —
otherwise the 30% Human-in-the-Loop gate can approve a task on one worker that
another worker never locked. That voids the ironclad property the test suite proves.

## 6. Security checklist for go-live
- [ ] LUQI_ADMIN_SECRET changed from any template value
- [ ] .env is NOT in git (check .gitignore)
- [ ] Database credentials are unique per environment
- [ ] Docker socket not exposed to any network interface
- [ ] Firewall: only 80/443 open; API behind reverse proxy with TLS
- [ ] `journalctl` retention configured (log disk fills are the #1 cause of outages)
