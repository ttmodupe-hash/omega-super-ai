#!/usr/bin/env python3
"""Merge digital_wellness_part1.py and digital_wellness_part2.py into digital_wellness.py"""
import os

def merge():
    base = os.path.dirname(os.path.abspath(__file__))
    p1 = os.path.join(base, 'digital_wellness_part1.py')
    p2 = os.path.join(base, 'digital_wellness_part2.py')
    out = os.path.join(base, '..', 'backend', 'digital_wellness.py')
    
    with open(p1, 'r', encoding='utf-8') as f:
        content1 = f.read()
    with open(p2, 'r', encoding='utf-8') as f:
        content2 = f.read()
    
    with open(out, 'w', encoding='utf-8') as f:
        f.write(content1)
        f.write('\n')
        f.write(content2)
    
    total_size = len(content1) + len(content2)
    print(f"[OK] Merged digital_wellness.py ({total_size} chars, {total_size/1024:.1f} KB)")
    print(f"     Output: {out}")

if __name__ == '__main__':
    merge()
