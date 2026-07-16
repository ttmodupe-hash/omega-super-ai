"""Omega AI v3 — Self-Registering Plugin Architecture

Plugin system where new capabilities can be added without modifying core_brain.py.

Example:
    @capability("weather", keywords=["weather", "forecast", "temperature"], priority=1)
    class WeatherPlugin:
        def handle(self, query: str) -> dict:
            return {"response": "Weather data here...", "sources": []}
"""
from __future__ import annotations

import importlib
import importlib.util
import inspect
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Type, Union


class PluginError(Exception):
    """Raised when a plugin operation fails."""


class PluginNotFoundError(PluginError):
    """Raised when a requested plugin handler is not found."""


class PluginInterface:
    """Abstract interface that all capability handler classes must implement."""

    def handle(self, query: str) -> dict:
        raise NotImplementedError("Plugins must implement handle(query: str) -> dict")


class _CapabilityRecord:
    """Internal data holder for a registered capability."""

    __slots__ = ("name", "handler_class", "keywords", "priority", "instance")

    def __init__(self, name: str, handler_class: Type, keywords: list[str], priority: int = 0) -> None:
        self.name = name
        self.handler_class = handler_class
        self.keywords = keywords
        self.priority = priority
        self.instance = None

    def get_instance(self):
        if self.instance is None:
            self.instance = self.handler_class()
        return self.instance

    def score(self, query: str) -> float:
        query_lower = query.lower()
        score = 0.0
        for kw in self.keywords:
            kw_lower = kw.lower()
            if kw_lower in query_lower:
                for word in query_lower.split():
                    if kw_lower == word:
                        score += 1.0
                        break
                else:
                    score += 0.3
        score += self.priority * 0.01
        return score

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "keywords": self.keywords,
            "priority": self.priority,
            "handler": f"{self.handler_class.__module__}.{self.handler_class.__qualname__}",
        }


class PluginRegistry:
    """Central registry for Omega-AI capability plugins (singleton)."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._capabilities = {}
            cls._instance._frozen = False
        return cls._instance

    def register(self, name: str, handler_class: Type, keywords: list[str], priority: int = 0) -> None:
        if not inspect.isclass(handler_class):
            raise PluginError(f"Handler for '{name}' must be a class, got {type(handler_class)}")
        if not hasattr(handler_class, "handle") or not callable(getattr(handler_class, "handle")):
            raise PluginError(f"Handler class for '{name}' must implement handle(query: str) -> dict")
        if name in self._capabilities and self._frozen:
            raise ValueError(f"Capability '{name}' is already registered and registry is frozen")
        self._capabilities[name] = _CapabilityRecord(name, handler_class, keywords, priority)

    def unregister(self, name: str) -> None:
        if name not in self._capabilities:
            raise PluginNotFoundError(f"Capability '{name}' not found in registry")
        del self._capabilities[name]

    def decorator(self, name: str, keywords: list[str], priority: int = 0):
        def _wrapper(cls: Type) -> Type:
            self.register(name, cls, keywords, priority)
            return cls
        return _wrapper

    def discover(self, directory: str | Path, package_prefix: str = "") -> int:
        count_before = len(self._capabilities)
        dir_path = Path(directory).resolve()
        if not dir_path.is_dir():
            raise PluginError(f"Plugin directory does not exist: {dir_path}")
        str_path = str(dir_path)
        added_to_path = False
        if str_path not in sys.path:
            sys.path.insert(0, str_path)
            added_to_path = True
        try:
            for entry in sorted(dir_path.glob("*.py")):
                if entry.name.startswith("_"):
                    continue
                module_name = f"{package_prefix}.{entry.stem}" if package_prefix else entry.stem
                try:
                    spec = importlib.util.spec_from_file_location(module_name, entry)
                    if spec is None or spec.loader is None:
                        continue
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
                except Exception as exc:
                    print(f"[PluginRegistry] Failed to load {entry.name}: {exc}")
        finally:
            if added_to_path:
                sys.path.remove(str_path)
        return len(self._capabilities) - count_before

    def get_handler(self, name: str):
        if name not in self._capabilities:
            raise PluginNotFoundError(f"Capability '{name}' not found. Registered: {list(self._capabilities.keys())}")
        return self._capabilities[name].get_instance()

    def match_intent(self, query: str, threshold: float = 0.0):
        if not self._capabilities:
            return None
        scored = [(record, record.score(query)) for record in self._capabilities.values()]
        scored.sort(key=lambda x: (x[1], x[0].priority), reverse=True)
        best_record, best_score = scored[0]
        if best_score <= threshold:
            return None
        return best_record.get_instance()

    def list_capabilities(self) -> list[dict]:
        return [record.to_dict() for record in self._capabilities.values()]

    def freeze(self) -> None:
        self._frozen = True

    def unfreeze(self) -> None:
        self._frozen = False

    def __len__(self) -> int:
        return len(self._capabilities)

    def __contains__(self, name: str) -> bool:
        return name in self._capabilities

    def __repr__(self) -> str:
        names = ", ".join(self._capabilities.keys())
        return f"PluginRegistry({len(self._capabilities)} capabilities: {names})"


registry = PluginRegistry()


def capability(name: str, keywords: list[str], priority: int = 0) -> Callable[[Type], Type]:
    """Class decorator — register the decorated class as a named capability."""
    return registry.decorator(name, keywords, priority)


# Built-in example plugins
@capability("weather", keywords=["weather", "forecast", "temperature", "rain", "sunny"], priority=1)
class WeatherPlugin:
    def handle(self, query: str) -> dict:
        return {"response": "Weather data would appear here... (integrate OpenWeatherMap or similar)", "sources": ["weather-api"]}


@capability("news", keywords=["news", "headlines", "latest", "today"], priority=0)
class NewsPlugin:
    def handle(self, query: str) -> dict:
        return {"response": "Latest headlines would appear here... (integrate NewsAPI or similar)", "sources": ["news-api"]}


@capability("stocks", keywords=["stock", "price", "ticker", "market", "invest"], priority=2)
class StocksPlugin:
    def handle(self, query: str) -> dict:
        return {"response": "Stock data would appear here... (integrate Yahoo Finance or similar)", "sources": ["yahoo-finance"]}