# -*- coding: utf-8 -*-
"""
Luqi AI — Text-to-Speech & Speech-to-Text Engine

VoiceEngine handles text-to-speech synthesis and speech-to-text
transcription for 80+ languages using OpenAI's APIs:
- TTS: OpenAI TTS (tts-1, tts-1-hd) — supports many languages
- STT: OpenAI Whisper (whisper-1) — supports 99+ languages

Usage:
    engine = VoiceEngine()
    engine.speak("Jambo! Habari yako?", "sw")
    text = engine.listen("recording.mp3", "sw")
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from lang.african_languages import AFRICAN_LANGUAGES, GLOBAL_LANGUAGES


# =============================================================================
# VOICE MAPPING
# =============================================================================

# OpenAI TTS voices (alloy, echo, fable, onyx, nova, shimmer)
TTS_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

# Language-to-preferred-voice mapping
LANGUAGE_VOICE_PREFERENCES: dict[str, str] = {
    # African languages
    "sw": "nova",       # Swahili — warm female voice
    "am": "alloy",      # Amharic — neutral voice
    "so": "onyx",       # Somali — deep male voice
    "om": "alloy",      # Oromo
    "rw": "nova",       # Kinyarwanda
    "rn": "nova",       # Kirundi
    "lg": "nova",       # Luganda
    "mg": "nova",       # Malagasy
    "ti": "alloy",      # Tigrinya
    "zu": "nova",       # Zulu
    "xh": "nova",       # Xhosa
    "af": "alloy",      # Afrikaans
    "st": "alloy",      # Sesotho
    "tn": "alloy",      # Setswana
    "nso": "alloy",     # Sepedi
    "ts": "nova",       # Tsonga
    "ve": "nova",       # Venda
    "ss": "nova",       # Swati
    "nr": "nova",       # Ndebele
    "sn": "nova",       # Shona
    "nd": "nova",       # North Ndebele
    "ny": "nova",       # Chewa
    "ha": "onyx",       # Hausa
    "yo": "onyx",       # Yoruba
    "ig": "onyx",       # Igbo
    "ff": "alloy",      # Fulfulde
    "ak": "nova",       # Akan
    "ee": "nova",       # Ewe
    "wo": "onyx",       # Wolof
    "bm": "nova",       # Bambara
    "mos": "nova",      # Moore
    "fon": "nova",      # Fon
    "ln": "nova",       # Lingala
    "kg": "alloy",      # Kikongo
    "ktu": "alloy",     # Kituba
    "lu": "nova",       # Luba-Kasai
    "sg": "nova",       # Sango
    "fan": "alloy",     # Fang
    "kr": "alloy",      # Kanuri
    "ar-eg": "onyx",    # Egyptian Arabic
    "ary": "onyx",      # Moroccan Arabic
    "kab": "nova",      # Kabyle
    "shi": "nova",      # Tashelhit
    # Global languages
    "en": "alloy",      # English
    "es": "nova",       # Spanish
    "fr": "nova",       # French
    "pt": "nova",       # Portuguese
    "de": "alloy",      # German
    "it": "nova",       # Italian
    "zh": "nova",       # Mandarin
    "ja": "nova",       # Japanese
    "ko": "nova",       # Korean
    "hi": "nova",       # Hindi
    "ar": "onyx",       # Arabic
    "ru": "onyx",       # Russian
    "tr": "onyx",       # Turkish
    "vi": "nova",       # Vietnamese
    "th": "nova",       # Thai
    "fa": "onyx",       # Persian
    "ur": "onyx",       # Urdu
    "id": "nova",       # Indonesian
    "nl": "alloy",      # Dutch
    "el": "nova",       # Greek
    "pl": "nova",       # Polish
    "uk": "nova",       # Ukrainian
    "ro": "nova",       # Romanian
    "he": "onyx",       # Hebrew
    "bn": "nova",       # Bengali
    "ta": "nova",       # Tamil
    "te": "nova",       # Telugu
    "ml": "nova",       # Malayalam
    "mr": "nova",       # Marathi
    "gu": "nova",       # Gujarati
    "pa": "nova",       # Punjabi
}


# Whisper language codes mapping
WHISPER_CODE_MAP: dict[str, str] = {
    # Map internal codes to Whisper language codes
    "ar-eg": "ar",
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
        tts_model: str = "tts-1",
        stt_model: str = "whisper-1",
    ) -> None:
        """
        Initialize the VoiceEngine.

        Args:
            api_key: OpenAI API key. Falls back to OPENAI_API_KEY env var.
            tts_model: TTS model to use ("tts-1" or "tts-1-hd").
            stt_model: STT model to use ("whisper-1").
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.tts_model = tts_model
        self.stt_model = stt_model
        self._client: Any = None
        self.all_languages = {**AFRICAN_LANGUAGES, **GLOBAL_LANGUAGES}

    @property
    def client(self) -> Any:
        """Lazy-load OpenAI client."""
        if self._client is None:
            try:
                import openai
                self._client = openai.OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "OpenAI package not installed. "
                    "Install with: pip install openai"
                )
        return self._client

    def speak(
        self,
        text: str,
        lang_code: str,
        voice: str | None = None,
        output_path: str | None = None,
        speed: float = 1.0,
    ) -> bytes:
        """
        Synthesize speech from text using OpenAI TTS.

        Args:
            text: Text to synthesize.
            lang_code: Language code for voice selection.
            voice: Specific voice to use (overrides default).
            output_path: Optional file path to save audio.
            speed: Speech speed multiplier (0.25 to 4.0).

        Returns:
            Audio data as bytes.

        Raises:
            ValueError: If text is empty or voice is invalid.
            RuntimeError: If API call fails.
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        selected_voice = voice or self.get_preferred_voice(lang_code)

        if selected_voice not in TTS_VOICES:
            raise ValueError(
                f"Invalid voice '{selected_voice}'. "
                f"Available: {', '.join(TTS_VOICES)}"
            )

        try:
            response = self.client.audio.speech.create(
                model=self.tts_model,
                voice=selected_voice,
                input=text,
                speed=speed,
            )

            audio_data = response.content

            if output_path:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(audio_data)

            return audio_data

        except Exception as e:
            raise RuntimeError(f"TTS synthesis failed: {e}") from e

    def listen(
        self,
        audio_file: str | bytes,
        lang_code: str | None = None,
        prompt: str | None = None,
        temperature: float = 0.0,
    ) -> str:
        """
        Transcribe speech from audio using OpenAI Whisper.

        Args:
            audio_file: Path to audio file or audio bytes.
            lang_code: Optional language code for language hint.
            prompt: Optional prompt to guide transcription.
            temperature: Sampling temperature (0.0 to 1.0).

        Returns:
            Transcribed text string.

        Raises:
            FileNotFoundError: If audio file doesn't exist.
            RuntimeError: If transcription fails.
        """
        try:
            kwargs: dict[str, Any] = {
                "model": self.stt_model,
                "temperature": temperature,
            }

            if lang_code:
                whisper_code = self.get_language_whisper_code(lang_code)
                kwargs["language"] = whisper_code

            if prompt:
                kwargs["prompt"] = prompt

            # Handle file path vs bytes
            if isinstance(audio_file, str):
                if not os.path.exists(audio_file):
                    raise FileNotFoundError(f"Audio file not found: {audio_file}")
                with open(audio_file, "rb") as f:
                    audio_data = f.read()
            else:
                audio_data = audio_file

            import io
            audio_buffer = io.BytesIO(audio_data)
            audio_buffer.name = "audio.mp3"

            response = self.client.audio.transcriptions.create(
                file=audio_buffer,
                **kwargs,
            )

            return response.text

        except FileNotFoundError:
            raise
        except Exception as e:
            raise RuntimeError(f"STT transcription failed: {e}") from e

    def list_voices(self, lang_code: str | None = None) -> list[str]:
        """
        List available TTS voices.

        Args:
            lang_code: Optional language code to filter preferred voices.

        Returns:
            List of available voice names.
        """
        if lang_code:
            preferred = self.get_preferred_voice(lang_code)
            # Return preferred voice first, then others
            others = [v for v in TTS_VOICES if v != preferred]
            return [preferred] + others
        return TTS_VOICES.copy()

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
            voice = LANGUAGE_VOICE_PREFERENCES.get(base_code)
        return voice or "alloy"  # Default fallback

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

def quick_speak(
    text: str,
    lang_code: str,
    voice: str | None = None,
    output_path: str | None = None,
) -> bytes:
    """Quick text-to-speech without instantiating a class."""
    engine = VoiceEngine()
    return engine.speak(text, lang_code, voice=voice, output_path=output_path)


def quick_listen(
    audio_file: str,
    lang_code: str | None = None,
) -> str:
    """Quick speech-to-text without instantiating a class."""
    engine = VoiceEngine()
    return engine.listen(audio_file, lang_code=lang_code)


def get_whisper_code(lang_code: str) -> str:
    """Get Whisper language code for a language."""
    engine = VoiceEngine()
    return engine.get_language_whisper_code(lang_code)
