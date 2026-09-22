"""LUQI Capability Router (Issue 22/23) - every human request gets:

1. Kimi's self-verdict: answerable confidently, or must escalate?
2. If escalate: pick the cheapest configured model whose class fits the task.
3. If nothing configured can do it: an HONEST refusal that names what is
   missing - never a fabricated answer with a confident tone.

Env-driven model table; a provider with no key is skipped, not errored.
Every routed call is logged with a request ID for the cost ledger.
Research/deep-research requests are honestly refused here - the research
tools family is Issue 21's Free API pack, not an LLM call.

Committed DORMANT; mounted with the dormant-router batch (Issue 23 wiring).
"""
import hashlib
import logging
import os
import time
import uuid
from dataclasses import dataclass, field

log = logging.getLogger("luqi.capability_router")

KIMI_MODEL = os.getenv("KIMI_MODEL", "kimi-k3")

# --- model table: class -> ordered candidates (cheapest adequate first) --------
MODEL_TABLE = {
    "kimi": {
        "key": os.getenv("KIMI_API_KEY", ""),
        "model": KIMI_MODEL,
        "classes": {"general", "reasoning", "longform", "math", "vision"},
    },
    "deepseek": {
        "key": os.getenv("DEEPSEEK_API_KEY", ""),
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        "classes": {"math", "reasoning", "general"},
        "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1/chat/completions"),
    },
    "openai": {
        "key": os.getenv("OPENAI_API_KEY", ""),
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "classes": {"longform", "vision", "general"},
    },
    "openrouter": {  # alternate anything
        "key": os.getenv("OPENROUTER_API_KEY", ""),
        "model": os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
        "classes": {"general", "reasoning", "longform", "math", "vision"},
        "base_url": os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1/chat/completions"),
    },
}

# class -> preference order (cost-capped: cheap adequate first)
CLASS_ORDER = {
    "reasoning": ["kimi", "deepseek", "openrouter"],
    "math": ["deepseek", "openrouter"],
    "longform": ["openai", "openrouter"],
    "vision": ["openai", "openrouter"],
    "general": ["openrouter"],
}

_RESEARCH_HINTS = ("research", "sources", "cite", "citation", "papers", "literature")


@dataclass
class RouteVerdict:
    request_id: str
    action: str            # answer | escalate | refuse
    provider: str = ""
    model: str = ""
    cls: str = "general"
    reason: str = ""
    latency_ms: float = 0.0
    metered: dict = field(default_factory=dict)


def classify(text: str) -> str:
    """Deterministic task class. Cheap heuristics; Kimi's self-verdict can
    override to 'reasoning' when it knows it is uncertain."""
    t = (text or "").lower()
    if any(h in t for h in ("integral", "derivative", "solve for", "equation", "math")):
        return "math"
    if any(h in t for h in ("essay", "report", "long answer", "assignment")):
        return "longform"
    if any(h in t for h in ("diagram", "photo", "image", "picture")):
        return "vision"
    if any(h in t for h in ("why", "prove", "reason", "compare", "explain")):
        return "reasoning"
    return "general"


def kimi_self_verdict(text: str) -> dict:
    """Ask Kimi whether it can answer confidently. No key = cannot self-judge
    -> treated as 'uncertain' so we never fake confidence."""
    table = MODEL_TABLE["kimi"]
    if not table["key"]:
        return {"confident": False, "reason": "no KIMI_API_KEY - cannot self-verify"}
    try:
        from core import kimi_client
        return kimi_client.self_verdict(text)  # {"confident": bool, "reason": str}
    except Exception as e:
        log.warning("self-verdict failed: %s", e)
        return {"confident": False, "reason": f"self-verdict error: {e}"}


def pick_escalation(cls: str) -> tuple:
    """First configured provider in the class's preference order."""
    for name in CLASS_ORDER.get(cls, []):
        entry = MODEL_TABLE.get(name)
        if entry and entry["key"]:
            return name, entry["model"]
    return None, None


def route(text: str, meter: dict = None) -> RouteVerdict:
    """The whole policy in one function. Deterministic except the two model
    calls (self-verdict, final answer), both key-gated and logged."""
    rid = uuid.uuid4().hex[:12]
    start = time.time()
    meter = meter if meter is not None else {}
    text = (text or "").strip()

    if not text:
        return RouteVerdict(rid, "refuse", reason="empty request")

    if any(h in text.lower() for h in _RESEARCH_HINTS):
        return RouteVerdict(
            rid, "refuse", cls="research",
            reason="Research questions need the sourced research tools (Issue 21 free-API "
                   "pack: Crossref/OpenAlex/PubMed/arXiv). An LLM-only answer would risk "
                   "fabricated citations - refused by policy.")

    cls = classify(text)
    verdict = kimi_self_verdict(text)

    if verdict.get("confident"):
        log.info("router: kimi confident request_id=%s cls=%s", rid, cls)
        v = RouteVerdict(rid, "answer", provider="kimi", model=MODEL_TABLE["kimi"]["model"],
                         cls=cls, reason=verdict.get("reason", "kimi confident"))
    else:
        provider, model = pick_escalation(cls)
        if provider is None:
            configured = [n for n, e in MODEL_TABLE.items() if e["key"]]
            v = RouteVerdict(
                rid, "refuse", cls=cls,
                reason=(f"Kimi not confident ({verdict.get('reason', 'uncertain')}) and no "
                        f"escalation provider configured for class '{cls}'. "
                        f"Configured: {configured or 'none'}. Set DEEPSEEK_API_KEY / "
                        f"OPENAI_API_KEY / OPENROUTER_API_KEY to widen coverage."))
        else:
            log.info("router: escalate request_id=%s cls=%s -> %s", rid, cls, provider)
            v = RouteVerdict(rid, "escalate", provider=provider, model=model, cls=cls,
                             reason=verdict.get("reason", "kimi uncertain"))

    v.latency_ms = round((time.time() - start) * 1000, 1)
    v.metered = {"request_id": rid, "action": v.action, "provider": v.provider,
                 "class": cls, "text_sha256": hashlib.sha256(text.encode()).hexdigest()[:12]}
    meter[rid] = v.metered
    log.info("router: %s ok request_id=%s", v.action, rid)
    return v
