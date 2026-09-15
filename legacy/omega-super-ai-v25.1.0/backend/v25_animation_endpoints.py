#!/usr/bin/env python3
"""
Luqi AI v24.5.0 — Animation & Visual Learning Endpoints
=========================================================
Registers all animated practical learning endpoints.
Integrates animation_engine and visual_learning into the system.

Part of Luqi AI v24.5.0 by Limitless Telecoms — Empowering Africa
"""

from __future__ import annotations

import html
import json
import logging
import secrets
import textwrap
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

# ═══════════════════════════════════════════════════════════════════
# 1.  Import the shared FastAPI app — NEVER crash on failure
# ═══════════════════════════════════════════════════════════════════

_APP_AVAILABLE = False
try:
    from backend.router import app  # type: ignore[attr-defined]

    _APP_AVAILABLE = True
except Exception as _app_exc:  # pragma: no cover
    # Fallback: create a minimal FastAPI app so the file still imports
    # cleanly in test / notebook environments.
    from fastapi import FastAPI

    app = FastAPI(
        title="Luqi AI v24.5.0 — Animation (Standalone)",
        description="Standalone animation endpoint module.",
        version="24.5.0",
    )
    logging.getLogger(__name__).warning(
        "Could not import 'app' from backend.router: %s. "
        "Using standalone FastAPI instance.",
        _app_exc,
    )

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# 2.  Import animation & visual-learning engines — graceful fallback
# ═══════════════════════════════════════════════════════════════════

# ── AnimationEngine ───────────────────────────────────────────────
_ANIMATION_AVAILABLE = False
try:
    from backend.animation_engine import AnimationEngine  # type: ignore[import]

    _ANIMATION_AVAILABLE = True
    logger.info("AnimationEngine loaded successfully.")
except Exception as _ae_exc:  # pragma: no cover
    logger.warning(
        "AnimationEngine not available (%s). Using stub implementation.", _ae_exc
    )

    class AnimationEngine:  # type: ignore[no-redef]
        """Stub AnimationEngine used when the real module is unavailable.

        Provides the same public API but returns safe fallback data so
        endpoints never crash.
        """

        def __init__(self) -> None:
            self._ready = False

        # ── Animation generation ────────────────────────────────────

        def generate_animation(
            self,
            topic: str,
            duration: int = 120,
            style: str = "educational",
        ) -> Dict[str, Any]:
            """Return a stub animation descriptor."""
            return {
                "animation_id": f"stub-{secrets.token_hex(8)}",
                "topic": topic,
                "duration": duration,
                "style": style,
                "status": "unavailable",
                "message": (
                    "AnimationEngine is not installed. "
                    "Install backend.animation_engine to enable full animation generation."
                ),
                "html": self._fallback_html(topic, duration),
            }

        def list_animations(
            self,
            course_id: Optional[str] = None,
            module_id: Optional[str] = None,
        ) -> List[Dict[str, Any]]:
            """Return an empty list — no real animations without the engine."""
            _ = course_id, module_id
            return []

        def get_animation(self, animation_id: str) -> Dict[str, Any]:
            """Return a not-found descriptor."""
            return {
                "animation_id": animation_id,
                "status": "not_found",
                "message": "AnimationEngine is not installed.",
            }

        def register_endpoints(self, application: Any) -> None:
            """No-op when the engine is unavailable."""
            _ = application
            logger.debug("Stub AnimationEngine.register_endpoints() called — no-op.")

        # ── Internal helpers ────────────────────────────────────────

        @staticmethod
        def _fallback_html(topic: str, duration: int) -> str:
            """Produce a minimal HTML placeholder so the UI stays responsive."""
            safe_topic = html.escape(topic)
            return textwrap.dedent(
                f"""\
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <title>{safe_topic} — Animation</title>
                    <style>
                        body {{
                            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                            color: #e0e0e0;
                            display: flex;
                            flex-direction: column;
                            align-items: center;
                            justify-content: center;
                            min-height: 100vh;
                            margin: 0;
                            padding: 2rem;
                            text-align: center;
                        }}
                        .card {{
                            background: rgba(255,255,255,0.05);
                            border-radius: 1rem;
                            padding: 3rem 2rem;
                            max-width: 600px;
                            backdrop-filter: blur(10px);
                            border: 1px solid rgba(255,255,255,0.1);
                        }}
                        h1 {{ font-size: 1.8rem; margin-bottom: 1rem; color: #ffd700; }}
                        p {{ line-height: 1.6; }}
                        .meta {{ color: #888; font-size: 0.9rem; margin-top: 1.5rem; }}
                    </style>
                </head>
                <body>
                    <div class="card">
                        <h1>🎥 {safe_topic}</h1>
                        <p>This animation requires the <strong>AnimationEngine</strong> module.</p>
                        <p>Please install <code>backend.animation_engine</code> to generate full animations.</p>
                        <div class="meta">Duration: {duration}s | Status: engine unavailable</div>
                    </div>
                </body>
                </html>
                """
            )


# ── VisualLearningEngine ──────────────────────────────────────────

_VISUAL_AVAILABLE = False
try:
    from backend.visual_learning import VisualLearningEngine  # type: ignore[import]

    _VISUAL_AVAILABLE = True
    logger.info("VisualLearningEngine loaded successfully.")
except Exception as _ve_exc:  # pragma: no cover
    logger.warning(
        "VisualLearningEngine not available (%s). Using stub implementation.", _ve_exc
    )

    class VisualLearningEngine:  # type: ignore[no-redef]
        """Stub VisualLearningEngine used when the real module is unavailable."""

        def __init__(self) -> None:
            self._ready = False

        # ── Visual aid generation ───────────────────────────────────

        def generate_visual_aid(
            self,
            topic: str,
            aid_type: str = "diagram",
        ) -> Dict[str, Any]:
            """Return a stub visual-aid descriptor."""
            return {
                "visual_id": f"stub-vis-{secrets.token_hex(8)}",
                "topic": topic,
                "aid_type": aid_type,
                "status": "unavailable",
                "message": (
                    "VisualLearningEngine is not installed. "
                    "Install backend.visual_learning to enable full visual learning."
                ),
                "svg": self._fallback_svg(topic),
            }

        def list_visual_aids(
            self,
            category: Optional[str] = None,
        ) -> List[Dict[str, Any]]:
            """Return built-in visual-aid catalogue even in stub mode."""
            _ = category
            return [
                {
                    "visual_id": "stub-diagram-001",
                    "title": "System Architecture Diagram",
                    "category": "diagram",
                    "description": "High-level system architecture overview",
                    "status": "placeholder",
                },
                {
                    "visual_id": "stub-flowchart-001",
                    "title": "Learning Flowchart",
                    "category": "flowchart",
                    "description": "Step-by-step learning progression flow",
                    "status": "placeholder",
                },
                {
                    "visual_id": "stub-infographic-001",
                    "title": "Training Progress Infographic",
                    "category": "infographic",
                    "description": "Visual summary of training achievements",
                    "status": "placeholder",
                },
            ]

        def get_visual_aid(self, visual_id: str) -> Dict[str, Any]:
            """Return a not-found descriptor."""
            return {
                "visual_id": visual_id,
                "status": "not_found",
                "message": "VisualLearningEngine is not installed.",
            }

        def generate_exercise(
            self,
            topic: str,
            exercise_type: str = "hands_on",
        ) -> Dict[str, Any]:
            """Return a stub exercise descriptor."""
            return {
                "exercise_id": f"stub-ex-{secrets.token_hex(8)}",
                "topic": topic,
                "exercise_type": exercise_type,
                "status": "unavailable",
                "message": "VisualLearningEngine is not installed.",
                "steps": [],
            }

        def generate_lab_walkthrough(
            self,
            course_id: str,
            lab_id: Optional[str] = None,
        ) -> Dict[str, Any]:
            """Return a stub lab-walkthrough descriptor."""
            return {
                "lab_id": lab_id or f"stub-lab-{secrets.token_hex(4)}",
                "course_id": course_id,
                "status": "unavailable",
                "message": "VisualLearningEngine is not installed.",
                "steps": [],
            }

        def register_endpoints(self, application: Any) -> None:
            """No-op when the engine is unavailable."""
            _ = application
            logger.debug("Stub VisualLearningEngine.register_endpoints() called — no-op.")

        # ── Internal helpers ────────────────────────────────────────

        @staticmethod
        def _fallback_svg(topic: str) -> str:
            """Produce a minimal SVG placeholder."""
            safe_topic = html.escape(topic)
            return textwrap.dedent(
                f"""\
                <svg xmlns="http://www.w3.org/2000/svg" width="600" height="400"
                     viewBox="0 0 600 400">
                  <defs>
                    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
                      <stop offset="0%" stop-color="#1a1a2e"/>
                      <stop offset="100%" stop-color="#16213e"/>
                    </linearGradient>
                  </defs>
                  <rect width="600" height="400" fill="url(#bg)" rx="12"/>
                  <text x="300" y="180" text-anchor="middle"
                        fill="#ffd700" font-size="22" font-family="sans-serif">
                    Visual Aid: {safe_topic}
                  </text>
                  <text x="300" y="220" text-anchor="middle"
                        fill="#888" font-size="14" font-family="sans-serif">
                    Install backend.visual_learning to enable full rendering
                  </text>
                </svg>
                """
            )


# ═══════════════════════════════════════════════════════════════════
# 3.  Singleton instances
# ═══════════════════════════════════════════════════════════════════

animation_engine: AnimationEngine = AnimationEngine()
visual_engine: VisualLearningEngine = VisualLearningEngine()

logger.info(
    "AnimationEndpoint module initialised — AnimationEngine=%s, VisualLearningEngine=%s",
    "available" if _ANIMATION_AVAILABLE else "stub",
    "available" if _VISUAL_AVAILABLE else "stub",
)


# ═══════════════════════════════════════════════════════════════════
# 4.  Register ALL engine-native endpoints
# ═══════════════════════════════════════════════════════════════════

def _register_engine_endpoints() -> None:
    """Register native endpoints exposed by each engine.

    Engines that provide a ``register_endpoints(application)`` method
    are invoked automatically.  Failures are logged but never propagated.
    """
    # AnimationEngine native endpoints
    try:
        animation_engine.register_endpoints(app)
        logger.info("AnimationEngine endpoints registered.")
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to register AnimationEngine endpoints: %s", exc)

    # VisualLearningEngine native endpoints
    try:
        visual_engine.register_endpoints(app)
        logger.info("VisualLearningEngine endpoints registered.")
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to register VisualLearningEngine endpoints: %s", exc)


_register_engine_endpoints()


# ═══════════════════════════════════════════════════════════════════
# 5.  Convenience endpoints for training integration
# ═══════════════════════════════════════════════════════════════════


# ── 5.1  List available animations for a training module ──────────

@app.get("/api/training/animated/{course_id}/{module_id}")
async def api_training_animated_list(
    course_id: str,
    module_id: str,
    detailed: bool = Query(False, description="Include full animation metadata"),
) -> JSONResponse:
    """Return the list of available animations for a training module.

    Parameters
    ----------
    course_id:
        Unique identifier of the training course.
    module_id:
        Unique identifier of the module within the course.
    detailed:
        When *True*, each animation item includes full metadata
        (creation date, author, tags, duration, etc.).

    Returns
    -------
    JSONResponse
        * ``animations`` — list of animation descriptors.
        * ``course_id`` — echoed course identifier.
        * ``module_id`` — echoed module identifier.
        * ``count`` — total number of animations returned.
        * ``engine_status`` — whether the full AnimationEngine is active.
    """
    try:
        animations = animation_engine.list_animations(
            course_id=course_id,
            module_id=module_id,
        )

        # Enrich stub responses with training-centric metadata when the
        # real engine is absent so the UI still has useful data.
        if not _ANIMATION_AVAILABLE and not animations:
            animations = _generate_default_animations(course_id, module_id)

        if detailed:
            animations = [_enrich_animation_meta(a) for a in animations]

        return JSONResponse(
            {
                "animations": animations,
                "course_id": course_id,
                "module_id": module_id,
                "count": len(animations),
                "engine_status": "active" if _ANIMATION_AVAILABLE else "stub",
            }
        )
    except Exception as exc:
        logger.error(
            "Error listing animations for course=%s module=%s: %s",
            course_id,
            module_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(exc))


# ── 5.2  Auto-generate animation script from lesson content ───────

@app.post("/api/training/animate-lesson")
async def api_training_animate_lesson(request: Request) -> JSONResponse:
    """Auto-generate an animation script and HTML from lesson content.

    Request body (JSON)
    -------------------
    * ``course_id``   — identifier of the parent course.
    * ``lesson_id``   — identifier of the lesson to animate.
    * ``lesson_content`` *(optional)* — raw text / markdown of the lesson.
      When omitted the endpoint attempts to fetch content from the
      course / lesson store.

    Returns
    -------
    JSONResponse
        * ``animation_id`` — unique id for the generated asset.
        * ``script`` — structured animation script (scenes, narration).
        * ``html`` — fully self-contained HTML animation file content.
        * ``topic`` — derived topic string.
        * ``duration_seconds`` — estimated playback duration.
    """
    try:
        data: Dict[str, Any] = json.loads(await request.body())
        course_id: str = data.get("course_id", "")
        lesson_id: str = data.get("lesson_id", "")
        lesson_content: str = data.get("lesson_content", "")

        if not course_id or not lesson_id:
            raise HTTPException(
                status_code=400,
                detail="Both 'course_id' and 'lesson_id' are required.",
            )

        topic = _derive_topic(lesson_content, lesson_id)

        # Attempt full animation generation; fall back to stub HTML
        result = animation_engine.generate_animation(
            topic=topic,
            duration=120,
            style="educational",
        )

        # Build a structured animation script
        script = _build_animation_script(topic, lesson_content)

        return JSONResponse(
            {
                "animation_id": result.get(
                    "animation_id", f"anim-{secrets.token_hex(8)}"
                ),
                "script": script,
                "html": result.get("html", ""),
                "topic": topic,
                "duration_seconds": result.get("duration", 120),
                "course_id": course_id,
                "lesson_id": lesson_id,
                "engine_status": "active" if _ANIMATION_AVAILABLE else "stub",
            }
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error animating lesson: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


# ── 5.3  Interactive lab walkthroughs for a course ────────────────

@app.get("/api/training/labs/{course_id}")
async def api_training_labs(
    course_id: str,
    lab_id: Optional[str] = None,
) -> JSONResponse:
    """Return interactive lab walkthroughs for a course.

    Parameters
    ----------
    course_id:
        Identifier of the training course.
    lab_id:
        When provided, return only that specific lab; otherwise all
        labs for the course are returned.

    Returns
    -------
    JSONResponse
        * ``labs`` — list of lab walkthrough descriptors.
        * ``course_id`` — echoed.
        * ``count`` — number of labs returned.
    """
    try:
        if lab_id:
            walkthrough = visual_engine.generate_lab_walkthrough(
                course_id=course_id,
                lab_id=lab_id,
            )
            labs = [walkthrough] if walkthrough else []
        else:
            labs = _generate_default_labs(course_id)

        return JSONResponse(
            {
                "labs": labs,
                "course_id": course_id,
                "count": len(labs),
                "engine_status": "active" if _VISUAL_AVAILABLE else "stub",
            }
        )
    except Exception as exc:
        logger.error(
            "Error fetching labs for course=%s: %s", course_id, exc, exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(exc))


# ── 5.4  Generate practical exercise with animations ──────────────

@app.post("/api/training/practical-exercise")
async def api_training_practical_exercise(request: Request) -> JSONResponse:
    """Generate a practical exercise with embedded animations.

    Request body (JSON)
    -------------------
    * ``topic``          — subject matter of the exercise.
    * ``exercise_type``  — one of ``hands_on``, ``simulation``, ``quiz``.
    * ``difficulty``     *(optional)* — ``beginner`` | ``intermediate`` | ``advanced``.
    * ``duration_min``   *(optional)* — expected completion time in minutes.

    Returns
    -------
    JSONResponse
        * ``exercise_id`` — unique identifier.
        * ``topic``, ``exercise_type``, ``difficulty``.
        * ``steps`` — ordered list of exercise steps with animation refs.
        * ``animations`` — list of associated animation descriptors.
    """
    try:
        data: Dict[str, Any] = json.loads(await request.body())
        topic: str = data.get("topic", "")
        exercise_type: str = data.get("exercise_type", "hands_on")
        difficulty: str = data.get("difficulty", "intermediate")
        duration_min: int = data.get("duration_min", 15)

        if not topic:
            raise HTTPException(status_code=400, detail="'topic' is required.")

        if exercise_type not in {"hands_on", "simulation", "quiz"}:
            raise HTTPException(
                status_code=400,
                detail="'exercise_type' must be one of: hands_on, simulation, quiz.",
            )

        # Generate exercise structure via visual engine
        exercise = visual_engine.generate_exercise(
            topic=topic,
            exercise_type=exercise_type,
        )

        # Generate companion animations
        anim_result = animation_engine.generate_animation(
            topic=topic,
            duration=duration_min * 60,
            style="interactive",
        )

        exercise_id = f"ex-{secrets.token_hex(8)}"

        return JSONResponse(
            {
                "exercise_id": exercise_id,
                "topic": topic,
                "exercise_type": exercise_type,
                "difficulty": difficulty,
                "duration_minutes": duration_min,
                "steps": exercise.get("steps", _default_exercise_steps(topic, exercise_type)),
                "animations": [
                    {
                        "animation_id": anim_result.get("animation_id", ""),
                        "html_preview": anim_result.get("html", ""),
                        "duration_seconds": anim_result.get("duration", duration_min * 60),
                    }
                ],
                "engine_status": {
                    "animation": "active" if _ANIMATION_AVAILABLE else "stub",
                    "visual": "active" if _VISUAL_AVAILABLE else "stub",
                },
            }
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error generating practical exercise: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


# ── 5.5  List available visual learning aids ──────────────────────

@app.get("/api/training/visual-aids")
async def api_training_visual_aids(
    category: Optional[str] = Query(None, description="Filter by category"),
) -> JSONResponse:
    """Return the catalogue of available visual learning aids.

    Parameters
    ----------
    category:
        Optional filter — ``diagram``, ``flowchart``, ``infographic``,
        ``animation``, ``interactive``, etc.

    Returns
    -------
    JSONResponse
        * ``visual_aids`` — list of visual-aid descriptors.
        * ``count`` — total available.
        * ``categories`` — distinct categories present.
    """
    try:
        aids = visual_engine.list_visual_aids(category=category)

        # Always inject training-relevant defaults when running in stub mode
        if not _VISUAL_AVAILABLE and not aids:
            aids = _generate_default_visual_aids()

        if category:
            aids = [a for a in aids if a.get("category") == category]

        categories = sorted({a.get("category", "general") for a in aids})

        return JSONResponse(
            {
                "visual_aids": aids,
                "count": len(aids),
                "categories": categories,
                "engine_status": "active" if _VISUAL_AVAILABLE else "stub",
            }
        )
    except Exception as exc:
        logger.error("Error listing visual aids: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


# ── 5.6  Quick 2-minute animation for any topic ───────────────────

@app.post("/api/training/quick-animation")
async def api_training_quick_animation(request: Request) -> HTMLResponse:
    """Generate a quick 2-minute HTML animation for any topic.

    The response is returned as a raw HTML document so it can be
    rendered directly in an ``<iframe>`` or browser tab.

    Request body (JSON)
    -------------------
    * ``topic`` — the subject to animate (required).
    * ``style`` *(optional)* — ``educational`` | ``minimal`` | "vibrant".

    Returns
    -------
    HTMLResponse
        Self-contained HTML animation document.
    """
    try:
        data: Dict[str, Any] = json.loads(await request.body())
        topic: str = data.get("topic", "")
        style: str = data.get("style", "educational")

        if not topic:
            raise HTTPException(status_code=400, detail="'topic' is required.")

        result = animation_engine.generate_animation(
            topic=topic,
            duration=120,
            style=style,
        )

        html_content: str = result.get("html", "")

        # If the engine returned a stub / empty HTML, generate a rich
        # fallback so the user still sees something useful.
        if not html_content or "engine unavailable" in html_content.lower():
            html_content = _generate_rich_fallback_html(topic, style)

        return HTMLResponse(content=html_content, status_code=200)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error generating quick animation: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


# ═══════════════════════════════════════════════════════════════════
# 6.  Health / status endpoint for the animation subsystem
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/training/animation-status")
async def api_training_animation_status() -> JSONResponse:
    """Return the operational status of the animation subsystem.

    Useful for dashboards and health-check probes.
    """
    return JSONResponse(
        {
            "module": "v25_animation_endpoints",
            "version": "24.5.0",
            "animation_engine": {
                "available": _ANIMATION_AVAILABLE,
                "status": "active" if _ANIMATION_AVAILABLE else "stub",
            },
            "visual_learning_engine": {
                "available": _VISUAL_AVAILABLE,
                "status": "active" if _VISUAL_AVAILABLE else "stub",
            },
            "app_import_ok": _APP_AVAILABLE,
            "timestamp": time.time(),
        }
    )


# ═══════════════════════════════════════════════════════════════════
# 7.  Internal helper functions
# ═══════════════════════════════════════════════════════════════════


def _derive_topic(lesson_content: str, lesson_id: str) -> str:
    """Derive a concise topic string from lesson content or id.

    Parameters
    ----------
    lesson_content:
        Raw lesson text.  The first sentence or line is used when
        present, otherwise *lesson_id* is humanised.
    lesson_id:
        Fallback identifier used when content is empty.

    Returns
    -------
    str
        A short, human-readable topic string.
    """
    if lesson_content:
        # Use the first line / sentence, capped at 80 chars
        first = lesson_content.strip().split("\n")[0].split(".")[0]
        return first[:80] if first else lesson_id.replace("-", " ").title()
    return lesson_id.replace("-", " ").replace("_", " ").title()


def _build_animation_script(topic: str, lesson_content: str) -> Dict[str, Any]:
    """Build a structured animation script from lesson content.

    When the full AnimationEngine is absent this produces a sensible
    default script so the UI can still display scene breakdowns.
    """
    scenes: List[Dict[str, Any]] = []
    if lesson_content:
        paragraphs = [p.strip() for p in lesson_content.split("\n\n") if p.strip()]
        for idx, para in enumerate(paragraphs[:6], start=1):
            scenes.append(
                {
                    "scene_number": idx,
                    "title": f"Scene {idx}: {topic[:30]}",
                    "narration": para[:200],
                    "duration_seconds": 20,
                    "visual": "slide",
                    "transition": "fade",
                }
            )
    else:
        scenes = [
            {
                "scene_number": 1,
                "title": f"Introduction: {topic[:40]}",
                "narration": f"Welcome to the lesson on {topic}.",
                "duration_seconds": 30,
                "visual": "title_card",
                "transition": "fade",
            },
            {
                "scene_number": 2,
                "title": "Core Concepts",
                "narration": "Let's explore the core concepts together.",
                "duration_seconds": 60,
                "visual": "diagram",
                "transition": "slide_left",
            },
            {
                "scene_number": 3,
                "title": "Practical Application",
                "narration": "Now let's see how this works in practice.",
                "duration_seconds": 30,
                "visual": "demo",
                "transition": "fade",
            },
        ]

    return {
        "title": topic,
        "total_scenes": len(scenes),
        "total_duration_seconds": sum(s["duration_seconds"] for s in scenes),
        "scenes": scenes,
    }


def _enrich_animation_meta(animation: Dict[str, Any]) -> Dict[str, Any]:
    """Add computed metadata fields to an animation descriptor."""
    animation = dict(animation)
    animation.setdefault("created_at", time.strftime("%Y-%m-%dT%H:%M:%SZ"))
    animation.setdefault("author", "Luqi AI Animation System")
    animation.setdefault("tags", ["training", "auto-generated"])
    animation.setdefault("language", "en")
    return animation


def _generate_default_animations(
    course_id: str,
    module_id: str,
) -> List[Dict[str, Any]]:
    """Produce a set of default animation placeholders for a module."""
    return [
        {
            "animation_id": f"{course_id}-{module_id}-intro",
            "title": "Module Introduction",
            "description": f"Introduction animation for {module_id}",
            "duration": 60,
            "type": "intro",
            "status": "generated",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        {
            "animation_id": f"{course_id}-{module_id}-concepts",
            "title": "Core Concepts Walkthrough",
            "description": f"Animated explanation of key concepts in {module_id}",
            "duration": 120,
            "type": "explanation",
            "status": "generated",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        {
            "animation_id": f"{course_id}-{module_id}-demo",
            "title": "Practical Demonstration",
            "description": f"Hands-on demo animation for {module_id}",
            "duration": 180,
            "type": "demonstration",
            "status": "generated",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    ]


def _generate_default_labs(course_id: str) -> List[Dict[str, Any]]:
    """Produce default lab walkthroughs for a course."""
    return [
        {
            "lab_id": f"{course_id}-lab-001",
            "title": "Foundations Lab",
            "description": "Basic hands-on exercises to build core skills.",
            "difficulty": "beginner",
            "estimated_minutes": 30,
            "steps": [
                {"step": 1, "title": "Setup Environment", "duration_min": 5},
                {"step": 2, "title": "Complete Exercise A", "duration_min": 15},
                {"step": 3, "title": "Verify Results", "duration_min": 10},
            ],
            "status": "generated",
        },
        {
            "lab_id": f"{course_id}-lab-002",
            "title": "Intermediate Challenge",
            "description": "Apply learned concepts to solve realistic problems.",
            "difficulty": "intermediate",
            "estimated_minutes": 45,
            "steps": [
                {"step": 1, "title": "Read Scenario", "duration_min": 5},
                {"step": 2, "title": "Design Solution", "duration_min": 15},
                {"step": 3, "title": "Implement & Test", "duration_min": 20},
                {"step": 4, "title": "Submit for Review", "duration_min": 5},
            ],
            "status": "generated",
        },
        {
            "lab_id": f"{course_id}-lab-003",
            "title": "Capstone Project",
            "description": "Comprehensive project integrating all course concepts.",
            "difficulty": "advanced",
            "estimated_minutes": 90,
            "steps": [
                {"step": 1, "title": "Project Brief", "duration_min": 10},
                {"step": 2, "title": "Architecture Design", "duration_min": 20},
                {"step": 3, "title": "Implementation", "duration_min": 40},
                {"step": 4, "title": "Testing & QA", "duration_min": 15},
                {"step": 5, "title": "Presentation", "duration_min": 5},
            ],
            "status": "generated",
        },
    ]


def _generate_default_visual_aids() -> List[Dict[str, Any]]:
    """Produce the full catalogue of default visual learning aids."""
    return [
        {
            "visual_id": "va-diagram-001",
            "title": "System Architecture Diagram",
            "category": "diagram",
            "description": "High-level view of system components and data flow.",
            "tags": ["architecture", "overview"],
            "status": "available",
        },
        {
            "visual_id": "va-flowchart-001",
            "title": "Troubleshooting Flowchart",
            "category": "flowchart",
            "description": "Step-by-step diagnostic decision tree.",
            "tags": ["troubleshooting", "process"],
            "status": "available",
        },
        {
            "visual_id": "va-infographic-001",
            "title": "Training Roadmap",
            "category": "infographic",
            "description": "Visual progression from beginner to expert.",
            "tags": ["roadmap", "progression"],
            "status": "available",
        },
        {
            "visual_id": "va-animation-001",
            "title": "Protocol Handshake Animation",
            "category": "animation",
            "description": "Animated walkthrough of a TCP 3-way handshake.",
            "tags": ["networking", "tcp", "protocol"],
            "status": "available",
        },
        {
            "visual_id": "va-interactive-001",
            "title": "Subnet Calculator",
            "category": "interactive",
            "description": "Interactive tool for subnet mask calculations.",
            "tags": ["networking", "subnetting", "calculator"],
            "status": "available",
        },
        {
            "visual_id": "va-diagram-002",
            "title": "OSI Model Layers",
            "category": "diagram",
            "description": "Visual reference for the 7-layer OSI model.",
            "tags": ["networking", "osi-model", "reference"],
            "status": "available",
        },
    ]


def _default_exercise_steps(topic: str, exercise_type: str) -> List[Dict[str, Any]]:
    """Return generic exercise steps when the visual engine is unavailable."""
    base_steps = [
        {
            "step": 1,
            "title": "Understand the Objective",
            "instruction": f"Review the core concepts related to {topic}.",
            "animation_ref": None,
        },
        {
            "step": 2,
            "title": "Study the Example",
            "instruction": "Walk through the provided worked example carefully.",
            "animation_ref": None,
        },
        {
            "step": 3,
            "title": "Apply Your Knowledge",
            "instruction": "Complete the exercise using what you've learned.",
            "animation_ref": None,
        },
    ]
    if exercise_type == "hands_on":
        base_steps.append(
            {
                "step": 4,
                "title": "Practical Implementation",
                "instruction": "Implement the solution in the lab environment.",
                "animation_ref": None,
            }
        )
    elif exercise_type == "simulation":
        base_steps.append(
            {
                "step": 4,
                "title": "Run Simulation",
                "instruction": "Execute the simulation and observe the results.",
                "animation_ref": None,
            }
        )
    elif exercise_type == "quiz":
        base_steps.append(
            {
                "step": 4,
                "title": "Answer Questions",
                "instruction": "Answer all quiz questions to the best of your ability.",
                "animation_ref": None,
            }
        )
    base_steps.append(
        {
            "step": len(base_steps) + 1,
            "title": "Review & Reflect",
            "instruction": "Check your answers and review any mistakes.",
            "animation_ref": None,
        }
    )
    return base_steps


def _generate_rich_fallback_html(topic: str, style: str) -> str:
    """Generate a visually rich HTML animation when the engine is unavailable.

    The output is a self-contained, responsive HTML page with CSS animations
    so the user experience is still polished.
    """
    safe_topic = html.escape(topic)
    gradient_map = {
        "educational": "linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)",
        "minimal": "linear-gradient(135deg, #f5f5f5 0%, #e0e0e0 100%)",
        "vibrant": "linear-gradient(135deg, #ff6b6b 0%, #feca57 50%, #48dbfb 100%)",
    }
    bg = gradient_map.get(style, gradient_map["educational"])
    text_color = "#333" if style == "minimal" else "#e0e0e0"
    accent = "#ffd700" if style != "vibrant" else "#fff"

    return textwrap.dedent(
        f"""\
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{safe_topic} — Quick Animation</title>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
                    background: {bg};
                    color: {text_color};
                    min-height: 100vh;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    overflow: hidden;
                    padding: 2rem;
                }}
                .container {{
                    text-align: center;
                    max-width: 800px;
                    animation: fadeInUp 1s ease-out;
                }}
                @keyframes fadeInUp {{
                    from {{ opacity: 0; transform: translateY(30px); }}
                    to   {{ opacity: 1; transform: translateY(0); }}
                }}
                .icon {{
                    font-size: 5rem;
                    margin-bottom: 1.5rem;
                    animation: bounce 2s infinite;
                }}
                @keyframes bounce {{
                    0%, 100% {{ transform: translateY(0); }}
                    50%      {{ transform: translateY(-15px); }}
                }}
                h1 {{
                    font-size: 2.5rem;
                    margin-bottom: 1rem;
                    color: {accent};
                    text-shadow: 0 2px 10px rgba(0,0,0,0.3);
                }}
                .subtitle {{
                    font-size: 1.2rem;
                    opacity: 0.85;
                    margin-bottom: 2rem;
                    line-height: 1.6;
                }}
                .meta {{
                    display: inline-flex;
                    gap: 1.5rem;
                    flex-wrap: wrap;
                    justify-content: center;
                    margin-top: 2rem;
                }}
                .badge {{
                    background: rgba(255,255,255,0.1);
                    border: 1px solid rgba(255,255,255,0.2);
                    border-radius: 2rem;
                    padding: 0.5rem 1.2rem;
                    font-size: 0.85rem;
                    backdrop-filter: blur(5px);
                }}
                .progress-bar {{
                    width: 100%;
                    max-width: 400px;
                    height: 4px;
                    background: rgba(255,255,255,0.1);
                    border-radius: 2px;
                    margin: 2rem auto;
                    overflow: hidden;
                }}
                .progress-fill {{
                    width: 0%;
                    height: 100%;
                    background: {accent};
                    border-radius: 2px;
                    animation: fillBar 2s ease-out forwards;
                }}
                @keyframes fillBar {{
                    to {{ width: 100%; }}
                }}
                .footer {{
                    position: fixed;
                    bottom: 1rem;
                    font-size: 0.75rem;
                    opacity: 0.5;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">📚</div>
                <h1>{safe_topic}</h1>
                <p class="subtitle">
                    A quick 2-minute animated overview of <strong>{safe_topic}</strong>.<br>
                    Install the full AnimationEngine for richer, interactive content.
                </p>
                <div class="progress-bar">
                    <div class="progress-fill"></div>
                </div>
                <div class="meta">
                    <span class="badge">🎥 2 min</span>
                    <span class="badge">💾 Auto-generated</span>
                    <span class="badge">🌐 Luqi AI</span>
                </div>
            </div>
            <div class="footer">Luqi AI v24.5.0 — Limitless Telecoms</div>
        </body>
        </html>
        """
    )


# ═══════════════════════════════════════════════════════════════════
# Module load complete
# ═══════════════════════════════════════════════════════════════════

logger.info(
    "v25_animation_endpoints loaded — 7 convenience endpoints registered "
    "(/api/training/animated/*, /api/training/animate-lesson, "
    "/api/training/labs/*, /api/training/practical-exercise, "
    "/api/training/visual-aids, /api/training/quick-animation, "
    "/api/training/animation-status)"
)
