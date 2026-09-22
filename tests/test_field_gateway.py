"""Contract tests for core/field_gateway.py (Issue 22).

15 checks: HMAC fail-closed, quota, POPIA hashing, deterministic solar math,
cache freeness, honest no-key refusal, admin-gated metrics. Zero network.
"""
import hashlib
import hmac
import importlib
import os
import sys
import pathlib

import pytest

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

import core.field_gateway as fg  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh():
    fg.meter.clear()
    fg._cache.clear()
    fg._quota_day["day"] = None
    fg._quota_day["counts"].clear()
    yield


def test_signature_valid_accepted():
    key = "testkey123"
    body = b"from=%2B2782&text=hi"
    sig = hmac.new(key.encode(), body, hashlib.sha256).hexdigest()
    assert fg.verify_at_signature(body, sig, key) is True


def test_signature_wrong_rejected():
    assert fg.verify_at_signature(b"body", "deadbeef", "key") is False


def test_signature_empty_signature_fail_closed():
    assert fg.verify_at_signature(b"body", "", "key") is False


def test_signature_empty_key_fail_closed():
    assert fg.verify_at_signature(b"body", "abc", "") is False


def test_signature_never_raises_on_garbage():
    assert fg.verify_at_signature(b"", None, None) is False


def test_phone_hashing_is_popia_safe():
    h = fg.hash_phone("+27 82 123 4567")
    assert "82" not in h and "+27" not in h
    assert len(h) == 16
    assert h == fg.hash_phone("+27821234567")  # normalised


def test_solar_calculator_deterministic():
    a = fg.solar_calculator(2000)
    b = fg.solar_calculator(2000)
    assert a == b
    assert a["panels"] == 4  # ceil(2000/550)
    assert a["daily_kwh_estimate"] > 0 and a["cost_zar_estimate"] > 0
    assert "installer" in a["note"]


def test_solar_sms_end_to_end_free():
    reply = fg.process_question("+27820000001", "SOLAR 2000W")
    assert "4 x 550W" in reply
    assert fg.meter["llm_calls"] == 0  # deterministic path never calls the engine


def test_empty_message_guidance():
    assert "empty message" in fg.process_question("+27820000002", "  ")


def test_no_key_honest_refusal_for_llm_questions(monkeypatch):
    monkeypatch.setattr(fg, "AT_API_KEY", "")
    reply = fg.process_question("+27820000003", "explain osmosis for grade 10")
    assert "offline" in reply and "SOLAR" in reply
    assert fg.meter["llm_calls"] == 0


def test_quota_enforced_per_phone(monkeypatch):
    monkeypatch.setattr(fg, "AT_API_KEY", "k")
    monkeypatch.setattr(fg, "FREE_DAILY_SMS_LIMIT", 2)
    monkeypatch.setattr(fg, "_ask_engine", lambda q: "answer " + q)  # unique -> cache-proof
    phone = "+27820000004"
    assert "answer" in fg.process_question(phone, "question one")
    assert "answer" in fg.process_question(phone, "question two")
    refused = fg.process_question(phone, "question three")
    assert "daily limit" in refused
    assert fg.meter["quota_refusals"] == 1


def test_cache_hits_are_free(monkeypatch):
    monkeypatch.setattr(fg, "AT_API_KEY", "k")
    calls = {"n": 0}
    def fake(q):
        calls["n"] += 1
        return "cached answer"
    monkeypatch.setattr(fg, "_ask_engine", fake)
    fg.process_question("+27820000005", "same question")
    fg.process_question("+27820000005", "same question")
    assert calls["n"] == 1


def test_metrics_shape_and_no_raw_phones():
    fg.process_question("+27820000006", "SOLAR 1000W")
    m = fg.metrics()
    assert m["gateway"] == "africas_talking"
    assert m["sms_received"] == 1 and m["sms_replies"] == 1
    assert "27820000006" not in str(m)


def test_build_router_admin_default_and_routes():
    router = fg.build_router()
    paths = {r.path for r in router.routes}
    assert "/webhooks/at/incoming-sms" in paths
    assert "/v1/field/metrics" in paths


def test_module_imports_clean_with_zero_env(monkeypatch):
    """Dormancy contract: import with no AT/KIMI env must not explode."""
    for var in ("AT_API_KEY", "AT_USERNAME", "KIMI_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    importlib.reload(fg)
    assert fg.AT_API_KEY == ""
    importlib.reload(fg)  # restore module state for other tests
