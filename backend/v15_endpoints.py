"""Luqi AI v15 — ASI Cognitive Endpoints

Multi-agent hive mind, cross-domain synthesis, adaptive education,
voice system, safety alignment, and physics simulation endpoints.

Import in router.py to activate all v15 endpoints.
"""

import json
import logging
from typing import Optional

from fastapi import HTTPException, Query, Request
from fastapi.responses import JSONResponse

from backend.router import app

logger = logging.getLogger(__name__)

# Auth helper (shared with v14)
def _get_user_id(request: Request) -> str:
    """Extract user_id from API key."""
    api_key = request.headers.get("X-API-Key", "anonymous")
    try:
        from backend.subscriptions import get_user_id
        return get_user_id(api_key)
    except Exception:
        import hashlib
        return hashlib.sha256(api_key.encode()).hexdigest()[:16]


# ═══════════════════════════════════════════════════════════════════
# v15: COGNITIVE ENGINE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/cognitive/think")
async def api_cognitive_think(request: Request):
    """Multi-agent hive mind deliberation on a question."""
    try:
        from backend.cognitive_engine import HiveMind, SubAgent
        data = json.loads(await request.body())
        question = data.get("question", "")
        agents_config = data.get("agents", ["researcher", "critic", "creative", "logician"])
        depth = data.get("depth", "standard")
        
        agents = [SubAgent(role=r) for r in agents_config]
        hive = HiveMind(agents=agents)
        result = hive.deliberate(question)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Cognitive think error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cognitive/synthesize")
async def api_cognitive_synthesize(request: Request):
    """Cross-domain synthesis: map concepts between fields."""
    try:
        from backend.cognitive_engine import cross_domain_synthesize
        data = json.loads(await request.body())
        result = cross_domain_synthesize(
            concept=data.get("concept", ""),
            from_domain=data.get("from_domain", ""),
            to_domain=data.get("to_domain", ""),
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Cognitive synthesize error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cognitive/analogy")
async def api_cognitive_analogy(request: Request):
    """Generate analogy between two domains."""
    try:
        from backend.cognitive_engine import generate_analogy
        data = json.loads(await request.body())
        result = generate_analogy(
            concept=data.get("concept", ""),
            source_domain=data.get("source_domain", ""),
            target_domain=data.get("target_domain", ""),
            tier=data.get("tier", "middle"),
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Cognitive analogy error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cognitive/metacognition")
async def api_cognitive_metacognition(request: Request):
    """Metacognitive analysis of reasoning."""
    try:
        from backend.cognitive_engine import metacognition_reflect, detect_fallacies, calibrate_confidence
        data = json.loads(await request.body())
        reasoning = data.get("reasoning", "")
        
        reflection = metacognition_reflect(reasoning)
        fallacies = detect_fallacies(reasoning)
        confidence = calibrate_confidence([reasoning])
        
        return JSONResponse({
            "reflection": reflection,
            "fallacies": fallacies,
            "confidence": confidence,
        })
    except Exception as e:
        logger.error("Cognitive metacognition error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cognitive/debate")
async def api_cognitive_debate(request: Request):
    """Run a multi-agent debate on a topic."""
    try:
        from backend.cognitive_engine import HiveMind, SubAgent
        data = json.loads(await request.body())
        topic = data.get("topic", "")
        perspectives = data.get("perspectives", ["pro", "con", "neutral"])
        
        agents = [SubAgent(role=p) for p in perspectives]
        hive = HiveMind(agents=agents)
        result = hive.deliberate(topic)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Cognitive debate error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cognitive/domains")
async def api_cognitive_domains():
    """List all available knowledge domains."""
    try:
        from backend.cognitive_engine import get_domains
        return JSONResponse({"domains": get_domains()})
    except Exception as e:
        logger.error("Cognitive domains error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# v15: EDUCATION SYSTEM ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/education/tutor")
async def api_education_tutor(request: Request):
    """Adaptive tutoring session with Socratic dialogue."""
    try:
        from backend.education_system import SocraticDialogue, StudentProfile
        data = json.loads(await request.body())
        student_data = data.get("student", {})
        concept = data.get("concept", "")
        student_answer = data.get("answer", "")
        
        profile = StudentProfile(**student_data) if student_data else StudentProfile(user_id="guest")
        dialogue = SocraticDialogue(student_profile=profile)
        
        result = dialogue.ask_guiding_question(student_answer, "", concept)
        return JSONResponse({"guidance": result, "concept": concept})
    except Exception as e:
        logger.error("Education tutor error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/education/explain")
async def api_education_explain(request: Request):
    """Multi-tiered explanation of a concept."""
    try:
        from backend.education_system import explain_concept, explain_with_interest, StudentProfile
        data = json.loads(await request.body())
        concept = data.get("concept", "")
        tier = data.get("tier", "middle")
        interest = data.get("interest", "")
        student_data = data.get("student", {})
        profile = StudentProfile(**student_data) if student_data else StudentProfile(user_id="guest")
        
        if interest:
            result = explain_with_interest(concept, interest, tier)
        else:
            result = explain_concept(concept, tier, profile)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Education explain error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/education/profile")
async def api_education_profile(request: Request):
    """Get student learning profile."""
    try:
        from backend.education_system import StudentProfile
        user_id = _get_user_id(request)
        profile = StudentProfile(user_id=user_id)
        return JSONResponse(profile.to_dict())
    except Exception as e:
        logger.error("Education profile error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/education/assess")
async def api_education_assess(request: Request):
    """Knowledge assessment for a topic."""
    try:
        from backend.education_system import KnowledgeMap
        data = json.loads(await request.body())
        topic = data.get("topic", "")
        user_id = _get_user_id(request)
        
        km = KnowledgeMap()
        result = km.assess_mastery(user_id, topic)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Education assess error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/education/simulate")
async def api_education_simulate(request: Request):
    """Generate a virtual learning simulation."""
    try:
        from backend.education_system import generate_simulation
        data = json.loads(await request.body())
        result = generate_simulation(
            topic=data.get("topic", ""),
            age_group=data.get("age_group", "child"),
            interests=data.get("interests", []),
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Education simulate error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/education/curriculum")
async def api_education_curriculum(subject: str, request: Request):
    """Get personalized curriculum for a subject."""
    try:
        from backend.education_system import CurriculumEngine, StudentProfile
        user_id = _get_user_id(request)
        profile = StudentProfile(user_id=user_id)
        engine = CurriculumEngine()
        result = engine.generate_curriculum(subject, profile)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Education curriculum error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/education/tiers")
async def api_education_tiers():
    """List available explanation tiers."""
    try:
        from backend.education_system import get_explanation_tiers
        return JSONResponse({"tiers": get_explanation_tiers()})
    except Exception as e:
        logger.error("Education tiers error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/education/practice")
async def api_education_practice(request: Request):
    """Generate practice problems."""
    try:
        from backend.education_system import generate_practice_problems
        data = json.loads(await request.body())
        result = generate_practice_problems(
            topic=data.get("topic", ""),
            difficulty=data.get("difficulty", "medium"),
            count=data.get("count", 5),
        )
        return JSONResponse({"problems": result})
    except Exception as e:
        logger.error("Education practice error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# v15: VOICE SYSTEM ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/voice/voices")
async def api_voice_voices(language: Optional[str] = None):
    """List available voices."""
    try:
        from backend.voice_system import get_voices
        return JSONResponse({"voices": get_voices(language)})
    except Exception as e:
        logger.error("Voice voices error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/voice/speak")
async def api_voice_speak(request: Request):
    """Text-to-speech conversion."""
    try:
        from backend.voice_system import text_to_speech
        data = json.loads(await request.body())
        result = text_to_speech(
            text=data.get("text", ""),
            language=data.get("language", "en"),
            voice_id=data.get("voice_id", ""),
            speed=data.get("speed", 1.0),
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Voice speak error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/voice/cloning/setup")
async def api_voice_cloning_setup(request: Request):
    """Setup a voice clone from audio samples."""
    try:
        from backend.voice_system import VoiceCloner
        data = json.loads(await request.body())
        user_id = _get_user_id(request)
        cloner = VoiceCloner()
        result = cloner.register_voice(
            name=data.get("name", ""),
            audio_samples=data.get("samples", []),
            user_id=user_id,
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Voice cloning setup error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/voice/cloning/speak")
async def api_voice_cloning_speak(request: Request):
    """Speak in a cloned voice."""
    try:
        from backend.voice_system import VoiceCloner
        data = json.loads(await request.body())
        cloner = VoiceCloner()
        result = cloner.speak_with_voice(
            text=data.get("text", ""),
            voice_id=data.get("voice_id", ""),
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Voice cloning speak error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/voice/transcribe")
async def api_voice_transcribe(request: Request):
    """Speech-to-text transcription."""
    try:
        from backend.voice_system import speech_to_text
        data = json.loads(await request.body())
        import base64
        audio_data = base64.b64decode(data.get("audio", ""))
        result = speech_to_text(audio_data, data.get("language", "en"))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Voice transcribe error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/voice/commands")
async def api_voice_commands(request: Request):
    """Detect voice commands in transcript."""
    try:
        from backend.voice_system import detect_voice_commands
        data = json.loads(await request.body())
        result = detect_voice_commands(data.get("transcript", ""))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Voice commands error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# v15: SAFETY & ALIGNMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/safety/check")
async def api_safety_check(request: Request):
    """Safety check on content."""
    try:
        from backend.safety_alignment import safety_check
        data = json.loads(await request.body())
        result = safety_check(data.get("content", ""), data.get("context", ""))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Safety check error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/safety/redteam")
async def api_safety_redteam(request: Request):
    """Run automated red-team analysis."""
    try:
        from backend.safety_alignment import RedTeamEngine
        data = json.loads(await request.body())
        engine = RedTeamEngine()
        result = engine.run_full_audit()
        return JSONResponse(result)
    except Exception as e:
        logger.error("Safety redteam error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/safety/interpret")
async def api_safety_interpret(request: Request):
    """Interpret reasoning chain for transparency."""
    try:
        from backend.safety_alignment import interpret_reasoning
        data = json.loads(await request.body())
        result = interpret_reasoning(data.get("prompt", ""), data.get("response", ""))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Safety interpret error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/safety/score")
async def api_safety_score(response: str):
    """Get alignment score for a response."""
    try:
        from backend.safety_alignment import alignment_score
        result = alignment_score(response)
        return JSONResponse(result)
    except Exception as e:
        logger.error("Safety score error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/safety/principles")
async def api_safety_principles():
    """List ethical principles."""
    try:
        from backend.safety_alignment import ETHICAL_PRINCIPLES, VALUE_ANCHORS
        return JSONResponse({
            "principles": ETHICAL_PRINCIPLES,
            "value_anchors": VALUE_ANCHORS,
        })
    except Exception as e:
        logger.error("Safety principles error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# v15: PHYSICS SIMULATOR ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/physics/simulate")
async def api_physics_simulate(request: Request):
    """Run a physics simulation."""
    try:
        from backend.physics_simulator import PhysicsEngine
        data = json.loads(await request.body())
        engine = PhysicsEngine()
        sim_type = data.get("type", "projectile")
        
        if sim_type == "projectile":
            result = engine.simulate_projectile(
                data.get("velocity", 10),
                data.get("angle", 45),
                data.get("gravity", 9.81),
                data.get("drag", 0),
            )
        elif sim_type == "pendulum":
            result = engine.simulate_pendulum(
                data.get("length", 1.0),
                data.get("mass", 1.0),
                data.get("gravity", 9.81),
                data.get("damping", 0),
            )
        elif sim_type == "orbital":
            result = engine.simulate_orbital_mechanics(data.get("bodies", []))
        elif sim_type == "wave":
            result = engine.simulate_wave(
                data.get("amplitude", 1.0),
                data.get("frequency", 1.0),
                data.get("wavelength", 2.0),
                data.get("medium", "air"),
            )
        elif sim_type == "ohms":
            result = engine.simulate_ohms_law(
                data.get("voltage", 12),
                data.get("resistance", 100),
            )
        elif sim_type == "gas":
            result = engine.simulate_gas_laws(
                data.get("P"), data.get("V"),
                data.get("n"), data.get("T"),
            )
        elif sim_type == "doppler":
            result = engine.simulate_doppler(
                data.get("f0", 440),
                data.get("v_source", 0),
                data.get("v_observer", 0),
            )
        else:
            result = {"error": f"Unknown simulation type: {sim_type}"}
        
        return JSONResponse({"type": sim_type, **result})
    except Exception as e:
        logger.error("Physics simulate error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/physics/hypothesis")
async def api_physics_hypothesis(request: Request):
    """Generate and evaluate a scientific hypothesis."""
    try:
        from backend.physics_simulator import HypothesisEngine
        data = json.loads(await request.body())
        engine = HypothesisEngine()
        result = engine.generate_hypothesis(
            domain=data.get("domain", ""),
            observation=data.get("observation", ""),
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Physics hypothesis error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/physics/compound")
async def api_physics_compound(request: Request):
    """Analyze or generate a chemical compound."""
    try:
        from backend.physics_simulator import MolecularSimulator
        data = json.loads(await request.body())
        engine = MolecularSimulator()
        
        if data.get("formula"):
            result = engine.predict_properties(data["formula"])
        elif data.get("target_properties"):
            result = engine.generate_hypothetical_compound(data["target_properties"])
        else:
            result = {"error": "Provide formula or target_properties"}
        
        return JSONResponse(result)
    except Exception as e:
        logger.error("Physics compound error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/physics/calculate")
async def api_physics_calculate(request: Request):
    """Scientific calculator with physics constants."""
    try:
        from backend.physics_simulator import scientific_calculate
        data = json.loads(await request.body())
        result = scientific_calculate(data.get("expression", ""))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Physics calculate error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/physics/convert")
async def api_physics_convert(request: Request):
    """Unit conversion."""
    try:
        from backend.physics_simulator import unit_convert
        data = json.loads(await request.body())
        result = unit_convert(
            data.get("value", 0),
            data.get("from", ""),
            data.get("to", ""),
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Physics convert error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/physics/constants")
async def api_physics_constants():
    """Get physics constants."""
    try:
        from backend.physics_simulator import PHYSICS_CONSTANTS
        return JSONResponse({"constants": PHYSICS_CONSTANTS})
    except Exception as e:
        logger.error("Physics constants error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


logger.info("v15 endpoints loaded: cognitive(6), education(8), voice(6), safety(5), physics(6) = 31 new endpoints")
