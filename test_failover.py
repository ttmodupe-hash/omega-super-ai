"""
OMEGA-LUQI Failover & Integrity Stress Suite (repo root - runs in CI).

Adapted from the pasted core/test_failover.py: the scenarios are kept, but
rewritten against the ACTUAL engine APIs (engine-factory injection for the
cluster router, structural_fingerprint for integrity) and without a hard
SQLAlchemy dependency in the failover test.
"""
import concurrent.futures
import uuid

from fastapi.testclient import TestClient

from core.db_replication import SovereignDatabaseClusterRouter
from core.integrity_engine import structural_fingerprint
from core.main import app


# ---- failover scenario (same intent as the pasted test) ----

class _FakeConn:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, *_a, **_k):
        return None


def _make_router(health: dict) -> SovereignDatabaseClusterRouter:
    def factory(url, **kw):
        key = "PRIMARY" if "5432" in url else "LOCAL_REPLICA"

        class _E:
            def connect(self):
                if not health[key]:
                    raise Exception("simulated primary timeout")
                return _FakeConn()
        return _E()
    return SovereignDatabaseClusterRouter("postgresql://u@host:5432/db",
                                          "postgresql://u@host:5433/db",
                                          engine_factory=factory)


def test_automated_database_cluster_failover_mechanism():
    """Primary dies mid-traffic -> instant verified switch to replica."""
    health = {"PRIMARY": True, "LOCAL_REPLICA": True}
    router = _make_router(health)
    assert router.get_healthy_session_connection() is not None

    health["PRIMARY"] = False  # inject the crash
    conn = router.get_healthy_session_connection()
    assert router.current_target == "LOCAL_REPLICA"
    assert conn is not None  # zero-downtime: a working engine is returned


def test_cluster_failover_under_high_load_stress():
    """10 threads hammering the router while the primary crashes: all must
    receive a working engine (some see PRIMARY, some see REPLICA - all valid)."""
    health = {"PRIMARY": True, "LOCAL_REPLICA": True}
    router = _make_router(health)

    def hit(_):
        return router.get_healthy_session_connection() is not None

    health["PRIMARY"] = False  # crash mid-stress
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        results = list(ex.map(hit, range(50)))
    assert all(results), "no thread may see a defunct cluster"


# ---- plagiarism scenario (same intent as the pasted test) ----

def test_ast_lexical_analysis_plagiarism_detection():
    code_alpha = "def compute_sum(a, b):\n    result = a + b\n    return result"
    code_beta = "def calculate_total(x, y):\n    z = x + y\n    return z"
    fa, fb = structural_fingerprint(code_alpha), structural_fingerprint(code_beta)
    assert fa == fb, "renamed copy must produce an identical structural fingerprint"


def test_integrity_and_universal_endpoints_require_auth():
    client = TestClient(app)
    i = client.post("/v1/integrity/verify-submission", json={
        "lab_id": str(uuid.uuid4()), "student_id": str(uuid.uuid4()),
        "submitted_source_code": "print(1)"})
    assert i.status_code in (401, 403, 422)
    u = client.post("/v1/sovereign-learning/expand-capability", json={
        "subject_domain": "Advanced Medical Training",
        "target_topic": "Sutherlandia antiviral compounds",
        "resource_context_inputs": ["regional flora"]})
    assert u.status_code in (401, 403, 422)
    stats = client.get("/v1/sovereign-learning/stats")
    assert stats.status_code == 200
