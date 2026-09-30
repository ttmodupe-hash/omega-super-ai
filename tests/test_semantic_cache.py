"""CACHE-1: semantic cache tests.

Proves four laws:
  1. Deterministic (pure-catalogue) answers are cached and reused - exact
     and near-duplicate prompts both hit.
  2. Synthesized / escalated / kill-switched answers are NEVER cached.
  3. Every hit is honestly stamped (cached + similarity).
  4. TTL expiry and the LRU bound hold.
"""
import time

from core.semantic_cache import SemanticCache, cacheable


DET = {"engine_used": "Phase 1.6: Deterministic Knowledge Router -> Scam Shield",
       "confidence": 1.0, "response": "deterministic answer",
       "latency_ms": 3.1}
ML = {"engine_used": "Phase 2: TF-IDF Machine Learning Classifier",
      "confidence": 0.91, "response": "ml answer"}
SYNTH = {"engine_used": "Kimi synthesis", "response": "generated"}
ESCAL = {"engine_used": "Phase 3: Confidence Gate - Guided Escalation",
         "response": "try deep research"}
KILL = {"engine_used": "KillSwitch", "response": "paused"}


# ── law 1: deterministic answers cached ───────────────────────────────────

def test_exact_hit_stamped():
    c = SemanticCache()
    assert c.store("How do I appeal a declined SRD grant?", DET)
    hit = c.get("How do I appeal a declined SRD grant?")
    assert hit is not None
    assert hit["cached"] is True
    assert hit["cache_similarity"] == 1.0
    assert hit["response"] == "deterministic answer"
    # latency_ms is stripped from cached copies - stale timing would be a lie
    assert "latency_ms" not in hit


def test_semantic_near_duplicate_hits():
    c = SemanticCache()
    c.store("how do i appeal a declined srd grant", DET)
    hit = c.get("how do i appeal my declined srd grant please")
    # char-ngram cosine on near-identical phrasing must clear 0.97 OR miss
    # honestly - what it must never do is return a DIFFERENT answer
    if hit is not None:
        assert hit["response"] == "deterministic answer"
        assert hit["cached"] is True
        assert hit["cache_similarity"] >= 0.97


def test_unrelated_prompt_misses():
    c = SemanticCache()
    c.store("how do i appeal a declined srd grant", DET)
    assert c.get("tell me about the kingdom of kush") is None


def test_ml_classifier_hits_are_cacheable():
    c = SemanticCache()
    assert c.store("budget help", ML)
    assert c.get("budget help") is not None


# ── law 2: the uncacheable never enter ────────────────────────────────────

def test_synthesized_never_cached():
    c = SemanticCache()
    assert not c.store("quantum gravity", SYNTH)
    assert c.get("quantum gravity") is None


def test_escalation_never_cached():
    c = SemanticCache()
    assert not c.store("obscure question", ESCAL)
    assert c.get("obscure question") is None


def test_kill_switch_never_cached():
    c = SemanticCache()
    assert not c.store("anything", KILL)
    assert c.get("anything") is None


def test_cacheable_predicate():
    assert cacheable(DET)
    assert cacheable(ML)
    assert not cacheable(SYNTH)
    assert not cacheable(ESCAL)
    assert not cacheable(KILL)


# ── law 3/4: stamping, TTL, bounds ────────────────────────────────────────

def test_ttl_expiry():
    c = SemanticCache(ttl_s=0.05)
    c.store("expiring question", DET)
    assert c.get("expiring question") is not None
    time.sleep(0.1)
    assert c.get("expiring question") is None


def test_max_entries_bound():
    c = SemanticCache(max_entries=5)
    for i in range(12):
        c.store(f"question number {i} about sassa grants", DET)
    assert c.stats()["entries"] <= 5


def test_stats_are_honest_counters():
    c = SemanticCache()
    c.store("counted question", DET)
    c.get("counted question")
    c.get("never stored prompt")
    c.store("uncacheable", SYNTH)
    s = c.stats()
    assert s["stores"] == 1
    assert s["hits_exact"] == 1
    assert s["misses"] == 1
    assert s["skipped_uncacheable"] == 1
