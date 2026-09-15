# -*- coding: utf-8 -*-
"""
Luqi AI — Universal Language System

Comprehensive multilingual support for 50+ African languages and 30+
global languages. Provides language detection, routing, translation, TTS/STT, and cultural context.

Modules:
    african_languages: Language databases (AFRICAN_LANGUAGES, GLOBAL_LANGUAGES)
    language_detector: Language detection and routing (LanguageDetector)
    multilingual_router: Multilingual response routing (MultilingualRouter)
    tts_stt: Voice engine for speech synthesis and recognition (VoiceEngine)
    tests: Self-test suite

Usage:
    from lang import LanguageDetector, MultilingualRouter, VoiceEngine
    from lang.african_languages import AFRICAN_LANGUAGES, GLOBAL_LANGUAGES
"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "Luqi AI"
__all__ = [
    "AFRICAN_LANGUAGES",
    "GLOBAL_LANGUAGES",
    "LanguageDetector",
    "MultilingualRouter",
    "VoiceEngine",
    "get_all_languages",
    "get_languages_by_country",
    "get_languages_by_region",
    "get_languages_by_family",
]


def get_all_languages() -> dict[str, dict]:
    """Return combined dictionary of all African and global languages."""
    from lang.african_languages import AFRICAN_LANGUAGES, GLOBAL_LANGUAGES
    combined = {}
    combined.update(AFRICAN_LANGUAGES)
    combined.update(GLOBAL_LANGUAGES)
    return combined


def get_languages_by_country(country: str) -> dict[str, dict]:
    """Return all languages spoken in a given country."""
    from lang.african_languages import AFRICAN_LANGUAGES
    result = {}
    search = country.lower()
    for code, info in AFRICAN_LANGUAGES.items():
        if any(search in c.lower() for c in info.get("countries", [])):
            result[code] = info
    return result


def get_languages_by_region(region: str) -> dict[str, dict]:
    """Return all languages in a given African region."""
    from lang.african_languages import AFRICAN_LANGUAGES
    result = {}
    search = region.lower()
    for code, info in AFRICAN_LANGUAGES.items():
        if search in info.get("region", "").lower():
            result[code] = info
    return result


def get_languages_by_family(family: str) -> dict[str, dict]:
    """Return all languages in a given language family."""
    from lang.african_languages import AFRICAN_LANGUAGES
    result = {}
    search = family.lower()
    for code, info in AFRICAN_LANGUAGES.items():
        if search in info.get("language_family", "").lower():
            result[code] = info
    return result
