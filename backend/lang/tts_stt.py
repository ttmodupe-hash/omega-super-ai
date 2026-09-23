# -*- coding: utf-8 -*-
"""
Luqi AI — Text-to-Speech and Speech-to-Text Engine

Voice support for 80+ languages using OpenAI TTS and Whisper APIs.
Handles language-specific voice preferences and accent handling.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, BinaryIO

from .african_languages import AFRICAN_LANGUAGES, GLOBAL_LANGUAGES, get_language_by_code


# OpenAI TTS voices with characteristics
TTS_VOICES: dict[str, str] = {
    "alloy": "Neutral, versatile voice",
    "echo": "Warm, conversational male voice",
    "fable": "Expressive, storytelling voice",
    "onyx": "Deep, authoritative male voice",
    "nova": "Friendly, upbeat female voice",
    "shimmer": "Clear, gentle female voice",
}

# Language to preferred voice mapping (cultural appropriateness)
LANGUAGE_VOICE_PREFERENCES: dict[str, str] = {
    # African languages - warm, clear voices preferred
    "zu": "onyx",       # Zulu - deep, respectful
    "xh": "onyx",       # Xhosa - deep, respectful
    "st": "echo",       # Sesotho - warm
    "tn": "echo",       # Setswana - warm
    "nso": "echo",      # Sepedi - warm
    "ts": "nova",       # Xitsonga - friendly
    "ve": "nova",       # Tshivenda - friendly
    "ss": "nova",       # Siswati - friendly
    "nr": "echo",       # Ndebele - warm
    "sn": "echo",       # Shona - warm
    "ny": "nova",       # Chichewa - friendly
    "sw": "onyx",       # Swahili - deep, authoritative
    "am": "echo",       # Amharic - warm
    "so": "echo",       # Somali - warm
    "om": "nova",       # Oromo - friendly
    "rw": "nova",       # Kinyarwanda - friendly
    "rn": "nova",       # Kirundi - friendly
    "lg": "echo",       # Luganda - warm
    "mg": "nova",       # Malagasy - friendly
    "ti": "echo",       # Tigrinya - warm
    "ha": "onyx",       # Hausa - deep
    "yo": "echo",       # Yoruba - warm
    "ig": "echo",       # Igbo - warm
    "ff": "onyx",       # Fulfulde - deep
    "ak": "echo",       # Akan - warm
    "ee": "nova",       # Ewe - friendly
    "wo": "onyx",       # Wolof - deep
    "bm": "echo",       # Bambara - warm
    "ln": "echo",       # Lingala - warm
    "kg": "echo",       # Kikongo - warm
    # Global languages
    "en": "alloy",      # English - neutral
    "fr": "shimmer",    # French - clear
    "es": "nova",       # Spanish - friendly
    "pt": "nova",       # Portuguese - friendly
    "zh": "shimmer",    # Chinese - clear
    "hi": "echo",       # Hindi - warm
    "ar": "onyx",       # Arabic - deep
    "de": "echo",       # German - warm
    "ja": "shimmer",    # Japanese - clear
    "ko": "shimmer",    # Korean - clear
    "ru": "onyx",       # Russian - deep
    "bn": "nova",       # Bengali - friendly
    # Default for other languages
    "default": "alloy",
}

# TTS models
TTS_MODEL = "tts-1"
TTS_MODEL_HD = "tts-1-hd"

# Whisper model
WHISPER_MODEL = "whisper-1"

# Whisper language codes mapping
WHISPER_CODE_MAP: dict[str, str] = {
    # Map internal codes to Whisper language codes
    "ar-eg": "ar",
    "x-sepitori": "nso",  # Sepitori (Pretoria Sotho): no Whisper support — route through Sepedi, its superstrate
    "ary": "ar",
    "kab": "kab",
    "shi": "shi",
    "ktu": "kg",
    "mos": "mos",
    "fan": "fan",
    "gaa": "gaa",
    "sgn": "sgn",
    "tbz": "tbz",
    "dz": "dz",
    "cjb": "sn",
    "sot": "st",
    "loz": "loz",
    "chw": "chw",
    "lua": "lu",
    "nym": "nym",
    "bez": "bez",
}


class VoiceEngine:
    """
    Text-to-Speech and Speech-to-Text engine for Luqi AI.

    Provides voice synthesis and speech recognition across 80+
    languages using OpenAI's TTS and Whisper APIs.

    Attributes:
        tts_model: OpenAI TTS model name.
        stt_model: OpenAI STT model name.
        api_key: OpenAI API key.
        client: OpenAI client instance (initialized on first use).
    """

    def __init__(
        self,
        api_key: str | None = None,
        tts_model: str = TTS_MODEL,
        stt_model: str = WHISPER_MODEL,
    ) -> None:
        """
        Initialize the voice engine.

        Args:
            api_key: OpenAI API key (defaults to env var).
            tts_model: TTS model to use.
            stt_model: Whisper model to use.
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.tts_model = tts_model
        self.stt_model = stt_model
        self._client = None
        self.all_languages = {**AFRICAN_LANGUAGES, **GLOBAL_LANGUAGES}

    @property
    def client(self):
        """Lazy-initialize OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise RuntimeError("OpenAI package not installed")
        return self._client

    def get_preferred_voice(self, lang_code: str) -> str:
        """
        Get the preferred voice for a language.

        Args:
            lang_code: Language ISO code.

        Returns:
            Voice name string.
        """
        voice = LANGUAGE_VOICE_PREFERENCES.get(lang_code)
        if voice is None:
            # Check if there's a base language code match
            base_code = lang_code.split("-")[0]
            voice = LANGUAGE_VOICE_PREFERENCES.get(base_code, "alloy")
        return voice

    def get_language_whisper_code(self, lang_code: str) -> str:
        """
        Get the Whisper language code for a given language code.

        Args:
            lang_code: Internal language code.

        Returns:
            Whisper-compatible language code.
        """
        # Check direct mapping
        whisper_code = WHISPER_CODE_MAP.get(lang_code)
        if whisper_code:
            return whisper_code

        # Check base code
        base_code = lang_code.split("-")[0]

        # Check if base code is directly in Whisper's supported languages
        return base_code

    def get_supported_languages(self) -> list[dict[str, str]]:
        """
        Get list of languages supported by the voice engine.

        Returns:
            List of language info dictionaries.
        """
        result = []
        for code, info in self.all_languages.items():
            result.append({
                "code": code,
                "name": info.get("name", code),
                "english_name": info.get("english_name", code),
                "whisper_code": self.get_language_whisper_code(code),
                "tts_voice": self.get_preferred_voice(code),
                "script": info.get("script", "Latin"),
            })
        return sorted(result, key=lambda x: x["name"])

    def is_language_supported(self, lang_code: str) -> bool:
        """
        Check if a language is supported by the voice engine.

        Args:
            lang_code: Language code to check.

        Returns:
            True if supported, False otherwise.
        """
        return lang_code in self.all_languages


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================
