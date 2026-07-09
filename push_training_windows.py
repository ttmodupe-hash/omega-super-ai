#!/usr/bin/env python3
"""
Luqi AI - Push IT Security Training to GitHub (Windows)
========================================================
Simple script that pushes it_security_training.py to GitHub.

Prerequisites:
1. You have a GitHub Personal Access Token with 'repo' scope
2. You have Python installed (use 'py' on Windows)

Usage:
    py push_training_windows.py YOUR_GITHUB_TOKEN

Get a token: https://github.com/settings/tokens/new
"""

import sys
import os
import json
import base64
import urllib.request
import urllib.error
from pathlib import Path

REPO_OWNER = "ttmodupe-hash"
REPO_NAME = "omega-super-ai"
BRANCH = "main"
FILE_PATH = "backend/it_security_training.py"

def api_call(token, path, method="GET", data=None):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Luqi-AI-Windows-Push",
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
        err = e.read().decode()
        print(f"  API Error {e.code}: {err[:200]}")
        return None

def push_file(token, local_path, repo_path, message):
    local = Path(local_path)
    if not local.exists():
        print(f"ERROR: File not found: {local}")
        return False

    content = local.read_bytes()
    size_kb = len(content) / 1024
    print(f"\nPushing: {repo_path} ({size_kb:.1f} KB)")

    existing = api_call(token, f"contents/{repo_path}?ref={BRANCH}")
    sha = existing.get("sha") if existing else None

    if len(content) > 100 * 1024:
        print("  File > 100KB, using Git Data API...")
        return push_large_file(token, content, repo_path, message)

    b64 = base64.b64encode(content).decode()
    data = {
        "message": message,
        "content": b64,
        "branch": BRANCH,
    }
    if sha:
        data["sha"] = sha

    result = api_call(token, f"contents/{repo_path}", method="PUT", data=data)
    if result:
        print(f"  SUCCESS: {result['content']['html_url']}")
        return True
    return False

def push_large_file(token, content_bytes, repo_path, message):
    ref = api_call(token, f"git/ref/heads/{BRANCH}")
    if not ref:
        print("  ERROR: Could not get current commit")
        return False
    commit_sha = ref["object"]["sha"]
    print(f"  Current commit: {commit_sha[:8]}")

    commit = api_call(token, f"git/commits/{commit_sha}")
    tree_sha = commit["tree"]["sha"]
    print(f"  Base tree: {tree_sha[:8]}")

    print("  Creating blob...")
    blob_data = {
        "encoding": "base64",
        "content": base64.b64encode(content_bytes).decode(),
    }
    blob = api_call(token, "git/blobs", method="POST", data=blob_data)
    if not blob:
        print("  ERROR: Could not create blob")
        return False
    blob_sha = blob["sha"]
    print(f"  Blob: {blob_sha[:8]}")

    tree_data = {
        "base_tree": tree_sha,
        "tree": [{
            "path": repo_path,
            "mode": "100644",
            "type": "blob",
            "sha": blob_sha,
        }]
    }
    print("  Creating tree...")
    tree = api_call(token, "git/trees", method="POST", data=tree_data)
    if not tree:
        print("  ERROR: Could not create tree")
        return False
    new_tree_sha = tree["sha"]
    print(f"  New tree: {new_tree_sha[:8]}")

    commit_data = {
        "message": message,
        "tree": new_tree_sha,
        "parents": [commit_sha],
    }
    print("  Creating commit...")
    new_commit = api_call(token, "git/commits", method="POST", data=commit_data)
    if not new_commit:
        print("  ERROR: Could not create commit")
        return False
    new_commit_sha = new_commit["sha"]
    print(f"  New commit: {new_commit_sha[:8]}")

    result = api_call(token, f"git/refs/heads/{BRANCH}", method="PATCH",
                      data={"sha": new_commit_sha})
    if result:
        print(f"  SUCCESS!")
        print(f"  View: https://github.com/{REPO_OWNER}/{REPO_NAME}/commit/{new_commit_sha}")
        return True
    print("  ERROR: Could not update branch")
    return False

def reconstruct_from_parts():
    parts_dir = Path("chunks_security")
    output = Path("backend") / "it_security_training.py"

    manifest = parts_dir / "manifest_parts.json"
    if not manifest.exists():
        return None

    with open(manifest) as f:
        m = json.load(f)

    parts = []
    for name in m.get("parts", []):
        part_path = parts_dir / name
        if not part_path.exists():
            print(f"  MISSING: {part_path}")
            return None
        with open(part_path) as f:
            parts.append(f.read())
        print(f"  [OK] {name}")

    output.parent.mkdir(exist_ok=True)
    with open(output, "w") as f:
        f.write("\n".join(parts))

    size = output.stat().st_size
    print(f"\n  Reconstructed: {output} ({size/1024:.1f} KB)")
    return str(output)

def main():
    print("=" * 60)
    print("Luqi AI - Push IT Security Training to GitHub")
    print("=" * 60)

    token = sys.argv[1] if len(sys.argv) > 1 else ""
    if not token:
        token = input("Enter your GitHub Personal Access Token: ").strip()
    if not token:
        print("ERROR: No token provided")
        sys.exit(1)

    print("\nVerifying token...")
    user = api_call(token, "")
    if not user:
        print("ERROR: Invalid token or no network access")
        print("  - Create a token at: https://github.com/settings/tokens/new")
        print("  - Required scope: 'repo' (full control of private repositories)")
        sys.exit(1)
    print(f"  Authenticated as: {user.get('login', 'unknown')}")

    local_path = FILE_PATH.replace("/", os.sep)

    if not Path(local_path).exists():
        print(f"\n{local_path} not found locally.")
        print("Attempting to reconstruct from parts...")
        reconstructed = reconstruct_from_parts()
        if reconstructed:
            local_path = reconstructed
        else:
            print("\nERROR: Could not find or reconstruct the file.")
            print("  1. The file should be at: backend\\it_security_training.py")
            print("  2. Or part files should be in: chunks_security\\")
            sys.exit(1)

    success = push_file(
        token, local_path, FILE_PATH,
        "v24.4.0: Add IT Security Training Academy (4,571 lines, 15 courses)\n\n"
        "Comprehensive cybersecurity training platform with:\n"
        "- 15 training modules (Network Security to Threat Intelligence)\n"
        "- 99 lessons, 52 hands-on labs, 219 quiz questions\n"
        "- 15 CTF challenges, 39 skill badges\n"
        "- 4 certification tracks: Security+, CEH, CISSP, OSCP prep\n"
        "- Africa-specific: Mobile money security, USSD, SIM swap\n"
        "\nPushed via Git Data API."
    )

    if success:
        print("\n" + "=" * 60)
        print("SUCCESS! IT Security Training is now on GitHub!")
        print("=" * 60)
    else:
        print("\nFAILED. Check errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
