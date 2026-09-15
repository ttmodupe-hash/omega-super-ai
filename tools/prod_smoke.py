"""Run the backend smoke matrix against a LIVE deployment (CI: prod_smoke.yml).

Usage: PROD_URL=https://your-app.up.railway.app [PROD_ADMIN_SECRET=...] python tools/prod_smoke.py
Fails (exit 1) if any check fails. Read-only against production.

v5.31.4 advances:
  - stale-deploy detection: the live /v1/health version must equal the version
    in THIS checkout (the commit CI checked out). A mismatch means Railway is
    serving an older build - the most expensive production failure there is.
  - admin probes authenticate with PROD_ADMIN_SECRET (GitHub Secrets in CI),
    never a workflow input.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROD_URL = os.getenv("PROD_URL", "").rstrip("/")
if not PROD_URL:
    print("PROD_URL env var required (https://...up.railway.app)", file=sys.stderr)
    sys.exit(2)

from fastapi.testclient import TestClient  # noqa: E402
from core.main import app  # noqa: E402
import test_smoke_backends as sm  # noqa: E402

sm.client = TestClient(app, base_url=PROD_URL)
ADMIN = {"X-Luqi-Admin-Auth": os.getenv("PROD_ADMIN_SECRET", "SuperSecretAdminKey123")}

fails = 0

for path, params, expected in sm.PUBLIC_GETS:
    code = sm.client.get(path, params=params).status_code
    if code not in expected:
        fails += 1
        print("FAIL PUBLIC", path, code)
for path in sm.ADMIN_GETS:
    anon = sm.client.get(path).status_code
    authed = sm.client.get(path, headers=ADMIN).status_code
    if not (anon in (401, 403, 422) and authed == 200):
        fails += 1
        print("FAIL ADMIN", path, anon, authed)
for path in sm.AUTH_GETS:
    params = {"trade": "electrician"} if path == "/v1/skills/gap-analysis" else {}
    if sm.client.get(path, params=params).status_code not in (401, 403, 422):
        fails += 1
        print("FAIL AUTH", path)

# ---- stale-deploy detection: live version must equal this checkout's version ----
local_src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "core", "main.py")).read()
local_version = re.search(r'version="(5\.\d+\.\d+)"', local_src).group(1)
live = sm.client.get("/v1/health").json()
live_version = live.get("version", "?")
if live_version != local_version:
    fails += 1
    print(f"FAIL VERSION: live deployment is {live_version} but this commit is {local_version} "
          f"- stale build (redeploy or check Railway build logs)")
else:
    print(f"VERSION MATCH: live {live_version} == commit {local_version}")

total = len(sm.PUBLIC_GETS) + len(sm.ADMIN_GETS) * 2 + len(sm.AUTH_GETS) + 1
print(f"production smoke: {total - fails}/{total} checks passed against {PROD_URL}")
sys.exit(1 if fails else 0)
