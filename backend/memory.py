"""Vector Memory System with ChromaDB

Provides persistent vector storage for conversations, documents, and semantic
search using ChromaDB with OpenAI embeddings.

Classes:
    VectorMemory: Manages vector storage, retrieval, and conversation history.

Typical usage:
    from backend.memory import VectorMemory
    mem = VectorMemory()
    mem.add("Important fact", metadata={"category": "knowledge"})
    results = mem.query("What was that fact?", n_results=3)
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
    """Vector memory backed by ChromaDB with conversation persistence.

    Stores text with vector embeddings for semantic search and maintains
    conversation history in SQLite. Auto-creates collections on init.

    Attributes:
        config: Backend configuration dictionary.
        chroma_client: Persistent ChromaDB client.
        collection: Default collection for vector storage.
        ai_engine: AIEngine instance for creating embeddings.
        db_path: Path to the SQLite conversation database.

    Example:
        >>> mem = VectorMemory()
        >>> mem.add("Python is great", {"tag": "programming"})
        >>> mem.save_message("sess-1", "user", "Hello!")
        >>> hist = mem.get_conversation("sess-1")
        >>> hits = mem.query("programming languages")
    """

    def __init__(self, config: Optional[Dict[str, object]] = None) -> None:
        """Initialize vector memory with ChromaDB and SQLite.

        Args:
            config: Optional configuration dictionary. Loads from env if omitted.
        """
        self.config = config or load_backend_config()
        self.ai_engine = AIEngine(self.config)

        # ChromaDB setup
        chroma_path = str(self.config.get("chroma_path", "./chroma_db"))
        Path(chroma_path).parent.mkdir(parents=True, exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.chroma_client.get_or_create_collection(
            name="luqi_memory",
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("ChromaDB collection ready: luqi_memory")

        # SQLite for conversation history
        self.db_path = str(self.config.get("db_path", "luqi_memory.db"))
        self._init_sqlite()

    # ── Vector Storage ──────────────────────────────────────────────────

    def add(self, text: str, metadata: Optional[Dict[str, str]] = None) -> str:
        """Store text with vector embedding.

        Args:
            text: Text content to store.
            metadata: Optional metadata dict (e.g., category, source).

        Returns:
            ID of the stored document.
        """
        doc_id = str(uuid.uuid4())
        embedding = self.ai_engine.embed(text)
        if embedding is None:
            logger.error("Failed to create embedding for text")
            return ""

        meta: Dict[str, str] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **(metadata or {}),
        }
        self.collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[meta],
        )
        logger.debug("Added document id=%s", doc_id)
        return doc_id

    def query(self, text: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Semantic search across stored memories.

        Args:
            text: Query text.
            n_results: Number of results to return (default 5).

        Returns:
            List of result dicts with id, text, metadata, distance.
        """
        embedding = self.ai_engine.embed(text)
        if embedding is None:
            return []

        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=min(n_results, 50),
            include=["documents", "metadatas", "distances"],
        )
        return self._format_results(results)

    def delete(self, doc_id: str) -> bool:
        """Delete a document by ID.

        Args:
            doc_id: Document ID to delete.

        Returns:
            True if deleted, False otherwise.
        """
        try:
            self.collection.delete(ids=[doc_id])
            return True
        except Exception as exc:
            logger.error("Delete error: %s", exc)
            return False

    def get_all(
        self, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List all stored memories with pagination.

        Args:
            limit: Maximum items per page.
            offset: Pagination offset.

        Returns:
            List of memory dicts with id, text, metadata.
        """
        results = self.collection.get(
            limit=limit,
            offset=offset,
            include=["documents", "metadatas"],
        )
        return self._format_results(results, include_distance=False)

    # ── Conversation Management ─────────────────────────────────────────

    def save_message(
        self, session_id: str, role: str, content: str
    ) -> bool:
        """Save a conversation message to SQLite.

        Args:
            session_id: Unique session identifier.
            role: Message role (user, assistant, system).
            content: Message text content.

        Returns:
            True if saved successfully.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO conversations (session_id, role, content, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (
                    session_id,
                    role,
                    content,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
            conn.close()

            # Also add to vector store for semantic search
            self.add(
                content,
                {
                    "session_id": session_id,
                    "role": role,
                    "category": "conversation",
                },
            )
            return True
        except Exception as exc:
            logger.error("Save message error: %s", exc)
            return False

    def get_conversation(
        self, session_id: str, limit: int = 50
    ) -> List[Dict[str, str]]:
        """Get conversation history for a session.

        Args:
            session_id: Session identifier.
            limit: Maximum messages to retrieve.

        Returns:
            List of message dicts with role, content, timestamp.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT role, content, timestamp FROM conversations
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (session_id, limit),
            )
            rows = cursor.fetchall()
            conn.close()
            return [
                {"role": r[0], "content": r[1], "timestamp": r[2]}
                for r in reversed(rows)
            ]
        except Exception as exc:
            logger.error("Get conversation error: %s", exc)
            return []

    def search_conversations(
        self, query: str, n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Semantic search across all conversation history.

        Args:
            query: Search query text.
            n_results: Number of results.

        Returns:
            List of matching messages with metadata.
        """
        embedding = self.ai_engine.embed(query)
        if embedding is None:
            return []

        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=min(n_results, 50),
            where={"category": "conversation"},
            include=["documents", "metadatas", "distances"],
        )
        return self._format_results(results)

    def clear_conversation(self, session_id: str) -> bool:
        """Delete all messages for a session.

        Args:
            session_id: Session to clear.

        Returns:
            True if cleared.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM conversations WHERE session_id = ?",
                (session_id,),
            )
            conn.commit()
            conn.close()
            logger.info("Cleared conversation session=%s", session_id)
            return True
        except Exception as exc:
            logger.error("Clear conversation error: %s", exc)
            return False

    # ── Private ─────────────────────────────────────────────────────────

    def _init_sqlite(self) -> None:
        """Initialize SQLite tables for conversation storage."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_session
                ON conversations(session_id)
                """
            )
            conn.commit()
            conn.close()
            logger.info("SQLite conversation store ready")
        except Exception as exc:
            logger.error("SQLite init error: %s", exc)

    @staticmethod
    def _format_results(
        results: Dict[str, Any], include_distance: bool = True
    ) -> List[Dict[str, Any]]:
        """Format ChromaDB query results into clean dicts."""
        formatted: List[Dict[str, Any]] = []
        ids = results.get("ids", [[]])
        docs = results.get("documents", [[]])
        metas = results.get("metadatas", [[]])
        dists = results.get("distances", [[]])

        # Handle get() vs query() result shapes
        if ids and isinstance(ids[0], list):
            ids = ids[0]
            docs = docs[0] if docs else []
            metas = metas[0] if metas else []
            dists = dists[0] if dists else []

        for i, doc_id in enumerate(ids):
            item: Dict[str, Any] = {
                "id": doc_id,
                "text": docs[i] if i < len(docs) else "",
                "metadata": metas[i] if i < len(metas) else {},
            }
            if include_distance and dists and i < len(dists):
                item["distance"] = dists[i]
            formatted.append(item)

        return formatted
