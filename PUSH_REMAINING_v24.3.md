#!/usr/bin/env python3
"""
Push multiple files or entire directories to GitHub using the Git Data API
in a single atomic commit.

Usage:
    export GITHUB_TOKEN=ghp_xxxxxxxx
    python3 push_large_file.py backend/ script.py path/to/file.txt "Commit message"
"""

import os
import sys
import json
import base64
import urllib.request
import urllib.error
from pathlib import Path

REPO_OWNER = "ttmodupe-hash"
REPO_NAME = "omega-super-ai"
BRANCH = "main"


def get_token():
    token = os.environ.get("GITHUB_TOKEN", "").strip() or os.environ.get("GH_TOKEN", "").strip()
    if not token:
        print("ERROR: Missing token. Set GITHUB_TOKEN or GH_TOKEN.")
        sys.exit(1)
    return token


def github_api(token, path, method="GET", data=None):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Luqi-AI-Large-File-Push",
    }
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode("utf-8", errors="ignore")
        print(f"  API Error ({e.code}): {error_msg[:300]}")
        return None


def create_blob(token, file_path):
    try:
        content = file_path.read_bytes()
    except Exception as e:
        print(f"  ERROR: Could not read file {file_path}: {e}")
        return None

    size_mb = len(content) / (1024 * 1024)

    if size_mb > 100:
        print(f"  SKIP: {file_path.name} ({size_mb:.2f} MB) exceeds GitHub 100MB API limit.")
        return None

    b64_content = base64.b64encode(content).decode("utf-8")
    data = {"encoding": "base64", "content": b64_content}
    result = github_api(token, "git/blobs", method="POST", data=data)
    
    if result and "sha" in result:
        print(f"  Created blob: {file_path.as_posix()} ({size_mb:.2f} MB) -> {result['sha'][:8]}")
        return result["sha"]
    return None


def collect_file_paths(paths):
    """Recursively collect all files from files and directories."""
    files_to_process = []
    for p_str in paths:
        p = Path(p_str)
        if p.is_file():
            files_to_process.append(p)
        elif p.is_dir():
            # Recursively collect all non-hidden files inside directory
            for entry in p.rglob("*"):
                if entry.is_file() and not any(part.startswith(".") for part in entry.parts):
                    files_to_process.append(entry)
        else:
            print(f"WARNING: Path not found or invalid: {p_str}")
    return sorted(list(set(files_to_process)))


def get_relative_repo_path(file_path):
    """
    Normalizes local paths to relative POSIX paths suitable for GitHub repository trees.
    """
    resolved = file_path.resolve()
    cwd = Path.cwd().resolve()
    
    try:
        rel = resolved.relative_to(cwd)
    except ValueError:
        # Fallback if file is outside the current working directory
        rel = file_path

    # Convert Windows backslashes to POSIX slashes and strip leading separators
    return rel.as_posix().lstrip("/")


def push_batch(token, input_paths, commit_message):
    file_paths = collect_file_paths(input_paths)
    if not file_paths:
        print("ERROR: No valid files found to commit.")
        return False

    print(f"Preparing commit with {len(file_paths)} file(s)...")

    # 1. Fetch current HEAD commit
    ref_info = github_api(token, f"git/ref/heads/{BRANCH}")
    if not ref_info:
        print(f"ERROR: Could not fetch ref heads/{BRANCH}")
        return False
    parent_commit_sha = ref_info["object"]["sha"]

    # 2. Get base tree
    commit_info = github_api(token, f"git/commits/{parent_commit_sha}")
    if not commit_info:
        print("ERROR: Could not fetch commit details")
        return False
    base_tree_sha = commit_info["tree"]["sha"]

    # 3. Create blobs for each file
    tree_items = []
    for file_path in file_paths:
        blob_sha = create_blob(token, file_path)
        if not blob_sha:
            print(f"ERROR: Halting due to failed blob creation for {file_path}")
            return False

        repo_path = get_relative_repo_path(file_path)

        tree_items.append({
            "path": repo_path,
            "mode": "100644",
            "type": "blob",
            "sha": blob_sha,
        })

    # 4. Create new tree referencing all blobs
    tree_data = {
        "base_tree": base_tree_sha,
        "tree": tree_items,
    }
    print("\nCreating tree...")
    tree_result = github_api(token, "git/trees", method="POST", data=tree_data)
    if not tree_result:
        print("ERROR: Failed to create tree")
        return False
    new_tree_sha = tree_result["sha"]

    # 5. Create commit
    commit_data = {
        "message": commit_message,
        "tree": new_tree_sha,
        "parents": [parent_commit_sha],
    }
    print("Creating commit...")
    commit_result = github_api(token, "git/commits", method="POST", data=commit_data)
    if not commit_result:
        print("ERROR: Failed to create commit")
        return False
    new_commit_sha = commit_result["sha"]

    # 6. Update reference
    ref_data = {"sha": new_commit_sha, "force": False}
    ref_result = github_api(token, f"git/refs/heads/{BRANCH}", method="PATCH", data=ref_data)

    if ref_result:
        print(f"\nSUCCESS! Pushed {len(tree_items)} file(s) in a single commit.")
        print(f"Commit URL: https://github.com/{REPO_OWNER}/{REPO_NAME}/commit/{new_commit_sha}")
        return True

    print("ERROR: Failed to update branch reference")
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 push_large_file.py <file1_or_dir1> [file2_or_dir2 ...] [commit_message]")
        sys.exit(1)

    args = sys.argv[1:]
    
    # Check if last argument looks like a custom commit message (not an existing path)
    if len(args) > 1 and not Path(args[-1]).exists():
        commit_msg = args[-1]
        target_paths = args[:-1]
    else:
        target_paths = args
        commit_msg = f"Add/update {len(target_paths)} target item(s)"

    auth_token = get_token()
    success = push_batch(auth_token, target_paths, commit_msg)
    sys.exit(0 if success else 1)
