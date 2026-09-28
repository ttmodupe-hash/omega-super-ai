┌─────────────────────────┐
                       │   GitHub Repository     │
                       │ ttmodupe-hash/omega-... │
                       └────────────┬────────────┘
                                    │ (Native Auto-Deploy on push)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        Railway Project Canvas                          │
│                                                                        │
│   ┌─────────────────────────┐           ┌──────────────────────────┐   │
│   │   PostgreSQL Service    │           │    FastAPI App Service   │   │
│   │  (Plugin: DB_URL)       ├──────────►│  (Builds via Nixpacks)   │   │
│   └─────────────────────────┘           └─────────────┬────────────┘   │
│                                                       │                │
└───────────────────────────────────────────────────────┼────────────────┘
                                                        │
                                                        ▼
                                       https://<project>.up.railway.app
Deployment Checklist1. Project CreationLog into railway.app using GitHub authentication.Click New Project $\rightarrow$ Deploy from GitHub repo $\rightarrow$ Select ttmodupe-hash/omega-super-ai.Railway automatically reads railway.toml (utilizing the Nixpacks builder, uvicorn entrypoint, and /v1/health health check).2. Database ProvisioningCRITICAL: Do NOT select MySQL. The schema, wallet ledger, migrations, and RLS policies require PostgreSQL. (Note: Since v5.35.10, non-Postgres configurations will boot in a degraded/DB-less state rather than crashing, but database features will remain disabled.)In the canvas, click New $\rightarrow$ Database $\rightarrow$ Add PostgreSQL.Open the Postgres service settings, go to the Connect tab, and copy DATABASE_URL (references ${{Postgres.DATABASE_URL}}).3. Environment Variables StrategyIn the App Service $\rightarrow$ Variables tab, set the following required keys:VariableDescription & GuidanceDATABASE_URLPostreSQL reference (postgresql+psycopg2://...)LUQI_ADMIN_SECRET32-byte secure random stringJWT_SECRET_SIGNING_KEYFresh secure random signing keyKIMI_API_KEYActive Moonshot API keyMulti-Node / Scaling Configuration:STATE_BACKEND=redisREDIS_URL (Required prior to setting numReplicas > 1 so the 30% gate ledger is shared)4. Automatic Migrations Executionstart.sh executes alembic upgrade head automatically on every deployment boot before starting the application listener.Resilience Mechanism: Migrations execute against valid PostgreSQL URLs only. Invalid database configurations fall back gracefully to a degraded state while logging warning outputs. Look for "[start] schema at head" in the deploy logs.5. Verification & Health Probes               [ Deployment Verification Sequence ]

   1. Generate Domain  ──► Settings -> Domains -> Generate Domain
   2. Health Status    ──► GET https://<domain>/v1/health -> {"status":"operational"}
   3. System Board     ──► GET https://<domain>/v1/system/token-status
   4. OpenAPI Docs     ──► GET https://<domain>/docs
6. Custom Domain & DNSUnder Settings $\rightarrow$ Domains, select Add Custom Domain.Add a CNAME record in your DNS provider pointing to Railway's target host. TLS termination is managed automatically by Railway.Update PUBLIC_BASE_URL in your environment variables to reflect the new custom domain.7. Automated Production Smoke VerificationTo verify live releases post-push:Navigate to GitHub Actions $\rightarrow$ Production Smoke Verification $\rightarrow$ Run workflow.Enter your Railway endpoint URL (https://<domain>.up.railway.app).The workflow validates API routes read-only, confirms live v1/health commit hashes against the source repository, and authenticates using the PROD_ADMIN_SECRET secret.
