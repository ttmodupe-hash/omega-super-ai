"""Omega AI v3 — Local & Cloud LLM Integration
Ollama local LLM with OpenAI fallback.
"""
from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Any

from config import CONFIG
from utils import print_warning, print_info


class OllamaClient:
    """Client for Ollama local LLM server."""

    def __init__(self, host: str = "", model: str = "") -> None:
        self.host = host or str(CONFIG.get("OLLAMA_HOST", "http://localhost:11434"))
        self.model = model or str(CONFIG.get("OLLAMA_MODEL", "llama3"))
        self._available: bool | None = None

    def is_available(self) -> bool:
        """Check if Ollama server is reachable."""
        if self._available is not None:
            return self._available
        try:
            req = urllib.request.Request(f"{self.host}/api/tags", method="GET", timeout=5)
            with urllib.request.urlopen(req) as resp:
                self._available = resp.status == 200
                return self._available
        except Exception:
            self._available = False
            return False

    def list_models(self) -> list[str]:
        """List available local models."""
        try:
            req = urllib.request.Request(f"{self.host}/api/tags", method="GET", timeout=5)
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read())
                return [m.get("name", "") for m in data.get("models", [])]
        except Exception as e:
            return [f"Error: {e}"]

    def chat(self, prompt: str, system_prompt: str = "", model: str = "", temperature: float = 0.7) -> str:
        """Send chat request to Ollama."""
        target_model = model or self.model
        payload: dict[str, Any] = {
            "model": target_model,
            "messages": [],
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system_prompt:
            payload["messages"].append({"role": "system", "content": system_prompt})
        payload["messages"].append({"role": "user", "content": prompt})

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.host}/api/chat",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read())
                return result.get("message", {}).get("content", "")
        except Exception as e:
            return f"[Ollama Error: {e}]"


class OpenAIFallback:
    """OpenAI API fallback when Ollama is unavailable."""

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key or str(CONFIG.get("OPENAI_API_KEY", ""))
        self.base_url = "https://api.openai.com/v1"

    def is_available(self) -> bool:
        return bool(self.api_key)

    def chat(self, prompt: str, system_prompt: str = "", model: str = "gpt-3.5-turbo", temperature: float = 0.7) -> str:
        """Send chat request to OpenAI."""
        if not self.api_key:
            return "[Error: No OpenAI API key configured]"

        payload: dict[str, Any] = {
            "model": model,
            "messages": [],
            "temperature": temperature,
        }
        if system_prompt:
            payload["messages"].append({"role": "system", "content": system_prompt})
        payload["messages"].append({"role": "user", "content": prompt})

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/chat/completions",
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read())
                return result["choices"][0]["message"].get("content", "")
        except Exception as e:
            return f"[OpenAI Error: {e}]"


class LLM:
    """Unified LLM interface — auto-selects best available provider."""

    def __init__(self) -> None:
        self.ollama = OllamaClient()
        self.openai = OpenAIFallback()
        self.provider: str = ""
        self._select_provider()

    def _select_provider(self) -> None:
        """Select the best available LLM provider."""
        if self.ollama.is_available():
            self.provider = "ollama"
            print_info("Using Ollama local LLM")
        elif self.openai.is_available():
            self.provider = "openai"
            print_info("Using OpenAI API")
        else:
            self.provider = "mock"
            print_warning("No LLM available — using keyword-based mock responses")

    def chat(self, prompt: str, system_prompt: str = "", temperature: float = 0.7) -> str:
        """Send chat to selected provider."""
        if self.provider == "ollama":
            return self.ollama.chat(prompt, system_prompt, temperature=temperature)
        elif self.provider == "openai":
            return self.openai.chat(prompt, system_prompt, temperature=temperature)
        else:
            return self._mock_response(prompt)

    def _mock_response(self, prompt: str) -> str:
        """Generate a context-aware mock response when no LLM is available."""
        prompt_lower = prompt.lower()
        if "research" in prompt_lower or "analyze" in prompt_lower:
            return f"[Research Mode] Based on available data about '{truncate_text(prompt, 80)}'...\n\nNote: Connect Ollama or set OPENAI_API_KEY for full LLM responses."
        elif "invest" in prompt_lower or "crypto" in prompt_lower or "bitcoin" in prompt_lower:
            return "[Investment Analysis] Crypto markets are volatile. DYOR. Consider hardware costs, electricity, and pool fees for mining.\n\nNote: Connect Ollama or set OPENAI_API_KEY for detailed analysis."
        elif "tax" in prompt_lower:
            return "[Tax Guidance] Tax rules vary by country. Please specify your country for accurate guidance.\n\nNote: Connect Ollama or set OPENAI_API_KEY for detailed advice."
        else:
            return f"[Luqi-AI Response] I received your query about '{truncate_text(prompt, 80)}'.\n\nNote: For enhanced responses, connect Ollama (http://localhost:11434) or set OPENAI_API_KEY in your .env file."


def truncate_text(text: str, max_len: int = 500) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rsplit(" ", 1)[0] + "..."


if __name__ == "__main__":
    llm = LLM()
    print(f"Provider: {llm.provider}")
    resp = llm.chat("Explain Bitcoin mining in simple terms", system_prompt="You are a helpful assistant.")
    print(resp[:500])
