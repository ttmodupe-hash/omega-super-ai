"""
OMEGA-LUQI Failover & Integrity Stress Suite (repo root - runs in CI).

Advanced integration test suite validating high-concurrency database failover,
AST lexical code fingerprinting, and API security boundary constraints.
"""

from __future__ import annotations

import concurrent.futures
import threading
import uuid
from typing import Any, Dict, Generator, List, Optional, Tuple

import pytest
from fastapi.testclient import TestClient

from core.db_replication import SovereignDatabaseClusterRouter
from core.integrity_engine import structural_fingerprint
from core.main import app


# ═══════════════════════════════════════════════════════════════════════════════
# MOCK INFRASTRUCTURE & FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

class MockConnection:
    """Simulated database connection context manager."""

    def __init__(self, target: str) -> None:
        self.target = target

    def __enter__(self) -> MockConnection:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        return False

    def execute(self, query: str, *args: Any, **kwargs: Any) -> Dict[str, str]:
        return {"status": "SUCCESS", "node": self.target}


class MockEngine:
    """Simulated database engine with failure injection capabilities."""

    def __init__(self, target_node: str, health_state: Dict[str, bool]) -> None:
        self.target_node = target_node
        self._health_state = health_state

    def connect(self) -> MockConnection:
        if not self._health_state.get(self.target_node, False):
            raise ConnectionError(f"Simulated database timeout on target: {self.target_node}")
        return MockConnection(self.target_node)


def build_mock_router_factory(health_state: Dict[str, bool]):
    """Engine factory closure for injecting failure states into SovereignDatabaseClusterRouter."""
    def factory(url: str, **kwargs: Any) -> MockEngine:
        key = "PRIMARY" if "5432" in url else "LOCAL_REPLICA"
        return MockEngine(target_node=key, health_state=health_state)
    return factory


@pytest.fixture
def cluster_health() -> Dict[str, bool]:
    return {"PRIMARY": True, "LOCAL_REPLICA": True}


@pytest.fixture
def cluster_router(cluster_health: Dict[str, bool]) -> SovereignDatabaseClusterRouter:
    return SovereignDatabaseClusterRouter(
        primary_url="postgresql://omega:secure@primary-db:5432/omega_db",
        replica_url="postgresql://omega:secure@replica-db:5433/omega_db",
        engine_factory=build_mock_router_factory(cluster_health),
    )


@pytest.fixture
def api_client() -> Generator[TestClient, None, None]:
    with TestClient(app) as client:
        yield client


# ═══════════════════════════════════════════════════════════════════════════════
# 1. HIGH-AVAILABILITY DATABASE FAILOVER SCENARIOS
# ═══════════════════════════════════════════════════════════════════════════════

def test_automated_database_cluster_failover_mechanism(
    cluster_health: Dict[str, bool],
    cluster_router: SovereignDatabaseClusterRouter,
) -> None:
    """Validates instant, zero-downtime switchover from Primary to Replica upon outage."""
    # Phase 1: Verify primary node is serving active traffic
    primary_conn = cluster_router.get_healthy_session_connection()
    assert primary_conn is not None
    assert cluster_router.current_target == "PRIMARY"

    # Phase 2: Inject simulated primary node outage
    cluster_health["PRIMARY"] = False

    # Phase 3: Next connection request must seamlessly fall back to LOCAL_REPLICA
    replica_conn = cluster_router.get_healthy_session_connection()
    assert replica_conn is not None
    assert cluster_router.current_target == "LOCAL_REPLICA"


def test_cluster_failover_under_high_load_stress(
    cluster_health: Dict[str, bool],
    cluster_router: SovereignDatabaseClusterRouter,
) -> None:
    """Validates concurrent thread stability during mid-traffic primary node failure."""
    total_workers = 12
    iterations_per_worker = 10
    barrier = threading.Barrier(total_workers)

    def worker_stress_task(worker_id: int) -> List[Tuple[bool, str]]:
        worker_results = []
        # Synchronize all threads before starting load test
        barrier.wait()

        for i in range(iterations_per_worker):
            # Inject primary outage at step 4 across all active threads
            if i == 4 and worker_id == 0:
                cluster_health["PRIMARY"] = False

            try:
                conn = cluster_router.get_healthy_session_connection()
                success = conn is not None
                target = cluster_router.current_target
            except Exception:
                success = False
                target = "DISRUPTED"

            worker_results.append((success, target))
        return worker_results

    with concurrent.futures.ThreadPoolExecutor(max_workers=total_workers) as executor:
        futures = [executor.submit(worker_stress_task, wid) for wid in range(total_workers)]
        all_thread_outputs = [f.result() for f in concurrent.futures.as_completed(futures)]

    # Flatten and analyze execution outputs
    flattened_results = [res for thread_output in all_thread_outputs for res in thread_output]
    successes = [res[0] for res in flattened_results]

    assert all(successes), "Cluster router dropped requests during high-concurrency failover."


# ═══════════════════════════════════════════════════════════════════════════════
# 2. CODE INTEGRITY & LEXICAL AST PLAGIARISM DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize(
    "code_alpha, code_beta, should_match",
    [
        (
            "def compute_sum(a, b):\n    result = a + b\n    return result",
            "def calculate_total(x, y):\n    z = x + y\n    return z",
            True,  # Renamed variables and function signature -> structural clone
        ),
        (
            "def process_data(items):\n    return [i * 2 for i in items]",
            "def process_data(items):\n    res = []\n    for i in items:\n        res.append(i * 2)\n    return res",
            False, # List comprehension vs explicit for-loop -> distinct AST structure
        ),
        (
            "def validate(val):\n    if val > 10:\n        return True\n    return False",
            "def validate(v):\n    # Adding inline comment\n    if v > 10:\n        return True\n    return False",
            True,  # Comments do not alter AST structure
        ),
    ],
)
def test_ast_lexical_analysis_plagiarism_detection(
    code_alpha: str, code_beta: str, should_match: bool
) -> None:
    """Verifies that structural AST fingerprinting detects lexical transformations accurately."""
    fp_a = structural_fingerprint(code_alpha)
    fp_b = structural_fingerprint(code_beta)

    if should_match:
        assert fp_a == fp_b, f"Structural fingerprints should match:\nAlpha: {fp_a}\nBeta:  {fp_b}"
    else:
        assert fp_a != fp_b, f"Structural fingerprints must differ for non-equivalent ASTs:\nAlpha: {fp_a}\nBeta:  {fp_b}"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. ENDPOINT AUTHENTICATION & SECURITY BOUNDARIES
# ═══════════════════════════════════════════════════════════════════════════════

def test_integrity_and_universal_endpoints_require_auth(api_client: TestClient) -> None:
    """Enforces role-based security boundaries on protected core endpoints."""
    # Test protected Integrity verification route
    integrity_resp = api_client.post(
        "/v1/integrity/verify-submission",
        json={
            "lab_id": str(uuid.uuid4()),
            "student_id": str(uuid.uuid4()),
            "submitted_source_code": "print('hello omega')",
        },
    )
    assert integrity_resp.status_code in (401, 403, 422), (
        f"Protected route returned unexpected status: {integrity_resp.status_code}"
    )

    # Test protected Sovereign Learning expansion route
    expansion_resp = api_client.post(
        "/v1/sovereign-learning/expand-capability",
        json={
            "subject_domain": "Advanced Medical Training",
            "target_topic": "Sutherlandia antiviral compounds",
            "resource_context_inputs": ["regional flora"],
        },
    )
    assert expansion_resp.status_code in (401, 403, 422), (
        f"Protected expansion route returned unexpected status: {expansion_resp.status_code}"
    )

    # Verify public telemetry endpoint remains accessible
    stats_resp = api_client.get("/v1/sovereign-learning/stats")
    assert stats_resp.status_code == 200, (
        f"Public telemetry route failed with status: {stats_resp.status_code}"
    )
