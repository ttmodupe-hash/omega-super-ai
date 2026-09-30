"""
OMEGA-LUQI Semantic Cache (CACHE-1) - in-process near-duplicate reuse.

Cost law: the founder funds this platform personally. Statutory and scam
questions repeat endlessly across users ("srd appeal", "SRD grant appeal",
"how do I appeal my SRD..."). Re-answering them wastes cycles and latency.

Safety law (the reason this module is narrow BY DESIGN):
  ONLY deterministic responses are cacheable - outputs that are pure
  functions of the shipped catalogue (Phase 1 / Phase 1.6 / Phase 2 router
  hits). Reuse of a pure function's output is exact truth, not approximation.
  Kimi-synthesized, escalated, or kill-switched responses are NEVER cached:
  a cached hallucination would be a hallucination with staying power.

Mechanics:
  - Exact path: normalized-prompt dict lookup, O(1).
  - Semantic path: TF-IDF (word 1-2 grams + char 3-5 grams) cosine >= 0.97
    against cached prompts, via scikit-learn (already a pinned dependency -
    no new infra, no Redis, no hosting cost).
  - TTL 24h + 2048-entry LRU bound; catalogue reloads (process restart)
    naturally flush it since the cache is in-process.
  - Every hit is stamped "cached": true with its similarity score - the
    console may show it, and telemetry can prove the saving honestly.

Env: LUQI_CACHE=0 disables; LUQI_CACHE_THRESHOLD overrides 0.97;
LUQI_CACHE_TTL_S overrides 86400; LUQI_CACHE_MAX overrides 2048.
"""
import os
import re
import threading
import time
from collections import OrderedDict
from typing import Any, Dict, Optional, Tuple

ENABLED = os.getenv("LUQI_CACHE", "1") != "0"
THRESHOLD = float(os.getenv("LUQI_CACHE_THRESHOLD", "0.97"))
TTL_S = float(os.getenv("LUQI_CACHE_TTL_S", "86400"))
MAX_ENTRIES = int(os.getenv("LUQI_CACHE_MAX", "2048"))

_CACHEABLE_MARKERS = ("Deterministic", "Phase 2: TF-IDF")

_norm_re = re.compile(r"[^a-z0-9 ]+")


def _normalize(text: str) -> str:
    return " ".join(_norm_re.sub(" ", text.lower()).split())


def cacheable(response: Dict[str, Any]) -> bool:
    """True only for pure-catalogue responses. Anything synthesized,
    escalated, or kill-switched is uncacheable BY LAW."""
    engine = str(response.get("engine_used", ""))
    return any(m in engine for m in _CACHEABLE_MARKERS)


class SemanticCache:
    """Thread-safe, in-process. One instance per worker - which is the
    correct scope: a worker crash or redeploy flushes stale knowledge."""

    def __init__(self, threshold: float = THRESHOLD, ttl_s: float = TTL_S,
                 max_entries: int = MAX_ENTRIES):
        self.threshold = threshold
        self.ttl_s = ttl_s
        self.max_entries = max_entries
        self._lock = threading.Lock()
        # norm_prompt -> (timestamp, response)
        self._exact: "OrderedDict[str, Tuple[float, Dict[str, Any]]]" = OrderedDict()
        self._vectorizer = None      # lazy: sklearn import only when caching
        self._matrix = None          # sparse matrix aligned with _keys
        self._keys: list = []
        # Per-instance counters: a shared global would let one cache's
        # numbers pose as another's - telemetry must be as honest as answers.
        self._meter = {"hits_exact": 0, "hits_semantic": 0, "misses": 0,
                       "stores": 0, "skipped_uncacheable": 0}

    def _vec(self):
        if self._vectorizer is None:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self._vectorizer = TfidfVectorizer(
                analyzer="char_wb", ngram_range=(3, 5), min_df=1)
        return self._vectorizer

    def _rebuild_matrix_locked(self):
        if self._keys:
            self._matrix = self._vec().fit_transform(
                [k for k in self._keys])
        else:
            self._matrix = None

    def _evict_locked(self):
        now = time.time()
        expired = [k for k, (ts, _) in self._exact.items()
                   if now - ts > self.ttl_s]
        for k in expired:
            self._exact.pop(k, None)
        while len(self._exact) > self.max_entries:
            self._exact.popitem(last=False)  # LRU: oldest first
        live = list(self._exact.keys())
        if live != self._keys:
            self._keys = live
            self._rebuild_matrix_locked()

    def get(self, text: str) -> Optional[Dict[str, Any]]:
        """Exact first, then semantic near-dup. Stamped copy or None."""
        if not ENABLED:
            return None
        norm = _normalize(text)
        if not norm:
            return None
        now = time.time()
        with self._lock:
            self._evict_locked()
            hit = self._exact.get(norm)
            if hit and now - hit[0] <= self.ttl_s:
                self._exact.move_to_end(norm)
                self._meter["hits_exact"] += 1
                out = dict(hit[1])
                out["cached"] = True
                out["cache_similarity"] = 1.0
                return out
            # semantic path
            if self._matrix is not None and self._keys:
                q = self._vec().transform([norm])
                scores = (self._matrix @ q.T).toarray().ravel()
                best = int(scores.argmax())
                if scores[best] >= self.threshold:
                    key = self._keys[best]
                    ts, resp = self._exact[key]
                    self._exact.move_to_end(key)
                    self._meter["hits_semantic"] += 1
                    out = dict(resp)
                    out["cached"] = True
                    out["cache_similarity"] = round(float(scores[best]), 4)
                    return out
            self._meter["misses"] += 1
            return None

    def store(self, text: str, response: Dict[str, Any]) -> bool:
        """Store only cacheable (deterministic) responses."""
        if not ENABLED:
            return False
        if not cacheable(response):
            self._meter["skipped_uncacheable"] += 1
            return False
        norm = _normalize(text)
        if not norm:
            return False
        with self._lock:
            self._evict_locked()
            clean = {k: v for k, v in response.items()
                     if k not in ("cached", "cache_similarity", "latency_ms")}
            self._exact[norm] = (time.time(), clean)
            self._exact.move_to_end(norm)
            self._evict_locked()  # bound holds at ALL times, not just pre-insert
            self._keys = list(self._exact.keys())
            self._rebuild_matrix_locked()
            self._meter["stores"] += 1
            return True

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {**self._meter, "entries": len(self._exact),
                    "enabled": ENABLED, "threshold": self.threshold,
                    "ttl_s": self.ttl_s, "max_entries": self.max_entries}


# Shared instance for the hybrid front door.
hybrid_cache = SemanticCache()
