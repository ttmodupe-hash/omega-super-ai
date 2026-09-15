"""Omega AI v3 — Local & Cloud LLM Integration
Ollama local LLM with OpenAI fallback. Now with streaming support.
"""
from __future__ import annotations

import json
import urllib.request
from typing import Any, Generator

from config import CONFIG
from utils import print_warning, print_info


class OllamaClient:
    def __init__(self, host: str = "", model: str = "") -> None:
        self.host = host or str(CONFIG.get("OLLAMA_HOST", "http://localhost:11434"))
        self.model = model or str(CONFIG.get("OLLAMA_MODEL", "llama3"))
        self._available: bool | None = None

    def is_available(self) -> bool:
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

    def chat(self, prompt: str, system_prompt: str = "", model: str = "", temperature: float = 0.7) -> str:
        target_model = model or self.model
        payload: dict[str, Any] = {
            "model": target_model, "messages": [], "stream": False,
            "options": {"temperature": temperature},
        }
        if system_prompt:
            payload["messages"].append({"role": "system", "content": system_prompt})
        payload["messages"].append({"role": "user", "content": prompt})
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.host}/api/chat", data=data,
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read())
                return result.get("message", {}).get("content", "")
        except Exception as e:
            return f"[Ollama Error: {e}]"


class OpenAIFallback:
    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key or str(CONFIG.get("OPENAI_API_KEY", ""))
        self.base_url = "https://api.openai.com/v1"

    def is_available(self) -> bool:
        return bool(self.api_key)

    def chat(self, prompt: str, system_prompt: str = "", model: str = "gpt-3.5-turbo", temperature: float = 0.7) -> str:
        if not self.api_key:
            return "[Error: No OpenAI API key configured]"
        payload: dict[str, Any] = {
            "model": model, "messages": [], "temperature": temperature}
        if system_prompt:
            payload["messages"].append({"role": "system", "content": system_prompt})
        payload["messages"].append({"role": "user", "content": prompt})
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/chat/completions", data=data,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
                method="POST")
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read())
                return result["choices"][0]["message"].get("content", "")
        except Exception as e:
            return f"[OpenAI Error: {e}]"


class LLM:
    def __init__(self) -> None:
        self.ollama = OllamaClient()
        self.openai = OpenAIFallback()
        self.provider: str = ""
        self._select_provider()

    def _select_provider(self) -> None:
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
        if self.provider == "ollama":
            return self.ollama.chat(prompt, system_prompt, temperature=temperature)
        elif self.provider == "openai":
            return self.openai.chat(prompt, system_prompt, temperature=temperature)
        else:
            return self._mock_response(prompt)

    def _mock_response(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        if "research" in prompt_lower or "analyze" in prompt_lower:
            return f"[Research Mode] Based on available data about '{truncate_text(prompt, 80)}'...\n\nNote: Connect Ollama or set OPENAI_API_KEY for full LLM responses."
        elif "invest" in prompt_lower or "crypto" in prompt_lower or "bitcoin" in prompt_lower:
            return "[Investment Analysis] Crypto markets are volatile. DYOR. Consider hardware costs, electricity, and pool fees for mining.\n\nNote: Connect Ollama or set OPENAI_API_KEY for detailed analysis."
        elif "tax" in prompt_lower:
            return "[Tax Guidance] Tax rules vary by country. Please specify your country for accurate guidance.\n\nNote: Connect Ollama or set OPENAI_API_KEY for detailed advice."
        else:
            return f"[Luqi-AI Response] I received your query about '{truncate_text(prompt, 80)}'.\n\nNote: For enhanced responses, connect Ollama (http://localhost:11434) or set OPENAI_API_KEY in your .env file."

    # -- Streaming (new) --

    def stream_chat(self, prompt: str, system_prompt: str = "", temperature: float = 0.7) -> Generator[str, None, None]:
        if self.provider == "ollama":
            yield from self._stream_ollama(prompt, system_prompt, temperature)
        elif self.provider == "openai":
            yield from self._stream_openai(prompt, system_prompt, temperature)
        else:
            yield self._mock_response(prompt)

    def _stream_ollama(self, prompt: str, system_prompt: str, temperature: float) -> Generator[str, None, None]:
        payload: dict[str, Any] = {
            "model": self.ollama.model, "messages": [], "stream": True,
            "options": {"temperature": temperature},
        }
        if system_prompt:
            payload["messages"].append({"role": "system", "content": system_prompt})
        payload["messages"].append({"role": "user", "content": prompt})
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.ollama.host}/api/chat", data=data,
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=60) as resp:
                for line in resp:
                    if line.strip():
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if chunk.get("done", False):
                            break
        except Exception as e:
            yield f"[Streaming Error: {e}]"

    def _stream_openai(self, prompt: str, system_prompt: str, temperature: float, model: str = "gpt-3.5-turbo") -> Generator[str, None, None]:
        if not self.openai.api_key:
            yield "[Error: No OpenAI API key configured]"
            return
        payload: dict[str, Any] = {
            "model": model, "messages": [], "temperature": temperature, "stream": True}
        if system_prompt:
            payload["messages"].append({"role": "system", "content": system_prompt})
        payload["messages"].append({"role": "user", "content": prompt})
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.openai.base_url}/chat/completions", data=data,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.openai.api_key}"},
                method="POST")
            with urllib.request.urlopen(req, timeout=60) as resp:
                for line in resp:
                    line_str = line.decode("utf-8").strip()
                    if not line_str or not line_str.startswith("data: "):
                        continue
                    json_str = line_str[6:]
                    if json_str == "[DONE]":
                        break
                    chunk = json.loads(json_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if delta:
                        yield delta
        except Exception as e:
            yield f"[Streaming Error: {e}]"


def truncate_text(text: str, max_len: int = 500) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rsplit(" ", 1)[0] + "..."