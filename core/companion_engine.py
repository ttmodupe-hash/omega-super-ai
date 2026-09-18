"""
OMEGA-LUQI Companion Engine — persistent identity, durable memory, bounded training.

UNIFY-12: companion trainer + bounded self-improvement.

WHAT "SELF-IMPROVEMENT" MEANS HERE (bounded, by design):
  feedback rows -> deterministic rule engine -> whitelisted behavior
  DIRECTIVES in Postgres -> injected as FIXED TEMPLATE SENTENCES into the
  companion system prompt -> measurable behavior change, auditable in
  companion_training_log (old_value -> new_value + feedback ids).

WHAT IT NEVER DOES:
  - no code writes, no model weight updates, no autonomous prompt edits
  - raw feedback text NEVER enters the system prompt (injection-safe:
    only knob/value pairs from the closed DIRECTIVE_KNOBS whitelist render,
    and only as the fixed sentences in DIRECTIVE_PROMPT_LINES)

Durable upgrade of core/memory.py + core/feedback.py (both per-boot
in-memory): companion state survives restarts and works multi-node.

Costs money -> chat is AUTH-GATED and fail-closed without KIMI_API_KEY
(same contract as pedagogy_engine). Every DB endpoint fails closed with
503 when the persistence layer is down - no fake profiles, no fake recall.
"""
import json
import os
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .auth import LuqiAuthManager, UserSessionProfile
from .companion_models import (
    CompanionDirective,
    CompanionFeedback,
    CompanionMemory,
    CompanionProfile,
    CompanionTrainingLog,
)
from .pii_scrub import scrub_pii

companion_router = APIRouter(prefix="/v1/companion", tags=["Companion System"])

# ------------------------------------------------------------------ #
# Bounded behavior space (the full extent of "self-improvement")
# ------------------------------------------------------------------ #

DIRECTIVE_KNOBS: Dict[str, set] = {
    "verbosity": {"concise", "balanced", "detailed"},
    "pace": {"slower", "steady", "faster"},
    "example_density": {"low", "medium", "high"},
    "encouragement_style": {"gentle", "energetic", "formal"},
    "language_mix": {"english_only", "local_flavor"},
    "review_frequency": {"light", "spaced", "dense"},
}

# Fixed template sentences - the ONLY way a directive reaches the prompt.
DIRECTIVE_PROMPT_LINES: Dict[tuple, str] = {
    ("verbosity", "concise"): "Keep answers short and to the point; avoid long digressions.",
    ("verbosity", "balanced"): "Balance brevity with enough detail to be useful.",
    ("verbosity", "detailed"): "Give thorough, in-depth answers with full explanations.",
    ("pace", "slower"): "Go slowly: one concept at a time, check understanding often.",
    ("pace", "steady"): "Keep a steady, even pace through the material.",
    ("pace", "faster"): "Move quickly; the user picks things up fast.",
    ("example_density", "low"): "Use few examples; focus on principles.",
    ("example_density", "medium"): "Use an example when it clarifies a concept.",
    ("example_density", "high"): "Use many concrete, worked examples for every concept.",
    ("encouragement_style", "gentle"): "Be warm and gentle in encouragement; never pushy.",
    ("encouragement_style", "energetic"): "Be energetic and celebratory about progress.",
    ("encouragement_style", "formal"): "Keep a professional, formal tone.",
    ("language_mix", "english_only"): "Respond in English only.",
    ("language_mix", "local_flavor"): "Where natural, weave in the user's local language flavor and local examples.",
    ("review_frequency", "light"): "Suggest review only occasionally.",
    ("review_frequency", "spaced"): "Actively remind the user of spaced-repetition reviews that are due.",
    ("review_frequency", "dense"): "Frequently quiz and review earlier material.",
}

MAX_DIRECTIVES_PER_USER = 8
MAX_MEMORIES_PER_USER = 200
MAX_MEMORIES_IN_PROMPT = 5
TRUST_STEP = Decimal("0.005")
TRUST_CAP = Decimal("1.000")
SPACED_INTERVALS_DAYS = (1, 3, 7, 16, 35)  # by recall_count, capped at last


def _naive(dt: Optional[datetime]) -> Optional[datetime]:
    """Normalize tz-aware Postgres timestamps (TIMESTAMP WITH TIME ZONE via
    psycopg2) to naive UTC so they mix safely with datetime.utcnow()."""
    if dt is not None and dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


COMPANION_MODES = {"chat", "mentor", "coach", "quiz", "explain"}
LEVELS = {"beginner", "intermediate", "advanced", "expert"}

# Deterministic feedback rules: (keywords_any, knob, value, min_rating, max_rating)
# A rule fires when ANY keyword appears in the lowercased comment AND the
# rating is inside [min_rating, max_rating]. This is the ENTIRE learning
# signal path - deterministic, inspectable, no model in the loop.
_FEEDBACK_RULES = [
    (("too long", "shorter", "concise", "brief", "tl;dr"), "verbosity", "concise", 1, 5),
    (("more detail", "in depth", "elaborate", "too short", "longer answers", "deeper"), "verbosity", "detailed", 1, 5),
    (("more example", "examples please", "with examples"), "example_density", "high", 1, 5),
    (("fewer examples", "too many examples"), "example_density", "low", 1, 5),
    (("too fast", "slow down", "slower", "confusing", "lost me", "hard to follow"), "pace", "slower", 1, 5),
    (("too slow", "faster", "speed up", "drags"), "pace", "faster", 1, 5),
    (("setswana", "zulu", "xhosa", "afrikaans", "sesotho", "local language", "mother tongue"), "language_mix", "local_flavor", 1, 5),
    (("english only",), "language_mix", "english_only", 1, 5),
    (("more review", "remind me to review", "revision"), "review_frequency", "dense", 1, 5),
    (("encourag", "motivat", "supportive"), "encouragement_style", "gentle", 4, 5),
    (("too harsh", "gentler", "kinder"), "encouragement_style", "gentle", 1, 3),
    (("more energy", "hype", "celebrat"), "encouragement_style", "energetic", 1, 5),
]


# ------------------------------------------------------------------ #
# Schemas
# ------------------------------------------------------------------ #

class ProfileUpdate(BaseModel):
    companion_name: Optional[str] = Field(default=None, max_length=60)
    personality: Optional[Dict[str, int]] = None   # warmth/humor/formality, 1-5
    level: Optional[str] = None


class ChatRequest(BaseModel):
    mode: str = "chat"
    message: str = Field(min_length=1, max_length=4000)
    topic: Optional[str] = Field(default=None, max_length=120)


class MemoryWrite(BaseModel):
    topic: str = Field(min_length=1, max_length=100)
    fact: str = Field(min_length=1, max_length=1000)
    importance: int = Field(default=3, ge=1, le=5)


class FeedbackWrite(BaseModel):
    mode: str = "chat"
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=500)


class DirectiveWrite(BaseModel):
    knob: str
    value: str


# ------------------------------------------------------------------ #
# Internal helpers
# ------------------------------------------------------------------ #

def _db(request: Request) -> Session:
    engine = getattr(request.app.state, "db_engine", None)
    if engine is None:
        raise HTTPException(status_code=503, detail="Companion persistence unavailable: database layer is down.")
    return Session(engine)


def _get_or_create_profile(session: Session, user: UserSessionProfile) -> CompanionProfile:
    profile = (
        session.query(CompanionProfile)
        .filter(CompanionProfile.user_id == user.user_id)
        .one_or_none()
    )
    if profile is None:
        profile = CompanionProfile(
            user_id=user.user_id,
            country_code=user.country_code.upper()[:3],
            personality={"warmth": 4, "humor": 3, "formality": 2},
        )
        session.add(profile)
        session.commit()
        session.refresh(profile)
    return profile


def _profile_dict(p: CompanionProfile) -> Dict[str, Any]:
    return {
        "companion_name": p.companion_name,
        "personality": p.personality,
        "level": p.level,
        "trust_score": float(p.trust_score),
        "interaction_count": p.interaction_count,
        "streak_days": p.streak_days,
        "last_interaction_at": p.last_interaction_at.isoformat() if p.last_interaction_at else None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def _touch_relationship(profile: CompanionProfile) -> None:
    """Update interaction stats: streak, count, trust. Bounded and deterministic."""
    now = datetime.utcnow()
    last = _naive(profile.last_interaction_at)
    if last is None:
        profile.streak_days = 1
    else:
        gap = (now.date() - last.date()).days
        if gap == 1:
            profile.streak_days += 1
        elif gap > 1:
            profile.streak_days = 1
        # gap == 0 (same day): streak unchanged
    profile.interaction_count += 1
    profile.last_interaction_at = now
    profile.trust_score = min(TRUST_CAP, Decimal(profile.trust_score) + TRUST_STEP)


def _active_directives(session: Session, user_id) -> List[CompanionDirective]:
    return (
        session.query(CompanionDirective)
        .filter(CompanionDirective.user_id == user_id)
        .order_by(CompanionDirective.knob)
        .all()
    )


def _top_memories(session: Session, user_id, topic: Optional[str] = None) -> List[CompanionMemory]:
    """Topic-relevant recall first; if nothing matches the topic, fall back to
    the user's most important memories overall - a companion that knows you
    should never walk into a conversation with empty context."""
    base = session.query(CompanionMemory).filter(CompanionMemory.user_id == user_id)
    ordering = (CompanionMemory.importance.desc(), CompanionMemory.created_at.desc())
    if topic:
        matched = (
            base.filter(CompanionMemory.topic.ilike(f"%{topic[:50]}%"))
            .order_by(*ordering).limit(MAX_MEMORIES_IN_PROMPT).all()
        )
        if matched:
            return matched
    return base.order_by(*ordering).limit(MAX_MEMORIES_IN_PROMPT).all()


def build_system_prompt(
    profile: CompanionProfile,
    directives: List[CompanionDirective],
    memories: List[CompanionMemory],
    mode: str,
) -> str:
    """Render the companion persona prompt.

    Injection safety: directive influence enters ONLY as fixed sentences from
    DIRECTIVE_PROMPT_LINES. Memory facts are user data and enter as a quoted
    recall block (clearly delimited as facts, never as instructions). Raw
    feedback text is never read here at all.
    """
    pers = profile.personality or {}
    warmth = int(pers.get("warmth", 4))
    tone = "warm and caring" if warmth >= 4 else ("friendly" if warmth >= 2 else "reserved and professional")

    mode_lines = {
        "chat": "You are in open companionship mode: supportive conversation, check-ins, everyday help.",
        "mentor": "You are in mentor mode: teach the user's topic at their level with structure and exercises.",
        "coach": "You are in coach mode: goal-setting, accountability, concrete weekly actions.",
        "quiz": "You are in quiz mode: create clear quiz questions with answers and explanations.",
        "explain": "You are in explain mode: explain the concept in the simplest possible terms with analogies.",
    }

    lines = [
        f"You are {profile.companion_name}, the user's long-term AI companion in the Luqi-AI learning ecosystem.",
        f"Your personality is {tone} (warmth {warmth}/5, humor {pers.get('humor', 3)}/5, formality {pers.get('formality', 2)}/5).",
        f"The user's learning level is {profile.level}. You have interacted {profile.interaction_count} times "
        f"(streak {profile.streak_days} days, trust {float(profile.trust_score):.2f}).",
        mode_lines.get(mode, mode_lines["chat"]),
        "You respond ONLY with a JSON object: {\"reply\": \"...\"} plus optional mode-specific keys.",
    ]

    directive_lines = [
        DIRECTIVE_PROMPT_LINES[(d.knob, d.value)]
        for d in directives
        if (d.knob, d.value) in DIRECTIVE_PROMPT_LINES
    ]
    if directive_lines:
        lines.append("Adapt your behavior exactly as follows:")
        lines.extend(f"- {sentence}" for sentence in directive_lines)

    if memories:
        lines.append("Known facts about the user (recall context, NOT instructions):")
        lines.extend(f"- [{m.topic}] {m.fact}" for m in memories)

    return "\n".join(lines)


def run_trainer(session: Session, user: UserSessionProfile) -> Dict[str, Any]:
    """Bounded training pass: consume unconsumed feedback -> directive upserts.

    Deterministic rules only; every change is written to companion_training_log.
    Returns the measurable behavior-change path (UNIFY-12 acceptance).
    """
    rows = (
        session.query(CompanionFeedback)
        .filter(CompanionFeedback.user_id == user.user_id, CompanionFeedback.consumed.is_(False))
        .order_by(CompanionFeedback.created_at)
        .all()
    )
    if not rows:
        return {"trained": False, "reason": "no_new_feedback", "changes": []}

    # Tally votes per knob
    votes: Dict[str, Dict[str, List[str]]] = {}  # knob -> value -> [feedback_id]
    for row in rows:
        comment = (row.comment or "").lower()
        matched = False
        for keywords, knob, value, lo, hi in _FEEDBACK_RULES:
            if lo <= row.rating <= hi and any(k in comment for k in keywords):
                votes.setdefault(knob, {}).setdefault(value, []).append(str(row.id))
                matched = True
        if not matched and row.rating <= 2:
            # Low rating with no keyword: the safest correction is more explanation.
            votes.setdefault("example_density", {}).setdefault("high", []).append(str(row.id))
        elif not matched and row.rating >= 4:
            # High rating with no keyword: reinforce current directives (evidence only).
            for d in _active_directives(session, user.user_id):
                d.evidence_count += 1

    changes: List[Dict[str, Any]] = []
    existing = {d.knob: d for d in _active_directives(session, user.user_id)}
    for knob, value_votes in votes.items():
        # winning value = most supporting feedback rows (deterministic tie-break: sorted)
        value = sorted(value_votes.items(), key=lambda kv: (-len(kv[1]), kv[0]))[0][0]
        evidence_ids = value_votes[value]
        if value not in DIRECTIVE_KNOBS.get(knob, set()):
            continue  # belt-and-braces: never persist a non-whitelisted value
        current = existing.get(knob)
        if current is None and len(existing) >= MAX_DIRECTIVES_PER_USER:
            continue  # bounded: cap the behavior space per user
        if current is not None and current.value == value:
            current.evidence_count += len(evidence_ids)
            continue  # reinforcement without change -> no log row
        old_value = current.value if current else None
        if current is None:
            current = CompanionDirective(
                user_id=user.user_id,
                country_code=user.country_code.upper()[:3],
                knob=knob, value=value, source="feedback",
                evidence_count=len(evidence_ids),
            )
            session.add(current)
            existing[knob] = current
        else:
            current.value = value
            current.evidence_count += len(evidence_ids)
        session.add(CompanionTrainingLog(
            user_id=user.user_id,
            country_code=user.country_code.upper()[:3],
            knob=knob, old_value=old_value, new_value=value,
            feedback_ids=evidence_ids,
        ))
        changes.append({"knob": knob, "old_value": old_value, "new_value": value,
                        "evidence": len(evidence_ids)})

    for row in rows:
        row.consumed = True
    session.commit()
    return {"trained": bool(changes), "feedback_consumed": len(rows), "changes": changes}


# ------------------------------------------------------------------ #
# Endpoints
# ------------------------------------------------------------------ #

@companion_router.get("/profile")
async def get_profile(
    request: Request,
    user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token),
):
    """Get-or-create the user's companion identity."""
    with _db(request) as session:
        return _profile_dict(_get_or_create_profile(session, user))


@companion_router.put("/profile")
async def update_profile(
    update: ProfileUpdate,
    request: Request,
    user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token),
):
    """Name your companion, tune personality (1-5 sliders), set your level."""
    with _db(request) as session:
        profile = _get_or_create_profile(session, user)
        if update.companion_name is not None:
            name = scrub_pii(update.companion_name).strip()[:60]
            if name:
                profile.companion_name = name
        if update.personality is not None:
            pers = dict(profile.personality or {})
            for key in ("warmth", "humor", "formality"):
                if key in update.personality:
                    pers[key] = max(1, min(5, int(update.personality[key])))
            profile.personality = pers
        if update.level is not None:
            level = update.level.lower().strip()
            if level not in LEVELS:
                raise HTTPException(status_code=400, detail=f"level must be one of {sorted(LEVELS)}")
            profile.level = level
        session.commit()
        session.refresh(profile)
        return _profile_dict(profile)


@companion_router.post("/chat")
async def companion_chat(
    req: ChatRequest,
    request: Request,
    user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token),
):
    """Talk to your companion. Profile + memories + trained directives shape
    the persona; every chat advances the relationship (streak, trust).

    Fail-closed without KIMI_API_KEY (same contract as every paid engine).
    """
    mode = req.mode.lower().strip()
    if mode not in COMPANION_MODES:
        raise HTTPException(status_code=400, detail=f"mode must be one of {sorted(COMPANION_MODES)}")

    with _db(request) as session:
        profile = _get_or_create_profile(session, user)
        directives = _active_directives(session, user.user_id)
        memories = _top_memories(session, user.user_id, req.topic)
        system = build_system_prompt(profile, directives, memories, mode)

        user_msg = scrub_pii(req.message)
        if mode in {"mentor", "quiz", "explain"} and req.topic:
            user_msg = f"Topic: {scrub_pii(req.topic)}\n\n{user_msg}"

        from .kimi_client import chat_completion
        try:
            import asyncio
            raw = await asyncio.to_thread(chat_completion, system, user_msg, timeout=60)
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=503, detail=f"Companion AI uplink error: {e}")

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"reply": raw}

        _touch_relationship(profile)
        session.commit()
        return {
            "mode": mode,
            "companion_name": profile.companion_name,
            "response": payload,
            "directives_applied": sorted({d.knob for d in directives}),
            "memories_used": len(memories),
            "relationship": {
                "interaction_count": profile.interaction_count,
                "streak_days": profile.streak_days,
                "trust_score": float(profile.trust_score),
            },
        }


@companion_router.post("/memory")
async def remember(
    note: MemoryWrite,
    request: Request,
    user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token),
):
    """Durable memory write (PII-scrubbed, capped per user)."""
    with _db(request) as session:
        count = session.query(CompanionMemory).filter(CompanionMemory.user_id == user.user_id).count()
        if count >= MAX_MEMORIES_PER_USER:
            oldest = (
                session.query(CompanionMemory)
                .filter(CompanionMemory.user_id == user.user_id)
                .order_by(CompanionMemory.importance.asc(), CompanionMemory.created_at.asc())
                .first()
            )
            session.delete(oldest)  # cap: drop lowest-importance oldest
        session.add(CompanionMemory(
            user_id=user.user_id,
            country_code=user.country_code.upper()[:3],
            topic=scrub_pii(note.topic)[:100],
            fact=scrub_pii(note.fact)[:1000],
            importance=note.importance,
        ))
        session.commit()
        return {"stored": True, "total": min(count + 1, MAX_MEMORIES_PER_USER)}


@companion_router.get("/memory")
async def recall(
    request: Request,
    topic: Optional[str] = None,
    user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token),
):
    """Durable recall. Recalling bumps recall_count (drives spaced review)."""
    with _db(request) as session:
        q = session.query(CompanionMemory).filter(CompanionMemory.user_id == user.user_id)
        if topic:
            q = q.filter(CompanionMemory.topic.ilike(f"%{topic[:50]}%"))
        rows = q.order_by(CompanionMemory.importance.desc(), CompanionMemory.created_at.desc()).limit(50).all()
        now = datetime.utcnow()
        for r in rows:
            r.recall_count += 1
            r.last_recalled_at = now
        session.commit()
        return {"memories": [
            {"topic": r.topic, "fact": r.fact, "importance": r.importance,
             "recall_count": r.recall_count, "created_at": r.created_at.isoformat()}
            for r in rows
        ]}


@companion_router.post("/feedback")
async def leave_feedback(
    entry: FeedbackWrite,
    request: Request,
    user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token),
):
    """Rate the companion. Unconsumed rows fuel the next training pass."""
    mode = entry.mode.lower().strip()
    if mode not in COMPANION_MODES | {"general"}:
        raise HTTPException(status_code=400, detail="unknown mode")
    with _db(request) as session:
        session.add(CompanionFeedback(
            user_id=user.user_id,
            country_code=user.country_code.upper()[:3],
            mode=mode, rating=entry.rating,
            comment=scrub_pii(entry.comment)[:500],
        ))
        session.commit()
        return {"recorded": True, "hint": "POST /v1/companion/train applies feedback as bounded behavior directives."}


@companion_router.post("/train")
async def train(
    request: Request,
    user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token),
):
    """Bounded training pass: feedback -> whitelisted directives (+ audit log).
    This is the ENTIRE self-improvement mechanism - no code writes, ever."""
    with _db(request) as session:
        result = run_trainer(session, user)
        result["directives"] = [
            {"knob": d.knob, "value": d.value, "evidence_count": d.evidence_count, "source": d.source}
            for d in _active_directives(session, user.user_id)
        ]
        return result


@companion_router.get("/directives")
async def list_directives(
    request: Request,
    user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token),
):
    """Current behavior directives - the visible, bounded state of training."""
    with _db(request) as session:
        return {"directives": [
            {"knob": d.knob, "value": d.value, "evidence_count": d.evidence_count,
             "source": d.source, "updated_at": d.updated_at.isoformat() if d.updated_at else None}
            for d in _active_directives(session, user.user_id)
        ]}


@companion_router.put("/directives")
async def set_directive(
    directive: DirectiveWrite,
    request: Request,
    user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token),
):
    """Explicitly set a behavior knob (source='explicit'). Whitelist-enforced."""
    knob = directive.knob.lower().strip()
    value = directive.value.lower().strip()
    if knob not in DIRECTIVE_KNOBS:
        raise HTTPException(status_code=400, detail=f"knob must be one of {sorted(DIRECTIVE_KNOBS)}")
    if value not in DIRECTIVE_KNOBS[knob]:
        raise HTTPException(status_code=400, detail=f"value must be one of {sorted(DIRECTIVE_KNOBS[knob])}")
    with _db(request) as session:
        existing = {d.knob: d for d in _active_directives(session, user.user_id)}
        current = existing.get(knob)
        old_value = current.value if current else None
        if current is None:
            if len(existing) >= MAX_DIRECTIVES_PER_USER:
                raise HTTPException(status_code=400, detail="directive cap reached")
            current = CompanionDirective(
                user_id=user.user_id, country_code=user.country_code.upper()[:3],
                knob=knob, value=value, source="explicit", evidence_count=1,
            )
            session.add(current)
        else:
            current.value = value
            current.source = "explicit"
        session.add(CompanionTrainingLog(
            user_id=user.user_id, country_code=user.country_code.upper()[:3],
            knob=knob, old_value=old_value, new_value=value, feedback_ids=[],
        ))
        session.commit()
        return {"knob": knob, "old_value": old_value, "new_value": value}


@companion_router.get("/training-log")
async def training_log(
    request: Request,
    user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token),
):
    """The auditable behavior-change path: every directive change, with cause."""
    with _db(request) as session:
        rows = (
            session.query(CompanionTrainingLog)
            .filter(CompanionTrainingLog.user_id == user.user_id)
            .order_by(CompanionTrainingLog.created_at.desc())
            .limit(50)
            .all()
        )
        return {"log": [
            {"knob": r.knob, "old_value": r.old_value, "new_value": r.new_value,
             "feedback_ids": r.feedback_ids, "at": r.created_at.isoformat()}
            for r in rows
        ]}


@companion_router.get("/checkin")
async def checkin(
    request: Request,
    user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token),
):
    """Proactive companion check-in - computed from DB, no AI call needed:
    streak health, spaced-repetition reviews due, training state, and a
    suggested next action. Works fully offline of the model gateway."""
    with _db(request) as session:
        profile = _get_or_create_profile(session, user)
        now = datetime.utcnow()

        due_reviews = []
        memories = (
            session.query(CompanionMemory)
            .filter(CompanionMemory.user_id == user.user_id, CompanionMemory.importance >= 4)
            .all()
        )
        for m in memories:
            interval = SPACED_INTERVALS_DAYS[min(m.recall_count, len(SPACED_INTERVALS_DAYS) - 1)]
            anchor = _naive(m.last_recalled_at or m.created_at)
            if anchor and (now - anchor).days >= interval:
                due_reviews.append({"topic": m.topic, "fact": m.fact, "days_overdue": (now - anchor).days - interval})

        pending_feedback = (
            session.query(CompanionFeedback)
            .filter(CompanionFeedback.user_id == user.user_id, CompanionFeedback.consumed.is_(False))
            .count()
        )
        directives = _active_directives(session, user.user_id)

        streak_alive = bool(
            profile.last_interaction_at
            and (now.date() - _naive(profile.last_interaction_at).date()).days <= 1
        )
        if due_reviews:
            suggested = f"Review {len(due_reviews)} due topic(s), starting with '{due_reviews[0]['topic']}'."
        elif not streak_alive and profile.interaction_count > 0:
            suggested = "Say hello to restart your streak."
        elif pending_feedback:
            suggested = "Run a training pass to apply your recent feedback."
        else:
            suggested = "Learn something new today - mentor mode is ready."

        return {
            "companion_name": profile.companion_name,
            "streak_days": profile.streak_days,
            "streak_alive": streak_alive,
            "trust_score": float(profile.trust_score),
            "interaction_count": profile.interaction_count,
            "due_reviews": due_reviews,
            "pending_feedback": pending_feedback,
            "active_directives": len(directives),
            "suggested_action": suggested,
        }
