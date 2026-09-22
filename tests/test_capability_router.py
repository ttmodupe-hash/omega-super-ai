"""Contract tests for core/capability_router.py (Issue 22/23).

20 checks: classification, key-gated self-verdict, capped escalation order,
honest refusals (research + no-provider), metering, request IDs. Zero network.
"""
import importlib
import sys
import pathlib

import pytest

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

import core.capability_router as cr  # noqa: E402


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    # deterministic table: kimi keyed, deepseek keyed, openai/openrouter keyless
    table = {k: dict(v) for k, v in cr.MODEL_TABLE.items()}
    table["kimi"]["key"] = "k"
    table["deepseek"]["key"] = "d"
    table["openai"]["key"] = ""
    table["openrouter"]["key"] = ""
    monkeypatch.setattr(cr, "MODEL_TABLE", table)
    yield


def _confident(monkeypatch, confident=True, reason=""):
    monkeypatch.setattr(cr, "kimi_self_verdict",
                        lambda t: {"confident": confident, "reason": reason})


# --- classification ------------------------------------------------------------
def test_classify_math():
    assert cr.classify("solve for x in this equation") == "math"


def test_classify_longform():
    assert cr.classify("write my assignment essay") == "longform"


def test_classify_vision():
    assert cr.classify("what is in this diagram") == "vision"


def test_classify_reasoning():
    assert cr.classify("explain why OSPF forms adjacencies") == "reasoning"


def test_classify_general_default():
    assert cr.classify("hello") == "general"


# --- self-verdict key gate ------------------------------------------------------
def test_no_kimi_key_is_uncertain_not_confident(monkeypatch):
    monkeypatch.setattr(cr, "MODEL_TABLE", {**cr.MODEL_TABLE,
                                            "kimi": {**cr.MODEL_TABLE["kimi"], "key": ""}})
    importlib.reload(cr)  # module-level verdict uses MODEL_TABLE live; call direct
    v = cr.kimi_self_verdict("anything")
    assert v["confident"] is False and "KIMI_API_KEY" in v["reason"]


# --- routing policy --------------------------------------------------------------
def test_confident_kimi_answers_directly(monkeypatch):
    _confident(monkeypatch, True, "sure")
    v = cr.route("explain why the sky is blue")
    assert v.action == "answer" and v.provider == "kimi"
    assert v.model == cr.MODEL_TABLE["kimi"]["model"]


def test_uncertain_reasoning_escalates_cheapest_first(monkeypatch):
    _confident(monkeypatch, False, "unsure")
    v = cr.route("explain why engineers use per-unit")
    assert v.action == "escalate"
    assert v.provider == "deepseek"  # reasoning order: kimi(skip, not confident) -> deepseek


def test_math_skips_kimi_in_order(monkeypatch):
    _confident(monkeypatch, False)
    v = cr.route("solve for x in this equation")
    assert v.action == "escalate" and v.provider == "deepseek"


def test_longform_with_no_openai_falls_to_openrouter_else_refuses(monkeypatch):
    _confident(monkeypatch, False)
    v = cr.route("write my assignment essay")
    # openai keyless, openrouter keyless -> nothing left for longform
    assert v.action == "refuse" and "escalation provider" in v.reason


def test_refusal_names_configured_providers(monkeypatch):
    _confident(monkeypatch, False, "unsure")
    v = cr.route("write my assignment essay")
    assert "deepseek" in v.reason  # honestly reports what IS configured


def test_research_requests_refused_by_policy(monkeypatch):
    _confident(monkeypatch, True)
    v = cr.route("research papers on load shedding with citations")
    assert v.action == "refuse" and v.cls == "research"
    assert "fabricated citations" in v.reason


def test_empty_request_refused():
    v = cr.route("   ")
    assert v.action == "refuse" and v.reason == "empty request"


# --- metering / observability ----------------------------------------------------
def test_request_ids_unique(monkeypatch):
    _confident(monkeypatch, True)
    a, b = cr.route("explain why x"), cr.route("explain why x")
    assert a.request_id != b.request_id and len(a.request_id) == 12


def test_meter_records_without_text(monkeypatch):
    _confident(monkeypatch, True)
    meter = {}
    v = cr.route("explain why transformers hum", meter=meter)
    rec = meter[v.request_id]
    assert rec["action"] == "answer"
    assert "transformers" not in str(rec)  # only a hash, never raw text


def test_latency_measured(monkeypatch):
    _confident(monkeypatch, True)
    assert cr.route("explain why x").latency_ms >= 0


# --- table integrity --------------------------------------------------------------
def test_every_class_order_entry_exists_in_table():
    for cls, order in cr.CLASS_ORDER.items():
        for name in order:
            assert name in cr.MODEL_TABLE, f"{cls} -> {name} missing from table"


def test_every_table_provider_supports_a_known_class():
    known = set(cr.CLASS_ORDER)
    for name, entry in cr.MODEL_TABLE.items():
        assert entry["classes"] & known or name == "kimi"


def test_module_imports_clean_with_zero_env(monkeypatch):
    for var in ("KIMI_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    importlib.reload(cr)
    assert cr.MODEL_TABLE["kimi"]["key"] == ""
    importlib.reload(cr)
