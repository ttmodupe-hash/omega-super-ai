# Multi-Provider Setup Manual (v5.9.2) - CORRECTED

## 0. The golden rule for tokens
NEVER copy tokens from chat transcripts (including the Omega AI Build & Sync
chat). Anything that appeared in any conversation is treated as compromised.
Fetch FRESH tokens from the provider consoles; rotate any token that was ever
pasted into a chat. All app secrets live in /opt/luqi-ai/.env only.

## 1. GitHub Actions secrets (ONLY these two)
Settings -> Secrets and variables -> Actions:
  PROD_SERVER_IP       - public IPv4 of the production node
  PROD_SERVER_SSH_KEY  - private key for deploy sync
Do NOT add KIMI_API_KEY / GEMINI_API_KEY / CLAUDE_API_KEY as repo secrets:
the application reads provider keys from the server .env at runtime. Putting
them in CI expands exposure (any workflow run can read them) for zero benefit.

## 2. Server-side key provisioning (use the hardened script)
    ./deploy/inject_secrets.sh /opt/luqi-ai/.env luqi-core.service
It backs up .env, replaces the multipolar keys, flags leftover placeholders,
runs `alembic upgrade head` BEFORE restarting, then verifies health + board.

Fresh keys come from:
  KIMI_API_KEY       -> platform.moonshot.ai console
  GEMINI_API_KEY     -> Google AI Studio (or Vertex AI, africa-south1 for
                        on-continent data residency)
  CLAUDE_API_KEY     -> console.anthropic.com
JWT secret (generate, do not invent):
    openssl rand -hex 32

## 3. What the corrected step 4 actually is
The pasted manual ran:  docker compose exec luqi-core-app python3 core/seed_data.py
That file DOES NOT EXIST. Seeding is migration 002 and already ran in step 2's
`alembic upgrade head`. Verify the seed instead:
    psql $DATABASE_URL -c "SELECT lab_track FROM lab_progress WHERE saved_state_metadata->>'is_template' = 'true';"
(Expect: indigenous_botanic_synthesis, mechatronics_mineral_refinement.)

## 4. Verify
    curl http://localhost:8000/v1/health
    curl -H "X-Luqi-Admin-Auth: <key>" http://localhost:8000/v1/system/token-status
All three providers show ACTIVE; placeholder keys were flagged in step 2 if left.
