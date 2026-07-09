#!/usr/bin/env python3
"""
Reconstruct it_security_training.py from 4 text parts.
Usage: py reconstruct_from_parts.py
"""
import json
from pathlib import Path

CHUNKS_DIR = Path("chunks_security")
MANIFEST = CHUNKS_DIR / "manifest_parts.json"
OUTPUT = Path("backend") / "it_security_training.py"

def reconstruct():
    print("=" * 50)
    print("Reconstructing it_security_training.py")
    print("=" * 50)
    with open(MANIFEST) as f:
        m = json.load(f)
    parts = []
    for name in m["parts"]:
        path = CHUNKS_DIR / name
        if not path.exists():
            print(f"MISSING: {name}")
            return False
        with open(path) as f:
            parts.append(f.read())
        print(f"  [OK] {name}")
    OUTPUT.parent.mkdir(exist_ok=True)
    with open(OUTPUT, "w") as f:
        f.write("\n".join(parts))
    size = OUTPUT.stat().st_size
    print(f"\nSUCCESS: {OUTPUT} ({size/1024:.1f} KB)")
    return True

if __name__ == "__main__":
    reconstruct()
