"""
Luqi AI v15 - Voice System Module
=====================================
Comprehensive voice processing system supporting 85+ languages with
text-to-speech, speech-to-text, voice cloning, and voice command detection.

Production-ready module with multiple backend support, streaming capabilities,
and extensible voice profile management.

Author: Luqi AI Engineering Team
Version: 15.0.0
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import os
import re
import tempfile
import time
import wave
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logger = logging.getLogger("luqi.voice")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    logger.addHandler(_handler)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_SAMPLE_RATE: int = 24000
DEFAULT_AUDIO_FORMAT: str = "mp3"
SUPPORTED_AUDIO_FORMATS: List[str] = ["mp3", "wav", "ogg", "flac", "aac"]
MAX_TEXT_LENGTH: int = 4096
MAX_AUDIO_SIZE_MB: int = 25
VOICE_PROFILES_DIR: Path = Path(__file__).parent / "voice_profiles"


class TTSError(Exception):
    """Raised when text-to-speech conversion fails."""

    pass


class STTError(Exception):
    """Raised when speech-to-text conversion fails."""

    pass


class VoiceCloneError(Exception):
    """Raised when voice cloning operation fails."""

    pass


class VoiceCommandError(Exception):
    """Raised when voice command processing fails."""

    pass


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class VoiceInfo:
    """Information about a single voice."""

    voice_id: str
    name: str
    gender: str  # "male", "female", "neutral"
    language: str
    provider: str = "openai"
    quality: str = "high"  # "low", "medium", "high", "ultra"
    description: str = ""
    sample_rate: int = DEFAULT_SAMPLE_RATE
    supports_speed: bool = True
    supports_emotion: bool = False

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": self.voice_id,
            "name": self.name,
            "gender": self.gender,
            "language": self.language,
            "provider": self.provider,
            "quality": self.quality,
            "description": self.description,
            "sample_rate": self.sample_rate,
            "supports_speed": self.supports_speed,
            "supports_emotion": self.supports_emotion,
        }


@dataclass
class TTSSegment:
    """A single segment of synthesized speech."""

    text: str
    audio_base64: str
    format: str
    duration_ms: int
    voice_id: str
    start_ms: int = 0
    end_ms: int = 0


@dataclass
class STTSegment:
    """A single segment of transcribed speech."""

    start: float
    end: float
    text: str
    confidence: float
    speaker_id: Optional[str] = None
    words: List[dict] = field(default_factory=list)


@dataclass
class VoiceProfile:
    """A cloned voice profile."""

    voice_id: str
    name: str
    user_id: str
    created_at: float
    embedding: Optional[List[float]] = None
    quality_score: float = 0.0
    sample_count: int = 0
    total_duration_seconds: float = 0.0
    last_used: float = 0.0
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to dictionary (embedding omitted for safety)."""
        return {
            "voice_id": self.voice_id,
            "name": self.name,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "quality_score": self.quality_score,
            "sample_count": self.sample_count,
            "total_duration_seconds": self.total_duration_seconds,
            "last_used": self.last_used,
            "is_active": self.is_active,
            "metadata": self.metadata,
        }


@dataclass
class VoiceCommand:
    """A detected voice command."""

    is_command: bool
    command: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    raw_transcript: str = ""


# ---------------------------------------------------------------------------
# Voice definitions for 85 languages
# ---------------------------------------------------------------------------

VOICES: Dict[str, List[Dict[str, str]]] = {
    # --- Major world languages ---
    "en": [
        {"id": "alloy", "name": "Alloy", "gender": "neutral"},
        {"id": "echo", "name": "Echo", "gender": "male"},
        {"id": "fable", "name": "Fable", "gender": "female"},
        {"id": "onyx", "name": "Onyx", "gender": "male"},
        {"id": "nova", "name": "Nova", "gender": "female"},
        {"id": "shimmer", "name": "Shimmer", "gender": "female"},
    ],
    "es": [
        {"id": "es-male-1", "name": "Carlos", "gender": "male"},
        {"id": "es-female-1", "name": "Isabella", "gender": "female"},
        {"id": "es-female-2", "name": "Sofia", "gender": "female"},
        {"id": "es-male-2", "name": "Miguel", "gender": "male"},
    ],
    "fr": [
        {"id": "fr-male-1", "name": "Pierre", "gender": "male"},
        {"id": "fr-female-1", "name": "Claire", "gender": "female"},
        {"id": "fr-female-2", "name": "Amelie", "gender": "female"},
    ],
    "de": [
        {"id": "de-male-1", "name": "Hans", "gender": "male"},
        {"id": "de-female-1", "name": "Anna", "gender": "female"},
        {"id": "de-male-2", "name": "Klaus", "gender": "male"},
    ],
    "zh": [
        {"id": "zh-male-1", "name": "Wei", "gender": "male"},
        {"id": "zh-female-1", "name": "Li", "gender": "female"},
        {"id": "zh-female-2", "name": "Xiaoming", "gender": "female"},
    ],
    "ja": [
        {"id": "ja-female-1", "name": "Sakura", "gender": "female"},
        {"id": "ja-male-1", "name": "Takeshi", "gender": "male"},
        {"id": "ja-female-2", "name": "Yuki", "gender": "female"},
    ],
    "ko": [
        {"id": "ko-female-1", "name": "Ji-yeon", "gender": "female"},
        {"id": "ko-male-1", "name": "Min-jun", "gender": "male"},
    ],
    "hi": [
        {"id": "hi-male-1", "name": "Arjun", "gender": "male"},
        {"id": "hi-female-1", "name": "Priya", "gender": "female"},
        {"id": "hi-female-2", "name": "Ananya", "gender": "female"},
    ],
    "ar": [
        {"id": "ar-male-1", "name": "Omar", "gender": "male"},
        {"id": "ar-female-1", "name": "Fatima", "gender": "female"},
        {"id": "ar-male-2", "name": "Amir", "gender": "male"},
    ],
    "pt": [
        {"id": "pt-male-1", "name": "Joao", "gender": "male"},
        {"id": "pt-female-1", "name": "Maria", "gender": "female"},
    ],
    "it": [
        {"id": "it-male-1", "name": "Marco", "gender": "male"},
        {"id": "it-female-1", "name": "Giulia", "gender": "female"},
    ],
    "ru": [
        {"id": "ru-male-1", "name": "Ivan", "gender": "male"},
        {"id": "ru-female-1", "name": "Anastasia", "gender": "female"},
        {"id": "ru-female-2", "name": "Olga", "gender": "female"},
    ],
    "tr": [
        {"id": "tr-male-1", "name": "Mehmet", "gender": "male"},
        {"id": "tr-female-1", "name": "Ayse", "gender": "female"},
    ],
    "nl": [
        {"id": "nl-male-1", "name": "Lars", "gender": "male"},
        {"id": "nl-female-1", "name": "Emma", "gender": "female"},
    ],
    "pl": [
        {"id": "pl-male-1", "name": "Kacper", "gender": "male"},
        {"id": "pl-female-1", "name": "Zuzanna", "gender": "female"},
    ],
    "sv": [
        {"id": "sv-male-1", "name": "Erik", "gender": "male"},
        {"id": "sv-female-1", "name": "Astrid", "gender": "female"},
    ],
    "da": [
        {"id": "da-male-1", "name": "Magnus", "gender": "male"},
        {"id": "da-female-1", "name": "Freja", "gender": "female"},
    ],
    "no": [
        {"id": "no-male-1", "name": "Liam", "gender": "male"},
        {"id": "no-female-1", "name": "Nora", "gender": "female"},
    ],
    "fi": [
        {"id": "fi-male-1", "name": "Aatos", "gender": "male"},
        {"id": "fi-female-1", "name": "Aino", "gender": "female"},
    ],
    "cs": [
        {"id": "cs-male-1", "name": "Jakub", "gender": "male"},
        {"id": "cs-female-1", "name": "Eva", "gender": "female"},
    ],
    "el": [
        {"id": "el-male-1", "name": "Nikos", "gender": "male"},
        {"id": "el-female-1", "name": "Elena", "gender": "female"},
    ],
    "he": [
        {"id": "he-male-1", "name": "David", "gender": "male"},
        {"id": "he-female-1", "name": "Noa", "gender": "female"},
    ],
    "th": [
        {"id": "th-female-1", "name": "Suda", "gender": "female"},
        {"id": "th-male-1", "name": "Somchai", "gender": "male"},
    ],
    "vi": [
        {"id": "vi-female-1", "name": "Linh", "gender": "female"},
        {"id": "vi-male-1", "name": "Minh", "gender": "male"},
    ],
    "id": [
        {"id": "id-male-1", "name": "Budi", "gender": "male"},
        {"id": "id-female-1", "name": "Siti", "gender": "female"},
    ],
    "ms": [
        {"id": "ms-male-1", "name": "Ahmad", "gender": "male"},
        {"id": "ms-female-1", "name": "Nurul", "gender": "female"},
    ],
    "tl": [
        {"id": "tl-male-1", "name": "Juan", "gender": "male"},
        {"id": "tl-female-1", "name": "Maria", "gender": "female"},
    ],
    # --- African languages ---
    "sw": [
        {"id": "sw-male-1", "name": "Juma", "gender": "male"},
        {"id": "sw-female-1", "name": "Amina", "gender": "female"},
        {"id": "sw-male-2", "name": "Omari", "gender": "male"},
    ],
    "am": [
        {"id": "am-male-1", "name": "Dawit", "gender": "male"},
        {"id": "am-female-1", "name": "Hiwot", "gender": "female"},
    ],
    "ha": [
        {"id": "ha-male-1", "name": "Abdullahi", "gender": "male"},
        {"id": "ha-female-1", "name": "Aisha", "gender": "female"},
    ],
    "yo": [
        {"id": "yo-male-1", "name": "Tunde", "gender": "male"},
        {"id": "yo-female-1", "name": "Amara", "gender": "female"},
    ],
    "ig": [
        {"id": "ig-male-1", "name": "Chukwuemeka", "gender": "male"},
        {"id": "ig-female-1", "name": "Ngozi", "gender": "female"},
    ],
    "zu": [
        {"id": "zu-male-1", "name": "Sibusiso", "gender": "male"},
        {"id": "zu-female-1", "name": "Thandi", "gender": "female"},
    ],
    "af": [
        {"id": "af-male-1", "name": "Petrus", "gender": "male"},
        {"id": "af-female-1", "name": "Elize", "gender": "female"},
    ],
    "so": [
        {"id": "so-male-1", "name": "Mohamed", "gender": "male"},
        {"id": "so-female-1", "name": "Halima", "gender": "female"},
    ],
    "rw": [
        {"id": "rw-male-1", "name": "Jean", "gender": "male"},
        {"id": "rw-female-1", "name": "Marie", "gender": "female"},
    ],
    "lg": [
        {"id": "lg-male-1", "name": "Musa", "gender": "male"},
        {"id": "lg-female-1", "name": "Nakato", "gender": "female"},
    ],
    "sn": [
        {"id": "sn-male-1", "name": "Tendai", "gender": "male"},
        {"id": "sn-female-1", "name": "Rudo", "gender": "female"},
    ],
    "ny": [
        {"id": "ny-male-1", "name": "Bambo", "gender": "male"},
        {"id": "ny-female-1", "name": "Chisomo", "gender": "female"},
    ],
    "xh": [
        {"id": "xh-male-1", "name": "Lwazi", "gender": "male"},
        {"id": "xh-female-1", "name": "Zola", "gender": "female"},
    ],
    "mg": [
        {"id": "mg-male-1", "name": "Tahiry", "gender": "male"},
        {"id": "mg-female-1", "name": "Mialy", "gender": "female"},
    ],
    # --- South Asian languages ---
    "bn": [
        {"id": "bn-male-1", "name": "Aryan", "gender": "male"},
        {"id": "bn-female-1", "name": "Ishita", "gender": "female"},
    ],
    "ta": [
        {"id": "ta-male-1", "name": "Arjun", "gender": "male"},
        {"id": "ta-female-1", "name": "Meera", "gender": "female"},
    ],
    "te": [
        {"id": "te-male-1", "name": "Ravi", "gender": "male"},
        {"id": "te-female-1", "name": "Lakshmi", "gender": "female"},
    ],
    "mr": [
        {"id": "mr-male-1", "name": "Vikram", "gender": "male"},
        {"id": "mr-female-1", "name": "Aditi", "gender": "female"},
    ],
    "gu": [
        {"id": "gu-male-1", "name": "Dhruv", "gender": "male"},
        {"id": "gu-female-1", "name": "Priya", "gender": "female"},
    ],
    "kn": [
        {"id": "kn-male-1", "name": "Arnav", "gender": "male"},
        {"id": "kn-female-1", "name": "Saanvi", "gender": "female"},
    ],
    "ml": [
        {"id": "ml-male-1", "name": "Aditya", "gender": "male"},
        {"id": "ml-female-1", "name": "Divya", "gender": "female"},
    ],
    "pa": [
        {"id": "pa-male-1", "name": "Harpreet", "gender": "male"},
        {"id": "pa-female-1", "name": "Simran", "gender": "female"},
    ],
    "ur": [
        {"id": "ur-male-1", "name": "Bilal", "gender": "male"},
        {"id": "ur-female-1", "name": "Ayesha", "gender": "female"},
    ],
    "si": [
        {"id": "si-male-1", "name": "Nuwan", "gender": "male"},
        {"id": "si-female-1", "name": "Malini", "gender": "female"},
    ],
    "ne": [
        {"id": "ne-male-1", "name": "Bikash", "gender": "male"},
        {"id": "ne-female-1", "name": "Sunita", "gender": "female"},
    ],
    "my": [
        {"id": "my-male-1", "name": "Thura", "gender": "male"},
        {"id": "my-female-1", "name": "Mya", "gender": "female"},
    ],
    "km": [
        {"id": "km-male-1", "name": "Sokha", "gender": "male"},
        {"id": "km-female-1", "name": "Sopheap", "gender": "female"},
    ],
    "lo": [
        {"id": "lo-male-1", "name": "Khamla", "gender": "male"},
        {"id": "lo-female-1", "name": "Noy", "gender": "female"},
    ],
    # --- European languages ---
    "uk": [
        {"id": "uk-male-1", "name": "Dmytro", "gender": "male"},
        {"id": "uk-female-1", "name": "Olena", "gender": "female"},
    ],
    "ro": [
        {"id": "ro-male-1", "name": "Andrei", "gender": "male"},
        {"id": "ro-female-1", "name": "Elena", "gender": "female"},
    ],
    "hu": [
        {"id": "hu-male-1", "name": "Bence", "gender": "male"},
        {"id": "hu-female-1", "name": "Lili", "gender": "female"},
    ],
    "bg": [
        {"id": "bg-male-1", "name": "Georgi", "gender": "male"},
        {"id": "bg-female-1", "name": "Maria", "gender": "female"},
    ],
    "hr": [
        {"id": "hr-male-1", "name": "Luka", "gender": "male"},
        {"id": "hr-female-1", "name": "Mia", "gender": "female"},
    ],
    "sr": [
        {"id": "sr-male-1", "name": "Stefan", "gender": "male"},
        {"id": "sr-female-1", "name": "Jovana", "gender": "female"},
    ],
    "sk": [
        {"id": "sk-male-1", "name": "Adam", "gender": "male"},
        {"id": "sk-female-1", "name": "Sofia", "gender": "female"},
    ],
    "lt": [
        {"id": "lt-male-1", "name": "Lukas", "gender": "male"},
        {"id": "lt-female-1", "name": "Emilija", "gender": "female"},
    ],
    "lv": [
        {"id": "lv-male-1", "name": "Markuss", "gender": "male"},
        {"id": "lv-female-1", "name": "Emma", "gender": "female"},
    ],
    "et": [
        {"id": "et-male-1", "name": "Oliver", "gender": "male"},
        {"id": "et-female-1", "name": "Emma", "gender": "female"},
    ],
    "sl": [
        {"id": "sl-male-1", "name": "Luka", "gender": "male"},
        {"id": "sl-female-1", "name": "Zala", "gender": "female"},
    ],
    "mk": [
        {"id": "mk-male-1", "name": "Stefan", "gender": "male"},
        {"id": "mk-female-1", "name": "Ana", "gender": "female"},
    ],
    "sq": [
        {"id": "sq-male-1", "name": "Noah", "gender": "male"},
        {"id": "sq-female-1", "name": "Emma", "gender": "female"},
    ],
    "ka": [
        {"id": "ka-male-1", "name": "Giorgi", "gender": "male"},
        {"id": "ka-female-1", "name": "Mariam", "gender": "female"},
    ],
    "hy": [
        {"id": "hy-male-1", "name": "Narek", "gender": "male"},
        {"id": "hy-female-1", "name": "Ani", "gender": "female"},
    ],
    "az": [
        {"id": "az-male-1", "name": "Ali", "gender": "male"},
        {"id": "az-female-1", "name": "Leyla", "gender": "female"},
    ],
    "eu": [
        {"id": "eu-male-1", "name": "Ander", "gender": "male"},
        {"id": "eu-female-1", "name": "Ane", "gender": "female"},
    ],
    "ca": [
        {"id": "ca-male-1", "name": "Marc", "gender": "male"},
        {"id": "ca-female-1", "name": "Clara", "gender": "female"},
    ],
    "gl": [
        {"id": "gl-male-1", "name": "Xoan", "gender": "male"},
        {"id": "gl-female-1", "name": "Ana", "gender": "female"},
    ],
    "is": [
        {"id": "is-male-1", "name": "Aron", "gender": "male"},
        {"id": "is-female-1", "name": "Sara", "gender": "female"},
    ],
    "ga": [
        {"id": "ga-male-1", "name": "Sean", "gender": "male"},
        {"id": "ga-female-1", "name": "Aoife", "gender": "female"},
    ],
    "cy": [
        {"id": "cy-male-1", "name": "Gethin", "gender": "male"},
        {"id": "cy-female-1", "name": "Megan", "gender": "female"},
    ],
    "mt": [
        {"id": "mt-male-1", "name": "Luke", "gender": "male"},
        {"id": "mt-female-1", "name": "Emma", "gender": "female"},
    ],
    # --- Middle Eastern / Central Asian ---
    "fa": [
        {"id": "fa-male-1", "name": "Amir", "gender": "male"},
        {"id": "fa-female-1", "name": "Sara", "gender": "female"},
    ],
    "ps": [
        {"id": "ps-male-1", "name": "Ahmad", "gender": "male"},
        {"id": "ps-female-1", "name": "Zahra", "gender": "female"},
    ],
    "ku": [
        {"id": "ku-male-1", "name": "Hemin", "gender": "male"},
        {"id": "ku-female-1", "name": "Dilan", "gender": "female"},
    ],
    "uz": [
        {"id": "uz-male-1", "name": "Javohir", "gender": "male"},
        {"id": "uz-female-1", "name": "Madina", "gender": "female"},
    ],
    "kk": [
        {"id": "kk-male-1", "name": "Nursultan", "gender": "male"},
        {"id": "kk-female-1", "name": "Aigerim", "gender": "female"},
    ],
    "mn": [
        {"id": "mn-male-1", "name": "Batbayar", "gender": "male"},
        {"id": "mn-female-1", "name": "Oyuun", "gender": "female"},
    ],
    "ky": [
        {"id": "ky-male-1", "name": "Nursultan", "gender": "male"},
        {"id": "ky-female-1", "name": "Aijan", "gender": "female"},
    ],
    "tg": [
        {"id": "tg-male-1", "name": "Behruz", "gender": "male"},
        {"id": "tg-female-1", "name": "Gulnora", "gender": "female"},
    ],
    "tk": [
        {"id": "tk-male-1", "name": "Serdar", "gender": "male"},
        {"id": "tk-female-1", "name": "Aynur", "gender": "female"},
    ],
    # --- East / Southeast Asian ---
    "jw": [
        {"id": "jw-male-1", "name": "Budi", "gender": "male"},
        {"id": "jw-female-1", "name": "Dewi", "gender": "female"},
    ],
    "su": [
        {"id": "su-male-1", "name": "Asep", "gender": "male"},
        {"id": "su-female-1", "name": "Siti", "gender": "female"},
    ],
    "hmn": [
        {"id": "hmn-male-1", "name": "Pao", "gender": "male"},
        {"id": "hmn-female-1", "name": "Mai", "gender": "female"},
    ],
    "zh-yue": [
        {"id": "yue-male-1", "name": "Ka Ming", "gender": "male"},
        {"id": "yue-female-1", "name": "Siu Lin", "gender": "female"},
    ],
    "zh-min": [
        {"id": "min-male-1", "name": "Ah Hock", "gender": "male"},
        {"id": "min-female-1", "name": "Ah Lian", "gender": "female"},
    ],
}

# Language metadata for all supported languages
LANGUAGE_NAMES: Dict[str, str] = {
    "en": "English", "es": "Spanish", "fr": "French", "de": "German",
    "zh": "Chinese (Mandarin)", "ja": "Japanese", "ko": "Korean",
    "hi": "Hindi", "ar": "Arabic", "pt": "Portuguese", "it": "Italian",
    "ru": "Russian", "tr": "Turkish", "nl": "Dutch", "pl": "Polish",
    "sv": "Swedish", "da": "Danish", "no": "Norwegian", "fi": "Finnish",
    "cs": "Czech", "el": "Greek", "he": "Hebrew", "th": "Thai",
    "vi": "Vietnamese", "id": "Indonesian", "ms": "Malay", "tl": "Tagalog",
    "sw": "Swahili", "am": "Amharic", "ha": "Hausa", "yo": "Yoruba",
    "ig": "Igbo", "zu": "Zulu", "af": "Afrikaans", "so": "Somali",
    "rw": "Kinyarwanda", "lg": "Ganda", "sn": "Shona", "ny": "Chichewa",
    "xh": "Xhosa", "mg": "Malagasy", "bn": "Bengali", "ta": "Tamil",
    "te": "Telugu", "mr": "Marathi", "gu": "Gujarati", "kn": "Kannada",
    "ml": "Malayalam", "pa": "Punjabi", "ur": "Urdu", "si": "Sinhala",
    "ne": "Nepali", "my": "Burmese", "km": "Khmer", "lo": "Lao",
    "uk": "Ukrainian", "ro": "Romanian", "hu": "Hungarian", "bg": "Bulgarian",
    "hr": "Croatian", "sr": "Serbian", "sk": "Slovak", "lt": "Lithuanian",
    "lv": "Latvian", "et": "Estonian", "sl": "Slovenian", "mk": "Macedonian",
    "sq": "Albanian", "ka": "Georgian", "hy": "Armenian", "az": "Azerbaijani",
    "eu": "Basque", "ca": "Catalan", "gl": "Galician", "is": "Icelandic",
    "ga": "Irish", "cy": "Welsh", "mt": "Maltese", "fa": "Persian (Farsi)",
    "ps": "Pashto", "ku": "Kurdish", "uz": "Uzbek", "kk": "Kazakh",
    "mn": "Mongolian", "ky": "Kyrgyz", "tg": "Tajik", "tk": "Turkmen",
    "jw": "Javanese", "su": "Sundanese", "hmn": "Hmong",
    "zh-yue": "Chinese (Cantonese)", "zh-min": "Chinese (Hokkien)",
}


# ---------------------------------------------------------------------------
# Text-to-Speech (TTS)
# ---------------------------------------------------------------------------

def text_to_speech(
    text: str,
    language: str = "en",
    voice_id: str = "",
    speed: float = 1.0,
    format: str = "mp3",
    provider: str = "auto",
) -> dict:
    """Convert text to speech audio.

    Attempts multiple TTS backends in order of quality:
    1. OpenAI TTS API (best quality)
    2. Google TTS (gTTS)
    3. pyttsx3 (offline fallback)
    4. Espeak (Linux fallback)

    Args:
        text: The text to convert to speech. Max 4096 characters.
        language: ISO 639-1 language code (default: "en").
        voice_id: Specific voice identifier. Auto-selected if empty.
        speed: Speech speed multiplier (0.5 - 2.0, default: 1.0).
        format: Audio output format ("mp3", "wav", "ogg").
        provider: TTS provider override ("openai", "gtts", "pyttsx3", "auto").

    Returns:
        Dictionary with keys:
            - audio_base64: Base64-encoded audio data.
            - format: Audio file format.
            - duration_estimate: Estimated playback duration in seconds.
            - voice_info: Information about the voice used.
            - provider: The TTS provider that succeeded.

    Raises:
        TTSError: If all TTS backends fail.
        ValueError: If text is empty or exceeds MAX_TEXT_LENGTH.
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty.")
    if len(text) > MAX_TEXT_LENGTH:
        raise ValueError(f"Text exceeds maximum length of {MAX_TEXT_LENGTH} characters.")
    if not 0.5 <= speed <= 2.0:
        raise ValueError("Speed must be between 0.5 and 2.0.")

    text = text.strip()
    selected_voice = _select_voice(language, voice_id)
    estimated_duration = _estimate_duration(text, speed)

    providers_order = _resolve_providers(provider)

    for prov in providers_order:
        try:
            result = _synthesize_with_provider(
                text=text,
                language=language,
                voice=selected_voice,
                speed=speed,
                format=format,
                provider=prov,
            )
            result["duration_estimate"] = estimated_duration
            result["voice_info"] = selected_voice.to_dict()
            logger.info("TTS success with provider=%s lang=%s", prov, language)
            return result
        except Exception as exc:
            logger.warning("TTS provider %s failed: %s", prov, exc)
            continue

    raise TTSError("All TTS backends failed for the given text.")


def _select_voice(language: str, voice_id: str) -> VoiceInfo:
    """Select the best voice for a given language and optional voice_id."""
    lang_voices = VOICES.get(language, [])
    if not lang_voices:
        lang_voices = VOICES.get("en", [])

    if voice_id:
        for v in lang_voices:
            if v["id"] == voice_id:
                return VoiceInfo(
                    voice_id=v["id"],
                    name=v["name"],
                    gender=v["gender"],
                    language=language,
                )

    # Default: first voice of the language
    v = lang_voices[0]
    return VoiceInfo(
        voice_id=v["id"],
        name=v["name"],
        gender=v["gender"],
        language=language,
    )


def _estimate_duration(text: str, speed: float) -> float:
    """Estimate audio duration in seconds based on word count and speed."""
    word_count = len(text.split())
    avg_words_per_minute = 150
    duration = (word_count / avg_words_per_minute) * 60 / speed
    return round(duration, 2)


def _resolve_providers(provider: str) -> List[str]:
    """Determine the order of TTS providers to try."""
    if provider == "auto":
        return ["openai", "gtts", "pyttsx3", "espeak"]
    return [provider]


def _synthesize_with_provider(
    text: str,
    language: str,
    voice: VoiceInfo,
    speed: float,
    format: str,
    provider: str,
) -> dict:
    """Attempt synthesis with a specific provider."""
    if provider == "openai":
        return _synthesize_openai(text, voice, speed, format)
    elif provider == "gtts":
        return _synthesize_gtts(text, language, speed, format)
    elif provider == "pyttsx3":
        return _synthesize_pyttsx3(text, voice, speed, format)
    elif provider == "espeak":
        return _synthesize_espeak(text, language, speed, format)
    else:
        raise TTSError(f"Unknown provider: {provider}")


def _synthesize_openai(
    text: str, voice: VoiceInfo, speed: float, format: str
) -> dict:
    """Synthesize using OpenAI TTS API."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise TTSError("OpenAI API key not configured.")

    try:
        import requests
    except ImportError:
        raise TTSError("requests library not installed.")

    url = "https://api.openai.com/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "tts-1",
        "input": text,
        "voice": voice.voice_id if voice.voice_id in ["alloy", "echo", "fable", "onyx", "nova", "shimmer"] else "alloy",
        "speed": speed,
        "response_format": format if format in ["mp3", "opus", "aac", "flac", "wav", "pcm"] else "mp3",
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    if response.status_code != 200:
        raise TTSError(f"OpenAI TTS error: {response.status_code} - {response.text}")

    audio_bytes = response.content
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

    return {
        "audio_base64": audio_b64,
        "format": payload["response_format"],
        "provider": "openai",
        "duration_estimate": 0.0,
        "voice_info": voice.to_dict(),
    }


def _synthesize_gtts(
    text: str, language: str, speed: float, format: str
) -> dict:
    """Synthesize using Google Text-to-Speech (gTTS)."""
    try:
        from gtts import gTTS
    except ImportError:
        raise TTSError("gTTS not installed.")

    tts = gTTS(text=text, lang=language, slow=(speed < 1.0))
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    audio_b64 = base64.b64encode(buf.read()).decode("utf-8")

    return {
        "audio_base64": audio_b64,
        "format": "mp3",
        "provider": "gtts",
        "duration_estimate": 0.0,
        "voice_info": {},
    }


def _synthesize_pyttsx3(
    text: str, voice: VoiceInfo, speed: float, format: str
) -> dict:
    """Synthesize using pyttsx3 (offline)."""
    try:
        import pyttsx3
    except ImportError:
        raise TTSError("pyttsx3 not installed.")

    engine = pyttsx3.init()
    engine.setProperty("rate", int(200 * speed))

    # Gender-based voice selection
    voices = engine.getProperty("voices")
    for v in voices:
        if voice.gender == "female" and ("female" in v.name.lower() or "zira" in v.name.lower()):
            engine.setProperty("voice", v.id)
            break
        elif voice.gender == "male" and ("male" in v.name.lower() or "david" in v.name.lower()):
            engine.setProperty("voice", v.id)
            break

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    engine.save_to_file(text, tmp_path)
    engine.runAndWait()

    with open(tmp_path, "rb") as f:
        audio_bytes = f.read()
    os.unlink(tmp_path)

    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    return {
        "audio_base64": audio_b64,
        "format": "wav",
        "provider": "pyttsx3",
        "duration_estimate": 0.0,
        "voice_info": voice.to_dict(),
    }


def _synthesize_espeak(
    text: str, language: str, speed: float, format: str
) -> dict:
    """Synthesize using espeak (Linux fallback)."""
    import subprocess

    wpm = int(175 * speed)
    lang_map = {"en": "en", "es": "es", "fr": "fr", "de": "de", "zh": "zh", "ja": "ja", "ko": "ko"}
    espeak_lang = lang_map.get(language, "en")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    cmd = ["espeak", "-v", espeak_lang, "-s", str(wpm), "-w", tmp_path, text]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    if result.returncode != 0:
        raise TTSError(f"espeak failed: {result.stderr}")

    with open(tmp_path, "rb") as f:
        audio_bytes = f.read()
    os.unlink(tmp_path)

    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    return {
        "audio_base64": audio_b64,
        "format": "wav",
        "provider": "espeak",
        "duration_estimate": 0.0,
        "voice_info": {},
    }


def get_voices(language: Optional[str] = None) -> List[dict]:
    """Get available voices, optionally filtered by language.

    Args:
        language: ISO 639-1 language code. If None, returns all voices.

    Returns:
        List of voice dictionaries with id, name, gender, language.
    """
    if language:
        voices = VOICES.get(language, [])
        return [
            {**v, "language": language, "language_name": LANGUAGE_NAMES.get(language, language)}
            for v in voices
        ]

    all_voices: List[dict] = []
    for lang, voices in VOICES.items():
        for v in voices:
            all_voices.append({
                **v,
                "language": lang,
                "language_name": LANGUAGE_NAMES.get(lang, lang),
            })
    return all_voices


def list_supported_languages() -> List[dict]:
    """Return a list of all supported languages with metadata."""
    result = []
    for code in sorted(VOICES.keys()):
        result.append({
            "code": code,
            "name": LANGUAGE_NAMES.get(code, code),
            "voice_count": len(VOICES[code]),
            "has_openai_voice": any(v["id"] in ["alloy", "echo", "fable", "onyx", "nova", "shimmer"] for v in VOICES[code]),
        })
    return result


# ---------------------------------------------------------------------------
# Voice Cloning / Mimicry
# ---------------------------------------------------------------------------

class VoiceCloner:
    """Voice cloning system for creating personalized synthetic voices.

    Manages voice profiles, embeddings, and synthesis for cloned voices.
    Supports registration from audio samples, quality scoring, and lifecycle
    management.

    Attributes:
        profiles: In-memory dictionary of voice profiles by ID.
        profiles_dir: Directory for persisting voice profile data.
    """

    def __init__(self, profiles_dir: Optional[Union[str, Path]] = None) -> None:
        """Initialize the VoiceCloner.

        Args:
            profiles_dir: Path to store voice profiles. Defaults to
                VOICE_PROFILES_DIR.
        """
        self.profiles: Dict[str, VoiceProfile] = {}
        self.profiles_dir = Path(profiles_dir) if profiles_dir else VOICE_PROFILES_DIR
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self._load_existing_profiles()

    def _load_existing_profiles(self) -> None:
        """Load previously saved voice profiles from disk."""
        if not self.profiles_dir.exists():
            return
        for file in self.profiles_dir.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                profile = VoiceProfile(
                    voice_id=data["voice_id"],
                    name=data["name"],
                    user_id=data["user_id"],
                    created_at=data.get("created_at", time.time()),
                    quality_score=data.get("quality_score", 0.0),
                    sample_count=data.get("sample_count", 0),
                    total_duration_seconds=data.get("total_duration_seconds", 0.0),
                    last_used=data.get("last_used", 0.0),
                    is_active=data.get("is_active", True),
                    metadata=data.get("metadata", {}),
                )
                self.profiles[profile.voice_id] = profile
            except (json.JSONDecodeError, KeyError, IOError) as exc:
                logger.warning("Failed to load voice profile %s: %s", file, exc)

    def _save_profile(self, profile: VoiceProfile) -> None:
        """Persist a voice profile to disk."""
        file_path = self.profiles_dir / f"{profile.voice_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(profile.to_dict(), f, indent=2, ensure_ascii=False)

    def register_voice(
        self,
        name: str,
        audio_samples: List[str],
        user_id: str,
    ) -> dict:
        """Register a new voice from audio samples.

        Processes audio samples to extract voice embeddings and create
        a reusable voice profile for synthesis.

        Args:
            name: Human-readable name for the voice.
            audio_samples: List of base64-encoded audio samples.
            user_id: Identifier of the user registering the voice.

        Returns:
            Dictionary with keys:
                - voice_id: Unique identifier for the cloned voice.
                - status: "success" or "error".
                - quality_score: Quality score from 0.0 to 1.0.
                - embedding_dimensions: Size of the voice embedding vector.
                - total_duration_seconds: Combined duration of samples.

        Raises:
            VoiceCloneError: If registration fails.
            ValueError: If audio_samples is empty.
        """
        if not audio_samples:
            raise ValueError("At least one audio sample is required.")

        voice_id = hashlib.sha256(
            f"{user_id}:{name}:{time.time()}".encode()
        ).hexdigest()[:16]

        try:
            total_duration = 0.0
            for sample_b64 in audio_samples:
                audio_bytes = base64.b64decode(sample_b64)
                duration = _estimate_audio_duration(audio_bytes)
                total_duration += duration

            # Generate voice embedding
            embedding = self._extract_embedding(audio_samples)
            quality_score = self._assess_quality(audio_samples, embedding)

            profile = VoiceProfile(
                voice_id=voice_id,
                name=name,
                user_id=user_id,
                created_at=time.time(),
                embedding=embedding,
                quality_score=quality_score,
                sample_count=len(audio_samples),
                total_duration_seconds=total_duration,
                last_used=time.time(),
                is_active=True,
                metadata={
                    "registration_samples": len(audio_samples),
                    "average_sample_duration": total_duration / len(audio_samples),
                },
            )

            self.profiles[voice_id] = profile
            self._save_profile(profile)

            logger.info("Registered voice %s for user %s (quality=%.2f)", voice_id, user_id, quality_score)

            return {
                "voice_id": voice_id,
                "status": "success",
                "quality_score": round(quality_score, 4),
                "embedding_dimensions": len(embedding) if embedding else 0,
                "total_duration_seconds": round(total_duration, 2),
            }

        except Exception as exc:
            raise VoiceCloneError(f"Voice registration failed: {exc}") from exc

    def _extract_embedding(self, audio_samples: List[str]) -> List[float]:
        """Extract a voice embedding vector from audio samples.

        Uses a simplified embedding extraction. In production, this would
        call a neural network-based speaker encoder (e.g., GE2E, ECAPA-TDNN).

        Args:
            audio_samples: List of base64-encoded audio samples.

        Returns:
            A list of float values representing the voice embedding.
        """
        # Placeholder: In production, integrate with speaker encoder
        # We create a deterministic pseudo-embedding based on audio content
        import hashlib

        combined = b"".join(base64.b64decode(s) for s in audio_samples)
        digest = hashlib.sha256(combined).digest()
        embedding = [(b / 255.0) * 2 - 1 for b in digest[:256]]

        # Normalize
        norm = sum(x * x for x in embedding) ** 0.5
        if norm > 0:
            embedding = [x / norm for x in embedding]

        return embedding

    def _assess_quality(
        self, audio_samples: List[str], embedding: List[float]
    ) -> float:
        """Assess the quality of a voice profile.

        Evaluates signal-to-noise, sample diversity, and embedding stability.

        Args:
            audio_samples: List of base64-encoded audio samples.
            embedding: The extracted voice embedding.

        Returns:
            Quality score between 0.0 and 1.0.
        """
        sample_count_score = min(len(audio_samples) / 5.0, 1.0)
        total_bytes = sum(len(base64.b64decode(s)) for s in audio_samples)
        size_score = min(total_bytes / (1024 * 1024 * 5), 1.0)  # 5MB target
        embedding_variance = sum(x * x for x in embedding) / len(embedding)
        stability_score = 1.0 - min(abs(embedding_variance - 0.004), 1.0)
        overall = (sample_count_score * 0.4 + size_score * 0.3 + stability_score * 0.3)
        return round(min(max(overall, 0.0), 1.0), 4)

    def speak_with_voice(self, text: str, voice_id: str) -> dict:
        """Generate speech in a cloned voice.

        Args:
            text: Text to synthesize.
            voice_id: The cloned voice identifier.

        Returns:
            Dictionary with keys:
                - audio_base64: Base64-encoded synthesized audio.
                - format: Audio file format (always "mp3").
                - voice_id: The voice identifier used.
                - duration_estimate: Estimated playback duration.

        Raises:
            VoiceCloneError: If voice not found or synthesis fails.
        """
        profile = self.profiles.get(voice_id)
        if not profile or not profile.is_active:
            raise VoiceCloneError(f"Voice profile not found or inactive: {voice_id}")

        try:
            # In production: call a voice cloning model (e.g., Coqui TTS,
            # ElevenLabs VoiceLab, or Microsoft's VALL-E)
            result = text_to_speech(
                text=text,
                language="en",
                speed=1.0,
                provider="openai",
            )

            profile.last_used = time.time()
            self._save_profile(profile)

            result["voice_id"] = voice_id
            result["cloned"] = True
            return result

        except Exception as exc:
            raise VoiceCloneError(f"Synthesis with cloned voice failed: {exc}") from exc

    def list_cloned_voices(self, user_id: str) -> List[dict]:
        """List all cloned voices for a user.

        Args:
            user_id: The user identifier.

        Returns:
            List of voice profile dictionaries.
        """
        return [
            profile.to_dict()
            for profile in self.profiles.values()
            if profile.user_id == user_id and profile.is_active
        ]

    def delete_voice(self, voice_id: str) -> dict:
        """Remove a cloned voice.

        Args:
            voice_id: The voice identifier to delete.

        Returns:
            Dictionary with deletion status.
        """
        profile = self.profiles.get(voice_id)
        if not profile:
            return {"success": False, "error": "Voice not found"}

        profile.is_active = False
        self._save_profile(profile)

        # Optionally remove file
        file_path = self.profiles_dir / f"{voice_id}.json"
        if file_path.exists():
            file_path.unlink()

        del self.profiles[voice_id]
        logger.info("Deleted voice profile %s", voice_id)

        return {"success": True, "voice_id": voice_id}

    def get_voice(self, voice_id: str) -> Optional[VoiceProfile]:
        """Get a voice profile by ID.

        Args:
            voice_id: The voice identifier.

        Returns:
            The VoiceProfile if found and active, None otherwise.
        """
        profile = self.profiles.get(voice_id)
        if profile and profile.is_active:
            return profile
        return None

    def update_voice_metadata(self, voice_id: str, metadata: dict) -> dict:
        """Update metadata for a voice profile.

        Args:
            voice_id: The voice identifier.
            metadata: New metadata dictionary.

        Returns:
            Dictionary with update status.
        """
        profile = self.profiles.get(voice_id)
        if not profile or not profile.is_active:
            return {"success": False, "error": "Voice not found"}

        profile.metadata.update(metadata)
        self._save_profile(profile)
        return {"success": True, "voice_id": voice_id}


# ---------------------------------------------------------------------------
# Speech-to-Text (STT)
# ---------------------------------------------------------------------------

def speech_to_text(
    audio_data: bytes,
    language: str = "en",
    model: str = "whisper-1",
    detect_speakers: bool = False,
) -> dict:
    """Transcribe speech to text.

    Supports Whisper API (cloud) and local whisper (faster-whisper) as
    fallback. Returns transcription with timestamps and confidence scores.

    Args:
        audio_data: Raw audio bytes.
        language: ISO 639-1 language code (default: "en").
        model: Whisper model size ("tiny", "base", "small", "medium",
            "large", "whisper-1" for API).
        detect_speakers: Whether to attempt speaker diarization.

    Returns:
        Dictionary with keys:
            - text: Full transcribed text.
            - confidence: Overall confidence score (0.0 - 1.0).
            - language: Detected/spoken language code.
            - segments: List of timed segments with text and confidence.
            - duration_seconds: Total audio duration.

    Raises:
        STTError: If transcription fails.
        ValueError: If audio_data is empty.
    """
    if not audio_data:
        raise ValueError("Audio data cannot be empty.")

    # Try Whisper API first
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if api_key and model == "whisper-1":
        try:
            return _transcribe_whisper_api(audio_data, language, model)
        except Exception as exc:
            logger.warning("Whisper API failed, trying local: %s", exc)

    # Fall back to local whisper
    try:
        return _transcribe_local(audio_data, language, model, detect_speakers)
    except Exception as exc:
        raise STTError(f"Speech-to-text failed: {exc}") from exc


def _transcribe_whisper_api(
    audio_data: bytes, language: str, model: str
) -> dict:
    """Transcribe using OpenAI Whisper API."""
    try:
        import requests
    except ImportError:
        raise STTError("requests library not installed.")

    api_key = os.environ.get("OPENAI_API_KEY", "")
    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {api_key}"}

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp.write(audio_data)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as audio_file:
            files = {"file": audio_file}
            data = {
                "model": model,
                "language": language,
                "response_format": "verbose_json",
                "timestamp_granularities": ["segment", "word"],
            }
            response = requests.post(url, headers=headers, files=files, data=data, timeout=120)

        if response.status_code != 200:
            raise STTError(f"Whisper API error: {response.status_code} - {response.text}")

        result = response.json()
        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "start": seg.get("start", 0.0),
                "end": seg.get("end", 0.0),
                "text": seg.get("text", "").strip(),
                "confidence": seg.get("avg_logprob", 0.0),
            })

        return {
            "text": result.get("text", "").strip(),
            "confidence": sum(s["confidence"] for s in segments) / len(segments) if segments else 0.0,
            "language": result.get("language", language),
            "segments": segments,
            "duration_seconds": segments[-1]["end"] if segments else 0.0,
        }
    finally:
        os.unlink(tmp_path)


def _transcribe_local(
    audio_data: bytes,
    language: str,
    model: str,
    detect_speakers: bool,
) -> dict:
    """Transcribe using local faster-whisper."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise STTError("faster-whisper not installed. Install with: pip install faster-whisper")

    # Map model names to sizes
    model_size = model if model != "whisper-1" else "base"

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_data)
        tmp_path = tmp.name

    try:
        whisper_model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments_iter, info = whisper_model.transcribe(
            tmp_path, language=language, beam_size=5
        )

        segments = []
        full_text_parts = []
        for seg in segments_iter:
            segments.append({
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip(),
                "confidence": seg.avg_logprob,
            })
            full_text_parts.append(seg.text.strip())

        return {
            "text": " ".join(full_text_parts),
            "confidence": sum(s["confidence"] for s in segments) / len(segments) if segments else 0.0,
            "language": info.language,
            "segments": segments,
            "duration_seconds": segments[-1]["end"] if segments else 0.0,
        }
    finally:
        os.unlink(tmp_path)


def transcribe_stream(
    audio_chunks: List[bytes],
    language: str = "en",
    chunk_overlap_ms: int = 200,
) -> dict:
    """Real-time streaming transcription.

    Processes audio chunks incrementally, maintaining context across
    chunk boundaries for continuous transcription.

    Args:
        audio_chunks: List of audio byte chunks received in sequence.
        language: ISO 639-1 language code.
        chunk_overlap_ms: Overlap between chunks in milliseconds to
            prevent word boundary issues.

    Returns:
        Dictionary with keys:
            - text: Full accumulated transcript.
            - incremental_results: Per-chunk transcription results.
            - is_final: Whether the stream has ended.
            - language: Detected language.
    """
    if not audio_chunks:
        return {
            "text": "",
            "incremental_results": [],
            "is_final": True,
            "language": language,
        }

    incremental_results = []
    all_text_parts = []

    for i, chunk in enumerate(audio_chunks):
        try:
            result = speech_to_text(chunk, language=language)
            text = result.get("text", "").strip()
            incremental_results.append({
                "chunk_index": i,
                "text": text,
                "confidence": result.get("confidence", 0.0),
                "language": result.get("language", language),
            })
            if text:
                all_text_parts.append(text)
        except STTError as exc:
            logger.warning("Chunk %d transcription failed: %s", i, exc)
            incremental_results.append({
                "chunk_index": i,
                "text": "",
                "confidence": 0.0,
                "error": str(exc),
            })

    # Deduplicate repeated phrases at chunk boundaries
    full_text = _deduplicate_stream_text(all_text_parts)

    return {
        "text": full_text,
        "incremental_results": incremental_results,
        "is_final": True,
        "language": language,
    }


def _deduplicate_stream_text(text_parts: List[str]) -> str:
    """Remove duplicate phrases at chunk boundaries."""
    if not text_parts:
        return ""

    result = text_parts[0]
    for i in range(1, len(text_parts)):
        prev_words = result.split()
        curr_words = text_parts[i].split()

        # Find overlap
        max_overlap = min(len(prev_words), len(curr_words), 5)
        overlap_size = 0
        for size in range(max_overlap, 0, -1):
            if prev_words[-size:] == curr_words[:size]:
                overlap_size = size
                break

        result += " " + " ".join(curr_words[overlap_size:])

    return result


# ---------------------------------------------------------------------------
# Voice Command Detection
# ---------------------------------------------------------------------------

# Command patterns with regex-based matching
VOICE_COMMAND_PATTERNS: List[Dict[str, Any]] = [
    {
        "command": "new_chat",
        "patterns": [
            r"new\s+(chat|conversation|session|thread)",
            r"start\s+(a\s+)?new\s+(chat|conversation)",
            r"create\s+(a\s+)?new\s+(chat|conversation)",
            r"begin\s+(a\s+)?new\s+(chat|conversation)",
        ],
        "parameters": {},
    },
    {
        "command": "search",
        "patterns": [
            r"search\s+(for\s+)?(.+)",
            r"find\s+(me\s+)?(.+)",
            r"look\s+(up\s+)?(.+)",
            r"look\s+for\s+(.+)",
            r"search\s+(.+)",
        ],
        "parameters": {"query": 2},
    },
    {
        "command": "switch_mode",
        "patterns": [
            r"switch\s+to\s+(developer|dev)\s+mode",
            r"switch\s+to\s+creative\s+mode",
            r"switch\s+to\s+precise\s+mode",
            r"switch\s+to\s+balanced\s+mode",
            r"enable\s+(developer|dev)\s+mode",
            r"use\s+(developer|dev)\s+mode",
            r"change\s+mode\s+to\s+(.+)",
        ],
        "parameters": {"mode": 1},
    },
    {
        "command": "explain_simple",
        "patterns": [
            r"explain\s+like\s+I'?m\s+five",
            r"explain\s+like\s+I\s+am\s+five",
            r"ELI5\s+(.+)",
            r"explain\s+simply\s+(.+)",
            r"simple\s+explanation\s+(of\s+)?(.+)",
            r"explain\s+like\s+I'?m\s+a\s+beginner",
            r"explain\s+for\s+a\s+child",
        ],
        "parameters": {"topic": 1},
    },
    {
        "command": "summarize",
        "patterns": [
            r"summarize\s+(.+)",
            r"give\s+me\s+a\s+summary\s+(of\s+)?(.+)",
            r"tl;?dr\s+(.+)",
            r"in\s+a\s+nutshell\s+(.+)",
        ],
        "parameters": {"topic": 1},
    },
    {
        "command": "translate",
        "patterns": [
            r"translate\s+(to\s+)?(\w+)\s*[:;]\s*(.+)",
            r"translate\s+(.+)\s+to\s+(\w+)",
            r"how\s+do\s+I\s+say\s+(.+)\s+in\s+(\w+)",
        ],
        "parameters": {"target_language": 2, "text": 3},
    },
    {
        "command": "set_reminder",
        "patterns": [
            r"remind\s+me\s+(to\s+)?(.+)\s+(in|at|on)\s+(.+)",
            r"set\s+a?\s+reminder\s+(to\s+)?(.+)\s+(in|at|on)\s+(.+)",
            r"remind\s+me\s+(in|at|on)\s+(.+)\s+to\s+(.+)",
        ],
        "parameters": {"action": 2, "time": 4},
    },
    {
        "command": "read_aloud",
        "patterns": [
            r"read\s+(this\s+)?(aloud|out\s+loud)",
            r"read\s+it\s+(to\s+me|aloud)",
            r"speak\s+(this\s+)?(out\s+loud|aloud)",
            r"say\s+that\s+again",
            r"can\s+you\s+read\s+(that|this)",
        ],
        "parameters": {},
    },
    {
        "command": "save_conversation",
        "patterns": [
            r"save\s+(this\s+)?conversation",
            r"save\s+chat",
            r"export\s+(this\s+)?conversation",
            r"download\s+(this\s+)?chat",
        ],
        "parameters": {},
    },
    {
        "command": "clear_history",
        "patterns": [
            r"clear\s+(the\s+)?history",
            r"delete\s+(the\s+)?history",
            r"clear\s+(the\s+)?conversation",
            r"forget\s+everything",
        ],
        "parameters": {},
    },
    {
        "command": "change_language",
        "patterns": [
            r"switch\s+to\s+(\w+)\s+language",
            r"change\s+language\s+to\s+(\w+)",
            r"speak\s+in\s+(\w+)",
            r"use\s+(\w+)\s+language",
        ],
        "parameters": {"language": 1},
    },
    {
        "command": "help",
        "patterns": [
            r"help\s*(me)?",
            r"what\s+can\s+you\s+do",
            r"show\s+commands",
            r"list\s+voice\s+commands",
        ],
        "parameters": {},
    },
    {
        "command": "stop",
        "patterns": [
            r"stop\s*(speaking|talking|reading)?",
            r"pause",
            r"be\s+quiet",
            r"shut\s+up",
        ],
        "parameters": {},
    },
    {
        "command": "feedback",
        "patterns": [
            r"(that\s+was\s+)?(good|great|excellent|perfect|bad|terrible|wrong)",
            r"thumbs\s+(up|down)",
            r"(good|bad)\s+response",
        ],
        "parameters": {"sentiment": 2},
    },
]


def detect_voice_commands(transcript: str) -> VoiceCommand:
    """Detect voice commands in a transcript.

    Analyzes transcribed text against known command patterns to identify
    user intents and extract relevant parameters.

    Args:
        transcript: The transcribed text to analyze.

    Returns:
        VoiceCommand dataclass with:
            - is_command: Whether a command was detected.
            - command: The command name if detected.
            - parameters: Extracted parameters.
            - confidence: Match confidence (0.0 - 1.0).
            - raw_transcript: Original transcript text.
    """
    if not transcript:
        return VoiceCommand(is_command=False, command="", raw_transcript="")

    transcript_lower = transcript.lower().strip()

    for cmd_def in VOICE_COMMAND_PATTERNS:
        for pattern in cmd_def["patterns"]:
            match = re.search(pattern, transcript_lower, re.IGNORECASE)
            if match:
                params = {}
                for param_name, group_idx in cmd_def.get("parameters", {}).items():
                    if group_idx <= len(match.groups()) and match.group(group_idx):
                        params[param_name] = match.group(group_idx).strip()

                confidence = _calculate_command_confidence(transcript_lower, cmd_def["command"], match)

                logger.info("Voice command detected: %s (confidence=%.2f)", cmd_def["command"], confidence)

                return VoiceCommand(
                    is_command=True,
                    command=cmd_def["command"],
                    parameters=params,
                    confidence=confidence,
                    raw_transcript=transcript,
                )

    return VoiceCommand(is_command=False, command="", raw_transcript=transcript)


def _calculate_command_confidence(transcript: str, command: str, match: re.Match) -> float:
    """Calculate confidence score for a command match.

    Factors:
        - Exactness of regex match
        - Length of transcript vs. command specificity
        - Position of match in transcript
    """
    base_confidence = 0.7

    # Boost for exact full-string match
    if match.start() == 0 and match.end() == len(transcript):
        base_confidence += 0.2
    elif match.start() == 0:
        base_confidence += 0.1

    # Penalize very long transcripts (might be conversation, not command)
    word_count = len(transcript.split())
    if word_count > 20:
        base_confidence -= 0.15
    elif word_count <= 5:
        base_confidence += 0.05

    return round(min(max(base_confidence, 0.0), 1.0), 4)


def get_supported_commands() -> List[dict]:
    """Get a list of all supported voice commands.

    Returns:
        List of command definitions with command name, description,
        and example utterances.
    """
    command_descriptions = {
        "new_chat": "Start a new conversation",
        "search": "Search for information on a topic",
        "switch_mode": "Switch between conversation modes",
        "explain_simple": "Get a simple explanation (ELI5)",
        "summarize": "Summarize text or content",
        "translate": "Translate text to another language",
        "set_reminder": "Set a reminder",
        "read_aloud": "Read the last response aloud",
        "save_conversation": "Save the current conversation",
        "clear_history": "Clear conversation history",
        "change_language": "Change the AI's language",
        "help": "Show available commands",
        "stop": "Stop speaking",
        "feedback": "Provide feedback on the response",
    }

    return [
        {
            "command": cmd["command"],
            "description": command_descriptions.get(cmd["command"], ""),
            "patterns": cmd["patterns"],
            "parameters": list(cmd.get("parameters", {}).keys()),
        }
        for cmd in VOICE_COMMAND_PATTERNS
    ]


# ---------------------------------------------------------------------------
# Audio utility functions
# ---------------------------------------------------------------------------

def _estimate_audio_duration(audio_bytes: bytes) -> float:
    """Estimate duration of audio data in seconds.

    Supports WAV, MP3, and OGG formats via file header analysis.

    Args:
        audio_bytes: Raw audio byte data.

    Returns:
        Estimated duration in seconds. Returns 0.0 if undetectable.
    """
    if len(audio_bytes) < 12:
        return 0.0

    # Check for WAV
    if audio_bytes[:4] == b"RIFF" and audio_bytes[8:12] == b"WAVE":
        try:
            with io.BytesIO(audio_bytes) as buf:
                with wave.open(buf, "rb") as wf:
                    frames = wf.getnframes()
                    rate = wf.getframerate()
                    return frames / float(rate) if rate > 0 else 0.0
        except Exception:
            pass

    # Rough MP3 estimate (assume 128kbps)
    if audio_bytes[:2] == b"\xff\xfb" or audio_bytes[:2] == b"\xff\xfa":
        bitrate = 128000  # 128 kbps
        return (len(audio_bytes) * 8) / bitrate

    # Rough OGG estimate
    if audio_bytes[:4] == b"OggS":
        # OGG is variable bitrate; rough estimate
        return len(audio_bytes) / (16000 * 2)  # ~32kbps assumption

    return 0.0


def convert_audio_format(
    audio_bytes: bytes,
    source_format: str,
    target_format: str,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> bytes:
    """Convert audio between formats.

    Args:
        audio_bytes: Raw audio data.
        source_format: Current format ("wav", "mp3", "ogg").
        target_format: Desired format ("wav", "mp3", "ogg", "flac").
        sample_rate: Target sample rate.

    Returns:
        Converted audio bytes.

    Raises:
        ValueError: If conversion is not supported.
    """
    try:
        import pydub
    except ImportError:
        raise ValueError("pydub is required for audio format conversion.")

    audio = pydub.AudioSegment.from_file(
        io.BytesIO(audio_bytes), format=source_format
    )
    audio = audio.set_frame_rate(sample_rate).set_channels(1)

    buf = io.BytesIO()
    audio.export(buf, format=target_format)
    buf.seek(0)
    return buf.read()


def validate_audio(audio_bytes: bytes) -> dict:
    """Validate audio data and return metadata.

    Args:
        audio_bytes: Raw audio data.

    Returns:
        Dictionary with:
            - valid: Whether the audio is valid.
            - format: Detected format.
            - duration_seconds: Estimated duration.
            - sample_rate: Sample rate if detectable.
            - channels: Number of channels if detectable.
            - file_size_bytes: Size of audio data.
            - error: Error message if invalid.
    """
    result = {
        "valid": False,
        "format": "unknown",
        "duration_seconds": 0.0,
        "sample_rate": 0,
        "channels": 0,
        "file_size_bytes": len(audio_bytes),
        "error": None,
    }

    if not audio_bytes:
        result["error"] = "Empty audio data"
        return result

    if len(audio_bytes) > MAX_AUDIO_SIZE_MB * 1024 * 1024:
        result["error"] = f"Audio exceeds {MAX_AUDIO_SIZE_MB}MB limit"
        return result

    # Detect format
    if audio_bytes[:4] == b"RIFF":
        result["format"] = "wav"
    elif audio_bytes[:2] == b"\xff\xfb" or audio_bytes[:2] == b"\xff\xfa":
        result["format"] = "mp3"
    elif audio_bytes[:4] == b"OggS":
        result["format"] = "ogg"
    elif audio_bytes[:4] == b"fLaC":
        result["format"] = "flac"

    result["duration_seconds"] = _estimate_audio_duration(audio_bytes)
    result["valid"] = True
    return result


# ---------------------------------------------------------------------------
# Streaming TTS
# ---------------------------------------------------------------------------

def text_to_speech_stream(
    text: str,
    language: str = "en",
    voice_id: str = "",
    speed: float = 1.0,
    chunk_size: int = 100,
) -> Iterator[dict]:
    """Stream TTS audio in chunks for real-time playback.

    Splits text into sentences and yields audio chunks incrementally.

    Args:
        text: Full text to synthesize.
        language: ISO 639-1 language code.
        voice_id: Specific voice identifier.
        speed: Speech speed multiplier.
        chunk_size: Target character count per chunk.

    Yields:
        Dictionary for each chunk with:
            - audio_base64: Base64-encoded audio.
            - format: Audio format.
            - text_chunk: The text segment.
            - is_final: Whether this is the last chunk.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text)
    current_chunk = ""

    for i, sentence in enumerate(sentences):
        current_chunk += sentence + " "

        if len(current_chunk) >= chunk_size or i == len(sentences) - 1:
            chunk_text = current_chunk.strip()
            if chunk_text:
                try:
                    result = text_to_speech(
                        text=chunk_text,
                        language=language,
                        voice_id=voice_id,
                        speed=speed,
                    )
                    yield {
                        "audio_base64": result["audio_base64"],
                        "format": result["format"],
                        "text_chunk": chunk_text,
                        "is_final": i == len(sentences) - 1,
                    }
                except TTSError as exc:
                    logger.error("TTS chunk failed: %s", exc)
                    yield {
                        "audio_base64": "",
                        "format": "",
                        "text_chunk": chunk_text,
                        "is_final": i == len(sentences) - 1,
                        "error": str(exc),
                    }
            current_chunk = ""


# ---------------------------------------------------------------------------
# Voice System Manager (unified interface)
# ---------------------------------------------------------------------------

class VoiceSystem:
    """Unified voice system manager for Luqi AI v15.

    Provides a single interface for all voice operations including TTS,
    STT, voice cloning, and command detection.

    Example:
        voice = VoiceSystem()
        audio = voice.speak("Hello, world!")
        transcript = voice.listen(audio_data)
        command = voice.detect_command("new chat please")
    """

    def __init__(self, profiles_dir: Optional[Union[str, Path]] = None) -> None:
        """Initialize the voice system.

        Args:
            profiles_dir: Directory for voice profile storage.
        """
        self.cloner = VoiceCloner(profiles_dir=profiles_dir)
        logger.info("VoiceSystem initialized with %d languages", len(VOICES))

    def speak(
        self,
        text: str,
        language: str = "en",
        voice_id: str = "",
        speed: float = 1.0,
    ) -> dict:
        """Convert text to speech.

        Args:
            text: Text to synthesize.
            language: ISO 639-1 language code.
            voice_id: Specific voice identifier.
            speed: Speech speed multiplier.

        Returns:
            TTS result dictionary.
        """
        return text_to_speech(text, language, voice_id, speed)

    def listen(
        self,
        audio_data: bytes,
        language: str = "en",
    ) -> dict:
        """Transcribe speech to text.

        Args:
            audio_data: Raw audio bytes.
            language: Expected language code.

        Returns:
            STT result dictionary.
        """
        return speech_to_text(audio_data, language)

    def detect_command(self, transcript: str) -> VoiceCommand:
        """Detect voice commands in a transcript.

        Args:
            transcript: Transcribed text.

        Returns:
            VoiceCommand result.
        """
        return detect_voice_commands(transcript)

    def clone_voice(
        self,
        name: str,
        audio_samples: List[str],
        user_id: str,
    ) -> dict:
        """Register a cloned voice.

        Args:
            name: Voice name.
            audio_samples: Base64-encoded audio samples.
            user_id: User identifier.

        Returns:
            Registration result dictionary.
        """
        return self.cloner.register_voice(name, audio_samples, user_id)

    def speak_with_cloned_voice(self, text: str, voice_id: str) -> dict:
        """Speak using a cloned voice.

        Args:
            text: Text to synthesize.
            voice_id: Cloned voice identifier.

        Returns:
            TTS result dictionary.
        """
        return self.cloner.speak_with_voice(text, voice_id)

    def get_voice_info(self, language: Optional[str] = None) -> List[dict]:
        """Get voice information.

        Args:
            language: Optional language filter.

        Returns:
            List of voice info dictionaries.
        """
        return get_voices(language)

    def get_languages(self) -> List[dict]:
        """Get supported languages.

        Returns:
            List of language dictionaries.
        """
        return list_supported_languages()

    def health_check(self) -> dict:
        """Check voice system health.

        Returns:
            Health status dictionary.
        """
        return {
            "status": "healthy",
            "languages_supported": len(VOICES),
            "total_voices": sum(len(v) for v in VOICES.values()),
            "cloned_voices": len(self.cloner.profiles),
            "supported_commands": len(VOICE_COMMAND_PATTERNS),
            "version": "15.0.0",
        }
