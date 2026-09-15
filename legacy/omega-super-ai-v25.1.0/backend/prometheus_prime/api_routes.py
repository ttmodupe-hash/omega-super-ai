"""api_routes.py — FastAPI Integration for Prometheus Prime.

Provides REST endpoints for feedback submission, status queries, report
generation, analysis triggering, knowledge-graph access, and more.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, Field

from .orchestrator_prime import PrometheusPrime

logger = logging.getLogger("prometheus_prime.api")

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class FeedbackRequest(BaseModel):
    """Explicit user feedback submission."""
    session_id: str = Field(..., description="Conversation identifier")
    rating: float = Field(..., ge=0, le=5, description="Star rating 0-5")
    comment: Optional[str] = Field(None, description="Optional free-form comment")


class ImplicitFeedbackRequest(BaseModel):
    """Implicit behavioural feedback for a session."""
    session_id: str = Field(..., description="Conversation identifier")
    follow_up_count: int = Field(0, ge=0, description="Number of user follow-up turns")
    response_time_ms: int = Field(0, ge=0, description="Response latency in milliseconds")
    user_corrected: int = Field(0, ge=0, le=1, description="1 if user corrected the response")
    response_copied: int = Field(0, ge=0, le=1, description="1 if user copied the response")
    session_duration_s: Optional[float] = Field(None, description="Total session duration in seconds")
    query_length: int = Field(0, ge=0, description="Character length of user query")
    response_length: int = Field(0, ge=0, description="Character length of assistant response")


class LearnRequest(BaseModel):
    """Request to trigger learning from a session."""
    session_id: str = Field(..., description="Conversation to learn from")
    query: str = Field("", description="User query (for recording new interaction)")
    response: str = Field("", description="Assistant response (for recording)")
    mode: str = Field("chat", description="Operating mode")
    duration_ms: int = Field(0, ge=0, description="Response generation time")
    user_feedback: Optional[float] = Field(None, ge=0, le=1, description="Optional quality score 0-1")


class TriggerRequest(BaseModel):
    """Request to trigger an analysis cycle."""
    cycle_type: str = Field("daily", description="Type of cycle: daily or weekly")


class GoalUpdateRequest(BaseModel):
    """Update progress on a strategic goal."""
    goal_id: int = Field(..., description="Goal ID")
    current_value: float = Field(..., description="New current value")


# ---------------------------------------------------------------------------
# Router factory
# ---------------------------------------------------------------------------


def create_router(prometheus: Optional[PrometheusPrime] = None) -> APIRouter:
    """Create and return the Prometheus Prime API router.

    Parameters
    ----------
    prometheus:
        An existing ``PrometheusPrime`` instance.  If ``None``, a new one
        is created lazily on first request.
    """
    router = APIRouter(prefix="/api/prometheus", tags=["prometheus"])
    _prometheus_ref: list[Optional[PrometheusPrime]] = [prometheus]

    def _get_prime() -> PrometheusPrime:
        if _prometheus_ref[0] is None:
            db_path = os.environ.get("PROMETHEUS_DB_PATH")
            _prometheus_ref[0] = PrometheusPrime(db_path=db_path)
        return _prometheus_ref[0]  # type: ignore[return-value]

    # ------------------------------------------------------------------ #
    # POST /api/prometheus/feedback
    # ------------------------------------------------------------------ #

    @router.post("/feedback", summary="Submit explicit user feedback")
    async def submit_feedback(request: FeedbackRequest) -> dict:
        """Submit a star rating and optional comment for a conversation."""
        try:
            prime = _get_prime()
            prime.feedback.collect_explicit_feedback(
                session_id=request.session_id,
                rating=request.rating,
                comment=request.comment,
            )
            # Calculate updated satisfaction
            satisfaction = prime.feedback.calculate_satisfaction_score(request.session_id)
            return {
                "status": "ok",
                "session_id": request.session_id,
                "rating": request.rating,
                "satisfaction_score": satisfaction,
            }
        except Exception as exc:
            logger.exception("Feedback submission failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    # ------------------------------------------------------------------ #
    # POST /api/prometheus/implicit-feedback
    # ------------------------------------------------------------------ #

    @router.post("/implicit-feedback", summary="Submit implicit behavioural feedback")
    async def submit_implicit_feedback(request: ImplicitFeedbackRequest) -> dict:
        """Submit behavioural signals derived from user interactions."""
        try:
            prime = _get_prime()
            result = prime.feedback.collect_implicit_feedback(
                session_id=request.session_id,
                interaction_data=request.model_dump(),
            )
            return {"status": "ok", **result}
        except Exception as exc:
            logger.exception("Implicit feedback submission failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    # ------------------------------------------------------------------ #
    # GET /api/prometheus/status
    # ------------------------------------------------------------------ #

    @router.get("/status", summary="Get Prometheus Prime system status")
    async def get_status() -> dict:
        """Return overall system health, learning stats, and capability scores."""
        try:
            return _get_prime().get_status()
        except Exception as exc:
            logger.exception("Status query failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    # ------------------------------------------------------------------ #
    # GET /api/prometheus/report
    # ------------------------------------------------------------------ #

    @router.get("/report", summary="Get improvement report")
    async def get_report(
        report_type: str = Query("daily", description="daily, weekly, monthly, or strategic"),
    ) -> dict:
        """Generate an improvement report of the specified type."""
        valid_types = {"daily", "weekly", "monthly", "strategic"}
        if report_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid report_type. Must be one of: {valid_types}",
            )
        try:
            report_text = _get_prime().get_report(report_type)
            return {"status": "ok", "report_type": report_type, "report": report_text}
        except Exception as exc:
            logger.exception("Report generation failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    # ------------------------------------------------------------------ #
    # POST /api/prometheus/trigger
    # ------------------------------------------------------------------ #

    @router.post("/trigger", summary="Trigger an analysis cycle")
    async def trigger_cycle(
        request: TriggerRequest,
        background_tasks: BackgroundTasks,
    ) -> dict:
        """Trigger a daily or weekly analysis cycle.

        The cycle runs in the background so the endpoint returns immediately.
        """
        cycle_type = request.cycle_type
        if cycle_type not in ("daily", "weekly"):
            raise HTTPException(status_code=400, detail="cycle_type must be 'daily' or 'weekly'")

        def _run_cycle() -> None:
            prime = _get_prime()
            if cycle_type == "daily":
                prime.daily_cycle()
            else:
                prime.weekly_cycle()

        background_tasks.add_task(_run_cycle)
        return {
            "status": "triggered",
            "cycle_type": cycle_type,
            "message": f"{cycle_type} cycle started in background",
        }

    # ------------------------------------------------------------------ #
    # GET /api/prometheus/knowledge
    # ------------------------------------------------------------------ #

    @router.get("/knowledge", summary="Get knowledge graph")
    async def get_knowledge_graph() -> dict:
        """Return the current knowledge graph (entities, relationships, clusters, gaps)."""
        try:
            graph = _get_prime().meta.build_knowledge_graph()
            return {"status": "ok", **graph}
        except Exception as exc:
            logger.exception("Knowledge graph query failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    # ------------------------------------------------------------------ #
    # GET /api/prometheus/roadmap
    # ------------------------------------------------------------------ #

    @router.get("/roadmap", summary="Get strategic roadmap")
    async def get_roadmap() -> dict:
        """Return the current strategic roadmap with goals and items."""
        try:
            roadmap = _get_prime().planner.create_roadmap()
            return {"status": "ok", **roadmap}
        except Exception as exc:
            logger.exception("Roadmap query failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    # ------------------------------------------------------------------ #
    # GET /api/prometheus/benchmarks
    # ------------------------------------------------------------------ #

    @router.get("/benchmarks", summary="Get benchmark history")
    async def get_benchmarks(
        mode: Optional[str] = Query(None, description="Filter by mode"),
        limit: int = Query(50, ge=1, le=200),
    ) -> dict:
        """Return recent interaction quality scores as benchmark data."""
        try:
            prime = _get_prime()
            with prime._lock:
                if mode:
                    rows = prime._conn.execute(
                        "SELECT mode, quality_score, timestamp FROM interactions "
                        "WHERE mode = ? ORDER BY timestamp DESC LIMIT ?",
                        (mode, limit),
                    ).fetchall()
                else:
                    rows = prime._conn.execute(
                        "SELECT mode, quality_score, timestamp FROM interactions "
                        "ORDER BY timestamp DESC LIMIT ?",
                        (limit,),
                    ).fetchall()

            benchmarks = [
                {
                    "mode": r["mode"],
                    "quality_score": r["quality_score"],
                    "timestamp": r["timestamp"],
                }
                for r in rows
            ]
            return {"status": "ok", "count": len(benchmarks), "benchmarks": benchmarks}
        except Exception as exc:
            logger.exception("Benchmark query failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    # ------------------------------------------------------------------ #
    # GET /api/prometheus/gaps
    # ------------------------------------------------------------------ #

    @router.get("/gaps", summary="Get capability gaps")
    async def get_capability_gaps() -> dict:
        """Return discovered capability gaps with patterns and suggested fixes."""
        try:
            gaps = _get_prime().meta.discover_capability_gaps()
            return {"status": "ok", "gap_count": len(gaps), "gaps": gaps}
        except Exception as exc:
            logger.exception("Capability gap query failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    # ------------------------------------------------------------------ #
    # POST /api/prometheus/learn
    # ------------------------------------------------------------------ #

    @router.post("/learn", summary="Trigger learning from a session")
    async def trigger_learning(request: LearnRequest) -> dict:
        """Record an interaction and trigger learning from a conversation session."""
        try:
            prime = _get_prime()
            result = prime.continuous_learning(
                session_id=request.session_id,
                query=request.query,
                response=request.response,
                mode=request.mode,
                duration_ms=request.duration_ms,
                user_feedback=request.user_feedback,
            )
            return {"status": "ok", **result}
        except Exception as exc:
            logger.exception("Learning trigger failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    # ------------------------------------------------------------------ #
    # GET /api/prometheus/goals
    # ------------------------------------------------------------------ #

    @router.get("/goals", summary="Get strategic goals")
    async def get_goals() -> dict:
        """Return all active strategic goals with progress."""
        try:
            progress = _get_prime().planner.track_goal_progress()
            return {"status": "ok", **progress}
        except Exception as exc:
            logger.exception("Goals query failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    # ------------------------------------------------------------------ #
    # POST /api/prometheus/goals/update
    # ------------------------------------------------------------------ #

    @router.post("/goals/update", summary="Update goal progress")
    async def update_goal_progress(request: GoalUpdateRequest) -> dict:
        """Update the current value of a strategic goal."""
        try:
            _get_prime().planner.update_goal_progress(request.goal_id, request.current_value)
            return {"status": "ok", "goal_id": request.goal_id, "new_value": request.current_value}
        except Exception as exc:
            logger.exception("Goal update failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    # ------------------------------------------------------------------ #
    # GET /api/prometheus/feedback/summary
    # ------------------------------------------------------------------ #

    @router.get("/feedback/summary", summary="Get feedback summary")
    async def get_feedback_summary(
        days: int = Query(7, ge=1, le=90),
    ) -> dict:
        """Return feedback summary for the specified period."""
        try:
            summary = _get_prime().feedback.get_feedback_summary(days=days)
            return {"status": "ok", **summary}
        except Exception as exc:
            logger.exception("Feedback summary failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    # ------------------------------------------------------------------ #
    # GET /api/prometheus/prompts/{mode}
    # ------------------------------------------------------------------ #

    @router.get("/prompts/{mode}", summary="Get prompt history for a mode")
    async def get_prompt_history(mode: str) -> dict:
        """Return the evolution history of system prompts for a given mode."""
        try:
            history = _get_prime().evolution.get_prompt_history(mode)
            return {"status": "ok", "mode": mode, "history": history}
        except Exception as exc:
            logger.exception("Prompt history query failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    # ------------------------------------------------------------------ #
    # POST /api/prometheus/prompts/{mode}/evolve
    # ------------------------------------------------------------------ #

    @router.post("/prompts/{mode}/evolve", summary="Evolve prompt for a mode")
    async def evolve_prompt(
        mode: str,
        background_tasks: BackgroundTasks,
        generations: int = Query(3, ge=1, le=10),
    ) -> dict:
        """Trigger prompt evolution for the specified mode."""
        def _run_evolution() -> None:
            _get_prime().evolution.evolve_prompt(mode, generations=generations)

        background_tasks.add_task(_run_evolution)
        return {
            "status": "triggered",
            "mode": mode,
            "generations": generations,
            "message": f"Prompt evolution for '{mode}' started in background",
        }

    # ------------------------------------------------------------------ #
    # GET /api/prometheus/failure-patterns
    # ------------------------------------------------------------------ #

    @router.get("/failure-patterns", summary="Get failure patterns")
    async def get_failure_patterns() -> dict:
        """Return identified failure patterns with suggested fixes."""
        try:
            patterns = _get_prime().feedback.identify_failure_patterns()
            return {"status": "ok", "pattern_count": len(patterns), "patterns": patterns}
        except Exception as exc:
            logger.exception("Failure pattern query failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return router


# Convenience: pre-built router (useful for simple imports)
router = create_router()
