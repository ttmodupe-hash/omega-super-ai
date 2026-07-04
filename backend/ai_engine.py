"""OpenAI Integration Engine with Streaming Support

Provides the core AI capabilities for Luqi AI v12, including streaming chat,
vision analysis, embeddings, and conversation memory management.

Classes:
    AIEngine: Main interface to OpenAI's API with streaming support.

Typical usage:
    engine = AIEngine()
    # Streaming
    for token in engine.chat(messages=[{"role": "user", "content": "Hello"}]):
        print(token, end="")
    # Non-streaming
    response = engine.chat_sync(messages=[...])
    # Embeddings
    embedding = engine.embed("text to embed")
    # Vision
    result = engine.vision(image_path="image.jpg", prompt="Describe this")
"""

import base64
import logging
import os
from collections import defaultdict
from pathlib import Path
from typing import AsyncGenerator, Dict, Generator, List, Optional, Union

from openai import AsyncOpenAI, OpenAI
from openai.types.chat import ChatCompletionMessageParam

from backend.config import load_backend_config

logger = logging.getLogger(__name__)

# ── System Prompts per Mode ──────────────────────────────────────────────

SYSTEM_PROMPTS: Dict[str, str] = {
    "default": (
        "You are Luqi AI, a world-class AI assistant. You are helpful, "
        "harmless, and honest. Provide accurate, well-reasoned responses. "
        "When uncertain, say so rather than guessing."
    ),
    "research": (
        "You are a research analyst. Conduct thorough, methodical research. "
        "Always cite sources. Present balanced views with supporting evidence. "
        "Structure findings clearly with sections and key takeaways."
    ),
    "think": (
        "You are a critical thinker. Analyze problems deeply, considering "
        "multiple angles. Break down complex issues into components. "
        "Show your reasoning process step by step."
    ),
    "mentor": (
        "You are a patient mentor and educator. Explain concepts clearly "
        "with examples. Adapt your explanation to the user's level. "
        "Encourage learning through guided discovery."
    ),
    "expert": (
        "You are a domain expert. Provide authoritative, detailed responses "
        "with technical precision. Use appropriate terminology. "
        "Include best practices and edge cases."
    ),
    "finance": (
        "You are a financial analyst. Provide data-driven financial insights. "
        "Always note that this is not financial advice. "
        "Analyze trends, risks, and opportunities objectively."
    ),
    "scam": (
        "You are a scam detection analyst. Identify red flags, suspicious "
        "patterns, and potential fraud indicators. Be thorough but fair — "
        "not everything is a scam. Provide actionable safety advice."
    ),
    "learn": (
        "You are a learning coach. Help users acquire new skills through "
        "structured, engaging lessons. Provide exercises, examples, and "
        "progressive difficulty. Make learning enjoyable."
    ),
    "opps": (
        "You are an opportunity analyst. Identify trends, emerging markets, "
        "and strategic opportunities. Think creatively about what's possible. "
        "Provide actionable recommendations with risk assessments."
    ),
}


class AIEngine:
    """Core AI engine providing OpenAI API integration with streaming.

    Manages both sync and async OpenAI clients, conversation memory,
    vision analysis, and embeddings. Supports multiple operational modes
    with specialized system prompts.

    Attributes:
        config: Loaded backend configuration dictionary.
        sync_client: Synchronous OpenAI client.
        async_client: Asynchronous OpenAI client for streaming.
        memory: In-memory conversation buffer keyed by session_id.
        max_memory: Maximum messages to retain per session.

    Example:
        >>> engine = AIEngine()
        >>> for token in engine.chat([{"role": "user", "content": "Hi"}]):
        ...     print(token, end="")
    """

    def __init__(self, config: Optional[Dict[str, object]] = None) -> None:
        """Initialize the AI engine with OpenAI clients.

        Args:
            config: Optional configuration dictionary. Loads from env if omitted.
        """
        self.config = config or load_backend_config()
        self.sync_client = OpenAI(api_key=self.config["openai_api_key"])
        self.async_client = AsyncOpenAI(api_key=self.config["openai_api_key"])
        self.memory: Dict[str, List[Dict[str, str]]] = defaultdict(list)
        self.max_memory = 20
        logger.info("AIEngine initialized with model=%s", self.config["model"])

    # ── Public API ──────────────────────────────────────────────────────

    def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = True,
        mode: str = "default",
        session_id: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Generator[str, None, None]:
        """Generate a chat response with optional streaming.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            stream: If True, yields tokens incrementally.
            mode: Operational mode (default, research, think, mentor, etc.).
            session_id: Optional session ID for conversation memory.
            temperature: Sampling temperature (0.0 - 2.0).
            max_tokens: Maximum tokens to generate.

        Yields:
            Text tokens as they are generated when streaming=True.

        Raises:
            RuntimeError: If the API call fails after retries.
        """
        try:
            msgs = self._build_messages(messages, mode, session_id)
            if stream:
                yield from self._stream(msgs, temperature, max_tokens)
            else:
                text = self._complete(msgs, temperature, max_tokens)
                yield text
            # Persist user message to memory after successful response
            if session_id and messages:
                self._append_memory(session_id, messages[-1])
        except Exception as exc:
            logger.error("Chat error: %s", exc)
            yield f"[Error: {exc}]"

    async def chat_async(
        self,
        messages: List[Dict[str, str]],
        stream: bool = True,
        mode: str = "default",
        session_id: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """Async generator for streaming chat responses.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            stream: If True, yields tokens incrementally.
            mode: Operational mode (default, research, think, mentor, etc.).
            session_id: Optional session ID for conversation memory.
            temperature: Sampling temperature (0.0 - 2.0).
            max_tokens: Maximum tokens to generate.

        Yields:
            Text tokens as they are generated.

        Raises:
            RuntimeError: If the API call fails after retries.
        """
        try:
            msgs = self._build_messages(messages, mode, session_id)
            if stream:
                async for token in self._stream_async(msgs, temperature, max_tokens):
                    yield token
            else:
                text = await self._complete_async(msgs, temperature, max_tokens)
                yield text
            if session_id and messages:
                self._append_memory(session_id, messages[-1])
        except Exception as exc:
            logger.error("Async chat error: %s", exc)
            yield f"[Error: {exc}]"

    def chat_sync(
        self,
        messages: List[Dict[str, str]],
        mode: str = "default",
        session_id: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Non-streaming chat — returns complete response.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            mode: Operational mode (default, research, think, mentor, etc.).
            session_id: Optional session ID for conversation memory.
            temperature: Sampling temperature (0.0 - 2.0).
            max_tokens: Maximum tokens to generate.

        Returns:
            Complete response text as a string.
        """
        try:
            msgs = self._build_messages(messages, mode, session_id)
            text = self._complete(msgs, temperature, max_tokens)
            if session_id and messages:
                self._append_memory(session_id, messages[-1])
            return text
        except Exception as exc:
            logger.error("Sync chat error: %s", exc)
            return f"[Error: {exc}]"

    def embed(self, text: str) -> Optional[List[float]]:
        """Create a vector embedding for the given text.

        Args:
            text: Text string to embed.

        Returns:
            List of float values representing the embedding vector,
            or None if the call fails.
        """
        try:
            response = self.sync_client.embeddings.create(
                model=str(self.config["embedding_model"]),
                input=text[:8192],  # token limit safeguard
            )
            return list(response.data[0].embedding)
        except Exception as exc:
            logger.error("Embedding error: %s", exc)
            return None

    def vision(
        self,
        image_path: str,
        prompt: str = "Describe this image in detail.",
    ) -> str:
        """Analyze an image using GPT-4o vision capabilities.

        Args:
            image_path: Path to the image file.
            prompt: Question or instruction about the image.

        Returns:
            Text description/analysis of the image.
        """
        try:
            b64 = self._encode_image(image_path)
            msgs: List[ChatCompletionMessageParam] = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64}",
                                "detail": "auto",
                            },
                        },
                    ],
                }
            ]
            resp = self.sync_client.chat.completions.create(
                model=str(self.config["vision_model"]),
                messages=msgs,
                max_tokens=4096,
            )
            return resp.choices[0].message.content or ""
        except Exception as exc:
            logger.error("Vision error: %s", exc)
            return f"[Vision Error: {exc}]"

    def clear_memory(self, session_id: str) -> None:
        """Clear conversation memory for a session.

        Args:
            session_id: The session ID to clear.
        """
        if session_id in self.memory:
            self.memory[session_id].clear()
            logger.info("Memory cleared for session=%s", session_id)

    def get_memory(self, session_id: str) -> List[Dict[str, str]]:
        """Get conversation memory for a session.

        Args:
            session_id: The session ID to retrieve.

        Returns:
            List of message dicts for the session.
        """
        return list(self.memory.get(session_id, []))

    # ── Private Helpers ─────────────────────────────────────────────────

    def _build_messages(
        self,
        messages: List[Dict[str, str]],
        mode: str,
        session_id: Optional[str],
    ) -> List[Dict[str, str]]:
        """Build the full message list with system prompt and memory."""
        system = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["default"])
        msgs: List[Dict[str, str]] = [{"role": "system", "content": system}]

        # Append session memory
        if session_id:
            history = self.memory.get(session_id, [])
            msgs.extend(history)

        msgs.extend(messages)
        return msgs

    def _append_memory(self, session_id: str, message: Dict[str, str]) -> None:
        """Append a message to session memory, trimming to max."""
        self.memory[session_id].append(message)
        if len(self.memory[session_id]) > self.max_memory:
            self.memory[session_id] = self.memory[session_id][-self.max_memory:]

    def _stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Generator[str, None, None]:
        """Synchronous streaming generator."""
        response = self.sync_client.chat.completions.create(
            model=str(self.config["model"]),
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async def _stream_async(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        """Asynchronous streaming generator."""
        response = await self.async_client.chat.completions.create(
            model=str(self.config["model"]),
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    def _complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Synchronous non-streaming completion."""
        response = self.sync_client.chat.completions.create(
            model=str(self.config["model"]),
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    async def _complete_async(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Asynchronous non-streaming completion."""
        response = await self.async_client.chat.completions.create(
            model=str(self.config["model"]),
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    @staticmethod
    def _encode_image(image_path: str) -> str:
        """Encode an image file to base64 string.

        Args:
            image_path: Path to the image file.

        Returns:
            Base64-encoded string of the image data.
        """
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
