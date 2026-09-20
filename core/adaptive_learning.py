"""
Adaptive Learning Engine — user-contributed kernel, hardened + engine-integrated.

Origin: user-pasted AdvancedAdaptiveEngine (BKT + ZPD + bandwidth routing +
proactive nudges). Review findings applied before integration:

  1. STUB REMOVED — _dispatch_notification printed to stdout. Now: real webhook
     transport (LUQI_NUDGE_WEBHOOK_URL) with an honestly-labeled no-transport
     log fallback. No fake SMS claims.
  2. DIVISION GUARD — BKT posterior denominators can hit 0 with extreme custom
     node params (p_prev=1 & guess=0, or p_prev=0 & slip=0). Guarded.
  3. DAEMON GOVERNED — the infinite nudge loop is env-gated (LUQI_ADAPTIVE_NUDGES=1,
     default OFF) and registered at startup, never silently running.
  4. ACTIVITY TRACKING — mastery updates now touch last_active_timestamp so the
     nudge daemon measures real inactivity.
  5. HOUSE PATTERN — profiles live in a documented in-memory registry v1 (same
     honest pattern as the auth registry); Postgres persistence is queued behind
     accounts unification.

BKT math (Corbett & Anderson): posterior P(L|obs) then transition P(L_n+1) —
verified against hand-computed values in tests/verify_adaptive.py.
"""
import asyncio
import os
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/adaptive", tags=["Adaptive Learning"])


class UIChannel(Enum):
    VISUAL_3D = "visual_3d_app"
    HYBRID_WEB = "hybrid_web"
    WHATSAPP_TEXT = "whatsapp_text"
    SMS_LOW_BANDWIDTH = "sms_text"


# Latency thresholds (ms) — the routing contract, exposed for clients + tests
CHANNEL_THRESHOLDS_MS = {"visual_3d_app": (0, 150), "hybrid_web": (150, 350),
                         "whatsapp_text": (350, 800), "sms_text": (800, None)}


@dataclass
class KnowledgeNode:
    concept_id: str
    mastery_probability: float = 0.1  # Initial P(L0)
    p_transit: float = 0.1            # Probability of learning on opportunity
    p_slip: float = 0.15              # Probability of slip given mastery
    p_guess: float = 0.20             # Probability of guessing correctly without mastery


@dataclass
class LearnerProfile:
    user_id: str
    culture_context: str = "Sub-Saharan"
    language_code: str = "en"
    streak_days: int = 1
    last_active_timestamp: float = field(default_factory=time.time)
    knowledge_graph: Dict[str, KnowledgeNode] = field(default_factory=dict)
    engagement_score: float = 0.85
    network_latency_ms: float = 120.0


# ── Profile registry (in-memory v1 — documented, same pattern as auth v1) ──
_PROFILES: Dict[str, LearnerProfile] = {}


def get_or_create_profile(user_id: str) -> LearnerProfile:
    return _PROFILES.setdefault(user_id, LearnerProfile(user_id=user_id))


class AdvancedAdaptiveEngine:
    def __init__(self, user_profile: LearnerProfile):
        self.profile = user_profile
        self.zpd_min_threshold = 0.65
        self.zpd_max_threshold = 0.85

    # -------------------------------------------------------------------
    # 1. BANDWIDTH & UI STATE ROUTING ENGINE
    # -------------------------------------------------------------------
    def resolve_ui_channel(self, latency_ms: Optional[float] = None) -> UIChannel:
        """Determines the exact UI delivery channel based on network latency and stability."""
        if latency_ms is not None:
            self.profile.network_latency_ms = latency_ms

        lat = self.profile.network_latency_ms
        if lat < 150.0:
            return UIChannel.VISUAL_3D
        elif 150.0 <= lat < 350.0:
            return UIChannel.HYBRID_WEB
        elif 350.0 <= lat < 800.0:
            return UIChannel.WHATSAPP_TEXT
        else:
            return UIChannel.SMS_LOW_BANDWIDTH

    # -------------------------------------------------------------------
    # 2. BAYESIAN KNOWLEDGE TRACING (BKT) & ZPD MODULATION
    # -------------------------------------------------------------------
    def update_skill_mastery(self, concept_id: str, is_correct: bool) -> float:
        """Applies Bayesian Knowledge Tracing to update mastery estimation P(L_n)."""
        node = self.profile.knowledge_graph.setdefault(
            concept_id, KnowledgeNode(concept_id=concept_id)
        )
        p_prev = node.mastery_probability

        # Calculate posterior P(L_n | Response) — denominator guarded against
        # degenerate custom params (e.g. p_prev=1 & p_guess=0).
        if is_correct:
            denom = p_prev * (1.0 - node.p_slip) + (1.0 - p_prev) * node.p_guess
            p_obs = (p_prev * (1.0 - node.p_slip)) / denom if denom > 1e-12 else p_prev
        else:
            denom = p_prev * node.p_slip + (1.0 - p_prev) * (1.0 - node.p_guess)
            p_obs = (p_prev * node.p_slip) / denom if denom > 1e-12 else p_prev

        # Apply transition probability to calculate P(L_n+1)
        p_next = p_obs + (1.0 - p_obs) * node.p_transit
        node.mastery_probability = round(p_next, 4)
        self.profile.last_active_timestamp = time.time()  # real activity signal
        return node.mastery_probability

    def calculate_desirable_difficulty_strategy(self, concept_id: str) -> Dict[str, Any]:
        """Maps current mastery to the Zone of Proximal Development (ZPD)."""
        mastery = self.profile.knowledge_graph.get(
            concept_id, KnowledgeNode(concept_id=concept_id)
        ).mastery_probability

        if mastery < self.zpd_min_threshold:
            return {
                "action": "SCAFFOLD_DOWN",
                "target_difficulty": max(0.1, mastery - 0.2),
                "pedagogical_mode": "ANALOGY_AND_MICRO_EXAMPLE",
                "challenge_multiplier": 0.8,
            }
        elif mastery > self.zpd_max_threshold:
            return {
                "action": "CHALLENGE_UP",
                "target_difficulty": min(1.0, mastery + 0.15),
                "pedagogical_mode": "ENTREPRENEURIAL_REAL_WORLD_PROJECT",
                "challenge_multiplier": 1.4,
            }
        else:
            return {
                "action": "MAINTAIN_FLOW",
                "target_difficulty": mastery,
                "pedagogical_mode": "DIRECT_INTERACTIVE_PRACTICE",
                "challenge_multiplier": 1.0,
            }

    # -------------------------------------------------------------------
    # 3. CONTEXT-AWARE LLM PROMPT SYNTHESIZER
    # -------------------------------------------------------------------
    def generate_llm_prompt_payload(self, concept_id: str, raw_query: str) -> Dict[str, Any]:
        """Constructs a system prompt payload tailored for an LLM generator."""
        channel = self.resolve_ui_channel()
        zpd_strategy = self.calculate_desirable_difficulty_strategy(concept_id)

        system_instruction = (
            f"You are a relatable, highly intelligent AI learning companion in {self.profile.culture_context}. "
            f"Your current UI constraint is '{channel.value}'. "
            f"Mode: '{zpd_strategy['pedagogical_mode']}'. "
            "Use local culturally relevant examples where helpful. Keep responses concise, encouraging, and actionable."
        )

        return {
            "system_instruction": system_instruction,
            "channel_constraints": {
                "max_characters": 160 if channel == UIChannel.SMS_LOW_BANDWIDTH else 1000,
                "format_as_json_cards": channel == UIChannel.VISUAL_3D,
                "use_emojis": channel in [UIChannel.WHATSAPP_TEXT, UIChannel.HYBRID_WEB],
            },
            "user_payload": raw_query,
            "pedagogy_strategy": zpd_strategy,
        }

    # -------------------------------------------------------------------
    # 4. PROACTIVE MOTIVATION & ENGAGEMENT SCHEDULER
    # -------------------------------------------------------------------
    def _craft_proactive_nudge(self, channel: UIChannel) -> str:
        streak = self.profile.streak_days
        if channel in [UIChannel.WHATSAPP_TEXT, UIChannel.SMS_LOW_BANDWIDTH]:
            return f"👋 Ready to keep your {streak}-day streak going? Level up your trade skill today in just 3 mins!"
        return f"🚀 Unlocked Level {streak + 1} challenge! Step back into your learning world to claim your micro-badge."


# ── Nudge dispatch — real transport or honest no-transport log ────────────

def dispatch_nudge(channel: UIChannel, message: str, user_id: str) -> Dict[str, Any]:
    """Dispatch a nudge. Transport: LUQI_NUDGE_WEBHOOK_URL (POST JSON).
    Without a configured transport the nudge is LOGGED VISIBLY — never
    silently swallowed, never claimed sent."""
    webhook = os.getenv("LUQI_NUDGE_WEBHOOK_URL")
    if not webhook:
        print(f"[NUDGE-NO-TRANSPORT] user={user_id} channel={channel.value}: {message}")
        return {"dispatched": False, "reason": "no LUQI_NUDGE_WEBHOOK_URL configured — logged only"}
    try:
        r = requests.post(webhook, json={"user_id": user_id, "channel": channel.value,
                                         "message": message}, timeout=10)
        return {"dispatched": r.status_code < 300, "transport_status": r.status_code}
    except requests.RequestException as e:
        print(f"[NUDGE-TRANSPORT-FAIL] user={user_id}: {e}")
        return {"dispatched": False, "reason": f"transport error: {e}"}


async def run_proactive_checkin_daemon(inactivity_timeout_seconds: float = 86400,
                                       poll_seconds: float = 3600) -> None:
    """Background worker: nudge every inactive registered profile.
    Started ONLY when LUQI_ADAPTIVE_NUDGES=1 (governed, never silent)."""
    while True:
        await asyncio.sleep(poll_seconds)
        now = time.time()
        for profile in list(_PROFILES.values()):
            if now - profile.last_active_timestamp >= inactivity_timeout_seconds:
                engine = AdvancedAdaptiveEngine(profile)
                channel = engine.resolve_ui_channel()
                dispatch_nudge(channel, engine._craft_proactive_nudge(channel), profile.user_id)
                # Half-reset: anti-spam backoff, matches the original kernel's intent
                profile.last_active_timestamp = now - (inactivity_timeout_seconds / 2)


# ── Schemas ───────────────────────────────────────────────────────────────

class ProfileUpsert(BaseModel):
    culture_context: Optional[str] = None
    language_code: Optional[str] = Field(default=None, max_length=10)
    network_latency_ms: Optional[float] = Field(default=None, ge=0)
    streak_days: Optional[int] = Field(default=None, ge=0)


class MasteryUpdate(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    concept_id: str = Field(min_length=1, max_length=200)
    is_correct: bool


class PromptPayloadRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    concept_id: str = Field(min_length=1, max_length=200)
    raw_query: str = Field(min_length=1, max_length=4000)


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.put("/profiles/{user_id}")
async def upsert_profile(user_id: str, req: ProfileUpsert) -> Dict[str, Any]:
    profile = get_or_create_profile(user_id)
    if req.culture_context is not None:
        profile.culture_context = req.culture_context
    if req.language_code is not None:
        profile.language_code = req.language_code
    if req.network_latency_ms is not None:
        profile.network_latency_ms = req.network_latency_ms
    if req.streak_days is not None:
        profile.streak_days = req.streak_days
    profile.last_active_timestamp = time.time()
    return {"user_id": user_id, "culture_context": profile.culture_context,
            "language_code": profile.language_code, "streak_days": profile.streak_days,
            "network_latency_ms": profile.network_latency_ms,
            "registry": "in-memory v1 (documented; Postgres queued behind accounts unification)"}


@router.get("/profiles/{user_id}")
async def get_profile(user_id: str) -> Dict[str, Any]:
    profile = _PROFILES.get(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="profile not found — create via PUT /profiles/{user_id}")
    return {"user_id": user_id, "culture_context": profile.culture_context,
            "language_code": profile.language_code, "streak_days": profile.streak_days,
            "engagement_score": profile.engagement_score,
            "network_latency_ms": profile.network_latency_ms,
            "knowledge_graph": {cid: asdict(node) for cid, node in profile.knowledge_graph.items()}}


@router.get("/channel/{user_id}")
async def resolve_channel(user_id: str, latency_ms: Optional[float] = None) -> Dict[str, Any]:
    engine = AdvancedAdaptiveEngine(get_or_create_profile(user_id))
    channel = engine.resolve_ui_channel(latency_ms)
    return {"user_id": user_id, "channel": channel.value,
            "network_latency_ms": engine.profile.network_latency_ms,
            "thresholds_ms": CHANNEL_THRESHOLDS_MS}


@router.post("/mastery")
async def update_mastery(req: MasteryUpdate) -> Dict[str, Any]:
    engine = AdvancedAdaptiveEngine(get_or_create_profile(req.user_id))
    mastery = engine.update_skill_mastery(req.concept_id, req.is_correct)
    return {"user_id": req.user_id, "concept_id": req.concept_id,
            "mastery_probability": mastery,
            "zpd_strategy": engine.calculate_desirable_difficulty_strategy(req.concept_id)}


@router.get("/strategy/{user_id}/{concept_id}")
async def get_strategy(user_id: str, concept_id: str) -> Dict[str, Any]:
    engine = AdvancedAdaptiveEngine(get_or_create_profile(user_id))
    return {"user_id": user_id, "concept_id": concept_id,
            **engine.calculate_desirable_difficulty_strategy(concept_id)}


@router.post("/prompt-payload")
async def prompt_payload(req: PromptPayloadRequest) -> Dict[str, Any]:
    engine = AdvancedAdaptiveEngine(get_or_create_profile(req.user_id))
    return engine.generate_llm_prompt_payload(req.concept_id, req.raw_query)
