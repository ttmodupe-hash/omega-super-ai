#!/usr/bin/env python3
"""
Luqi AI v24.4.0 — Foolproof GitHub Push Script
===============================================
Handles PowerShell, CMD, and Linux/Mac automatically.
Never fails silently — always tells you exactly what's wrong.

Usage (Windows PowerShell):
    $env:GITHUB_TOKEN = "ghp_YOUR_REAL_TOKEN"
    py push_to_github_v24.py

Usage (any OS, token as argument):
    py push_to_github_v24.py ghp_YOUR_REAL_TOKEN
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
    """Find GitHub token from every possible source."""
    sources = []

    # 1. Command line argument
    if len(sys.argv) > 1 and sys.argv[1].startswith("ghp_"):
        sources.append(("command line", sys.argv[1]))

    # 2. GITHUB_TOKEN env var
    t = os.environ.get("GITHUB_TOKEN", "").strip()
    if t:
        sources.append(("GITHUB_TOKEN env var", t))

    # 3. GH_TOKEN env var
    t = os.environ.get("GH_TOKEN", "").strip()
    if t:
        sources.append(("GH_TOKEN env var", t))

    # 4. Interactive prompt
    if not sources:
        print("\n" + "=" * 60)
        print("GITHUB TOKEN REQUIRED")
        print("=" * 60)
        print("\nYou need a GitHub Personal Access Token with 'repo' scope.")
        print("Get one: https://github.com/settings/tokens/new")
        print("\nPowerShell: $env:GITHUB_TOKEN = 'ghp_...'")
        print("Windows CMD: set GITHUB_TOKEN=ghp_...")
        print("Linux/Mac: export GITHUB_TOKEN=ghp_...")
        print("")
        token = input("Paste your token here (or press Ctrl+C to cancel): ").strip()
        if token:
            sources.append(("interactive prompt", token))

    # Validate
    for source_name, token in sources:
        if token.startswith("ghp_"):
            return token, source_name
        elif token.startswith("ghp_") is False and len(token) > 20:
            print(f"WARNING: Token from {source_name} doesn't start with 'ghp_' — checking anyway...")
            return token, source_name

    return None, None


def api_call(token, path, method="GET", data=None):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Luqi-AI-v24-Push",
    }
    if data:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    else:
        body = None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        return {"_error": True, "status": e.code, "message": err_body[:500]}
    except Exception as e:
        return {"_error": True, "status": 0, "message": str(e)}


def verify_token(token):
    print("\n[1/4] Verifying token...")
    result = api_call(token, "")
    if result.get("_error"):
        code = result["status"]
        if code == 401:
            print("  FAILED: Invalid token (HTTP 401)")
            print("  Your token may have expired or been revoked.")
        elif code == 404:
            print("  FAILED: Repository not found (HTTP 404)")
        elif code == 403:
            print("  FAILED: Rate limited or insufficient permissions (HTTP 403)")
        else:
            print(f"  FAILED: HTTP {code} — {result['message'][:200]}")
        print("  Generate a new token: https://github.com/settings/tokens/new")
        print("  Required scope: 'repo' (full control of private repositories)")
        return False
    login = result.get("login", "unknown")
    print(f"  OK: Authenticated as '{login}'")
    return True


def push_large_file(token, local_path, repo_path, message):
    local = Path(local_path)
    if not local.exists():
        return False, f"File not found: {local}"

    content = local.read_bytes()
    size_kb = len(content) / 1024
    print(f"\n  Pushing {repo_path} ({size_kb:.1f} KB)...")

    ref = api_call(token, f"git/ref/heads/{BRANCH}")
    if ref.get("_error"):
        return False, f"Cannot get commit: {ref['message'][:100]}"
    commit_sha = ref["object"]["sha"]

    commit = api_call(token, f"git/commits/{commit_sha}")
    tree_sha = commit["tree"]["sha"]

    blob_data = {
        "encoding": "base64",
        "content": base64.b64encode(content).decode(),
    }
    blob = api_call(token, "git/blobs", method="POST", data=blob_data)
    if blob.get("_error"):
        return False, f"Cannot create blob: {blob['message'][:100]}"

    tree_data = {
        "base_tree": tree_sha,
        "tree": [{"path": repo_path, "mode": "100644", "type": "blob", "sha": blob["sha"]}]
    }
    tree = api_call(token, "git/trees", method="POST", data=tree_data)
    if tree.get("_error"):
        return False, f"Cannot create tree: {tree['message'][:100]}"

    commit_data = {
        "message": message,
        "tree": tree["sha"],
        "parents": [commit_sha],
    }
    new_commit = api_call(token, "git/commits", method="POST", data=commit_data)
    if new_commit.get("_error"):
        return False, f"Cannot create commit: {new_commit['message'][:100]}"

    result = api_call(token, f"git/refs/heads/{BRANCH}", method="PATCH",
                      data={"sha": new_commit["sha"]})
    if result.get("_error"):
        return False, f"Cannot update branch: {result['message'][:100]}"

    return True, f"{size_kb:.1f} KB, commit {new_commit['sha'][:8]}"


def main():
    print("=" * 60)
    print("Luqi AI v24.4.0 — Foolproof GitHub Push")
    print("=" * 60)

    token, source = get_token()
    if not token:
        print("\nERROR: No GitHub token found.")
        sys.exit(1)
    print(f"\nToken source: {source}")

    if not verify_token(token):
        sys.exit(1)

    # Find files to push
    push_targets = []
    for local, remote, msg in [
        ("backend/it_security_training.py", "backend/it_security_training.py",
         "v24.4.0: IT Security Training Academy (4,571 lines, 15 courses)"),
        ("backend/digital_wellness.py", "backend/digital_wellness.py",
         "v24.3.0: Digital Wellness engine (fatigue prevention)"),
        ("web/wellness.html", "web/wellness.html",
         "v24.3.0: Wellness dashboard"),
    ]:
        p = Path(local)
        if p.exists() and p.stat().st_size > 1000:
            push_targets.append((local, remote, msg))
            print(f"  Found: {local} ({p.stat().st_size/1024:.1f} KB)")

    if not push_targets:
        print("\nNo large local files found to push.")
        print("Run 'git pull origin main' to get latest files from GitHub.")
        sys.exit(0)

    print(f"\n[2/4] Ready to push {len(push_targets)} file(s)")
    confirm = input("Continue? [Y/n]: ").strip().lower()
    if confirm and confirm not in ("y", "yes"):
        print("Aborted.")
        sys.exit(0)

    print("\n[3/4] Pushing...")
    success = 0
    for local, remote, msg in push_targets:
        ok, info = push_large_file(token, local, remote, msg)
        if ok:
            print(f"  SUCCESS: {remote} ({info})")
            success += 1
        else:
            print(f"  FAILED: {remote} — {info}")

    print(f"\n[4/4] Done: {success}/{len(push_targets)} files pushed")
    if success == len(push_targets):
        print(f"\nAll files on GitHub: https://github.com/{REPO_OWNER}/{REPO_NAME}")
    sys.exit(0 if success == len(push_targets) else 1)


if __name__ == "__main__":
    main()
