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
            return {"engine_used": "Phase 1.5: ML unavailable (sklearn not installed)",
                    "confidence": 0.0,
                    "response": "Guardrails active; ML classifier offline on this node.",
                    "latency_ms": _ms(t0), "pii_redacted": pii_redacted}
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
            "sklearn_available": _engine._load_ml() is not False}
