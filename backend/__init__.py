"""Luqi AI v20 - Backend Package

A world-class AI system serving Africa and the world.
Multi-agent orchestration, ASI cognitive engine, SaaS platform,
Law Studies, Africa-First capabilities, and 195+ endpoints.

Modules:
    config: Configuration management
    router: FastAPI application with all endpoints
    chat: AI chat with streaming
    memory: Vector memory system
    search: Web search
    developer: Code generation in 25 languages
    website_builder: Website generation
    education_system: K-PhD digital twin tutor
    cognitive_engine: Multi-agent hive mind
    voice_system: 92-language TTS/STT
    safety_alignment: Red-teaming
    physics_simulator: 172 compounds
    captainship: Project management
    companionship: Emotional AI friendship
    automotive: Vehicle diagnostics
    writing_assistant: Grammar and style
    law_studies: Legal research, case briefing, bar exam
    agricultural_advisor: African farming guidance
    healthcare_assistant: Health info for Africa
    teacher_assistant: Lesson plans for Africa
    business_advisor: Entrepreneurship for Africa
    offline_engine: Offline/SMS capability
"""

__version__ = "20.0.0"
__author__ = "Luqi AI"
__description__ = "World-class AI system serving Africa and the world"

from backend.config import load_backend_config

__all__ = ["load_backend_config"]
