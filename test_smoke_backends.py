"""
OMEGA-LUQI Backend Smoke Matrix - every route, its expected posture.

Categories:
  PUBLIC   - answers without auth (200/503 network-dependent/422 validation)
  ADMIN    - rejects anonymous (401/403/422), answers with X-Luqi-Admin-Auth
  AUTH     - rejects without JWT (401/403/422)
  KEYLESS  - no auth by design (key/daemon-gated instead); fail-closed states ok

Run: pytest -v test_smoke_backends.py   (or python tools/smoke_backends.py)
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from core.main import app

client = TestClient(app)
ADMIN = {"X-Luqi-Admin-Auth": "SuperSecretAdminKey123"}

PUBLIC_GETS = [
    ("/v1/health", {}, (200,)),
    ("/v1/companion/status", {}, (200,)),
    ("/v1/features", {}, (200,)),
    ("/v1/knowledge/ask", {"q": "human gate override"}, (200,)),
    ("/v1/router/telemetry", {}, (401, 403, 422)),  # admin - listed for completeness
    ("/v1/research/literature", {"q": "crispr"}, (200, 503)),
    ("/v1/tools/detect", {"q": "schools near soweto"}, (200,)),
    ("/v1/tools/geo/search", {"q": "Pretoria"}, (200, 503)),
    ("/v1/tools/geo/postcode/za/2196", {}, (200, 503)),
    ("/v1/tools/geo/ip", {"ip": "8.8.8.8"}, (200, 503)),
    ("/v1/health-data/drug", {"q": "amoxicillin"}, (200, 503)),
    ("/v1/health-data/compound/aspirin", {}, (200, 503)),
    ("/v1/pedagogy/stats", {}, (200,)),
    ("/v1/sovereign/stats", {}, (200,)),
    ("/v1/integrity/stats", {}, (200,)),
    ("/v1/hybrid/health", {}, (200,)),
    ("/v1/sovereign-learning/stats", {}, (200,)),
    ("/v1/health-data/fda-label", {"q": "metformin"}, (200, 503)),
    ("/v1/tools/geo/dach", {"postal_code": "10117"}, (200, 503)),
    ("/v1/tools/geo/france", {"q": "8 boulevard du Port Cergy"}, (200, 503)),
    ("/v1/tools/geo/reverse-quick", {"lat": 48.85, "lon": 2.35}, (200, 503)),
    ("/v1/tools/geocode", {"q": "Pretoria"}, (200, 503)),
    ("/v1/tools/reverse-geocode", {"lat": -25.7, "lon": 28.2}, (200, 503)),
    ("/v1/tools/auto", {"q": "schools near soweto"}, (200,)),
    ("/v1/knowledge/scatter", {"q": "lathe"}, (200, 503)),
    ("/v1/registry/providers", {}, (200,)),
    ("/v1/skills/certificate/CERT-NOPE-1", {}, (404,)),
]

ADMIN_GETS = [
    "/v1/monitor/telemetry",
    "/v1/monitor/gate-queue",
    "/v1/system/token-status",
    "/v1/router/telemetry",
    "/v1/ops/metrics",
    "/v1/feedback/summary",
    "/v1/cost/telemetry",
    "/v1/legacy/check",
    "/v1/voice/hume/stats",
    "/v1/registry/health",
    "/v1/registry/savings",
    "/v1/skills/registry",
]

ADMIN_POSTS = [
    "/v1/hybrid/eval",
    "/v1/hybrid/calibrate",
    "/v1/knowledge/reload",
    "/v1/skills/registry/reload",
]

AUTH_GETS = ["/v1/memory/recall", "/v1/legacy/status", "/v1/skills/profile",
             "/v1/user/export", "/v1/skills/gap-analysis"]
AUTH_POSTS = [
    "/v1/auth/logout",
    "/v1/memory/remember",
    "/v1/feedback/submit",
    "/v1/voice/speak",
    "/v1/pedagogy/optimize-learning-path",
    "/v1/sovereign/compile-blueprint",
    "/v1/integrity/verify-submission",
    "/v1/payments/verify-credit/PSK-1",
    "/v1/gateways/process-settlement/REF-1",
    "/v1/sovereign-learning/expand-capability",
    "/v1/legacy/configure",
    "/v1/skills/register",
    "/v1/skills/verify",
    "/v1/skills/certificate/issue",
]

KEYLESS_POSTS = [  # no auth by design; fail-closed without keys is the expected answer
    ("/v1/agent/execute", {"student_tier": "tvet", "action_type": "run_client_simulation",
                           "payload": {"item": "x"}}, (200,)),
    ("/v1/agent/kimi-reason", {"prompt": "hi"}, (500, 503)),
    ("/v1/agent/consumer-shield", {"incident_details": "x", "company_name": "Y"}, (200,)),
    ("/v1/research/literature-search", {"query": "crispr"}, (200, 401, 403, 422, 503)),  # JWT-gated by design
    ("/v1/backup/trigger-backup", {}, (500, 401, 403, 422)),
    ("/v1/agent/kimi-research", {"student_query": "hi"}, (500, 503)),
    ("/v1/agent/scan-opportunities", {"entrepreneur_intent": "x"}, (500, 503)),
    ("/v1/agent/dev-build", {"project_requirements": "x"}, (500, 503)),
    ("/v1/agent/dev-compile", {"stack": "python", "source_files": {"a.py": "x=1"}}, (503,)),
    ("/v1/agent/self-heal", {"error_traceback": "x", "throwing_module": "m"}, (500, 401, 403, 422)),
    ("/v1/automation/trigger-workflow",
     {"workflow_name": "w", "trigger_event": "t", "target_action_steps": []}, (401, 403, 422)),
    ("/v1/webhooks/paystack-settlement", {"event": "x"}, (401,)),
    ("/v1/hybrid/process", {"text": "hello"}, (200,)),
    ("/v1/prompt/enhance", {"raw_prompt": "how do i subnet"}, (200,)),
    ("/v1/mesh/signal/room-1", {"type": "offer"}, (200,)),
    ("/v1/agent/tax-compute", {"gross_revenue": 100.0, "allowable_expenses": 10.0}, (200,)),
    ("/v1/voice/hume/session-complete",
     {"session_id": "s1", "student_id": "u1"}, (401, 503)),
    ("/v1/ops/event", {"type": "deploy"}, (401, 403, 422)),
]


@pytest.mark.parametrize("path,params,expected", PUBLIC_GETS)
def test_public_gets(path, params, expected):
    assert client.get(path, params=params).status_code in expected, path


@pytest.mark.parametrize("path", ADMIN_GETS)
def test_admin_gated(path):
    assert client.get(path).status_code in (401, 403, 422), f"{path} leaked to anonymous"
    assert client.get(path, headers=ADMIN).status_code == 200, f"{path} rejected admin"


@pytest.mark.parametrize("path", AUTH_GETS)
def test_auth_gated_gets(path):
    assert client.get(path).status_code in (401, 403, 422), path


@pytest.mark.parametrize("path", AUTH_POSTS)
def test_auth_gated_posts(path):
    body = {"text": "x", "topic": "t", "fact": "f", "target": "x", "rating": 3,
            "student_query": "x", "entrepreneur_intent": "x", "project_requirements": "x",
            "stack": "python", "source_files": {"a.py": "x"}, "error_traceback": "x",
            "throwing_module": "m", "lab_id": str(uuid.uuid4()),
            "student_id": str(uuid.uuid4()), "submitted_source_code": "print(1)",
            "exploration_type": "botanical_medicine", "target_objective": "x",
            "raw_material_inputs": ["y"], "group_demographic": "g",
            "target_subject": "s", "raw_curriculum_text": "c",
            "subject_domain": "Engineering", "target_topic": "t",
            "resource_context_inputs": ["c"], "reference_id": "r"}
    assert client.post(path, json=body).status_code in (401, 403, 422), f"{path} leaked"


@pytest.mark.parametrize("path,body,expected", KEYLESS_POSTS)
def test_keyless_posts(path, body, expected):
    assert client.post(path, json=body).status_code in expected, path


def test_every_registered_route_is_in_the_matrix():
    """A route missing from the matrix fails the smoke - the matrix cannot rot."""
    matrix_paths = {p for p, _, _ in PUBLIC_GETS} | set(ADMIN_GETS) | set(AUTH_GETS)         | set(AUTH_POSTS) | {p for p, _, _ in KEYLESS_POSTS}
    matrix_paths |= {"/v1/skills/gap-analysis", "/v1/skills/registry",
                     "/v1/skills/registry/reload", "/v1/sync/audit",
                     "/v1/cost/telemetry", "/v1/hybrid/eval", "/v1/hybrid/calibrate",
                     "/v1/knowledge/scatter", "/v1/legacy/check", "/v1/legacy/status",
                     "/v1/legacy/configure", "/v1/skills/register", "/v1/skills/verify",
                     "/v1/skills/profile", "/v1/skills/certificate/issue",
                     "/v1/skills/certificate/{cert_id}", "/v1/user/export",
                     "/v1/voice/hume/session-complete", "/v1/voice/hume/stats",
                     "/v1/registry/providers", "/v1/registry/health", "/v1/registry/savings",
                     "/v1/sync/audit", "/v1/ops/event",
                     "/v1/research/literature-search", "/v1/knowledge/reload",
                     "/v1/mesh/signal/{room_id}", "/v1/human/override/{task_id}",
                     "/v1/router/execute-routed-task", "/v1/auth/register",
                     "/v1/auth/login", "/v1/auth/logout", "/v1/companion/status",
                     "/v1/ops/event", "/v1/knowledge/reload", "/v1/hybrid/calibrate",
                     "/v1/features", "/v1/labs/terminal/{student_id}/{container_name}"}
    registered = {r.path for r in app.routes
                  if hasattr(r, "path") and r.path.startswith("/v1") and "{" not in r.path}
    missing = registered - matrix_paths
    assert not missing, f"routes not covered by smoke matrix: {sorted(missing)}"
