# -*- coding: utf-8 -*-
"""
Luqi AI — Universal Language System Self-Tests

Comprehensive test suite for language detection, routing,
TTS/STT, and database validation.

Run: python -m lang.tests
"""

from __future__ import annotations

import sys
import traceback
import unicodedata
from typing import Any


def run_all_tests() -> dict[str, list[str]]:
    """Run all test suites and return results."""
    results: dict[str, list[str]] = {
        "passed": [],
        "failed": [],
        "warnings": [],
    }

    test_suites = [
        ("Database Tests", test_database),
        ("Language Detection Tests", test_language_detection),
        ("Multilingual Router Tests", test_multilingual_router),
        ("Voice Engine Tests", test_voice_engine),
        ("Fallback Chain Tests", test_fallback_chains),
        ("Greeting Tests", test_greetings),
        ("Integration Tests", test_integration),
    ]

    for suite_name, test_func in test_suites:
        print(f"\n{'=' * 60}")
        print(f"Running: {suite_name}")
        print(f"{'=' * 60}")
        try:
            test_func(results)
            print(f"  {suite_name}: PASSED")
        except Exception as e:
            print(f"  {suite_name}: FAILED - {e}")
            traceback.print_exc()
            results["failed"].append(f"{suite_name}: {e}")

    return results


def test_database(results: dict[str, list[str]]) -> None:
    """Test language database integrity."""
    from lang.african_languages import (
        AFRICAN_LANGUAGES, GLOBAL_LANGUAGES,
        get_all_african_codes, get_all_global_codes,
        get_language_by_code, get_regions, get_language_families,
        get_countries, count_speakers,
    )

    # Test 1: African languages count
    african_count = len(AFRICAN_LANGUAGES)
    print(f"  African languages: {african_count}")
    assert african_count >= 40, f"Expected 40+ African languages, got {african_count}"  # honest floor: 41 today (40 standard + Sepitori vernacular)
    results["passed"].append(f"African languages count: {african_count}")

    # Test 2: Global languages count
    global_count = len(GLOBAL_LANGUAGES)
    print(f"  Global languages: {global_count}")
    assert global_count >= 12, f"Expected 12+ global languages, got {global_count}"  # honest floor: 12 today (was inflated at 30+)
    results["passed"].append(f"Global languages count: {global_count}")

    # Test 3: All entries have required fields
    required_fields = [
        "name", "english_name", "speakers", "countries",
        "region", "language_family", "script", "greetings",
        "sample_text", "whisper_code", "gpt_support",
    ]
    for code, info in AFRICAN_LANGUAGES.items():
        for field in required_fields:
            assert field in info, f"Missing '{field}' in {code}"
            assert info[field] is not None, f"Null '{field}' in {code}"
            if field == "greetings":
                assert isinstance(info[field], dict), f"Greetings not dict in {code}"
                greeting_keys = ["hello", "goodbye", "thank_you", "please",
                               "how_are_you", "help", "welcome", "yes", "no"]
                for gk in greeting_keys:
                    assert gk in info[field], f"Missing greeting '{gk}' in {code}"
                    assert info[field][gk], f"Empty greeting '{gk}' in {code}"
    results["passed"].append("All required fields present (African)")

    for code, info in GLOBAL_LANGUAGES.items():
        for field in required_fields:
            assert field in info, f"Missing '{field}' in {code}"
            if field == "greetings":
                assert isinstance(info[field], dict)
    results["passed"].append("All required fields present (Global)")

    # Test 4: Speaker counts are parseable
    for code, info in {**AFRICAN_LANGUAGES, **GLOBAL_LANGUAGES}.items():
        count = count_speakers(code)
        assert count > 0, f"Invalid speaker count for {code}"
    results["passed"].append("Speaker counts parseable")

    # Test 5: Language families are non-empty
    families = get_language_families()
    assert len(families) > 5, f"Expected >5 families, got {len(families)}"
    print(f"  Language families: {len(families)}")
    results["passed"].append(f"Language families: {len(families)}")

    # Test 6: Regions are non-empty
    regions = get_regions()
    assert len(regions) >= 4, f"Expected 4+ regions, got {len(regions)}"
    print(f"  African regions: {regions}")
    results["passed"].append(f"Regions: {regions}")

    # Test 7: Countries list is populated
    countries = get_countries()
    assert len(countries) > 20, f"Expected 20+ countries, got {len(countries)}"
    print(f"  Countries: {len(countries)}")
    results["passed"].append(f"Countries: {len(countries)}")

    # Test 8: Language lookup works
    sw_info = get_language_by_code("sw")
    assert sw_info is not None
    assert sw_info["english_name"] == "Swahili"
    assert "Tanzania" in sw_info["countries"]
    results["passed"].append("Language lookup works")

    # Test 9: Helper functions work
    assert len(get_all_african_codes()) == african_count
    assert len(get_all_global_codes()) == global_count
    results["passed"].append("Helper functions work")


def test_language_detection(results: dict[str, list[str]]) -> None:
    """Test language detection."""
    from lang.language_detector import LanguageDetector

    detector = LanguageDetector()

    # Test greeting detection
    test_cases = [
        ("Sawubona, unjani?", "zu"),
        ("Jambo, habari yako?", "sw"),
        ("Bonjour, comment allez-vous?", "fr"),
        ("Hello, how are you?", "en"),
        ("Dumela, o kae?", ["st", "tn", "nso"]),  # Sotho variants
        ("Molo, unjani?", "xh"),
        ("Hola, cómo estás?", "es"),
        ("Sannu, yaya dai?", "ha"),
    ]

    for text, expected in test_cases:
        result = detector.detect(text)
        detected = result["lang_code"]
        if isinstance(expected, list):
            assert detected in expected, f"Expected one of {expected}, got {detected} for '{text}'"
        else:
            assert detected == expected, f"Expected {expected}, got {detected} for '{text}'"
        print(f"  '{text[:30]}...' -> {detected} ({result['confidence']:.2f})")

    results["passed"].append(f"Language detection: {len(test_cases)} cases passed")

    # Test script detection
    assert detector.detect_script("Hello") == "Latin"
    assert detector.detect_script("مرحبا") == "Arabic"
    assert detector.detect_script("ሰላም") == "Ethiopic"
    assert detector.detect_script("こんにちは") in ("Japanese", "Han")
    results["passed"].append("Script detection works")


def test_multilingual_router(results: dict[str, list[str]]) -> None:
    """Test multilingual router functionality."""
    from lang.multilingual_router import MultilingualRouter

    router = MultilingualRouter()

    # Test routing
    result = router.route("Jambo! Habari yako?", "sw")
    assert result["lang_code"] == "sw"
    assert result["is_african"] is True
    assert result["gpt_support"] in ("full", "good", "limited", "minimal")
    assert result["response_lang"] == "sw"  # Swahili has good support
    assert "system_prompt" in result
    assert "cultural_context" in result
    assert result["greeting"] == "Jambo / Habari"
    assert result["whisper_code"] == "sw"
    results["passed"].append("Router: Swahili routing works")

    # Test fallback routing (limited support language)
    result = router.route("Dumela!", "st")
    assert result["lang_code"] == "st"
    assert result["gpt_support"] == "limited"
    # Limited support should route to English with cultural prompt
    results["passed"].append("Router: Limited language fallback works")

    # Test Zulu routing
    result = router.route("Sawubona", "zu")
    assert result["is_african"] is True
    assert result["lang_english"] == "Zulu"
    results["passed"].append("Router: Zulu routing works")

    # Test English routing
    result = router.route("Hello, how are you?", "en")
    assert result["lang_code"] == "en"
    assert result["is_african"] is False
    assert result["gpt_support"] == "full"
    results["passed"].append("Router: English routing works")


def test_voice_engine(results: dict[str, list[str]]) -> None:
    """Test voice engine configuration."""
    from lang.tts_stt import VoiceEngine, LANGUAGE_VOICE_PREFERENCES, TTS_VOICES

    engine = VoiceEngine()

    # Test voice preferences exist for key languages
    key_langs = ["sw", "zu", "am", "yo", "ha", "en", "fr", "es", "zh", "ja"]
    for lang in key_langs:
        voice = engine.get_preferred_voice(lang)
        assert voice in TTS_VOICES, f"Invalid voice '{voice}' for {lang}"
    results["passed"].append("Voice preferences for key languages")

    # Test Whisper code mapping
    assert engine.get_language_whisper_code("sw") == "sw"
    assert engine.get_language_whisper_code("ar-eg") == "ar"
    assert engine.get_language_whisper_code("ary") == "ar"
    results["passed"].append("Whisper code mapping works")

    # Test language support check
    assert engine.is_language_supported("sw") is True
    assert engine.is_language_supported("en") is True
    assert engine.is_language_supported("xx") is False
    results["passed"].append("Language support check works")

    # Test supported languages list
    supported = engine.get_supported_languages()
    assert len(supported) == len(engine.all_languages), f"Supported list out of sync with registry: {len(supported)}"  # truth-tracking, no magic number
    print(f"  Supported languages: {len(supported)}")
    results["passed"].append(f"Supported languages: {len(supported)}")


def test_fallback_chains(results: dict[str, list[str]]) -> None:
    """Test language fallback chains."""
    from lang.multilingual_router import LANGUAGE_FALLBACKS

    # Test fallback entries exist
    assert "rw" in LANGUAGE_FALLBACKS  # Kinyarwanda -> Swahili
    assert "rn" in LANGUAGE_FALLBACKS  # Kirundi -> Swahili
    assert "ss" in LANGUAGE_FALLBACKS  # Swati -> Zulu

    # Test fallback values are valid
    for lang, fallback in LANGUAGE_FALLBACKS.items():
        assert isinstance(fallback, str), f"Invalid fallback for {lang}"
        assert len(fallback) > 0, f"Empty fallback for {lang}"
    results["passed"].append("Fallback chains valid")


def test_greetings(results: dict[str, list[str]]) -> None:
    """Test greeting database for key languages."""
    from lang.african_languages import AFRICAN_LANGUAGES

    key_langs = ["sw", "zu", "xh", "af", "yo", "ha", "ig", "am", "so", "rw"]
    for lang in key_langs:
        info = AFRICAN_LANGUAGES[lang]
        greetings = info["greetings"]
        assert "hello" in greetings, f"Missing hello in {lang}"
        assert "goodbye" in greetings, f"Missing goodbye in {lang}"
        assert "thank_you" in greetings, f"Missing thank_you in {lang}"
        assert len(greetings["hello"]) > 0, f"Empty hello in {lang}"
    results["passed"].append("Greetings valid for key languages")


def test_integration(results: dict[str, list[str]]) -> None:
    """Integration test: full pipeline."""
    from lang.language_detector import LanguageDetector
    from lang.multilingual_router import MultilingualRouter

    detector = LanguageDetector()
    router = MultilingualRouter()

    # Full pipeline: detect -> route
    test_texts = [
        "Sawubona! Ngicela usizo ngemali.",  # Zulu: asking for money help
        "Jambo! Ninaweza kupata msaada?",      # Swahili
        "Bonjour! J'ai besoin d'aide.",        # French
    ]

    for text in test_texts:
        # Detect
        detected = detector.detect(text)
        lang_code = detected["lang_code"]
        assert detected["confidence"] > 0, f"No confidence for '{text}'"

        # Route
        routed = router.route(text, lang_code)
        assert routed["lang_code"] == lang_code
        assert "system_prompt" in routed

        # Get voice settings
        from lang.tts_stt import VoiceEngine
        engine = VoiceEngine()
        whisper_code = engine.get_language_whisper_code(detected)
        assert whisper_code == detected

        print(f"  '{text[:30]}...' -> {lang_code} (whisper: {whisper_code})")

    results["passed"].append(f"Integration pipeline: {len(test_texts)} texts processed")


def print_summary(results: dict[str, list[str]]) -> None:
    """Print test summary."""
    print(f"\n{'=' * 60}")
    print("TEST SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Passed: {len(results['passed'])}")
    print(f"  Failed: {len(results['failed'])}")
    print(f"  Warnings: {len(results['warnings'])}")

    if results["failed"]:
        print("\nFailed tests:")
        for failure in results["failed"]:
            print(f"  - {failure}")


def main() -> int:
    """Run all tests and return exit code."""
    print("Luqi AI Language System Tests")
    print("=" * 60)

    results = run_all_tests()
    print_summary(results)

    # Save results
    import json
    output_file = "lang_test_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_file}")

    return 0 if not results["failed"] else 1


if __name__ == "__main__":
    sys.exit(main())
