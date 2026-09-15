# Railway Deployment (browser-only, no terminal)

Prerequisite: the repo is pushed to GitHub (see PUSH_COMMANDS.sh). Railway
deploys FROM GitHub - it cannot receive files any other way.

## Step 1 - Create the project (5 min, all browser)
1. https://railway.app -> Login with GitHub.
2. **New Project -> Deploy from GitHub repo** -> select `ttmodupe-hash/omega-super-ai`.
   Railway auto-detects `railway.toml` (Nixpacks builder, uvicorn start, /v1/health check).

## Step 2 - Attach Postgres (required)
Railway filesystems are EPHEMERAL - a SQLite file would vanish on every
redeploy. The engine handles this natively: migrations + wallet + RLS all run
on Postgres.
1. In the project canvas: **New -> Database -> Add PostgreSQL**.
2. Open the Postgres service -> **Connect** tab -> copy the provided `DATABASE_URL`
   (it references `${{Postgres.DATABASE_URL}}` - Railway resolves it).
3. Add it to the app service's Variables (see Step 3).

## Step 3 - Required variables (app service -> Variables)
| Variable | Source |
|---|---|
| `DATABASE_URL` | from the Postgres plugin reference above (postgresql+psycopg2://...) |
| `LUQI_ADMIN_SECRET` | `openssl rand -hex 32` equivalent - generate anywhere; never paste real values into chats |
| `JWT_SECRET_SIGNING_KEY` | fresh random, same discipline |
| `KIMI_API_KEY` | your Moonshot key (the one already active) |
| Optional: `XI_API_KEY`, `AFRICAS_TALKING_API_KEY` + `ADMIN_PHONE_NUMBER`, `HUME_WEBHOOK_SECRET` | per feature |
| Optional multi-node: `STATE_BACKEND=redis` + `REDIS_URL` (Railway Redis plugin) | enables --workers > 1 |

Tier 2/3 variables from deploy/.env.active_now.template - uncomment as features go live.

## Step 4 - Migrations: AUTOMATIC on deploy
start.sh (invoked by railway.toml) runs `alembic upgrade head` on every boot
before serving - idempotent, no manual step. With DATABASE_URL set and a
migration failure, the deploy FAILS LOUDLY (by design). Without DATABASE_URL
the engine boots DB-less and migrations are skipped with a log line.

## Step 5 - Verify
1. Service -> **Settings -> Generate Domain** (gives https://<project>.up.railway.app).
2. Browse: `https://<domain>/v1/health` -> `{"status":"operational"}`.
3. `https://<domain>/v1/system/token-status` with your admin header -> board states.
4. `https://<domain>/docs` -> full OpenAPI surface.
5. Railway -> Deployments: the healthcheck must be green (railway.toml path /v1/health).

## Step 6 - Custom domain + PWA
1. **Settings -> Domains -> Add Custom Domain** -> point DNS (CNAME to Railway's target).
2. Railway terminates TLS automatically - no certbot, no nginx.
3. Update `PUBLIC_BASE_URL` (certificate URLs) to the custom domain.

## What Railway replaces from the AWS path
- nginx/TLS/certbot -> Railway proxy + managed domains.
- systemd -> Railway's restart policy (railway.toml).
- Terraform EC2 -> the Railway project itself.
- VERIFY_STAGING.sh steps 2 (docker socket) remains N/A - sandbox terminals will
  report degraded until a Docker-capable node exists; the API is fully functional.

## Scaling note
`numReplicas = 1` until STATE_BACKEND=redis + REDIS_URL are set (shared task ledger,
see docs/SRE.md). Then raise replicas in railway.toml / the service settings.

## Verifying a live deployment
Every push to main auto-deploys via Railway's native GitHub integration - no
broker workflow required. To verify a live deployment, run the
**Production Smoke Verification** workflow (Actions -> workflow_dispatch ->
enter your https://...up.railway.app URL). It runs the full route matrix
against production, read-only.

## Production smoke: stale-deploy detection + admin auth
The verifier compares the live /v1/health version against the pushed commit's
version - a mismatch means Railway serves an old build (fails the run).
Admin probes authenticate via the PROD_ADMIN_SECRET repository secret
(Settings -> Secrets and variables -> Actions), never a workflow input.
