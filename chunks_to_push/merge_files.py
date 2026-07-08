#!/usr/bin/env python3
"""
Luqi AI v24 -- File Merge Script
================================
Merges chunked files back into their original form.
Run this after cloning the repository to reconstruct large files.

Usage:
    python chunks_to_push/merge_files.py
"""

import json
import os
import sys


def merge_files():
    """Merge all chunked files back into their original locations."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    manifest_path = os.path.join(script_dir, "manifest.json")

    if not os.path.exists(manifest_path):
        print(f"ERROR: Manifest not found at {manifest_path}")
        sys.exit(1)

    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    repo_root = os.path.dirname(script_dir)
    merged_count = 0
    total_size = 0

    for original_path, info in manifest.items():
        full_output_path = os.path.join(repo_root, original_path)
        os.makedirs(os.path.dirname(full_output_path), exist_ok=True)

        # Read and concatenate all chunks
        content_parts = []
        for chunk_file in info["chunk_files"]:
            chunk_path = os.path.join(repo_root, chunk_file)
            if not os.path.exists(chunk_path):
                print(f"  MISSING CHUNK: {chunk_file}")
                continue
            with open(chunk_path, "rb") as cf:
                content_parts.append(cf.read())

        if len(content_parts) != info["chunks"]:
            print(f"  SKIP: {original_path} -- only found {len(content_parts)}/{info['chunks']} chunks")
            continue

        # Write merged file
        merged_content = b"".join(content_parts)
        with open(full_output_path, "wb") as of:
            of.write(merged_content)

        merged_count += 1
        total_size += len(merged_content)
        print(f"  MERGED: {original_path} ({len(merged_content)} bytes from {info['chunks']} chunks)")

    print(f"\nDone! Merged {merged_count}/{len(manifest)} files ({total_size:,} bytes total)")

    # Optionally remove chunk files
    print("\nChunk files are preserved in chunks_to_push/")
    print("You can delete them after verifying the merged files are correct.")


if __name__ == "__main__":
    merge_files()
