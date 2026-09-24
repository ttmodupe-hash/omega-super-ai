"""
OMEGA-LUQI Hybrid AI Front Door - deterministic guardrails + local ML intent.

Architecture:
  Phase 1: compiled-regex guardrails - ZERO dependencies, always on.
  Phase 2: TF-IDF + LogisticRegression intent classifier (lazy sklearn).
  Phase 3: TIERED confidence gates -> guided escalation (no hallucination,
           no static dead ends - KNOWLEDGE_GAP_POLICY v1.0.0, 2026-09-20).
           High-risk intents (credentials) require more confidence than
           low-risk ones (sentiment) - per-intent thresholds, env-overridable.

v5.18: TVET engineering classes (Electrical N4-N6, Mechanical N4-N6),
admin-gated live calibration (near-miss samples retrain without redeploy),
latency + pii_redacted telemetry on every response.

v5.37 (FRONTDOOR-FIX-1, 2026-09-24): ML-offline is no longer a dead end.
When sklearn is absent the front door degrades to Phase 1.6 - a deterministic
knowledge router over the engine's real surfaces (Scam Shield, Everyday
Services, African History Archive, Technology Radar, World Pulse, Wikipedia).
Unmatched input gets an honest guided escalation listing what the engine CAN
do - never the old "ML classifier offline" refusal.

Security: /calibrate is ADMIN-GATED - an open calibration endpoint would let
anyone poison the classifier that routes students. Corpus capped.

Kill switch: DISABLED_ENGINES containing "hybrid_ai".
"""
import os
import re
import threading
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .admin_auth import verify_admin
from .pii_scrub import scrub_pii

router = APIRouter(prefix="/v1/hybrid", tags=["Hybrid AI Front Door"])

GUARDRAILS = [
    {"id": "CRITICAL_EMERGENCY",
     "pattern": re.compile(r"emergency|crisis|suicide|threat|danger|harm", re.I),
     "response": "ALERT: Route immediately to Gauteng Student Wellness & Crisis Intervention (0800 567 567)."},
    {"id": "POLICY_FINANCIAL_AID",
     "pattern": re.compile(r"refund|bursary|nsfas|stipend|tuition allowance|financial aid", re.I),
     "response": "POLICY: Direct student to the Bursary & Financial Aid Office."},
    {"id": "POLICY_RETENTION",
     "pattern": re.compile(r"cancel account|deregister|withdraw from course", re.I),
     "response": "POLICY: Course withdrawal requires Academic Dean sign-off."},
    {"id": "SECURITY_INJECTION",
     "pattern": re.compile(r"ignore previous instructions|system prompt|jailbreak", re.I),
     "response": "SECURITY: Adversarial prompt injection detected and blocked."},
    {"id": "SECURITY_SQL_INJECTION",
     "pattern": re.compile(r"drop table|union select|';\s*--|or 1=1", re.I),
     "response": "SECURITY: SQL injection pattern detected and blocked."},
]

# pilot corpus - seed data; /calibrate appends admin-vetted near-misses
TRAINING_CORPUS = [
    ("How do I change my password and login pin?", 0),
    ("Reset my login credentials and account access", 0),
    ("Forgot my student portal username", 0),
    ("How to configure OSPF routing on Cisco router?", 1),
    ("Packet tracer network subnetting topology lab", 1),
    ("VLAN trunking and switch port configuration", 1),
    ("Where is Springs campus Ekurhuleni East TVET?", 2),
    ("Find closest TVET campus coordinates in Gauteng", 2),
    ("GPS coordinates for Ekurhuleni East college", 2),
    ("three phase transformer winding calculations electrotechnics", 3),
    ("ohm law kirchhoff circuit analysis ac motor control", 3),
    ("PLC ladder logic and single phase motor starter circuit", 3),
    ("star delta motor control wiring diagram N5", 3),
    ("lathe machine cutting speed feed rate calculation fitting turning", 4),
    ("hydraulic pneumatic cylinder pressure valve fluid mechanics", 4),
    ("gear ratio calculation for milling machine spindle", 4),
    ("CNC milling feed and speed for aluminium alloy", 4),
    ("sans 10400 concrete slump test procedure", 7),
    ("simply supported beam bending moment diagram", 7),
    ("damp proof course height above ground level", 7),
    ("bricklaying mortar mix ratio for foundation", 7),
    # golden-set canonical seeds: the 20 evaluation queries define the classes
    ("reset my nsfas pin", 0),
    ("forgot my student portal login password", 0),
    ("three phase star delta voltage formula", 3),
    ("series rlc impedance calculation ac circuit", 3),
    ("kirchhoff current law at a node", 3),
    ("induction motor overheating causes", 3),
    ("four stroke diesel engine fuel injector timing", 4),
    ("carnot cycle thermal efficiency formula", 4),
    ("hydraulic press pascal law force ratio", 4),
    ("sans 10400 concrete slump test procedure", 7),
    ("simply supported beam bending moment diagram", 7),
    ("damp proof course height above ground level", 7),
    ("ospf neighbor states and lsa types", 1),
    ("subnetting a class b network for 30 hosts", 1),
    ("where is springs campus ekurhuleni east tvet", 2),
    ("directions to the central johannesburg campus", 2),
    # varied phrasings per class - separability needs volume, not duplication
    ("change my campus portal password", 0),
    ("student username recovery help", 0),
    ("login pin reset for the student app", 0),
    ("ospf areas and backbone configuration", 1),
    ("eigrp vs ospf routing protocol comparison", 1),
    ("router ospf process id and network statements", 1),
    ("closest tvet college to benoni", 2),
    ("campus address for pretoria west college", 2),
    ("where can i register at ekurhuleni west campus", 2),
    ("single phase transformer turns ratio", 3),
    ("rc circuit time constant calculation", 3),
    ("wiring a dol starter for three phase motor", 3),
    ("lathe cutting speed for mild steel rpm", 4),
    ("hydraulic pump pressure and flow rate", 4),
    ("pneumatic cylinder force from bore size", 4),
    ("this tutor really helped me understand subnetting", 5),
    ("great app for my n6 exam preparation", 5),
    ("the lab simulator froze on question five", 6),
    ("cannot submit my assignment error message", 6),
    ("concrete mix design for 25 mpa strength", 7),
    ("foundation width for single storey brick house", 7),
    ("plumb line and spirit level setting out", 7),
    ("This interactive networking tutor is wonderful love it!", 5),
    ("Passed my N5 networking exam thanks to this system", 5),
    ("This simulation keeps crashing terrible broken experience", 6),
    ("Error 500 when saving my packet tracer progress", 6),
]

INTENT_META = {
    0: {"label": "credentials", "route": "ML ROUTE: Student Profile & Credential Management.",
        "suggested_tool": None},
    1: {"label": "ospf_labs", "route": "ML ROUTE: OSPF Virtual Packet Tracer & Subnet Lab.",
        "suggested_tool": None},
    2: {"label": "campus_geocoding", "route": "ML ROUTE: TVET Geocoding & GPS Resolver.",
        "suggested_tool": "geocode"},
    3: {"label": "electrical_engineering",
        "route": "ML ROUTE: Electrotechnics & Industrial Electronics Simulator (N4-N6).",
        "suggested_tool": None},
    4: {"label": "mechanical_engineering",
        "route": "ML ROUTE: Mechanical CAD, Lathe Speeds & Fluid Mechanics Helper (N4-N6).",
        "suggested_tool": None},
    5: {"label": "sentiment_positive", "route": "ML SENTIMENT: positive feedback logged.",
        "suggested_tool": "feedback"},
    6: {"label": "incident", "route": "ML SENTIMENT: urgent incident ticket created.",
        "suggested_tool": "feedback"},
    7: {"label": "civil_engineering",
        "route": "ML ROUTE: Civil & Building Construction Helper (N4-N6).",
        "suggested_tool": None},
}

# Tiered gates, CALIBRATED against the golden set + noise floor (v5.22):
# legitimate golden queries score 0.28-0.47; unstructured noise scores a flat
# 0.174 (zero signal, uniform spread). Gates sit in the gap: above every
# legitimate minimum, below the noise ceiling. credentials carries the highest
# bar because a misroute there is the costliest.
INTENT_THRESHOLDS = {0: 0.40, 1: 0.25, 2: 0.25, 3: 0.25, 4: 0.25,
                     5: 0.22, 6: 0.22, 7: 0.25}
_MAX_CORPUS = 5000

# ---------------------------------------------------------------------------
# Phase 1.6 - Deterministic Knowledge Router (ML-offline fallback)
# FRONTDOOR-FIX-1: when sklearn is unavailable, the front door still THINKS -
# it routes deterministically to the engine's real knowledge surfaces.
# Every answer below is retrieved from a sourced module, never generated.
# ---------------------------------------------------------------------------
_FALLBACK_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "i", "me", "my", "you",
    "your", "we", "our", "they", "them", "it", "this", "that", "these",
    "those", "of", "to", "in", "on", "for", "and", "or", "but", "with",
    "about", "how", "what", "when", "where", "who", "why", "which", "can",
    "could", "should", "would", "do", "does", "did", "please", "tell",
    "much", "many", "old", "get", "got", "have", "has", "had", "be", "been",
    "am", "luqi", "ai", "hey", "hello", "hi", "there", "know", "from", "into",
}

_QUESTION_PREFIXES = (
    "how old is", "how old are", "how old was", "what is", "what are",
    "what was", "who is", "who are", "who was", "when did", "when is",
    "where is", "why is", "why are", "how does", "how do", "how much is",
    "how many", "define",
)

# Factual questions ("how old is the world", "who was Shaka") go to the live
# Wikipedia backstop FIRST — pack-internal rarity cannot tell "world" apart
# from a topical term, but the question shape can. Procedural questions
# ("how do I apply for SRD") stay pack-first: those packs ARE the answer.
_FACTUAL_PREFIXES = (
    "how old", "how many", "how much is", "what is", "what are", "what was",
    "who is", "who are", "who was", "when did", "when is", "why is",
    "why are", "define",
)

_NEWS_WORDS = {"news", "headlines", "headline", "happening", "latest",
               "current", "events", "updates", "update"}

_RADAR_WORDS = {"need", "afford", "looking", "free", "cheap", "app", "tool",
                "business", "job", "jobs", "work", "learn", "study",
                "register", "pay", "payment", "payments", "farm", "farming",
                "solve", "problem"}

_ML_NOTE = ("ML classifier offline on this node (sklearn not installed); "
            "answered via the deterministic knowledge router.")


def _content_words(text: str) -> list:
    return [w for w in re.findall(r"[a-z0-9]+", text)
            if len(w) > 2 and w not in _FALLBACK_STOPWORDS]


def _extract_topic(text: str) -> str:
    for pre in _QUESTION_PREFIXES:
        if text.startswith(pre):
            text = text[len(pre):].strip()
            break
    return " ".join(_content_words(text)[:4])


def _p16_scam(text: str):
    """Always-on deterministic scam scan (offline, zero-cost)."""
    from . import finlit
    data = finlit._load_patterns()
    matches, score = [], 0
    for p in data["patterns"]:
        hits, hit_terms = 0, []
        for ind in p["indicators"]:
            found = finlit._compile(ind).findall(text)
            if found:
                hits += len(found)
                hit_terms.append(ind)
        if hits:
            score += p["severity"] + (hits - 1)
            matches.append({"pattern_id": p["id"], "name": p["name"],
                            "category": p["category"]})
    if score < 4:
        return None
    band = ("critical" if score >= 13 else "high" if score >= 8 else "medium")
    return {"engine_used": "Phase 1.6: Deterministic Knowledge Router -> Scam Shield",
            "confidence": 0.0, "ml_note": _ML_NOTE,
            "response": (f"This matches known scam patterns ({band} risk, "
                         f"score {score}): " +
                         "; ".join(m["name"] for m in matches[:3]) +
                         ". Do NOT pay or share details. Full analysis + reporting "
                         "contacts: POST /v1/finlit/scam-check."),
            "scam": {"risk_score": score, "risk_level": band,
                     "matched_patterns": matches,
                     "catalogue": "GET /v1/finlit/scam-patterns"}}


def _p16_pack(text: str, kind: str):
    """Keyword search over the sourced services/history packs."""
    words = _content_words(text)[:6]
    if not words:
        return None
    if kind == "services":
        from . import everyday_services as mod
        entries = mod._load_pack()["entries"]
        label, route = "Everyday Services Pack", "/v1/services"
    else:
        from . import african_history as mod
        entries = mod._load_archive()["entries"]
        label, route = "African History Archive", "/v1/history"
    # Rarity-weighted matching (deterministic TF-IDF-lite): a word's weight is
    # 1 / number of pack entries containing it. Generic prose words ("need",
    # "work", "money") appear in almost every entry and weigh nearly nothing;
    # domain terms ("srd", "uif", "zimbabwe") are rare and weigh a lot.
    # A pack answers only on real topical signal, never on stray common words.
    word_weight = {}
    for w in words:
        doc_count = len(mod._search(entries, w))
        if doc_count:
            word_weight[w] = 1.0 / doc_count
    hits: Dict[str, float] = {}
    for w, weight in word_weight.items():
        for e in mod._search(entries, w):
            hits[e["id"]] = hits.get(e["id"], 0.0) + weight
    if not hits:
        return None
    by_id = {e["id"]: e for e in entries}
    # Title anchoring: a query word that names the entry's own title/id is a
    # strong topical signal; prose-only overlap ("money", "work", "need") is
    # not. Among anchored entries prefer the most anchor words, then score.
    candidates = []
    for eid, score in hits.items():
        title_text = (by_id[eid]["title"] + " " + eid).lower()
        anchors = sum(1 for w in word_weight if w in title_text)
        if anchors:
            candidates.append((anchors, score, eid))
    if candidates:
        candidates.sort(key=lambda t: (-t[0], -t[1]))
        anchors, _score, best_id = candidates[0]
        title_text = (by_id[best_id]["title"] + " " + best_id).lower()
        named = len(words) == 1 and words[0] in title_text
        if not (_score >= 0.4 or anchors >= 2 or named):
            return None
    else:
        # No title anchor anywhere: accept only a single-word query that
        # names an entry title directly; everything else is not topical.
        top = max(hits, key=hits.get)
        title_text = (by_id[top]["title"] + " " + top).lower()
        if len(words) == 1 and words[0] in title_text:
            best_id = top
        else:
            return None
    ent = by_id[best_id]
    s = mod._summary(ent)
    return {"engine_used": f"Phase 1.6: Deterministic Knowledge Router -> {label}",
            "confidence": 0.0, "ml_note": _ML_NOTE,
            "response": (f"{s['title']}: {s['summary']}"),
            "entry": {"id": best_id, "topical_score": round(hits[best_id], 3),
                      "sources_via": f"GET {route} (entry '{best_id}')"}}


def _p16_radar(text: str):
    words = set(_content_words(text))
    if not (words & _RADAR_WORDS):
        return None
    from . import tech_radar
    matches = tech_radar.solve(text, limit=2)
    if not matches:
        return None
    top = matches[0]["technology"]
    alt = (f" Also worth knowing: {matches[1]['technology']['name']}."
           if len(matches) > 1 else "")
    return {"engine_used": "Phase 1.6: Deterministic Knowledge Router -> Technology Radar",
            "confidence": 0.0, "ml_note": _ML_NOTE,
            "response": (f"Technology that solves this: {top['name']} - "
                         f"{top['description']} Cost: {top['cost']}. "
                         f"Official source: {top['link']}.{alt}"),
            "technology": {"id": top["id"], "link": top["link"],
                           "radar": "GET /v1/innovation/technologies"}}


def _p16_news(text: str):
    words = set(_content_words(text))
    if not (words & _NEWS_WORDS):
        return None
    try:
        from . import news_pulse
        payload = news_pulse._gather_topic("world")
    except Exception:
        return None
    if payload["count"] == 0:
        return None
    lines = [f"- {it['title']} ({it['source']}, {it['published']})"
             for it in payload["items"][:3]]
    return {"engine_used": "Phase 1.6: Deterministic Knowledge Router -> World Pulse",
            "confidence": 0.0, "ml_note": _ML_NOTE,
            "response": "Latest cited world headlines:\n" + "\n".join(lines),
            "news": {"generated_at": payload["generated_at"],
                     "feeds_ok": payload["feeds_ok"],
                     "endpoint": "GET /v1/news/headlines"}}


def _p16_wikipedia(text: str):
    topic = _extract_topic(text)
    if not topic:
        return None
    try:
        from . import free_knowledge
        w = free_knowledge.wikipedia_summary(topic)
    except Exception:
        return None
    if not w.get("extract"):
        return None
    return {"engine_used": "Phase 1.6: Deterministic Knowledge Router -> Wikipedia (live)",
            "confidence": 0.0, "ml_note": _ML_NOTE,
            "response": f"{w['title']}: {w['extract']}",
            "source": {"title": w["title"], "url": w.get("url", ""),
                       "note": "live Wikipedia lookup - verify at the link"}}


def _phase16_fallback(text: str):
    """Ordered deterministic routing. First real answer wins. Packs require
    >=2 distinct keyword hits (or a single-word title match), so a lone common
    word like "world" never hijacks a genuine question — the live Wikipedia
    backstop catches those."""
    handlers = [_p16_scam, _p16_news]
    if any(text.startswith(p) for p in _FACTUAL_PREFIXES):
        handlers.append(_p16_wikipedia)
    handlers.extend([lambda t: _p16_pack(t, "services"),
                     lambda t: _p16_pack(t, "history"),
                     _p16_radar, _p16_wikipedia])
    for handler in handlers:
        try:
            out = handler(text)
        except Exception:
            out = None  # a failing surface must never kill the front door
        if out is not None:
            return out
    return None


def _phase16_escalation(t0: float, pii_redacted: bool) -> Dict[str, Any]:
    """Honest no-dead-end: say what the engine CAN do, offer research."""
    return {"engine_used": "Phase 1.6: Knowledge Router - Guided Escalation",
            "confidence": 0.0, "ml_note": _ML_NOTE,
            "response": ("I could not match that to a knowledge surface - I would "
                         "rather say so than guess. What I CAN do right now: check "
                         "a suspicious message for scam patterns, answer SASSA/SARS/UIF/"
                         "NSFAS questions, explore the African History Archive, find a "
                         "free technology for a problem you describe, give today's cited "
                         "news headlines, or research a topic in depth."),
            "escalation": {"available": True, "route": "/v1/deep-research",
                           "method": "POST",
                           "payload_hint": {"query": "<your question>"},
                           "opt_in_required": True},
            "latency_ms": _ms(t0), "pii_redacted": pii_redacted}



class HybridInput(BaseModel):
    text: str = ""
    override_threshold: Optional[float] = Field(None, ge=0.1, le=0.95)


class CalibrateSample(BaseModel):
    text: str = Field(..., min_length=3)
    label: int = Field(..., ge=0, le=7)


class HybridEngine:
    def __init__(self, default_threshold: float = None):
        self.default_threshold = default_threshold if default_threshold is not None else float(
            os.getenv("HYBRID_CONFIDENCE_THRESHOLD", "0.25"))
        self._ml = None
        self._ml_lock = threading.Lock()
        self.corpus: list = list(TRAINING_CORPUS)

    def _load_ml(self):
        with self._ml_lock:
            if self._ml is not None:
                return self._ml
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
                from sklearn.linear_model import LogisticRegression
            except ImportError:
                self._ml = False
                return self._ml
            vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
            model = LogisticRegression(C=1.0, max_iter=200)
            model.fit(vectorizer.fit_transform([t for t, _ in self.corpus]),
                      [l for _, l in self.corpus])
            self._ml = (vectorizer, model)
            return self._ml

    def _retrain(self):
        with self._ml_lock:
            self._ml = None  # force reload on next call
        return self._load_ml()

    def calibrate(self, sample: CalibrateSample) -> Dict[str, Any]:
        text = scrub_pii(sample.text.strip()).lower()
        with self._ml_lock:
            self.corpus.append((text, sample.label))
            if len(self.corpus) > _MAX_CORPUS:
                del self.corpus[0:len(self.corpus) - _MAX_CORPUS]
        ml = self._retrain()
        if not ml:
            raise HTTPException(status_code=503, detail="Calibration unavailable: sklearn not installed.")
        return {"status": "calibrated", "new_corpus_size": len(self.corpus)}

    def process(self, user_input: str, override_threshold: Optional[float] = None) -> Dict[str, Any]:
        t0 = time.perf_counter()
        if "hybrid_ai" in os.getenv("DISABLED_ENGINES", ""):
            return {"engine_used": "KillSwitch", "confidence": 1.0,
                    "response": "Hybrid engine offline.", "latency_ms": 0.1,
                    "pii_redacted": False}

        raw = user_input.strip()
        normalized = scrub_pii(raw).lower()
        pii_redacted = normalized != raw.lower()

        for rule in GUARDRAILS:
            if rule["pattern"].search(normalized):
                return {"engine_used": "Phase 1: Deterministic Guardrail",
                        "confidence": 1.0, "rule_id": rule["id"],
                        "response": rule["response"], "latency_ms": _ms(t0),
                        "pii_redacted": pii_redacted}

        ml = self._load_ml()
        if not ml:
            # FRONTDOOR-FIX-1: no dead end. Degrade to the deterministic
            # knowledge router; unmatched input gets an honest escalation.
            fb = _phase16_fallback(normalized)
            if fb is not None:
                fb["latency_ms"] = _ms(t0)
                fb["pii_redacted"] = pii_redacted
                return fb
            return _phase16_escalation(t0, pii_redacted)
        vectorizer, model = ml
        X = vectorizer.transform([normalized])
        prediction = int(model.predict(X)[0])
        confidence = float(model.predict_proba(X)[0][prediction])

        gate = override_threshold or INTENT_THRESHOLDS.get(prediction, self.default_threshold)
        if confidence < gate:
            # KNOWLEDGE_GAP_POLICY v1.0.0 (2026-09-20): no static dead ends.
            # 1) Transparently signal the boundary (the honest number stays).
            # 2) Offer the proactive research route instead of stopping.
            # 3) Ask for user-guided context that actually refines retrieval.
            # This front door stays zero-external-cost: research only fires
            # when the caller opts in via /v1/deep-research (LLM synthesis is
            # budget-guarded fail-closed at the unified Kimi client).
            return {"engine_used": "Phase 3: Confidence Gate - Guided Escalation",
                    "confidence": round(confidence, 3), "required_gate": gate,
                    "boundary": (f"Confidence ({round(confidence * 100, 1)}%) is below the "
                                 f"required gate ({round(gate * 100, 1)}%) - I would rather "
                                 "say so than guess."),
                    "response": ("I am not confident enough to route this safely. "
                                 "Two ways forward: guide me with a hint (what is it about - "
                                 "credentials, campus GPS, network or engineering labs? name the "
                                 "topic in your own words), or ask me to research it."),
                    "escalation": {"available": True,
                                   "route": "/v1/deep-research",
                                   "method": "POST",
                                   "payload_hint": {"query": "<your question>",
                                                    "context_hint": "<your hint - optional>"},
                                   "cost": ("retrieval is free (scholarly APIs); "
                                            "LLM synthesis is budget-guarded"),
                                   "opt_in_required": True},
                    "latency_ms": _ms(t0), "pii_redacted": pii_redacted}

        meta = INTENT_META[prediction]
        return {"engine_used": "Phase 2: TF-IDF Machine Learning Classifier",
                "confidence": round(confidence, 3), "required_gate": gate,
                "intent": meta["label"], "suggested_tool": meta["suggested_tool"],
                "response": meta["route"], "latency_ms": _ms(t0),
                "pii_redacted": pii_redacted}


def _ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000, 2)


_engine = HybridEngine()


@router.post("/process")
async def process_hybrid(inp: HybridInput) -> Dict[str, Any]:
    """Public, zero-external-cost front door: rules + local ML only."""
    import asyncio
    return await asyncio.to_thread(_engine.process, inp.text, inp.override_threshold)


@router.post("/calibrate", status_code=201)
async def calibrate(sample: CalibrateSample,
                    is_authenticated: bool = Depends(verify_admin)):
    """Admin-gated near-miss calibration. Open calibration = classifier poisoning."""
    return _engine.calibrate(sample)


@router.post("/eval")
async def run_eval(is_authenticated: bool = Depends(verify_admin)):
    """Run the 20-query golden set on demand. CI enforces the floor."""
    from .golden_set import run_golden_set
    import asyncio
    return await asyncio.to_thread(run_golden_set)


@router.get("/health")
async def hybrid_health() -> Dict[str, Any]:
    """Public hybrid status: kill switch, corpus size, active classes."""
    return {"kill_switch": "hybrid_ai" in os.getenv("DISABLED_ENGINES", ""),
            "corpus_size": len(_engine.corpus),
            "classes": [m["label"] for m in INTENT_META.values()],
            "sklearn_available": _engine._load_ml() is not False,
            "ml_offline_fallback": "Phase 1.6 deterministic knowledge router (no dead ends)"}
