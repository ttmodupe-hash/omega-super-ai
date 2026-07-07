"""Luqi AI v19 - Backend Package

A world-class AI system with multi-agent orchestration,
vector memory, real-time streaming, and advanced file processing.

Modules:
    config: Configuration management from environment variables
    ai_engine: OpenAI integration with streaming support
    search: Live web search with Serper and DuckDuckGo fallback
    memory: Vector memory using ChromaDB
    files: File upload and processing (PDF, images, text, docs)
    images: AI image generation with DALL-E 3
    agents: Multi-agent orchestration system
    router: FastAPI endpoints
    law_studies: Legal AI assistant with case law, contracts, bar prep
    companionship: Emotionally intelligent AI companion
"""

__version__ = "19.0.0"
__author__ = "Luqi AI"
__description__ = "World-class AI system with multi-agent orchestration, Law Studies, and emotional companionship"

from backend.config import load_backend_config

__all__ = ["load_backend_config"]
