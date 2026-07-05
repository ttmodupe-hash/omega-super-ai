"""Vector Memory System with ChromaDB

Provides persistent vector storage for conversations, documents, and semantic
search using ChromaDB with OpenAI embeddings.
"""

import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings

from backend.ai_engine import AIEngine
from backend.config import load_backend_config

logger = logging.getLogger(__name__)


class VectorMemory:
    """Vector memory backed by ChromaDB with conversation persistence."""

    def __init__(self, config: Optional[Dict[str, object]] = None) -> None:
        self.config = config or load_backend_config()
        self.ai_engine = AIEngine(self.config)
        chroma_path = str(self.config.get("chroma_persist_dir", "./chroma_db"))
        Path(chroma_path).mkdir(parents=True, exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(path=chroma_path, settings=Settings(anonymized_telemetry=False))
        self.collection = self.chroma_client.get_or_create_collection(name="luqi_memory", metadata={"hnsw:space": "cosine"})
        self.db_path = str(self.config.get("db_path", "luqi_memory.db"))
        self._init_sqlite()

    def add(self, text: str, metadata: Optional[Dict[str, str]] = None) -> str:
        """Store text with vector embedding."""
        doc_id = str(uuid.uuid4())
        embedding = self.ai_engine.embed(text)
        if embedding is None:
            logger.error("Failed to create embedding")
            return ""
        meta: Dict[str, str] = {"timestamp": datetime.now(timezone.utc).isoformat(), **(metadata or {})}
        self.collection.add(ids=[doc_id], embeddings=[embedding], documents=[text], metadatas=[meta])
        return doc_id

    def query(self, text: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Semantic search across stored memories."""
        embedding = self.ai_engine.embed(text)
        if embedding is None:
            return []
        results = self.collection.query(query_embeddings=[embedding], n_results=min(n_results, 50), include=["documents", "metadatas", "distances"])
        return self._format_results(results)

    def save_message(self, session_id: str, role: str, content: str) -> bool:
        """Save a conversation message to SQLite."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO conversations (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)", (session_id, role, content, datetime.now(timezone.utc).isoformat()))
            conn.commit()
            conn.close()
            self.add(content, {"session_id": session_id, "role": role, "category": "conversation"})
            return True
        except Exception as exc:
            logger.error("Save message error: %s", exc)
            return False

    def get_conversation(self, session_id: str, limit: int = 50) -> List[Dict[str, str]]:
        """Get conversation history for a session."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT role, content, timestamp FROM conversations WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?", (session_id, limit))
            rows = cursor.fetchall()
            conn.close()
            return [{"role": r[0], "content": r[1], "timestamp": r[2]} for r in reversed(rows)]
        except Exception as exc:
            logger.error("Get conversation error: %s", exc)
            return []

    def _init_sqlite(self) -> None:
        """Initialize SQLite tables for conversation storage."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS conversations (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, timestamp TEXT NOT NULL)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_session ON conversations(session_id)")
            conn.commit()
            conn.close()
        except Exception as exc:
            logger.error("SQLite init error: %s", exc)

    @staticmethod
    def _format_results(results: Dict[str, Any], include_distance: bool = True) -> List[Dict[str, Any]]:
        """Format ChromaDB query results into clean dicts."""
        formatted: List[Dict[str, Any]] = []
        ids = results.get("ids", [[]])
        docs = results.get("documents", [[]])
        metas = results.get("metadatas", [[]])
        dists = results.get("distances", [[]])
        if ids and isinstance(ids[0], list):
            ids = ids[0]
            docs = docs[0] if docs else []
            metas = metas[0] if metas else []
            dists = dists[0] if dists else []
        for i, doc_id in enumerate(ids):
            item: Dict[str, Any] = {"id": doc_id, "text": docs[i] if i < len(docs) else "", "metadata": metas[i] if i < len(metas) else {}}
            if include_distance and dists and i < len(dists):
                item["distance"] = dists[i]
            formatted.append(item)
        return formatted
