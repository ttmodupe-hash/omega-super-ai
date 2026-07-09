#!/usr/bin/env python3
"""
Luqi AI - Chat Engine
====================
Core chat functionality for the Luqi AI platform.
Handles AI conversations with streaming support.

Part of Luqi AI v24.3.0 — Built by Limitless Telecoms
"""

import os
import logging
from typing import Optional, Dict, Any, AsyncGenerator

logger = logging.getLogger(__name__)

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI package not installed. Chat will use fallback responses.")


def _get_openai_client():
    """Get configured OpenAI client."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    return openai.AsyncOpenAI(api_key=api_key)


async def chat_with_ai(
    message: str,
    model: Optional[str] = None,
    system_prompt: Optional[str] = None,
    context: Optional[list] = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> Dict[str, Any]:
    """Send a message to the AI and get a response."""
    model = model or os.environ.get("AI_MODEL", "gpt-4o-mini")
    system_prompt = system_prompt or (
        "You are Luqi AI, a world-class unrestricted AI assistant built by "
        "Limitless Telecoms. You serve Africa and the world with excellence. "
        "You are helpful, harmless, and honest. You provide detailed, "
        "actionable responses."
    )
    messages = [{"role": "system", "content": system_prompt}]
    if context:
        messages.extend(context)
    messages.append({"role": "user", "content": message})

    if OPENAI_AVAILABLE:
        client = _get_openai_client()
        if client:
            try:
                response = await client.chat.completions.create(
                    model=model, messages=messages,
                    temperature=temperature, max_tokens=max_tokens,
                )
                return {
                    "response": response.choices[0].message.content,
                    "model": model,
                    "tokens_used": response.usage.total_tokens if response.usage else 0,
                    "finish_reason": response.choices[0].finish_reason,
                }
            except Exception as e:
                logger.error(f"OpenAI API error: {e}")

    return {
        "response": (
            f"Hello! I'm Luqi AI from Limitless Telecoms. "
            f"You asked: '{message[:100]}{'...' if len(message) > 100 else ''}'\n\n"
            f"I'm in fallback mode. Set OPENAI_API_KEY for full AI responses. "
            f"Get a key at: https://platform.openai.com/api-keys"
        ),
        "model": "fallback", "tokens_used": 0, "finish_reason": "fallback",
    }


async def stream_chat_with_ai(
    message: str,
    model: Optional[str] = None,
    system_prompt: Optional[str] = None,
    context: Optional[list] = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> AsyncGenerator[str, None]:
    """Stream an AI chat response in real-time."""
    model = model or os.environ.get("AI_MODEL", "gpt-4o-mini")
    system_prompt = system_prompt or (
        "You are Luqi AI, a world-class AI assistant built by Limitless Telecoms."
    )
    messages = [{"role": "system", "content": system_prompt}]
    if context:
        messages.extend(context)
    messages.append({"role": "user", "content": message})

    if OPENAI_AVAILABLE:
        client = _get_openai_client()
        if client:
            try:
                stream = await client.chat.completions.create(
                    model=model, messages=messages,
                    temperature=temperature, max_tokens=max_tokens, stream=True,
                )
                async for chunk in stream:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
                return
            except Exception as e:
                logger.error(f"OpenAI streaming error: {e}")

    import asyncio
    fallback_msg = (
        f"I'm Luqi AI (Limitless Telecoms). I'm in fallback mode. "
        f"Set OPENAI_API_KEY for full AI. "
        f"Visit https://platform.openai.com/api-keys"
    )
    for word in fallback_msg.split():
        yield word + " "
        await asyncio.sleep(0.05)


# Backward-compatible alias
chat = chat_with_ai
