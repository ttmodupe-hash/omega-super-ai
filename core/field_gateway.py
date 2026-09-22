"""LUQI Field Gateway - Africa's Talking SMS front door (Issue 22).

Students on feature phones interact with the engine over SMS. This module is
the honest, deterministic core of that channel:

- HMAC callback signature verification, FAIL-CLOSED when signing is enabled
  (a missing/invalid signature is rejected, never warned-and-allowed).
- Per-phone daily quota on the free tier; the deterministic SOLAR curriculum
  calculator and the cache are always free (they cost us nothing).
- POPIA: phone numbers are stored only as salted SHA-256 hashes in metrics.
- No-key honesty: without AT_API_KEY the gateway answers every question it
  can deterministically and refuses LLM calls with an explicit reason.
- Cost meter is in-memory and admin-gated at the router level.

Mounted DORMANT: the router is built by build_router() and mounted with the
Issue 23 dormant-router batch. Nothing in this module runs at import time
beyond reading env configuration.
"""
import hashlib
import hmac
import logging
import os
import re
import time
from collections import defaultdict

log = logging.getLogger("luqi.field_gateway")

AT_API_KEY = os.getenv("AT_API_KEY", "")
AT_USERNAME = os.getenv("AT_USERNAME", "")
REQUIRE_SIGNATURE = os.getenv("AT_REQUIRE_SIGNATURE", "1") == "1"
FREE_DAILY_SMS_LIMIT = int(os.getenv("AT_FREE_DAILY_SMS_LIMIT", "20"))
PHONE_HASH_SALT = os.getenv("LUQI_PHONE_HASH_SALT", "luqi-popia-default-salt")

# --- POPIA: never store raw MSISDNs -------------------------------------------
def hash_phone(msisdn: str) -> str:
    """Salted SHA-256 of the normalised number. Raw numbers never persist."""
    norm = re.sub(r"[^0-9+]", "", msisdn or "")
    return hashlib.sha256(f"{PHONE_HASH_SALT}:{norm}".encode()).hexdigest()[:16]


# --- Africa's Talking callback signature --------------------------------------
def verify_at_signature(raw_body: bytes, signature: str, api_key: str) -> bool:
    """HMAC-SHA256(raw_body, api_key) compared constant-time. Fail-closed:
    empty signature or empty key -> False, never an exception."""
    if not signature or not api_key:
        return False
    digest = hmac.new(api_key.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature.strip().lower())


# --- quota (in-memory per day; Redis upgrade path is Issue 24) -----------------
_quota_day = {"day": None, "counts": defaultdict(int)}


def quota_check(msisdn_hash: str) -> bool:
    """True if the hashed number is under its free daily SMS quota."""
    today = time.strftime("%Y-%m-%d")
    if _quota_day["day"] != today:
        _quota_day["day"] = today
        _quota_day["counts"] = defaultdict(int)
    return _quota_day["counts"][msisdn_hash] < FREE_DAILY_SMS_LIMIT


def quota_consume(msisdn_hash: str) -> None:
    _quota_day["counts"][msisdn_hash] += 1


# --- deterministic SOLAR curriculum calculator ---------------------------------
_PANEL_W = float(os.getenv("SOLAR_PANEL_WATTS", "550"))
_PANEL_ZAR = float(os.getenv("SOLAR_PANEL_ZAR", "3200"))
_INVERTER_ZAR = float(os.getenv("SOLAR_INVERTER_ZAR", "9500"))
_INSTALL_ZAR = float(os.getenv("SOLAR_INSTALL_ZAR", "12000"))
_SUN_HOURS = float(os.getenv("SOLAR_SUN_HOURS_ZA", "4.5"))  # ZA average peak sun


def solar_calculator(watts_needed: float) -> dict:
    """Deterministic, offline, explainable. The curriculum's canonical solar
    sizing exercise - zero LLM, zero cost, always available over SMS."""
    panels = -(-watts_needed // _PANEL_W)  # ceil without math import
    panels = int(panels)
    daily_kwh = round(panels * _PANEL_W * _SUN_HOURS / 1000, 2)
    cost = round(panels * _PANEL_ZAR + _INVERTER_ZAR + _INSTALL_ZAR, 2)
    return {
        "panels": panels,
        "panel_watts": _PANEL_W,
        "daily_kwh_estimate": daily_kwh,
        "sun_hours_assumed": _SUN_HOURS,
        "cost_zar_estimate": cost,
        "note": "Estimate only - a certified installer must confirm sizing.",
    }


# --- tiny cache: identical questions are free to re-answer ---------------------
_cache = {}
_CACHE_MAX = 500


def _cache_get(key: str):
    hit = _cache.get(key)
    if hit and hit["expires"] > time.time():
        return hit["answer"]
    return None


def _cache_put(key: str, answer: str) -> None:
    if len(_cache) >= _CACHE_MAX:
        _cache.pop(next(iter(_cache)))  # oldest-first eviction
    _cache[key] = {"answer": answer, "expires": time.time() + 86400}


# --- the honest LLM fallback ----------------------------------------------------
def _ask_engine(question: str) -> str:
    """Only reached for non-deterministic questions. No key = honest refusal,
    never a fabricated answer."""
    from core import kimi_client  # lazy: engine boots without this module
    answer = kimi_client.ask(question)
    if not answer:
        raise RuntimeError("engine returned no answer")
    return answer


_SOLAR_RE = re.compile(
    r"solar.*?([0-9][0-9,]*)\s*(w|watt|watts)\b|([0-9][0-9,]*)\s*(w|watt|watts).*?solar",
    re.IGNORECASE,
)

meter = defaultdict(int)  # sms_received / quota_refusals / llm_calls / sms_replies


def process_question(msisdn: str, text: str) -> str:
    """One SMS in, one SMS out. Deterministic first, metered, quota-enforced."""
    meter["sms_received"] += 1
    ph = hash_phone(msisdn)
    text = (text or "").strip()
    if not text:
        return "LUQI: empty message. Send a question, e.g. 'SOLAR 2000W'."

    m = _SOLAR_RE.search(text)
    if m:
        watts = float((m.group(1) or m.group(3)).replace(",", ""))
        r = solar_calculator(watts)
        meter["sms_replies"] += 1
        return (f"LUQI Solar: {r['panels']} x {r['panel_watts']}W panels, ~"
                f"{r['daily_kwh_estimate']}kWh/day, ~R{r['cost_zar_estimate']:,.0f}. "
                f"{r['note']}")

    key = hashlib.sha256(text.lower().encode()).hexdigest()
    cached = _cache_get(key)
    if cached:
        meter["sms_replies"] += 1
        return cached

    if not quota_check(ph):
        meter["quota_refusals"] += 1
        return (f"LUQI: free daily limit reached ({FREE_DAILY_SMS_LIMIT} SMS). "
                "Resets at midnight. Upgrade via your college for unlimited.")

    if not AT_API_KEY:
        return "LUQI: AI answering is offline (no gateway key). Try SOLAR questions - always free."

    try:
        answer = _ask_engine(text)
    except Exception as e:
        log.warning("engine call failed for %s: %s", ph, e)
        return "LUQI: engine error - please retry. If it persists, tell your facilitator."

    quota_consume(ph)
    _cache_put(key, answer)
    meter["llm_calls"] += 1
    meter["sms_replies"] += 1
    return answer


# --- FastAPI surface (mounted dormant with Issue 23 wiring) ----------------------
def build_router(admin_dependency=None):
    """Webhook + admin metrics. admin_dependency defaults to the engine's verify_admin."""
    from fastapi import APIRouter, Depends, HTTPException, Request

    if admin_dependency is None:
        from core.admin_auth import verify_admin  # the engine's existing gate
        admin_dependency = verify_admin

    router = APIRouter()

    @router.post("/webhooks/at/incoming-sms")
    async def incoming_sms(request: Request):
        raw = await request.body()
        if REQUIRE_SIGNATURE:
            if not AT_API_KEY:
                raise HTTPException(500, "signature required but AT_API_KEY unset")
            sig = request.headers.get("x-at-signature") or request.query_params.get("signature")
            if not verify_at_signature(raw, sig, AT_API_KEY):
                raise HTTPException(403, "bad signature")
        form = dict(await request.form())
        reply = process_question(form.get("from", ""), form.get("text", ""))
        # Delivery back through Africa's Talking REST is wired in Issue 23;
        # the verified reply text is returned here so the mount can dispatch it.
        return {"reply": reply}

    @router.get("/v1/field/metrics")
    async def field_metrics(_admin=Depends(admin_dependency)):
        return metrics()

    return router


def metrics() -> dict:
    """Admin-facing counts. Phone numbers are hashes; nothing here identifies a person."""
    return {
        "gateway": "africas_talking",
        "signature_required": REQUIRE_SIGNATURE,
        "key_configured": bool(AT_API_KEY),
        "username_configured": bool(AT_USERNAME),
        "free_daily_sms_limit": FREE_DAILY_SMS_LIMIT,
        **{k: meter[k] for k in ("sms_received", "sms_replies", "llm_calls", "quota_refusals")},
    }
