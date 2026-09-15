#!/usr/bin/env python3
"""
Luqi AI v24.4.0 — File Merger
=============================
Simply concatenates part files (split at clean boundaries).
No overlap detection needed — parts are designed to be directly concatenated.

Usage:
    cd training_parts
    py merge_all.py
"""

import os
import sys
import py_compile

BASE = os.path.dirname(os.path.abspath(__file__))


def cat(parts, output):
    """Concatenate part files into output."""
    print(f"\n[+] Creating {os.path.basename(output)}...")

    result = []
    for p in parts:
        path = os.path.join(BASE, p)
        if not os.path.exists(path):
            print(f"  ERROR: {p} not found!")
            return False
        with open(path, "r", encoding="utf-8") as f:
            result.append(f.read())
        print(f"  OK: {p} ({os.path.getsize(path)} bytes)")

    full = "".join(result)
    os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        f.write(full)
    print(f"  => {output} ({len(full)} chars, {len(full)/1024:.1f} KB)")
    return True


def check(path):
    """Verify file compiles as valid Python."""
    try:
        py_compile.compile(path, doraise=True)
        print(f"  [PASS] Valid Python: {os.path.basename(path)}")
        return True
    except py_compile.PyCompileError as e:
        print(f"  [FAIL] Syntax error: {e}")
        return False


def main():
    print("=" * 60)
    print("Luqi AI v24.4.0 — Merge Part Files")
    print("=" * 60)

    all_ok = True

    # Merge IT Security Training (4 parts)
    ok = cat(
        [
            "it_security_training_part1.py",
            "it_security_training_part2.py",
            "it_security_training_part3.py",
            "it_security_training_part4.py",
        ],
        os.path.join(BASE, "..", "backend", "it_security_training.py"),
    )
    if ok:
        all_ok &= check(os.path.join(BASE, "..", "backend", "it_security_training.py"))
    else:
        all_ok = False

    # Merge Digital Wellness (2 parts)
    ok = cat(
        [
            "digital_wellness_part1.py",
            "digital_wellness_part2.py",
        ],
        os.path.join(BASE, "..", "backend", "digital_wellness.py"),
    )
    if ok:
        all_ok &= check(os.path.join(BASE, "..", "backend", "digital_wellness.py"))
    else:
        all_ok = False

    print("\n" + "=" * 60)
    if all_ok:
        print("SUCCESS! All files merged and verified.")
        print("=" * 60)
        sys.exit(0)
    else:
        print("ERRORS occurred during merge. Check output above.")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
