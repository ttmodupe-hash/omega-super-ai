#!/usr/bin/env python3
"""
Luqi AI v25.1.0 Voice Engine — Speech-to-Text & Text-to-Speech
===============================================================
Standalone voice processing module for the JARVIS agent integration.

Capabilities:
- Speech-to-Text (STT): Google Speech Recognition, multiple languages
- Text-to-Speech (TTS): gTTS with multiple voices and accents
- Audio playback via pygame
- Continuous listening mode
- Audio file management and cleanup

Dependencies:
    pip install SpeechRecognition gtts pygame

Usage:
    from backend.voice_engine import VoiceEngine
    voice = VoiceEngine()
    
    # Text to speech
    voice.speak("Hello, I am Luqi AI")
    
    # Speech to text
    text = voice.listen(timeout=5)
    
    # Continuous listening
    def on_speech(text):
        print(f"Heard: {text}")
    
    import threading
    stop_event = threading.Event()
    voice.listen_continuous(on_speech, stop_event)
"""

import logging
import os
import sys
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

# ── Optional Dependencies ────────────────────────────────────────────────────

try:
    import speech_recognition as sr
    _HAS_SPEECH = True
except ImportError:
    _HAS_SPEECH = False

try:
    from gtts import gTTS
    _HAS_GTTS = True
except ImportError:
    _HAS_GTTS = False

try:
    import pygame
    _HAS_PYGAME = True
except ImportError:
    _HAS_PYGAME = False

try:
    from pydub import AudioSegment
    _HAS_PYDUB = True
except ImportError:
    _HAS_PYDUB = False

logger = logging.getLogger(__name__)

# Default voice storage
PROJECT_ROOT = Path(__file__).parent.parent
VOICE_DIR = PROJECT_ROOT / "data" / "voice"
VOICE_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  VOICE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class VoiceEngine:
    """Speech-to-text and text-to-speech processing engine.
    
    Handles voice input capture, transcription, and voice output generation.
    Supports multiple languages for both STT and TTS.
    
    Attributes:
        voice_dir: Directory for storing generated audio files
        is_listening: Whether continuous listening is active
        default_language: Default language code for STT/TTS
    """
    
    # Supported languages for TTS
    SUPPORTED_LANGUAGES = {
        "en": "English", "es": "Spanish", "fr": "French",
        "de": "German", "it": "Italian", "pt": "Portuguese",
        "ru": "Russian", "ja": "Japanese", "ko": "Korean",
        "zh": "Chinese", "ar": "Arabic", "hi": "Hindi",
        "yo": "Yoruba", "ig": "Igbo", "ha": "Hausa",
        "sw": "Swahili", "af": "Afrikaans", "zu": "Zulu"
    }
    
    # Accent variants for English TTS
    ACCENTS = {
        "uk": "co.uk",      # British
        "us": "com",        # American
        "au": "com.au",     # Australian
        "ca": "ca",         # Canadian
        "in": "co.in",      # Indian
        "ie": "ie",         # Irish
        "za": "co.za"       # South African
    }
    
    def __init__(self, voice_dir: Optional[str] = None,
                 default_language: str = "en",
                 default_accent: str = "uk"):
        """Initialize the voice engine.
        
        Args:
            voice_dir: Directory for audio file storage
            default_language: Default language code
            default_accent: Default accent for TTS
        """
        self.voice_dir = Path(voice_dir or VOICE_DIR)
        self.voice_dir.mkdir(parents=True, exist_ok=True)
        self.default_language = default_language
        self.default_accent = default_accent
        self.is_listening = False
        self._temp_files: List[Path] = []
        self._recognizer = None
        
        # Initialize speech recognizer if available
        if _HAS_SPEECH:
            self._recognizer = sr.Recognizer()
            self._recognizer.dynamic_energy_threshold = True
            self._recognizer.energy_threshold = 300
            self._recognizer.pause_threshold = 0.8
    
    # ── Speech-to-Text ──────────────────────────────────────────────────
    
    def listen(self, timeout: int = 5, phrase_time_limit: int = 8,
               language: str = "en-US", ambient_duration: float = 0.5) -> str:
        """Capture audio from microphone and transcribe to text.
        
        Args:
            timeout: Maximum seconds to wait for speech to start
            phrase_time_limit: Maximum seconds for a single phrase
            language: Language code for recognition (e.g., 'en-US', 'yo-NG')
            ambient_duration: Seconds to sample ambient noise
            
        Returns:
            Transcribed text, or empty string on failure
        """
        if not _HAS_SPEECH:
            logger.error("Speech recognition not available. Install: pip install SpeechRecognition")
            return ""
        
        if self._recognizer is None:
            self._recognizer = sr.Recognizer()
        
        try:
            with sr.Microphone() as source:
                logger.info(f"Listening (timeout={timeout}s, lang={language})...")
                self._recognizer.adjust_for_ambient_noise(source, duration=ambient_duration)
                
                audio = self._recognizer.listen(
                    source, timeout=timeout,
                    phrase_time_limit=phrase_time_limit
                )
                
                text = self._recognizer.recognize_google(audio, language=language)
                logger.info(f"Transcribed: '{text}'")
                return text
                
        except sr.WaitTimeoutError:
            logger.warning("Listening timeout - no speech detected")
            return ""
        except sr.UnknownValueError:
            logger.warning("Could not understand audio")
            return ""
        except sr.RequestError as e:
            logger.error(f"Speech recognition service error: {e}")
            return ""
        except Exception as e:
            logger.error(f"STT error: {e}")
            return ""
    
    def listen_continuous(self, callback: Callable[[str], None],
                          stop_event: threading.Event,
                          language: str = "en-US"):
        """Listen continuously until stop_event is set.
        
        Calls callback with transcribed text after each utterance.
        Runs in the current thread — call from a background thread
        to avoid blocking.
        
        Args:
            callback: Function to call with transcribed text
            stop_event: threading.Event to signal stop
            language: Language code for recognition
        """
        if not _HAS_SPEECH:
            logger.error("Speech recognition not available")
            return
        
        if self._recognizer is None:
            self._recognizer = sr.Recognizer()
        
        self.is_listening = True
        
        try:
            with sr.Microphone() as source:
                logger.info("Starting continuous listening...")
                self._recognizer.adjust_for_ambient_noise(source, duration=1)
                
                while not stop_event.is_set() and self.is_listening:
                    try:
                        audio = self._recognizer.listen(
                            source, timeout=1,
                            phrase_time_limit=10
                        )
                        text = self._recognizer.recognize_google(
                            audio, language=language
                        )
                        if text:
                            callback(text)
                            
                    except sr.WaitTimeoutError:
                        continue
                    except sr.UnknownValueError:
                        continue
                    except Exception as e:
                        logger.error(f"Continuous listen error: {e}")
                        
        finally:
            self.is_listening = False
            logger.info("Continuous listening stopped")
    
    def stop_listening(self):
        """Stop continuous listening."""
        self.is_listening = False
    
    # ── Text-to-Speech ──────────────────────────────────────────────────
    
    def speak(self, text: str, language: Optional[str] = None,
              accent: Optional[str] = None, slow: bool = False,
              play: bool = True) -> str:
        """Convert text to speech and optionally play it.
        
        Args:
            text: Text to convert to speech
            language: Language code (defaults to instance default)
            accent: Accent code 'uk', 'us', 'au', etc.
            slow: Speak slowly
            play: Whether to play the audio immediately
            
        Returns:
            Path to generated audio file, or error message
        """
        if not _HAS_GTTS:
            return "TTS unavailable: gTTS not installed. Install with: pip install gtts"
        
        lang = language or self.default_language
        tld = self.ACCENTS.get(accent or self.default_accent, "co.uk")
        
        # Clean text for speech
        clean_text = self._clean_for_speech(text)
        
        if not clean_text:
            return "Error: No speakable text after cleaning"
        
        # Generate audio file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_path = self.voice_dir / f"tts_{timestamp}.mp3"
        
        try:
            tts = gTTS(text=clean_text, lang=lang, tld=tld, slow=slow)
            tts.save(str(audio_path))
            self._temp_files.append(audio_path)
            
            logger.info(f"TTS audio saved: {audio_path}")
            
            # Play audio
            if play and _HAS_PYGAME:
                self._play_audio(str(audio_path))
            
            return str(audio_path)
            
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return f"TTS failed: {str(e)}"
    
    def speak_to_file(self, text: str, output_path: str,
                      language: Optional[str] = None,
                      accent: Optional[str] = None,
                      slow: bool = False) -> str:
        """Convert text to speech and save to a specific file path.
        
        Args:
            text: Text to convert
            output_path: Destination file path
            language: Language code
            accent: Accent code
            slow: Speak slowly
            
        Returns:
            Path to saved file, or error message
        """
        if not _HAS_GTTS:
            return "TTS unavailable: gTTS not installed"
        
        lang = language or self.default_language
        tld = self.ACCENTS.get(accent or self.default_accent, "co.uk")
        clean_text = self._clean_for_speech(text)
        
        try:
            tts = gTTS(text=clean_text, lang=lang, tld=tld, slow=slow)
            tts.save(output_path)
            return output_path
        except Exception as e:
            return f"TTS save failed: {str(e)}"
    
    # ── Audio Playback ──────────────────────────────────────────────────
    
    def _play_audio(self, file_path: str):
        """Play an audio file using pygame."""
        if not _HAS_PYGAME:
            logger.warning("Audio playback unavailable: pygame not installed")
            return
        
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
                
            pygame.mixer.quit()
            
        except Exception as e:
            logger.error(f"Audio playback error: {e}")
    
    def play_file(self, file_path: str) -> bool:
        """Play an existing audio file.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            True if playback started successfully
        """
        if not _HAS_PYGAME:
            return False
        
        try:
            pygame.mixer.init()
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            return True
        except Exception as e:
            logger.error(f"Failed to play {file_path}: {e}")
            return False
    
    # ── Audio Utilities ─────────────────────────────────────────────────
    
    def _clean_for_speech(self, text: str, max_length: int = 500) -> str:
        """Clean text for speech output.
        
        Removes markdown, code blocks, URLs, and excessive formatting
        to produce natural-sounding speech.
        
        Args:
            text: Raw text input
            max_length: Maximum characters for speech
            
        Returns:
            Cleaned text suitable for TTS
        """
        import re
        
        # Remove code blocks
        text = re.sub(r'```[\s\S]*?```', ' Code block omitted. ', text)
        # Remove inline code
        text = re.sub(r'`[^`]+`', ' code ', text)
        # Remove markdown headers
        text = re.sub(r'#{1,6}\s+', '', text)
        # Remove bold/italic markers
        text = re.sub(r'[*_~`]{1,2}', '', text)
        # Replace URLs
        text = re.sub(r'https?://\S+', ' link ', text)
        # Remove markdown links [text](url)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Replace multiple whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        return text
    
    def get_audio_files(self) -> List[Dict]:
        """List all generated audio files.
        
        Returns:
            List of dicts with file info
        """
        files = []
        for f in sorted(self.voice_dir.glob("*.mp3"), key=lambda x: x.stat().st_mtime, reverse=True):
            stat = f.stat()
            files.append({
                "name": f.name,
                "path": str(f),
                "size_kb": round(stat.st_size / 1024, 1),
                "created": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        return files
    
    def cleanup(self, max_age_hours: int = 24):
        """Remove temporary audio files.
        
        Args:
            max_age_hours: Remove files older than this many hours
        """
        cutoff = time.time() - (max_age_hours * 3600)
        removed = 0
        
        # Clean tracked temp files
        for f in list(self._temp_files):
            try:
                if f.exists() and f.stat().st_mtime < cutoff:
                    f.unlink()
                    self._temp_files.remove(f)
                    removed += 1
            except Exception:
                pass
        
        # Clean old files in voice directory
        for f in self.voice_dir.glob("*.mp3"):
            try:
                if f.stat().st_mtime < cutoff:
                    f.unlink()
                    removed += 1
            except Exception:
                pass
        
        logger.info(f"Cleaned up {removed} audio files")
        return removed
    
    # ── Status ──────────────────────────────────────────────────────────
    
    def status(self) -> Dict:
        """Get voice engine status and capabilities.
        
        Returns:
            Dict with capability flags and configuration
        """
        return {
            "status": "ready",
            "stt_available": _HAS_SPEECH,
            "tts_available": _HAS_GTTS,
            "playback_available": _HAS_PYGAME,
            "pydub_available": _HAS_PYDUB,
            "is_listening": self.is_listening,
            "default_language": self.default_language,
            "default_accent": self.default_accent,
            "supported_languages": self.SUPPORTED_LANGUAGES,
            "voice_dir": str(self.voice_dir),
            "audio_files_count": len(list(self.voice_dir.glob("*.mp3")))
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  FASTAPI-COMPATIBLE INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

_engine_instance: Optional[VoiceEngine] = None

def _get_engine() -> VoiceEngine:
    """Get or create the singleton voice engine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = VoiceEngine()
    return _engine_instance


def voice_status() -> Dict:
    """Get voice engine status."""
    engine = _get_engine()
    return {
        "status": "success",
        **engine.status(),
        "timestamp": datetime.utcnow().isoformat()
    }


def voice_listen(timeout: int = 5, language: str = "en-US") -> Dict:
    """Listen for voice input and return transcription."""
    engine = _get_engine()
    text = engine.listen(timeout=timeout, language=language)
    
    return {
        "status": "success" if text else "no_speech",
        "transcribed_text": text,
        "language": language,
        "timestamp": datetime.utcnow().isoformat()
    }


def voice_speak(text: str, language: str = "en",
                accent: str = "uk", slow: bool = False) -> Dict:
    """Convert text to speech."""
    engine = _get_engine()
    audio_path = engine.speak(text, language=language, accent=accent, slow=slow)
    
    is_error = not audio_path.endswith(".mp3")
    return {
        "status": "error" if is_error else "success",
        "audio_file": None if is_error else audio_path,
        "error": audio_path if is_error else None,
        "text": text[:200],
        "timestamp": datetime.utcnow().isoformat()
    }


def voice_files() -> Dict:
    """List generated audio files."""
    engine = _get_engine()
    files = engine.get_audio_files()
    
    return {
        "status": "success",
        "total_files": len(files),
        "files": files,
        "timestamp": datetime.utcnow().isoformat()
    }


def voice_cleanup(max_age_hours: int = 24) -> Dict:
    """Clean up old audio files."""
    engine = _get_engine()
    removed = engine.cleanup(max_age_hours=max_age_hours)
    
    return {
        "status": "success",
        "files_removed": removed,
        "max_age_hours": max_age_hours,
        "timestamp": datetime.utcnow().isoformat()
    }
