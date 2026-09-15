#!/usr/bin/env python3
"""
Push it_security_training.py parts to GitHub.
Usage: py push_parts.py YOUR_GITHUB_TOKEN
"""
import sys
import json
import base64
import urllib.request
from pathlib import Path

REPO_OWNER = "ttmodupe-hash"
REPO_NAME = "omega-super-ai"
BRANCH = "main"

def get_sha(token, path):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{path}?ref={BRANCH}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Luqi-AI-Push-Parts"
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            return data.get("sha")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise

def push_file(token, local_path, repo_path, message):
    content = Path(local_path).read_bytes()
    b64_content = base64.b64encode(content).decode()
    sha = get_sha(token, repo_path)
    data = {
        "message": message,
        "content": b64_content,
        "branch": BRANCH,
    }
    if sha:
        data["sha"] = sha
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{repo_path}"
    req = urllib.request.Request(url, data=json.dumps(data).encode(), headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "Luqi-AI-Push-Parts"
    }, method="PUT")
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode())
        return result["content"]["sha"]

def main():
    if len(sys.argv) < 2:
        token = input("Enter your GitHub Personal Access Token: ").strip()
    else:
        token = sys.argv[1]

    if not token:
        print("ERROR: No token provided")
        sys.exit(1)

    base = Path("chunks_security")
    files = [
        ("manifest_parts.json", "v24.4.0: Part manifest for it_security_training.py"),
        ("it_security_training.py.part000.txt", "v24.4.0: Part 0/4 of IT Security Training (lines 0-1143)"),
        ("it_security_training.py.part001.txt", "v24.4.0: Part 1/4 of IT Security Training (lines 1143-2286)"),
        ("it_security_training.py.part002.txt", "v24.4.0: Part 2/4 of IT Security Training (lines 2286-3429)"),
        ("it_security_training.py.part003.txt", "v24.4.0: Part 3/4 of IT Security Training (lines 3429-4572)"),
    ]

    for filename, msg in files:
        local = base / filename
        repo = f"chunks_security/{filename}"
        if not local.exists():
            print(f"SKIP: {local} not found")
            continue
        size = local.stat().st_size
        print(f"Pushing {repo} ({size/1024:.1f} KB)...")
        try:
            sha = push_file(token, local, repo, msg)
            print(f"  OK: {sha[:12]}")
        except Exception as e:
            print(f"  FAIL: {e}")

    print("\nDone! Now run: py reconstruct_from_parts.py")

if __name__ == "__main__":
    main()
