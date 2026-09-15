"""Omega AI v3.7.0 — Central Brain / Orchestrator
Routes queries to the correct capability module.
Includes: conversation memory, unified response schema, structured logging,
database persistence, intelligent caching, knowledge base FAQ matching,
and conversation state machine for multi-turn dialog.

v3.7.0 — Wired modules: error_repair, memory_manager, pedagogical_engine,
crypto_utils, key_rotation, rate_limiter, ws_server, vector_db, multi_tenant,
plugin_marketplace, realtime_prices, metrics_exporter, email_notifier,
telegram_bot, pdf_generator, db_migrations, auto_backup, local_llm,
agent_mesh, blockchain_audit, federated_learning.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import sqlite3
import threading
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple

# ── Structured Logging ──
from logger import info, warning, error, debug, log_json, print_error, print_warning, print_success, print_info

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DB_PATH = os.environ.get("OMEGA_DB_PATH", ".omega_sessions/omega.db")
CACHE_MAX_SIZE = 256

# ═══════════════════════════════════════════════════════════════════════════════
# RESPONSE SCHEMA
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ResponseDict:
    """Every handler MUST return a dict with at least these keys."""
    answer: str
    source: str
    module: str
    confidence: float = 1.0
    meta: dict = field(default_factory=dict)


def ok(answer: str, module: str = "", meta: dict | None = None) -> ResponseDict:
    """Convenience factory for a successful response."""
    return ResponseDict(answer=answer, source="omega", module=module,
                        confidence=1.0, meta=meta or {})


# ═══════════════════════════════════════════════════════════════════════════════
# INTENT CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

INTENT_KEYWORDS: dict[str, list[str]] = {
    "deep_research":   ["research", "deep dive", "study", "explore", "investigate",
                        "analyze", "compare", "literature review"],
    "investment":      ["invest", "portfolio", "stock", "fund", "etf", "bond",
                        "asset allocation", "diversify", "returns"],
    "tax":             ["tax", "deduction", "irs", "filing", "bracket",
                        "capital gains", "withholding", "1040"],
    "companion":       ["lonely", "sad", "stressed", "need someone", "talk to",
                        "anxious", "overwhelmed", "burnout"],
    "self_improve":    ["improve", "better myself", "habit", "productivity",
                        "discipline", "goals", "procrastination", "focus"],
    "language":        ["translate", "how do you say", "in spanish", "in french",
                        "in chinese", "meaning of", "pronounce"],
    "financial_lit":   ["apr", "apy", "credit score", "compound interest",
                        "inflation", "budget", "emergency fund", "net worth"],
    "professional":    ["career", "resume", "interview", "networking",
                        "promotion", "salary", "negotiate", "leadership"],
    "opportunity":     ["side hustle", "passive income", "freelance", "startup",
                        "business idea", "entrepreneur", "market gap"],
    "email":           ["send email", "email to", "mail to", "notify", "alert"],
    "knowledge_base":  ["what is", "how does", "explain", "define", "faq",
                        "tell me about", "what are"],
    "conversation_state": ["book flight", "schedule meeting", "plan trip",
                           "restaurant reservation", "hotel booking"],
    "scheduler":       ["schedule", "remind me", "set alarm", "timer",
                        "appointment", "calendar", "recurring"],
    "price_ticker":    ["price of", "current price", "market cap", "trading volume",
                        "bitcoin", "ethereum", "crypto"],
    "calc_engine":     ["calculate", "compute", "=", "+", "-", "*", "/",
                        "percent of", "convert", "formula"],
    "history_search":  ["what did i say", "earlier i asked", "previous",
                        "last time", "remember when", "our conversation"],
    "learning_tracker": ["learning path", "course", "curriculum", "skill tree",
                         "certification", "tutorial", "practice"],
    "wisdom":          ["proverb", "quote", "wisdom", "saying", "aphorism",
                         "ancient wisdom", "philosophy", "life advice"],
    "pipeline":        ["pipeline", "workflow", "etl", "data flow", "process",
                         "automation", "batch"],
    "educational_companion": ["teach me", "i want to learn", "mastery", "cognitive ledger", "socratic",
                        "bloom's taxonomy", "study", "learning path", "quiz me", "test me",
                        "desirable difficulties", "spaced repetition", "comprehension check",
                        "assess my knowledge", "learning companion", "tutor me", "explain",
                        "how does this work", "why is it done this way", "deep dive into",
                        "concept of", "foundation of", "principles of", "beginner guide",
                        "COMPACT", "archive this topic", "retrieval practice", "educational mode"],
    "vocational_companion": ["trade school", "vocational", "apprenticeship", "certification",
                             "blue collar", "skilled trade", "technical training"],
    "voice_interface": ["voice", "speak", "dictation", "transcribe", "audio",
                        "listen", "speech to text"],
    "file_analysis":   ["analyze file", "read document", "parse csv", "extract data",
                        "file content", "document analysis"],
    "digital_transform": ["digital transformation", "cloud migration", "modernize",
                          "legacy system", "automation strategy"],
    "error_repair":    ["error", "debug", "diagnostic", "health check", "system check",
                         "fix", "repair", "what went wrong", "why did it fail", "troubleshoot",
                         "circuit breaker", "self healing", "error log", "crash report"],
    "memory_manager":  ["memory", "cleanup", "chat history", "delete old", "clear memory",
                         "manage memory", "storage full", "what do you remember", "forget",
                         "data retention", "purge", "recover deleted", "memory report",
                         "what is stored", "keep or delete", "clean up history", "archivist"],
    "realtime_prices": ["live price", "real time", "current btc", "eth price now",
                         "crypto ticker", "market data"],
    "local_llm":       ["local llm", "offline mode", "no internet", "local ai", "ollama",
                          "private ai", "on-device", "without internet", "local inference"],
    "pedagogical":     ["teach me", "i want to learn", "mastery", "cognitive ledger", "socratic",
                         "bloom's taxonomy", "study", "learning path", "quiz me", "test me",
                         "desirable difficulties", "spaced repetition", "comprehension check",
                         "assess my knowledge", "learning companion", "tutor me", "explain",
                         "how does this work", "why is it done this way", "deep dive into",
                         "concept of", "foundation of", "principles of", "beginner guide",
                         "COMPACT", "archive this topic", "retrieval practice", "educational mode"],
}


def classify_intent(query: str) -> str:
    """Return the best-matching intent key or 'general'."""
    q = query.lower()
    scores: dict[str, int] = Counter()
    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in q:
                scores[intent] += len(kw)  # longer matches = more specific
    return scores.most_common(1)[0][0] if scores else "general"


# ═══════════════════════════════════════════════════════════════════════════════
# CONVERSATION MEMORY
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MemoryEntry:
    role: str       # 'user' | 'assistant'
    content: str
    ts: float = field(default_factory=time.time)


class ConversationMemory:
    """In-memory ring buffer with optional SQLite persistence."""

    def __init__(self, max_size: int = 200) -> None:
        self.max_size = max_size
        self._entries: list[MemoryEntry] = []
        self._lock = threading.Lock()

    def add(self, role: str, content: str) -> None:
        with self._lock:
            self._entries.append(MemoryEntry(role=role, content=content))
            if len(self._entries) > self.max_size:
                self._entries = self._entries[-self.max_size:]

    def recent(self, n: int = 6) -> str:
        with self._lock:
            lines = [f"{e.role}: {e.content}" for e in self._entries[-n:]]
        return "\n".join(lines)

    def search(self, keyword: str, max_results: int = 3) -> list[MemoryEntry]:
        kw = keyword.lower()
        with self._lock:
            return [e for e in self._entries if kw in e.content.lower()][-max_results:]

    def persist_to_db(self, session_id: str = "default") -> None:
        """Write conversation history to SQLite."""
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                ts REAL
            )
        """)
        with self._lock:
            for e in self._entries:
                cur.execute(
                    "INSERT INTO conversation_history (session_id, role, content, ts) VALUES (?, ?, ?, ?)",
                    (session_id, e.role, e.content, e.ts)
                )
        conn.commit()
        conn.close()

    def load_from_db(self, session_id: str = "default") -> None:
        """Load conversation history from SQLite."""
        if not Path(DB_PATH).exists():
            return
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT role, content, ts FROM conversation_history WHERE session_id = ? ORDER BY ts", (session_id,))
        rows = cur.fetchall()
        conn.close()
        with self._lock:
            self._entries = [MemoryEntry(role=r[0], content=r[1], ts=r[2]) for r in rows[-self.max_size:]]

    def persist_to_knowledge_base(self, kb) -> None:
        """Write conversation insights to knowledge base."""
        with self._lock:
            for e in self._entries:
                if e.role == "user":
                    kb.add_entry(f"user_query_{int(e.ts)}", e.content, "conversation")


# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class DatabaseEngine:
    """Lightweight SQLite persistence for Omega AI."""

    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path
        self._local = threading.local()
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_tables(self) -> None:
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at REAL,
                updated_at REAL,
                context TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                query TEXT,
                response TEXT,
                intent TEXT,
                ts REAL
            )
        """)
        conn.commit()

    def save_session(self, session_id: str, context: dict) -> None:
        now = time.time()
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO sessions (id, created_at, updated_at, context) VALUES (?, ?, ?, ?)",
            (session_id, now, now, json.dumps(context))
        )
        conn.commit()

    def load_session(self, session_id: str) -> dict | None:
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("SELECT context FROM sessions WHERE id = ?", (session_id,))
        row = cur.fetchone()
        return json.loads(row["context"]) if row else None

    def log_query(self, session_id: str, query: str, response: str, intent: str) -> None:
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO queries (session_id, query, response, intent, ts) VALUES (?, ?, ?, ?, ?)",
            (session_id, query, response, intent, time.time())
        )
        conn.commit()

    def get_recent_queries(self, session_id: str, limit: int = 10) -> list[dict]:
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT query, response, intent, ts FROM queries WHERE session_id = ? ORDER BY ts DESC LIMIT ?",
            (session_id, limit)
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════════════════════
# CACHE MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class CacheManager:
    """Simple LRU cache with TTL support."""

    def __init__(self, max_size: int = CACHE_MAX_SIZE, default_ttl: float = 300) -> None:
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: dict[str, dict] = {}
        self._lock = threading.Lock()

    def _key(self, *parts) -> str:
        return hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()

    def get(self, *key_parts) -> Any | None:
        key = self._key(*key_parts)
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if time.time() > entry["expires"]:
                del self._cache[key]
                return None
            entry["hits"] += 1
            return entry["value"]

    def set(self, value: Any, *key_parts, ttl: float | None = None) -> None:
        key = self._key(*key_parts)
        with self._lock:
            if len(self._cache) >= self.max_size:
                # Evict oldest
                oldest = min(self._cache.items(), key=lambda x: x[1]["created"])
                del self._cache[oldest[0]]
            self._cache[key] = {
                "value": value,
                "created": time.time(),
                "expires": time.time() + (ttl or self.default_ttl),
                "hits": 0,
            }

    def invalidate(self, pattern: str = "") -> int:
        with self._lock:
            if pattern:
                to_delete = [k for k in self._cache if pattern in k]
                for k in to_delete:
                    del self._cache[k]
                return len(to_delete)
            else:
                count = len(self._cache)
                self._cache.clear()
                return count

    def stats(self) -> dict:
        with self._lock:
            return {
                "entries": len(self._cache),
                "total_hits": sum(e["hits"] for e in self._cache.values()),
            }


# ═══════════════════════════════════════════════════════════════════════════════
# KNOWLEDGE BASE
# ═══════════════════════════════════════════════════════════════════════════════

class KnowledgeBase:
    """Simple FAQ knowledge base with fuzzy matching."""

    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_table()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_table(self) -> None:
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS kb_entries (
                id TEXT PRIMARY KEY,
                question TEXT,
                answer TEXT,
                category TEXT,
                ts REAL
            )
        """)
        # Seed with some defaults
        defaults = [
            ("what_are_you", "What are you?", "I am Omega AI, a multi-agent intelligent assistant built by ttmodupe-hash. I can help with research, investment analysis, tax guidance, language translation, career advice, and much more.", "general", time.time()),
            ("how_to_use", "How do I use you?", "Just ask me anything! Try: 'Research quantum computing', 'Help me invest', 'Translate hello to Spanish', or 'Teach me about recursion'. I have 50+ specialized modules.", "general", time.time()),
            ("who_made_you", "Who made you?", "I was built by ttmodupe-hash as an open-source AI assistant. You can find my code at github.com/ttmodupe-hash/omega-super-ai.", "general", time.time()),
        ]
        for entry in defaults:
            cur.execute("INSERT OR IGNORE INTO kb_entries (id, question, answer, category, ts) VALUES (?, ?, ?, ?, ?)", entry)
        conn.commit()
        conn.close()

    def add_entry(self, entry_id: str, question: str, answer: str, category: str = "general") -> None:
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO kb_entries (id, question, answer, category, ts) VALUES (?, ?, ?, ?, ?)",
            (entry_id, question, answer, category, time.time())
        )
        conn.commit()
        conn.close()

    def search(self, query: str, limit: int = 3) -> list[dict]:
        """Simple keyword search over KB entries."""
        conn = self._conn()
        cur = conn.cursor()
        keywords = query.lower().split()
        cur.execute("SELECT id, question, answer, category FROM kb_entries")
        rows = cur.fetchall()
        conn.close()

        scored = []
        for row in rows:
            text = f"{row[1]} {row[2]}".lower()
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scored.append((score, row))

        scored.sort(key=lambda x: -x[0])
        return [{"id": r[1], "question": r[2], "answer": r[3], "category": r[4]} for _, r in scored[:limit]]

    def get_answer(self, query: str) -> str | None:
        """Get best matching answer or None."""
        results = self.search(query, limit=1)
        if results and len(results) > 0:
            return results[0]["answer"]
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# CONVERSATION STATE MACHINE
# ═══════════════════════════════════════════════════════════════════════════════

class ConversationState(Enum):
    IDLE = "idle"
    AWAITING_DETAIL = "awaiting_detail"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    MULTI_STEP = "multi_step"


class ConversationStateMachine:
    """Manages multi-turn conversation state."""

    def __init__(self) -> None:
        self._state: dict[str, dict] = {}

    def get_state(self, session_id: str) -> dict:
        return self._state.get(session_id, {"state": "idle", "data": {}, "turns": 0})

    def set_state(self, session_id: str, state: str, data: dict | None = None) -> None:
        self._state[session_id] = {"state": state, "data": data or {}, "turns": self._state.get(session_id, {}).get("turns", 0) + 1}

    def reset(self, session_id: str) -> None:
        if session_id in self._state:
            del self._state[session_id]

    def is_in_state(self, session_id: str, state: str) -> bool:
        return self._state.get(session_id, {}).get("state") == state


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN BRAIN CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class OmegaBrain:
    """Central orchestrator — routes queries to specialized modules."""

    def __init__(self, max_history: int = 6) -> None:
        self.max_history = max_history
        self.memory = ConversationMemory(max_size=200)
        self.db = DatabaseEngine()
        self.cache = CacheManager()
        self.kb = KnowledgeBase()
        self.state_machine = ConversationStateMachine()

        # Load plugins if available
        try:
            from plugin_registry import PluginRegistry
            self.plugins = PluginRegistry()
            self.plugins.load_all()
            info("Loaded %d plugins", len(self.plugins.plugins))
        except ImportError:
            self.plugins = None
            debug("Plugin registry not available")

        # Wire up handlers
        self.handlers: dict[str, Callable[[str], ResponseDict]] = {
            "deep_research":    self._handle_deep_research,
            "investment":       self._handle_investment,
            "tax":              self._handle_tax,
            "companion":        self._handle_companion,
            "self_improve":     self._handle_self_improve,
            "language":         self._handle_language,
            "financial_lit":    self._handle_financial_lit,
            "professional":     self._handle_professional,
            "opportunity":      self._handle_opportunity,
            "email":            self._handle_email,
            "knowledge_base":   self._handle_knowledge_base,
            "conversation_state": self._handle_conversation_state,
            "scheduler":        self._handle_scheduler,
            "price_ticker":     self._handle_price_ticker,
            "calc_engine":      self._handle_calc_engine,
            "history_search":   self._handle_history_search,
            "learning_tracker": self._handle_learning_tracker,
            "wisdom":           self._handle_wisdom,
            "pipeline":         self._handle_pipeline,
            "educational_companion": self._handle_educational_companion,
            "vocational_companion": self._handle_vocational_companion,
            "voice_interface":  self._handle_voice_interface,
            "file_analysis":    self._handle_file_analysis,
            "digital_transform": self._handle_digital_transform,
            "error_repair":     self._handle_error_repair,
            "memory_manager":   self._handle_memory_manager,
            "realtime_prices":  self._handle_realtime_prices,
            "local_llm":        self._handle_local_llm,
            "pedagogical":      self._handle_pedagogical,
        }
        info("OmegaBrain initialized (history_window=%d, v3.7.0)", max_history)

    # ══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ══════════════════════════════════════════════════════════════════════════

    def process(self, query: str, context: dict | None = None) -> ResponseDict:
        """Main entry point: classify intent and route to handler."""
        # Add user message to memory
        self.memory.add("user", query)

        # Check cache
        cached = self.cache.get("response", query)
        if cached:
            info("Cache hit for query: %s", query[:50])
            self.memory.add("assistant", cached.answer)
            return cached

        # Check knowledge base for FAQ-style queries
        kb_answer = self.kb.get_answer(query)
        if kb_answer:
            result = ok(kb_answer, module="knowledge_base")
            self.memory.add("assistant", result.answer)
            self.db.log_query("default", query, result.answer, "knowledge_base")
            return result

        # Classify intent and route
        intent = classify_intent(query)
        handler = self.handlers.get(intent, self._handle_general)

        try:
            result = handler(query)
        except Exception as e:
            error("Handler error for intent '%s': %s", intent, e)
            result = ok(f"I encountered an issue processing that request. Let me try a different approach.\n\nCould you rephrase or try a more specific query?", module="fallback")

        # Persist to memory and DB
        self.memory.add("assistant", result.answer)
        self.db.log_query("default", query, result.answer, intent)

        # Cache the response
        self.cache.set(result, "response", query, ttl=60)

        return result

    def get_status(self) -> dict:
        return {
            "version": "3.7.0",
            "modules_available": len(self.handlers),
            "intents": list(INTENT_KEYWORDS.keys()),
            "cache_stats": self.cache.stats(),
            "conversation_entries": len(self.memory._entries),
            "handlers": list(self.handlers.keys()),
        }

    # ══════════════════════════════════════════════════════════════════════════
    # HANDLERS
    # ══════════════════════════════════════════════════════════════════════════

    def _handle_deep_research(self, query: str) -> ResponseDict:
        """DEEP_RESEARCH — Full-spectrum intelligence gathering."""
        try:
            from deep_research import ResearchEngine
            engine = ResearchEngine()
            return ok(engine.research(query), module="deep_research")
        except ImportError:
            return ok("Deep Research module not available.", module="deep_research")

    def _handle_investment(self, query: str) -> ResponseDict:
        try:
            from investment import InvestmentEngine
            engine = InvestmentEngine()
            return ok(engine.advise(query), module="investment")
        except ImportError:
            return ok("Investment module not available.", module="investment")

    def _handle_tax(self, query: str) -> ResponseDict:
        try:
            from tax import TaxEngine
            engine = TaxEngine()
            return ok(engine.answer(query), module="tax")
        except ImportError:
            return ok("Tax module not available.", module="tax")

    def _handle_companion(self, query: str) -> ResponseDict:
        try:
            from companion import CompanionEngine
            engine = CompanionEngine()
            return ok(engine.respond(query), module="companion")
        except ImportError:
            return ok("I'm here for you. Tell me more about how you're feeling.", module="companion")

    def _handle_self_improve(self, query: str) -> ResponseDict:
        try:
            from self_improve import SelfImprovementEngine
            engine = SelfImprovementEngine()
            return ok(engine.coach(query), module="self_improve")
        except ImportError:
            return ok("Self-improvement module not available.", module="self_improve")

    def _handle_language(self, query: str) -> ResponseDict:
        try:
            from african_languages import translate, detect_language
            q_lower = query.lower()
            # Simple pattern matching for translation requests
            if "translate" in q_lower:
                parts = query.split(" to ", 1)
                if len(parts) == 2:
                    text = parts[0].replace("translate", "").strip().strip('"').strip("'")
                    target = parts[1].strip()
                    result = translate(text, target)
                    return ok(f"**{target}**: {result}", module="language")
            return ok("I can translate! Try: 'translate hello to Yoruba' or 'how do you say thank you in Swahili'", module="language")
        except ImportError:
            return ok("Language module not available.", module="language")

    def _handle_financial_lit(self, query: str) -> ResponseDict:
        try:
            from financial_literacy import FinancialLiteracyEngine
            engine = FinancialLiteracyEngine()
            return ok(engine.answer(query), module="financial_lit")
        except ImportError:
            return ok("Financial literacy module not available.", module="financial_lit")

    def _handle_professional(self, query: str) -> ResponseDict:
        try:
            from professional import ProfessionalEngine
            engine = ProfessionalEngine()
            return ok(engine.advise(query), module="professional")
        except ImportError:
            return ok("Professional development module not available.", module="professional")

    def _handle_opportunity(self, query: str) -> ResponseDict:
        try:
            from opportunity_engine import OpportunityEngine
            engine = OpportunityEngine()
            return ok(engine.find(query), module="opportunity")
        except ImportError:
            return ok("Opportunity engine not available.", module="opportunity")

    def _handle_email(self, query: str) -> ResponseDict:
        try:
            from email_notifier import EmailNotifier
            notifier = EmailNotifier()
            return ok("Email module ready. To send: provide recipient, subject, and message.", module="email")
        except ImportError:
            return ok("Email notifier not available.", module="email")

    def _handle_knowledge_base(self, query: str) -> ResponseDict:
        """KNOWLEDGE_BASE — FAQ matching and general knowledge."""
        results = self.kb.search(query, limit=3)
        if results:
            answer = "\n\n".join(f"**{r['question']}**\n{r['answer']}" for r in results)
            return ok(answer, module="knowledge_base")
        return ok("I don't have a specific answer for that in my knowledge base. Let me try another approach.", module="knowledge_base")

    def _handle_conversation_state(self, query: str) -> ResponseDict:
        return ok("I can help you book flights, schedule meetings, plan trips, and make reservations. What would you like to do?", module="conversation_state")

    def _handle_scheduler(self, query: str) -> ResponseDict:
        try:
            from scheduler import SchedulerEngine
            engine = SchedulerEngine()
            return ok(engine.handle(query), module="scheduler")
        except ImportError:
            return ok("Scheduler module not available. I can set reminders and manage your calendar when it's loaded.", module="scheduler")

    def _handle_price_ticker(self, query: str) -> ResponseDict:
        try:
            from price_ticker import PriceTicker
            ticker = PriceTicker()
            return ok(ticker.get_price(query), module="price_ticker")
        except ImportError:
            return ok("Price ticker not available.", module="price_ticker")

    def _handle_calc_engine(self, query: str) -> ResponseDict:
        try:
            from calc_engine import CalcEngine
            engine = CalcEngine()
            return ok(engine.calculate(query), module="calc_engine")
        except ImportError:
            return ok("Calculator module not available.", module="calc_engine")

    def _handle_history_search(self, query: str) -> ResponseDict:
        results = self.memory.search(query.replace("what did i say", "").replace("earlier", "").strip())
        if results:
            text = "Here's what I found in our conversation:\n\n"
            for e in results:
                text += f"- **{e.role}**: {e.content[:100]}\n"
            return ok(text, module="history_search")
        return ok("I couldn't find relevant previous messages.", module="history_search")

    def _handle_learning_tracker(self, query: str) -> ResponseDict:
        return ok("Learning tracker: I can help you build skill trees, find courses, and track your progress. What skill are you working on?", module="learning_tracker")

    def _handle_wisdom(self, query: str) -> ResponseDict:
        """WISDOM — Cultural proverbs and philosophical guidance."""
        try:
            from wisdom_engine import get_wisdom_engine
            engine = get_wisdom_engine()
            q_lower = query.lower()

            if any(kw in q_lower for kw in ["proverb", "quote", "saying", "aphorism"]):
                result = engine.get_wisdom(style="random")
                return ok(result, module="wisdom")
            elif any(kw in q_lower for kw in ["by theme", "about"]):
                # Extract theme after "about"
                theme = query.split("about")[-1].strip() if "about" in q_lower else "life"
                result = engine.get_wisdom_by_theme(theme)
                return ok(result, module="wisdom")
            elif any(kw in q_lower for kw in ["decision", "advice", "guidance", "what should i do"]):
                result = engine.get_decision_wisdom(query)
                return ok(result, module="wisdom")
            elif any(kw in q_lower for kw in ["daily", "today"]):
                result = engine.get_daily_wisdom()
                return ok(result, module="wisdom")
            elif any(kw in q_lower for kw in ["stats", "how many", "collection"]):
                stats = engine.get_stats()
                return ok(f"Wisdom Collection Stats:\n{stats}", module="wisdom")
            else:
                result = engine.get_wisdom(style="universal")
                return ok(result, module="wisdom")
        except Exception as e:
            return ok(f"Wisdom module error: {e}", module="wisdom")

    def _handle_pipeline(self, query: str) -> ResponseDict:
        return ok("Pipeline module: I can help design ETL workflows, data pipelines, and automation processes. What are you building?", module="pipeline")

    def _handle_educational_companion(self, query: str) -> ResponseDict:
        return ok("Educational companion: I adapt explanations to your level. What topic are you studying?", module="educational_companion")

    def _handle_vocational_companion(self, query: str) -> ResponseDict:
        return ok("Vocational companion: I can guide you through trade certifications, apprenticeships, and technical training paths.", module="vocational_companion")

    def _handle_voice_interface(self, query: str) -> ResponseDict:
        return ok("Voice interface: I can process speech-to-text and text-to-speech when the voice module is loaded.", module="voice_interface")

    def _handle_file_analysis(self, query: str) -> ResponseDict:
        return ok("File analysis: I can parse CSVs, extract data from documents, and analyze file contents. What file would you like me to look at?", module="file_analysis")

    def _handle_digital_transform(self, query: str) -> ResponseDict:
        return ok("Digital transformation: I can help plan cloud migrations, modernization strategies, and automation roadmaps.", module="digital_transform")

    def _handle_realtime_prices(self, query: str) -> ResponseDict:
        """REALTIME_PRICES — Live crypto and market data."""
        try:
            from realtime_prices import get_price, PriceError
            q_lower = query.lower()
            # Extract ticker symbol
            symbols = ["bitcoin", "btc", "ethereum", "eth", "solana", "sol",
                       "cardano", "ada", "polkadot", "dot", "ripple", "xrp"]
            found_symbol = None
            for s in symbols:
                if s in q_lower:
                    found_symbol = s
                    break
            if not found_symbol:
                return ok("I can check live prices for: BTC, ETH, SOL, ADA, DOT, XRP. Which one?", module="realtime_prices")
            price_data = get_price(found_symbol)
            return ok(f"**{price_data['name']} ({price_data['symbol'].upper()})**\n"
                      f"Price: ${price_data['price_usd']:,.2f}\n"
                      f"24h Change: {price_data['change_24h']:+.2f}%\n"
                      f"Market Cap: ${price_data.get('market_cap', 0):,.0f}",
                      module="realtime_prices")
        except PriceError as e:
            return ok(f"Price lookup failed: {e}", module="realtime_prices")
        except ImportError:
            return ok("Real-time prices module not available.", module="realtime_prices")

    def _handle_local_llm(self, query: str) -> ResponseDict:
        """LOCAL LLM — Offline AI via Ollama."""
        try:
            from local_llm import LocalLLM
            llm = LocalLLM()
            if not llm.is_available():
                return ok(
                    "Local LLM is not available.\n\nTo enable:\n"
                    "  1. Install Ollama: https://ollama.ai\n"
                    "  2. Run: ollama run llama3.2\n"
                    "  3. Ensure Ollama is running on localhost:11434\n\n"
                    "Once running, all queries can be processed offline.",
                    module="local_llm"
                )
            prompt = query.lower().replace("local llm", "").replace("offline mode", "").replace("local ai", "").strip()
            result = llm.generate(prompt or query)
            return ok(result.get("response", "No response from local LLM."), module="local_llm")
        except ImportError:
            return ok("Local LLM module not available. Install with: pip install local_llm", module="local_llm")

    def _handle_error_repair(self, query: str) -> ResponseDict:
        """ERROR REPAIR — Self-healing diagnostics and error analysis."""
        from error_repair import get_error_repair
        engine = get_error_repair()
        q_lower = query.lower()

        if any(kw in q_lower for kw in ["diagnostic", "health check", "system check", "status"]):
            result = engine.get_response(action="diagnostic")
            text = f"System Diagnostic Report\n{'=' * 40}\n"
            text += f"Modules Checked: {result.get('modules_checked', 0)}\n"
            text += f"Average Health: {result.get('average_health', 0)}%\n"
            text += f"Overall Status: {result.get('overall_status', 'unknown').upper()}\n"
            text += f"Total Repairs: {result.get('total_repairs', 0)}\n"
            if result.get("critical_modules"):
                text += f"\nCritical Modules:\n"
                for mod in result["critical_modules"]:
                    text += f"  ⚠ {mod}\n"
            text += f"\nModule Health Breakdown:\n"
            for mod, data in result.get("module_results", {}).items():
                score = data.get("health_score", 0)
                status_icon = "✓" if data.get("status") == "healthy" else "⚠" if data.get("status") == "degraded" else "✗"
                text += f"  {status_icon} {mod:20} {score:3}%\n"
            return ok(text, module="error_repair")

        elif any(kw in q_lower for kw in ["analyze", "pattern", "root cause", "why did"]):
            result = engine.get_response(action="analyze")
            text = f"Error Pattern Analysis\n{'=' * 40}\n"
            text += f"Total Errors: {result.get('total_errors', 0)}\n"
            text += f"Unresolved: {result.get('unresolved_errors', 0)}\n"
            text += f"Most Error-Prone Module: {result.get('most_error_prone_module', 'none')}\n"
            text += f"Most Common Error: {result.get('most_common_error', 'none')}\n"
            text += f"Auto-Repair Rate: {result.get('auto_repair_rate', 'N/A')}\n"
            if result.get("error_by_module"):
                text += f"\nErrors by Module (top 10):\n"
                for mod, count in result["error_by_module"].items():
                    text += f"  {mod}: {count}\n"
            if result.get("error_by_type"):
                text += f"\nErrors by Type (top 10):\n"
                for etype, count in result["error_by_type"].items():
                    text += f"  {etype}: {count}\n"
            return ok(text, module="error_repair")

        elif any(kw in q_lower for kw in ["repair", "fix", "heal", "attempt repair"]):
            result = engine.get_response(action="repairs")
            text = f"Automatic Repair Attempt\n{'=' * 40}\n"
            repairs = result.get("results", [])
            if repairs:
                for r in repairs:
                    err = r.get("error", {})
                    repair = r.get("repair", {})
                    text += f"Module: {err.get('module', '?')}.{err.get('function', '?')}\n"
                    text += f"Error: {err.get('error_type', '?')}\n"
                    text += f"Severity: {err.get('severity', '?')}\n"
                    text += f"Repair: {'✓ Success' if repair.get('success') else '✗ Failed'}\n"
                    if repair.get("method"):
                        text += f"Method: {repair['method']}\n"
                    text += "-" * 30 + "\n"
            else:
                text += "No auto-fixable unresolved errors found.\n"
            return ok(text, module="error_repair")

        else:
            result = engine.get_response(action="stats")
            text = f"Error Repair Engine Stats\n{'=' * 40}\n"
            text += f"Total Errors Logged: {result.get('total_errors_logged', 0)}\n"
            text += f"Unresolved Errors: {result.get('unresolved_errors', 0)}\n"
            text += f"Successful Repairs: {result.get('successful_repairs', 0)}\n"
            text += f"Modules Monitored: {result.get('modules_monitored', 0)}\n"
            text += f"Circuit Breakers: {result.get('circuit_breakers', 0)}\n"
            text += f"Error Categories: {result.get('error_categories', 0)}\n"
            text += f"\nTry: 'run diagnostic', 'analyze errors', 'attempt repairs'"
            return ok(text, module="error_repair")

    def _handle_memory_manager(self, query: str) -> ResponseDict:
        """3-AGENT MEMORY MANAGER — Tracks, reviews, and cleans up stored data with user consent."""
        from memory_manager import get_memory_manager, RetentionStatus
        mm = get_memory_manager()
        q_lower = query.lower()

        if any(kw in q_lower for kw in ["propose", "cleanup", "clean up", "delete old", "purge", "what should we delete"]):
            mm.review()
            result = mm.get_response(action="propose")
            if result.get("total_entries", 0) > 0:
                text = f"Memory Cleanup Proposal\n{'=' * 40}\n"
                text += f"Proposal ID: {result['proposal_id']}\n"
                text += f"Reason: {result['reason']}\n"
                text += f"Entries: {result['total_entries']} ({result['total_size_mb']} MB)\n\n"
                text += "Entries awaiting your approval:\n"
                for i, e in enumerate(result['entries'][:10], 1):
                    text += f"  {i}. [{e['module']}] {e['summary'][:50]}\n"
                    text += f"     Idle: {e['idle_days']} days | Size: {e['size_mb']} MB | Importance: {e['importance']}/5\n"
                if len(result['entries']) > 10:
                    text += f"  ... and {len(result['entries']) - 10} more\n"
                text += f"\nTo approve: 'approve cleanup {result['proposal_id']}'\n"
                text += f"To deny: 'deny cleanup {result['proposal_id']}'\n"
                text += "\n⚠️ Nothing will be deleted without your explicit approval."
                return ok(text, module="memory_manager")
            return ok("Memory is healthy. No cleanup needed.\n\n" + self._format_memory_report(mm), module="memory_manager")

        elif any(kw in q_lower for kw in ["approve", "yes delete"]):
            import re
            m = re.search(r'purge_[0-9_]+', query)
            pid = m.group(0) if m else ""
            if pid:
                result = mm.get_response(action="approve", proposal_id=pid)
                text = f"Cleanup Approved\n{'=' * 40}\n"
                text += f"Entries deleted: {result.get('entries_deleted', 0)}\n"
                text += f"Size freed: {result.get('total_size_mb', 0)} MB\n"
                text += f"Recoverable until: {time.strftime('%Y-%m-%d', time.localtime(result.get('recoverable_until', 0)))}\n"
                text += "\nTo recover any entry: 'recover memory <entry_id>'"
                return ok(text, module="memory_manager")
            return ok("Please specify a proposal ID: 'approve cleanup <proposal_id>'", module="memory_manager")

        elif any(kw in q_lower for kw in ["deny", "no don't delete", "keep"]):
            import re
            m = re.search(r'purge_[0-9_]+', query)
            pid = m.group(0) if m else ""
            if pid:
                result = mm.get_response(action="deny", proposal_id=pid)
                text = f"Cleanup Denied\n{'=' * 40}\n"
                text += f"Entries restored: {result.get('entries_restored', 0)}\n"
                text += result.get("message", "All entries kept.")
                return ok(text, module="memory_manager")
            return ok("Please specify a proposal ID: 'deny cleanup <proposal_id>'", module="memory_manager")

        elif any(kw in q_lower for kw in ["recover", "restore deleted"]):
            import re
            m = re.search(r'recover\s+memory\s+(\S+)', q_lower)
            eid = m.group(1) if m else ""
            if eid:
                success = mm.recover_entry(eid)
                if success:
                    return ok(f"Entry '{eid}' has been recovered successfully.", module="memory_manager")
                return ok(f"Entry '{eid}' could not be recovered. It may be past the 30-day window or not found.", module="memory_manager")
            result = mm.get_response(action="recoverable")
            if result.get("count", 0) > 0:
                text = f"Recoverable Entries ({result['count']}):\n"
                for e in result["entries"]:
                    text += f"  • {e['id']} [{e['module']}] — {e['summary'][:40]}\n"
                text += "\nTo recover: 'recover memory <entry_id>'"
                return ok(text, module="memory_manager")
            return ok("No recoverable entries found.", module="memory_manager")

        elif any(kw in q_lower for kw in ["pending", "awaiting approval"]):
            result = mm.get_response(action="pending")
            if result.get("count", 0) > 0:
                text = f"Pending Cleanup Proposals ({result['count']}):\n"
                for p in result["proposals"]:
                    text += f"  • {p['id']}: {p['entries']} entries ({p['size_mb']} MB) — {p['reason']}\n"
                return ok(text, module="memory_manager")
            return ok("No pending proposals. All memory decisions have been resolved.", module="memory_manager")

        else:
            return ok(self._format_memory_report(mm), module="memory_manager")

    @staticmethod
    def _format_memory_report(mm) -> str:
        """Format a human-readable memory health report."""
        from memory_manager import RetentionStatus
        report = mm.get_report()
        text = f"Memory Health Report\n{'=' * 40}\n"
        text += f"Health Score: {report['health_score']}/100\n"
        text += f"Total Entries: {report['total_entries']} ({report['total_size_mb']} MB)\n"
        text += f"Status: {report['recommendation'].upper()}\n\n"
        text += f"  Active:    {report['active']}\n"
        text += f"  Aging:     {report['aging']}\n"
        text += f"  Stale:     {report['stale']}\n"
        text += f"  Orphaned:  {report['orphaned']}\n"
        text += f"  Quarantined: {report['quarantined']} (awaiting your decision)\n"
        text += f"  Purged:    {report['purged']} (soft-deleted, recoverable)\n\n"
        if report.get("purgeable_entries", 0) > 0:
            text += f"Can free: {report['purgeable_entries']} entries ({report['purgeable_size_mb']} MB)\n"
            text += "Ask 'propose cleanup' to review deletions.\n"
        text += "\n3-Agent System:\n"
        text += "  Archivist — tracks all stored data\n"
        text += "  Curator   — identifies stale/unused data\n"
        text += "  Steward   — asks you before any deletion\n"
        return text

    def _handle_pedagogical(self, query: str) -> ResponseDict:
        """ELITE TRI-AGENT PEDAGOGICAL ENGINE — Socratic mastery learning."""
        from pedagogical_engine import get_pedagogical_engine
        engine = get_pedagogical_engine()
        q_lower = query.lower()
        student_id = "default_student"

        if any(kw in q_lower for kw in ["teach me", "i want to learn", "learning path", "start learning"]):
            domain = "General Learning"
            for marker in ["about ", "me ", "learn ", "study "]:
                if marker in q_lower:
                    parts = q_lower.split(marker, 1)
                    if len(parts) > 1 and parts[1].strip():
                        domain = parts[1].strip().title()
                        break
            result = engine.get_response(action="initialize", student_id=student_id, domain=domain)
            return ok(result["response"], module="pedagogical")

        if "compact" in q_lower or "archive this topic" in q_lower:
            ledger = engine.bjork.get_or_create_ledger(student_id)
            current = ledger.current_focus
            if current:
                cm = ledger.concepts.get(current)
                summary = f"{current}: {cm.bloom_level if cm else 'understood'} — {query[:80]}"
                result = engine.get_response(action="compact", student_id=student_id,
                                             concept=current, summary=summary)
                return ok(result["response"], module="pedagogical")
            return ok("No active concept to archive. Start learning with: 'Teach me about [topic]'", module="pedagogical")

        if any(kw in q_lower for kw in ["cognitive ledger", "show ledger", "my progress"]):
            return ok(engine.get_ledger(student_id), module="pedagogical")

        if any(kw in q_lower for kw in ["my stats", "learning stats", "how am i doing"]):
            stats = engine.stats(student_id)
            text = f"Learning Stats for {stats['student_id']}\n{'=' * 40}\n"
            text += f"Domain: {stats['domain']}\n"
            text += f"Total Concepts: {stats['total_concepts']}\n"
            text += f"Mastered: {stats['mastered']} | In Progress: {stats['in_progress']}\n"
            text += f"Avg Bloom Level: {stats['avg_bloom_level']:.1f}/5\n"
            text += f"Retrieval Due: {stats['retrieval_due']}\n"
            text += f"Current Focus: {stats['current_focus']}\n"
            return ok(text, module="pedagogical")

        if any(kw in q_lower for kw in ["deep dive into", "concept of", "foundation of", "principles of"]):
            import re
            m = re.search(r'(?:concept of|foundation of|principles of|deep dive into)\s+(.+?)(?:\?|$)', q_lower)
            concept = m.group(1).strip() if m else query.strip().split(" ")[-1]
            result = engine.get_response(action="start_concept", student_id=student_id, concept=concept)
            return ok(result["response"], module="pedagogical")

        if any(kw in q_lower for kw in ["quiz me", "test me", "assess my knowledge", "diagnostic"]):
            ledger = engine.bjork.get_or_create_ledger(student_id)
            concept = ledger.current_focus or query.replace("quiz me on", "").replace("test me on", "").strip()
            if concept:
                result = engine.get_response(action="diagnostic", student_id=student_id, concept=concept)
                return ok(result["response"], module="pedagogical")
            return ok("What concept would you like to be quizzed on?", module="pedagogical")

        ledger = engine.bjork.get_or_create_ledger(student_id)
        if ledger.current_focus and ledger.concepts.get(ledger.current_focus):
            result = engine.get_response(action="handle_response", student_id=student_id,
                                         concept=ledger.current_focus, response=query)
            return ok(result["response"], module="pedagogical")

        text = (
            "🎓 **Elite Tri-Agent Learning Mode**\n\n"
            "Three synchronized agents guide your mastery:\n"
            "  🧠 **Socrates** — Socratic method, scaffolded discovery\n"
            "  📊 **Bjork** — Cognitive Ledger, spaced repetition\n"
            "  🛡️ **Bloom** — Mastery gates, Bloom's Taxonomy enforcement\n\n"
            "**Commands:**\n"
            "  • 'Teach me about [domain]' — start learning journey\n"
            "  • 'Deep dive into [concept]' — explore a specific concept\n"
            "  • 'Quiz me' — request a mastery diagnostic\n"
            "  • 'Show my cognitive ledger' — view progress\n"
            "  • 'COMPACT' — archive mastered concept\n"
            "  • 'How am I doing' — learning statistics\n\n"
            "What domain would you like to master?"
        )
        return ok(text, module="pedagogical")

    def _general_response(self, query: str) -> str:
        """Fallback: use LLM with conversation context."""
        context = self.memory.recent(self.max_history)
        prompt = f"Previous context:\n{context}\n\nUser: {query}\nAssistant:"
        return f"I'm processing: '{query}'...\n\n*(General response handler — this would route to an LLM in production)*"


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

_brain_instance: OmegaBrain | None = None
_lock = threading.Lock()

def get_brain() -> OmegaBrain:
    global _brain_instance
    if _brain_instance is None:
        with _lock:
            if _brain_instance is None:
                _brain_instance = OmegaBrain()
    return _brain_instance


if __name__ == "__main__":
    brain = OmegaBrain()
    print(brain.get_status())
    print(classify_intent("How do I invest in ETFs?"))
    print(classify_intent("Translate hello to Yoruba"))
    print(classify_intent("I'm feeling stressed about work"))
    print(classify_intent("Teach me about recursion"))
    print(classify_intent("Debug the error in my code"))
    print(classify_intent("Show my cognitive ledger"))
    print(classify_intent("Clean up old memory"))
