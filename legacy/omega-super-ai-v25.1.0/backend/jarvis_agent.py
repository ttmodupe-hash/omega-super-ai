#!/usr/bin/env python3
"""
Luqi AI v25.1.0 "JARVIS" — Autonomous Agent Engine
=====================================================
Integrates persistent memory, web search, local system control, voice processing,
and OpenAI-compatible function calling into Luqi AI's Prometheus backend.

Capabilities:
- Persistent SQLite conversation memory across sessions
- DuckDuckGo web search for real-time information
- Local application launcher and file manager
- Python code execution in restricted sandbox
- Voice input (STT) and voice output (TTS)
- Dynamic tool registry with OpenAI function calling
- User fact storage and personalization

Usage:
    from backend.jarvis_agent import JarvisAgent
    agent = JarvisAgent()
    response = agent.chat("What's the weather in Lagos?")
"""

import json
import logging
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# ── Optional Dependencies ────────────────────────────────────────────────────

try:
    from duckduckgo_search import DDGS
    _HAS_DDGS = True
except ImportError:
    _HAS_DDGS = False

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
    from openai import OpenAI
    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

PROJECT_ROOT = Path(__file__).parent.parent
DB_DIR = PROJECT_ROOT / "data"
DB_FILE = DB_DIR / "jarvis_memory.db"
VOICE_DIR = PROJECT_ROOT / "data" / "voice"

DB_DIR.mkdir(parents=True, exist_ok=True)
VOICE_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_MODEL = "gpt-4o"
MAX_MEMORY_CONTEXT = 10


# ═══════════════════════════════════════════════════════════════════════════════
#  PERSISTENT MEMORY (SQLite)
# ═══════════════════════════════════════════════════════════════════════════════

class ConversationMemory:
    """SQLite-backed persistent conversation memory.
    
    Stores all user/assistant interactions with timestamps,
    supports retrieval by time range, keyword search, and
    context window assembly for agent prompts.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(db_path or DB_FILE)
        self._local = threading.local()
        self._init_db()
    
    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT DEFAULT 'default',
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tool_calls TEXT,
                metadata TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                confidence REAL DEFAULT 1.0
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tool_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_name TEXT NOT NULL,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                input_summary TEXT,
                output_summary TEXT,
                duration_ms INTEGER,
                success INTEGER DEFAULT 1
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"Memory database initialized at {self.db_path}")
    
    def save_message(self, role: str, content: str, 
                     session_id: str = "default",
                     tool_calls: Optional[List[Dict]] = None,
                     metadata: Optional[Dict] = None):
        try:
            conn = self._conn()
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO conversation_history 
                   (session_id, timestamp, role, content, tool_calls, metadata)
                   VALUES (?, datetime('now'), ?, ?, ?, ?)""",
                (session_id, role, content,
                 json.dumps(tool_calls) if tool_calls else None,
                 json.dumps(metadata) if metadata else None)
            )
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to save message: {e}")
    
    def get_recent_context(self, limit: int = MAX_MEMORY_CONTEXT,
                           session_id: str = "default") -> List[Dict[str, str]]:
        try:
            conn = self._conn()
            cursor = conn.cursor()
            cursor.execute(
                """SELECT role, content FROM conversation_history
                   WHERE session_id = ?
                   ORDER BY id DESC LIMIT ?""",
                (session_id, limit)
            )
            rows = cursor.fetchall()
            return [{"role": r[0], "content": r[1]} for r in reversed(rows)]
        except Exception as e:
            logger.error(f"Failed to retrieve memories: {e}")
            return []
    
    def search_memories(self, keyword: str, limit: int = 10) -> List[Dict]:
        try:
            conn = self._conn()
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM conversation_history
                   WHERE content LIKE ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (f"%{keyword}%", limit)
            )
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []
    
    def store_fact(self, key: str, value: str, 
                   category: str = "general", confidence: float = 1.0):
        try:
            conn = self._conn()
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO user_memory (key, value, category, confidence)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(key) DO UPDATE SET
                   value = excluded.value,
                   timestamp = datetime('now'),
                   confidence = excluded.confidence""",
                (key, value, category, confidence)
            )
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to store fact: {e}")
    
    def get_facts(self, category: Optional[str] = None, limit: int = 20) -> List[Dict]:
        try:
            conn = self._conn()
            cursor = conn.cursor()
            if category:
                cursor.execute(
                    "SELECT * FROM user_memory WHERE category = ? ORDER BY timestamp DESC LIMIT ?",
                    (category, limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM user_memory ORDER BY timestamp DESC LIMIT ?",
                    (limit,)
                )
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to retrieve facts: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        try:
            conn = self._conn()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM conversation_history")
            total_messages = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM user_memory")
            total_facts = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM tool_usage")
            total_tool_calls = cursor.fetchone()[0]
            cursor.execute(
                "SELECT tool_name, COUNT(*) as count FROM tool_usage GROUP BY tool_name ORDER BY count DESC"
            )
            tool_stats = [{"tool": row[0], "uses": row[1]} for row in cursor.fetchall()]
            return {
                "total_messages": total_messages,
                "total_facts": total_facts,
                "total_tool_calls": total_tool_calls,
                "tool_breakdown": tool_stats,
                "db_path": self.db_path
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}
    
    def clear_session(self, session_id: str = "default"):
        try:
            conn = self._conn()
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM conversation_history WHERE session_id = ?",
                (session_id,)
            )
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to clear session: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
#  TOOL REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

class ToolRegistry:
    """Dynamic tool registry for the agent with OpenAI function calling support."""
    
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._schemas: Dict[str, Dict] = {}
        self._metadata: Dict[str, Dict] = {}
    
    def register(self, name: str, func: Callable, schema: Dict,
                 description: str = "", category: str = "general"):
        self._tools[name] = func
        self._schemas[name] = schema
        self._metadata[name] = {
            "description": description or schema.get("description", ""),
            "category": category,
            "registered_at": datetime.utcnow().isoformat()
        }
        logger.info(f"Tool registered: {name}")
    
    def unregister(self, name: str):
        self._tools.pop(name, None)
        self._schemas.pop(name, None)
        self._metadata.pop(name, None)
    
    def get_function(self, name: str) -> Optional[Callable]:
        return self._tools.get(name)
    
    def get_schema(self, name: str) -> Optional[Dict]:
        return self._schemas.get(name)
    
    def list_tools(self) -> List[Dict]:
        return [
            {
                "name": name,
                "description": meta["description"],
                "category": meta["category"],
                "schema": self._schemas.get(name, {})
            }
            for name, meta in self._metadata.items()
        ]
    
    def get_openai_schemas(self) -> List[Dict]:
        schemas = []
        for name, schema in self._schemas.items():
            schemas.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": schema.get("description", ""),
                    "parameters": schema.get("parameters", {"type": "object", "properties": {}})
                }
            })
        return schemas
    
    def invoke(self, name: str, arguments: Dict) -> str:
        func = self._tools.get(name)
        if not func:
            return f"Error: Tool '{name}' not found."
        
        start = time.time()
        try:
            result = func(**arguments)
            return str(result)
        except Exception as e:
            logger.error(f"Tool '{name}' failed: {e}")
            return f"Tool '{name}' failed: {str(e)}"


# ═══════════════════════════════════════════════════════════════════════════════
#  BUILT-IN TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

def search_the_web(query: str) -> str:
    """Search the live web for real-time information."""
    if not _HAS_DDGS:
        return "Web search unavailable: duckduckgo-search not installed. Install with: pip install duckduckgo-search"
    
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=5)]
            if not results:
                return f"No results found for '{query}'."
            
            formatted = []
            for i, r in enumerate(results, 1):
                formatted.append(f"[{i}] {r['title']}\n    {r['body'][:200]}...\n    Source: {r.get('href', 'N/A')}")
            
            return f"Web search results for '{query}':\n\n" + "\n\n".join(formatted)
    except Exception as e:
        return f"Web search failed: {str(e)}"


def open_local_application(app_name: str) -> str:
    """Launch a local system application."""
    try:
        platform = sys.platform
        if platform == "win32":
            os.system(f"start {app_name}")
        elif platform == "darwin":
            subprocess.run(["open", "-a", app_name], check=True)
        else:
            subprocess.run([app_name], check=True, 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"Launched {app_name} successfully."
    except Exception as e:
        return f"Failed to launch {app_name}: {str(e)}"


def get_system_info() -> str:
    """Get system information."""
    info = {
        "platform": sys.platform,
        "python_version": sys.version,
        "cwd": os.getcwd(),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return json.dumps(info, indent=2)


def read_file(path: str, offset: int = 0, limit: int = 100) -> str:
    """Read a local file's contents."""
    try:
        file_path = Path(path).resolve()
        project_root = Path(__file__).parent.parent.resolve()
        if not str(file_path).startswith(str(project_root)):
            return "Error: Path is outside the project directory."
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            start = offset
            end = offset + limit
            selected = lines[start:end]
            return f"Lines {start+1}-{min(end, len(lines))} of {len(lines)}:\n" + "".join(selected)
    except Exception as e:
        return f"Error reading file: {str(e)}"


def write_file(path: str, content: str, append: bool = False) -> str:
    """Write content to a local file."""
    try:
        file_path = Path(path).resolve()
        project_root = Path(__file__).parent.parent.resolve()
        if not str(file_path).startswith(str(project_root)):
            return "Error: Path is outside the project directory."
        
        mode = 'a' if append else 'w'
        with open(file_path, mode, encoding='utf-8') as f:
            f.write(content)
        return f"File written successfully: {path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


def run_python_code(code: str) -> str:
    """Execute Python code in a restricted environment and return output."""
    try:
        safe_globals = {
            "__builtins__": {
                "len": len, "range": range, "enumerate": enumerate,
                "zip": zip, "map": map, "filter": filter,
                "sum": sum, "min": min, "max": max, "abs": abs,
                "round": round, "pow": pow, "divmod": divmod,
                "str": str, "int": int, "float": float, "bool": bool,
                "list": list, "dict": dict, "set": set, "tuple": tuple,
                "print": print, "sorted": sorted, "reversed": reversed,
                "isinstance": isinstance, "hasattr": hasattr, "getattr": getattr,
                "Exception": Exception, "TypeError": TypeError, "ValueError": ValueError,
                "json": json, "math": __import__("math"),
                "datetime": datetime, "time": time,
            }
        }
        
        import io
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        
        exec(code, safe_globals)
        
        output = sys.stdout.getvalue()
        sys.stdout = old_stdout
        
        return output if output else "Code executed successfully (no output)."
    except Exception as e:
        sys.stdout = old_stdout
        return f"Code execution error: {str(e)}"


# ═══════════════════════════════════════════════════════════════════════════════
#  VOICE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class VoiceEngine:
    """Speech-to-text and text-to-speech processing engine."""
    
    SUPPORTED_LANGUAGES = {
        "en": "English", "es": "Spanish", "fr": "French",
        "de": "German", "it": "Italian", "pt": "Portuguese",
        "ru": "Russian", "ja": "Japanese", "ko": "Korean",
        "zh": "Chinese", "ar": "Arabic", "hi": "Hindi",
        "yo": "Yoruba", "ig": "Igbo", "ha": "Hausa",
        "sw": "Swahili", "af": "Afrikaans", "zu": "Zulu"
    }
    
    ACCENTS = {
        "uk": "co.uk", "us": "com", "au": "com.au",
        "ca": "ca", "in": "co.in", "ie": "ie", "za": "co.za"
    }
    
    def __init__(self, voice_dir: Optional[str] = None,
                 default_language: str = "en",
                 default_accent: str = "uk"):
        self.voice_dir = Path(voice_dir or VOICE_DIR)
        self.voice_dir.mkdir(parents=True, exist_ok=True)
        self.default_language = default_language
        self.default_accent = default_accent
        self.is_listening = False
        self._temp_files: List[Path] = []
        self._recognizer = None
        
        if _HAS_SPEECH:
            self._recognizer = sr.Recognizer()
            self._recognizer.dynamic_energy_threshold = True
            self._recognizer.energy_threshold = 300
            self._recognizer.pause_threshold = 0.8
    
    def listen(self, timeout: int = 5, phrase_time_limit: int = 8,
               language: str = "en-US", ambient_duration: float = 0.5) -> str:
        if not _HAS_SPEECH:
            return ""
        
        if self._recognizer is None:
            self._recognizer = sr.Recognizer()
        
        try:
            with sr.Microphone() as source:
                logger.info(f"Listening (timeout={timeout}s, lang={language})...")
                self._recognizer.adjust_for_ambient_noise(source, duration=ambient_duration)
                audio = self._recognizer.listen(source, timeout=timeout,
                                                  phrase_time_limit=phrase_time_limit)
                text = self._recognizer.recognize_google(audio, language=language)
                logger.info(f"Transcribed: '{text}'")
                return text
        except (sr.WaitTimeoutError, sr.UnknownValueError, sr.RequestError, Exception):
            return ""
    
    def listen_continuous(self, callback: Callable, stop_event: threading.Event, language: str = "en-US"):
        if not _HAS_SPEECH:
            return
        
        if self._recognizer is None:
            self._recognizer = sr.Recognizer()
        
        self.is_listening = True
        try:
            with sr.Microphone() as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=1)
                while not stop_event.is_set() and self.is_listening:
                    try:
                        audio = self._recognizer.listen(source, timeout=1, phrase_time_limit=10)
                        text = self._recognizer.recognize_google(audio, language=language)
                        if text:
                            callback(text)
                    except (sr.WaitTimeoutError, sr.UnknownValueError):
                        continue
                    except Exception as e:
                        logger.error(f"Continuous listen error: {e}")
        finally:
            self.is_listening = False
    
    def stop_listening(self):
        self.is_listening = False
    
    def speak(self, text: str, language: Optional[str] = None,
              accent: Optional[str] = None, slow: bool = False,
              play: bool = True) -> str:
        if not _HAS_GTTS:
            return "TTS unavailable: gTTS not installed. Install with: pip install gtts"
        
        lang = language or self.default_language
        tld = self.ACCENTS.get(accent or self.default_accent, "co.uk")
        clean_text = self._clean_for_speech(text)
        
        if not clean_text:
            return "Error: No speakable text after cleaning"
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_path = self.voice_dir / f"tts_{timestamp}.mp3"
        
        try:
            tts = gTTS(text=clean_text, lang=lang, tld=tld, slow=slow)
            tts.save(str(audio_path))
            self._temp_files.append(audio_path)
            
            if play and _HAS_PYGAME:
                self._play_audio(str(audio_path))
            
            return str(audio_path)
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return f"TTS failed: {str(e)}"
    
    def _play_audio(self, file_path: str):
        if not _HAS_PYGAME:
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
    
    def _clean_for_speech(self, text: str, max_length: int = 500) -> str:
        import re
        text = re.sub(r'```[\s\S]*?```', ' Code block omitted. ', text)
        text = re.sub(r'`[^`]+`', ' code ', text)
        text = re.sub(r'#{1,6}\s+', '', text)
        text = re.sub(r'[*_~`]{1,2}', '', text)
        text = re.sub(r'https?://\S+', ' link ', text)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) > max_length:
            text = text[:max_length] + "..."
        return text
    
    def get_audio_files(self) -> List[Dict]:
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
        cutoff = time.time() - (max_age_hours * 3600)
        removed = 0
        for f in list(self._temp_files):
            try:
                if f.exists() and f.stat().st_mtime < cutoff:
                    f.unlink()
                    self._temp_files.remove(f)
                    removed += 1
            except Exception:
                pass
        for f in self.voice_dir.glob("*.mp3"):
            try:
                if f.stat().st_mtime < cutoff:
                    f.unlink()
                    removed += 1
            except Exception:
                pass
        return removed
    
    def status(self) -> Dict:
        return {
            "status": "ready",
            "stt_available": _HAS_SPEECH,
            "tts_available": _HAS_GTTS,
            "playback_available": _HAS_PYGAME,
            "is_listening": self.is_listening,
            "default_language": self.default_language,
            "default_accent": self.default_accent,
            "supported_languages": self.SUPPORTED_LANGUAGES,
            "voice_dir": str(self.voice_dir),
            "audio_files_count": len(list(self.voice_dir.glob("*.mp3")))
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  JARVIS AGENT
# ═══════════════════════════════════════════════════════════════════════════════

class JarvisAgent:
    """Main agent class — orchestrates memory, tools, voice, and AI."""
    
    SYSTEM_PROMPT = """You are Luqi AI v25 — an advanced autonomous assistant codenamed "Prometheus". 
You have access to powerful tools including web search, local application control, file management, 
and code execution. You remember conversations across sessions.

Guidelines:
- Be direct, helpful, and technically precise
- Use tools when they provide better answers than your training data
- Address the user respectfully
- If asked about real-time information, ALWAYS use web_search
- When launching apps or modifying files, confirm the action first
- Keep responses concise unless detail is requested
"""
    
    def __init__(self, api_key: Optional[str] = None, 
                 model: str = DEFAULT_MODEL,
                 db_path: Optional[str] = None):
        self.model = model
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.memory = ConversationMemory(db_path=db_path)
        self.voice = VoiceEngine()
        self.tools = ToolRegistry()
        self._register_builtin_tools()
        
        if _HAS_OPENAI:
            self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        else:
            self.client = None
            logger.warning("OpenAI client not available. Running in tool-only mode.")
    
    def _register_builtin_tools(self):
        self.tools.register(
            name="web_search",
            func=search_the_web,
            schema={
                "description": "Search the live web for real-time information, news, current events, sports scores, weather, stock prices, or any up-to-date data.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query. Be specific for best results."}
                    },
                    "required": ["query"]
                }
            },
            category="information"
        )
        
        self.tools.register(
            name="open_application",
            func=open_local_application,
            schema={
                "description": "Launch a local application on the user's computer.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "app_name": {"type": "string", "description": "Name or command of the application."}
                    },
                    "required": ["app_name"]
                }
            },
            category="system"
        )
        
        self.tools.register(
            name="system_info",
            func=get_system_info,
            schema={
                "description": "Get information about the current system.",
                "parameters": {"type": "object", "properties": {}},
                "required": []
            },
            category="system"
        )
        
        self.tools.register(
            name="read_file",
            func=read_file,
            schema={
                "description": "Read contents of a file within the project directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "offset": {"type": "integer"},
                        "limit": {"type": "integer"}
                    },
                    "required": ["path"]
                }
            },
            category="files"
        )
        
        self.tools.register(
            name="write_file",
            func=write_file,
            schema={
                "description": "Write or append content to a file within the project directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                        "append": {"type": "boolean"}
                    },
                    "required": ["path", "content"]
                }
            },
            category="files"
        )
        
        self.tools.register(
            name="run_python",
            func=run_python_code,
            schema={
                "description": "Execute Python code in a restricted sandbox and return the output.",
                "parameters": {
                    "type": "object",
                    "properties": {"code": {"type": "string"}},
                    "required": ["code"]
                }
            },
            category="code"
        )
    
    def chat(self, message: str, use_tools: bool = True,
             store_memory: bool = True) -> str:
        if not self.client:
            return "Error: OpenAI client not initialized. Set OPENAI_API_KEY."
        
        if store_memory:
            self.memory.save_message("user", message, session_id=self.session_id)
        
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]
        
        facts = self.memory.get_facts(limit=5)
        if facts:
            fact_text = "\n".join([f"- {f['key']}: {f['value']}" for f in facts])
            messages.append({"role": "system", "content": f"Known facts:\n{fact_text}"})
        
        messages.extend(self.memory.get_recent_context(
            limit=MAX_MEMORY_CONTEXT, session_id=self.session_id
        ))
        messages.append({"role": "user", "content": message})
        
        try:
            if use_tools and self.tools.list_tools():
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self.tools.get_openai_schemas(),
                    tool_choice="auto"
                )
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages
                )
            
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
            
            if tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": response_message.content or "",
                    "tool_calls": [
                        {"id": tc.id, "type": "function", 
                         "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                        for tc in tool_calls
                    ]
                })
                
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    logger.info(f"Executing tool: {function_name}({function_args})")
                    
                    func = self.tools.get_function(function_name)
                    tool_output = func(**function_args) if func else f"Tool '{function_name}' not found."
                    
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": str(tool_output)
                    })
                
                second_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages
                )
                reply = second_response.choices[0].message.content
            else:
                reply = response_message.content
            
            if store_memory and reply:
                self.memory.save_message("assistant", reply, session_id=self.session_id)
            
            return reply or "I processed your request but have no text response."
            
        except Exception as e:
            logger.error(f"Agent error: {e}")
            return f"Agent error: {str(e)}"
    
    def listen_and_respond(self, timeout: int = 5) -> Dict[str, str]:
        user_input = self.voice.listen(timeout=timeout)
        if not user_input:
            return {"input": "", "response": "I didn't catch that. Could you repeat?", "audio_path": ""}
        
        response = self.chat(user_input)
        audio_path = self.voice.speak(response)
        
        return {"input": user_input, "response": response, "audio_path": audio_path}
    
    def speak(self, text: str) -> str:
        return self.voice.speak(text)
    
    def store_fact(self, key: str, value: str, category: str = "general"):
        self.memory.store_fact(key, value, category)
    
    def get_facts(self, category: Optional[str] = None) -> List[Dict]:
        return self.memory.get_facts(category)
    
    def search_memories(self, keyword: str) -> List[Dict]:
        return self.memory.search_memories(keyword)
    
    def get_stats(self) -> Dict[str, Any]:
        return self.memory.get_stats()
    
    def clear_session(self):
        self.memory.clear_session(self.session_id)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def register_tool(self, name: str, func: Callable, schema: Dict,
                      description: str = "", category: str = "custom"):
        self.tools.register(name, func, schema, description, category)
    
    def list_tools(self) -> List[Dict]:
        return self.tools.list_tools()
    
    def cleanup(self):
        self.voice.cleanup()


# ═══════════════════════════════════════════════════════════════════════════════
#  FASTAPI INTERFACE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

_agent_instance: Optional[JarvisAgent] = None

def _get_agent() -> JarvisAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = JarvisAgent()
    return _agent_instance


def agent_chat(message: str, session_id: Optional[str] = None,
               use_tools: bool = True) -> Dict[str, Any]:
    agent = _get_agent()
    if session_id:
        agent.session_id = session_id
    
    reply = agent.chat(message, use_tools=use_tools)
    
    return {
        "status": "success",
        "version": "25.1.0",
        "codename": "JARVIS",
        "message": reply,
        "session_id": agent.session_id,
        "tools_used": [t["name"] for t in agent.list_tools()],
        "timestamp": datetime.utcnow().isoformat()
    }


def agent_voice_listen(timeout: int = 5) -> Dict[str, Any]:
    agent = _get_agent()
    result = agent.listen_and_respond(timeout=timeout)
    
    return {
        "status": "success" if result["input"] else "no_input",
        "transcribed_input": result["input"],
        "agent_response": result["response"],
        "audio_file": result["audio_path"],
        "session_id": agent.session_id,
        "timestamp": datetime.utcnow().isoformat()
    }


def agent_speak(text: str) -> Dict[str, Any]:
    agent = _get_agent()
    audio_path = agent.speak(text)
    
    return {
        "status": "success" if audio_path.endswith(".mp3") else "error",
        "audio_file": audio_path,
        "text_spoken": text[:100],
        "timestamp": datetime.utcnow().isoformat()
    }


def agent_memory_search(keyword: str) -> Dict[str, Any]:
    agent = _get_agent()
    results = agent.search_memories(keyword)
    
    return {
        "status": "success",
        "query": keyword,
        "results_count": len(results),
        "results": results[:10],
        "timestamp": datetime.utcnow().isoformat()
    }


def agent_memory_facts(category: Optional[str] = None) -> Dict[str, Any]:
    agent = _get_agent()
    facts = agent.get_facts(category)
    
    return {
        "status": "success",
        "category": category or "all",
        "facts_count": len(facts),
        "facts": facts,
        "timestamp": datetime.utcnow().isoformat()
    }


def agent_store_fact(key: str, value: str, 
                     category: str = "general") -> Dict[str, Any]:
    agent = _get_agent()
    agent.store_fact(key, value, category)
    
    return {
        "status": "success",
        "stored": {"key": key, "value": value, "category": category},
        "timestamp": datetime.utcnow().isoformat()
    }


def agent_stats() -> Dict[str, Any]:
    agent = _get_agent()
    stats = agent.get_stats()
    
    return {
        "status": "success",
        **stats,
        "available_tools": len(agent.list_tools()),
        "tool_list": [t["name"] for t in agent.list_tools()],
        "timestamp": datetime.utcnow().isoformat()
    }


def agent_list_tools() -> Dict[str, Any]:
    agent = _get_agent()
    tools = agent.list_tools()
    
    return {
        "status": "success",
        "total_tools": len(tools),
        "tools": tools,
        "timestamp": datetime.utcnow().isoformat()
    }


def agent_clear_session(session_id: Optional[str] = None) -> Dict[str, Any]:
    agent = _get_agent()
    if session_id:
        agent.memory.clear_session(session_id)
    else:
        agent.clear_session()
    
    return {
        "status": "success",
        "message": "Session memory cleared.",
        "new_session_id": agent.session_id,
        "timestamp": datetime.utcnow().isoformat()
    }


def web_search(query: str) -> Dict[str, Any]:
    results = search_the_web(query)
    
    return {
        "status": "success",
        "query": query,
        "results": results,
        "timestamp": datetime.utcnow().isoformat()
    }


def run_code(code: str) -> Dict[str, Any]:
    output = run_python_code(code)
    
    return {
        "status": "success",
        "code": code[:200],
        "output": output,
        "timestamp": datetime.utcnow().isoformat()
    }
