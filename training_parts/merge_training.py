#!/usr/bin/env python3
"""Merge it_security_training_part{1,2,3}.py into it_security_training.py

Usage:
    cd training_parts
    python3 merge_training.py

This concatenates all 3 parts into backend/it_security_training.py
"""
import os

def merge():
    base = os.path.dirname(os.path.abspath(__file__))
    parts = [
        os.path.join(base, 'it_security_training_part1.py'),
        os.path.join(base, 'it_security_training_part2.py'),
        os.path.join(base, 'it_security_training_part3.py'),
    ]
    out = os.path.join(base, '..', 'backend', 'it_security_training.py')
    
    total = 0
    with open(out, 'w', encoding='utf-8') as outfile:
        for part in parts:
            with open(part, 'r', encoding='utf-8') as f:
                content = f.read()
            outfile.write(content)
            outfile.write('\n')
            total += len(content)
            print(f"  [OK] {os.path.basename(part)} -> {len(content)} chars")
    
    print(f"\n[SUCCESS] Merged it_security_training.py")
    print(f"  Total: {total} chars ({total/1024:.1f} KB)")
    print(f"  Output: {out}")
    print(f"\nNext steps:")
    print(f"  1. Verify: python3 -c \"import py_compile; py_compile.compile('{out}', doraise=True)\"")
    print(f"  2. The module should now be importable from backend.it_security_training")

if __name__ == '__main__':
    merge()
