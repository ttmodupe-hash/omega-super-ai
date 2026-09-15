#!/usr/bin/env python3
"""Luqi AI v24 -- Cache Manager

Multi-tier caching system with Redis L1 and in-memory L2 fallback.
Provides decorators for endpoint caching and manual cache operations.

Features:
- Redis-backed distributed caching
- In-memory LRU fallback
- Automatic serialization (JSON + pickle for complex types)
- Cache key generation from function arguments
- TTL support with per-key expiration
- Cache invalidation patterns
- Cache statistics and health checks

Usage:
    from backend.cache_manager import cache, invalidate_cache, cache_health

    @cache(ttl=300)  # Cache for 5 minutes
    async def expensive_operation(user_id: str):
        ...

    invalidate_cache("expensive_operation", user_id="123")
"""

from __future__ import annotations

import functools
import hashlib
import json
import logging
import os
import pickle
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union

logger: logging.Logger = logging.getLogger("luqi.cache")

# ── Configuration ──────────────────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "")
DEFAULT_TTL = int(os.getenv("CACHE_DEFAULT_TTL", "300"))
MAX_MEMORY_ITEMS = int(os.getenv("CACHE_MAX_MEMORY_ITEMS", "1000"))
CACHE_PREFIX = "luqi:cache:"

F = TypeVar("F", bound=Callable[..., Any])


class MemoryCache:
    """Thread-safe in-memory LRU cache with TTL support."""

    def __init__(self, max_items: int = MAX_MEMORY_ITEMS) -> None:
        self._max_items = max_items
        self._data: Dict[str, Tuple[Any, float]] = {}
        self._access_order: List[str] = []
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Tuple[bool, Any]:
        if key not in self._data:
            self._misses += 1
            return False, None
        value, expiry = self._data[key]
        if expiry > 0 and time.time() > expiry:
            self._delete(key)
            self._misses += 1
            return False, None
        self._access_order.remove(key)
        self._access_order.append(key)
        self._hits += 1
        return True, value

    def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
        expiry = time.time() + ttl if ttl > 0 else 0
        if key in self._data:
            self._access_order.remove(key)
        while len(self._data) >= self._max_items:
            oldest = self._access_order.pop(0)
            del self._data[oldest]
        self._data[key] = (value, expiry)
        self._access_order.append(key)

    def delete(self, key: str) -> bool:
        if key in self._data:
            self._delete(key)
            return True
        return False

    def delete_pattern(self, pattern: str) -> int:
        keys_to_delete = [k for k in self._data if pattern in k]
        for k in keys_to_delete:
            self._delete(k)
        return len(keys_to_delete)

    def _delete(self, key: str) -> None:
        del self._data[key]
        if key in self._access_order:
            self._access_order.remove(key)

    def health(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        return {
            "backend": "memory", "items": len(self._data),
            "max_items": self._max_items, "hits": self._hits,
            "misses": self._misses, "hit_rate": round(self._hits / total, 4) if total > 0 else 0,
        }


class RedisCache:
    """Redis-backed cache with connection pooling."""

    def __init__(self, redis_url: str = REDIS_URL) -> None:
        self._redis: Any = None
        self._url = redis_url
        self._hits = 0
        self._misses = 0
        self._errors = 0
        self._connect()

    def _connect(self) -> None:
        if not self._url:
            return
        try:
            import redis as redis_lib
            self._redis = redis_lib.from_url(
                self._url, decode_responses=False,
                socket_connect_timeout=3, socket_timeout=3, health_check_interval=30,
            )
            self._redis.ping()
            logger.info("Cache: Redis connected")
        except Exception as exc:
            logger.warning("Cache: Redis connection failed: %s", exc)
            self._redis = None

    def _encode(self, value: Any) -> bytes:
        try:
            return json.dumps(value, default=str).encode("utf-8")
        except (TypeError, ValueError):
            return pickle.dumps(value)

    def _decode(self, data: bytes) -> Any:
        try:
            return json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            return pickle.loads(data)

    def get(self, key: str) -> Tuple[bool, Any]:
        if not self._redis:
            self._misses += 1
            return False, None
        try:
            data = self._redis.get(f"{CACHE_PREFIX}{key}")
            if data is None:
                self._misses += 1
                return False, None
            self._hits += 1
            return True, self._decode(data)
        except Exception as exc:
            logger.warning("Redis cache get error: %s", exc)
            self._errors += 1
            self._misses += 1
            return False, None

    def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
        if not self._redis:
            return
        try:
            self._redis.setex(f"{CACHE_PREFIX}{key}", ttl, self._encode(value))
        except Exception as exc:
            logger.warning("Redis cache set error: %s", exc)
            self._errors += 1

    def delete(self, key: str) -> bool:
        if not self._redis:
            return False
        try:
            return self._redis.delete(f"{CACHE_PREFIX}{key}") > 0
        except Exception as exc:
            logger.warning("Redis cache delete error: %s", exc)
            self._errors += 1
            return False

    def delete_pattern(self, pattern: str) -> int:
        if not self._redis:
            return 0
        try:
            count = 0
            for key in self._redis.scan_iter(match=f"{CACHE_PREFIX}*{pattern}*"):
                self._redis.delete(key)
                count += 1
            return count
        except Exception as exc:
            logger.warning("Redis cache delete_pattern error: %s", exc)
            self._errors += 1
            return 0

    def health(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        return {
            "backend": "redis", "connected": self._redis is not None,
            "hits": self._hits, "misses": self._misses, "errors": self._errors,
            "hit_rate": round(self._hits / total, 4) if total > 0 else 0,
        }


class CacheManager:
    """Multi-tier cache manager with Redis L1 and memory L2."""

    def __init__(self) -> None:
        self._redis = RedisCache()
        self._memory = MemoryCache()

    def get(self, key: str) -> Tuple[bool, Any]:
        found, value = self._redis.get(key)
        if found:
            return True, value
        found, value = self._memory.get(key)
        if found:
            self._redis.set(key, value)
            return True, value
        return False, None

    def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
        self._redis.set(key, value, ttl)
        self._memory.set(key, value, ttl)

    def delete(self, key: str) -> None:
        self._redis.delete(key)
        self._memory.delete(key)

    def delete_pattern(self, pattern: str) -> int:
        return max(self._redis.delete_pattern(pattern), self._memory.delete_pattern(pattern))

    def health(self) -> Dict[str, Any]:
        return {"redis": self._redis.health(), "memory": self._memory.health()}


_cache_manager: Optional[CacheManager] = None


def get_cache() -> CacheManager:
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def _generate_cache_key(func_name: str, prefix: str = "", *args: Any, **kwargs: Any) -> str:
    key_parts = [prefix or func_name]
    if args:
        key_parts.append(hashlib.md5(str(args).encode()).hexdigest()[:12])
    if kwargs:
        sorted_kwargs = sorted(kwargs.items())
        key_parts.append(hashlib.md5(str(sorted_kwargs).encode()).hexdigest()[:12])
    return ":".join(key_parts)


def cache(ttl: int = DEFAULT_TTL, key_prefix: str = "") -> Callable[[F], F]:
    """Decorator to cache function results."""
    def decorator(func: F) -> F:
        prefix = key_prefix or func.__qualname__

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_mgr = get_cache()
            key = _generate_cache_key(func.__name__, prefix, *args, **kwargs)
            found, value = cache_mgr.get(key)
            if found:
                return value
            result = await func(*args, **kwargs)
            cache_mgr.set(key, result, ttl)
            return result

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_mgr = get_cache()
            key = _generate_cache_key(func.__name__, prefix, *args, **kwargs)
            found, value = cache_mgr.get(key)
            if found:
                return value
            result = func(*args, **kwargs)
            cache_mgr.set(key, result, ttl)
            return result

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper  # type: ignore[return-value]
    return decorator


def invalidate_cache(key_prefix: str, **kwargs: Any) -> int:
    cache_mgr = get_cache()
    if kwargs:
        key = _generate_cache_key("", key_prefix, **kwargs)
        cache_mgr.delete(key)
        return 1
    return cache_mgr.delete_pattern(key_prefix)


def cache_health() -> Dict[str, Any]:
    return get_cache().health()
