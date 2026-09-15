#!/usr/bin/env python3
"""
Push a single large file to GitHub using the Git Data API.
Use this for files too large for normal push methods.

Usage:
    export GITHUB_TOKEN=ghp_xxxxxxxx
    python3 push_large_file.py backend/it_security_training.py
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
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        token = os.environ.get("GH_TOKEN", "").strip()
    if not token:
        print("No token found. Set GITHUB_TOKEN environment variable.")
        sys.exit(1)
    return token


def github_api(token, path, method="GET", data=None):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Luqi-AI-Large-File-Push",
    }
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    else:
        body = None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"  API Error: {e.code} - {e.read().decode('utf-8')[:200]}")
        return None


def create_blob(token, content_bytes):
    data = {"encoding": "base64", "content": base64.b64encode(content_bytes).decode("utf-8")}
    result = github_api(token, "git/blobs", method="POST", data=data)
    return result["sha"] if result else None


def push_file(token, file_path, commit_message):
    local_path = Path(file_path)
    if not local_path.exists():
        print(f"ERROR: File not found: {local_path}")
        return False

    content = local_path.read_bytes()
    size_kb = len(content) / 1024
    print(f"Pushing: {local_path} ({size_kb:.1f} KB)")

    result = github_api(token, f"git/ref/heads/{BRANCH}")
    if not result:
        print("ERROR: Could not get current commit")
        return False
    commit_sha = result["object"]["sha"]
    print(f"  Current commit: {commit_sha[:8]}")

    commit = github_api(token, f"git/commits/{commit_sha}")
    tree_sha = commit["tree"]["sha"]
    print(f"  Base tree: {tree_sha[:8]}")

    print("  Creating blob...")
    blob_sha = create_blob(token, content)
    if not blob_sha:
        print("ERROR: Could not create blob")
        return False
    print(f"  Blob: {blob_sha[:8]}")

    rel_path = str(local_path).replace("\\", "/")
    if rel_path.startswith("./"):
        rel_path = rel_path[2:]

    tree_data = {
        "base_tree": tree_sha,
        "tree": [{"path": rel_path, "mode": "100644", "type": "blob", "sha": blob_sha}]
    }
    print("  Creating tree...")
    tree_result = github_api(token, "git/trees", method="POST", data=tree_data)
    if not tree_result:
        print("ERROR: Could not create tree")
        return False
    new_tree_sha = tree_result["sha"]
    print(f"  New tree: {new_tree_sha[:8]}")

    commit_data = {"message": commit_message, "tree": new_tree_sha, "parents": [commit_sha]}
    commit_result = github_api(token, "git/commits", method="POST", data=commit_data)
    if not commit_result:
        print("ERROR: Could not create commit")
        return False
    new_commit_sha = commit_result["sha"]
    print(f"  New commit: {new_commit_sha[:8]}")

    ref_data = {"sha": new_commit_sha}
    ref_result = github_api(token, f"git/refs/heads/{BRANCH}", method="PATCH", data=ref_data)
    if ref_result:
        print(f"\n  SUCCESS! Pushed {rel_path}")
        print(f"  View: https://github.com/{REPO_OWNER}/{REPO_NAME}/commit/{new_commit_sha}")
        return True
    else:
        print("ERROR: Could not update branch ref")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 push_large_file.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    msg = sys.argv[2] if len(sys.argv) > 2 else f"Add {file_path}"
    token = get_token()

    print("=" * 50)
    print("Luqi AI - Large File Push")
    print("=" * 50)

    success = push_file(token, file_path, msg)
    sys.exit(0 if success else 1)
