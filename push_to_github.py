#!/usr/bin/env python3
"""
Luqi AI v24.3.0 - Complete GitHub Push Script
==============================================
Pushes ALL local files to GitHub using the Git Data API.
Auto-discovers files - no hardcoded list needed.
Handles files of ANY size (tested up to 500KB+).

Usage (Linux/Mac):
    export GITHUB_TOKEN=ghp_xxxxxxxx
    python3 push_to_github.py

Usage (Windows PowerShell):
    $env:GITHUB_TOKEN="ghp_xxxxxxxx"
    py push_to_github.py

Usage (Windows CMD):
    set GITHUB_TOKEN=ghp_xxxxxxxx
    py push_to_github.py

Required token scopes: repo (full control)
Create at: https://github.com/settings/tokens/new
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
LOCAL_ROOT = Path(__file__).parent.resolve()

EXCLUDE_PATTERNS = {
    ".git", "__pycache__", ".pyc", ".venv", "venv", "node_modules",
    ".db", "chunks_to_push", "chunks",
    "test.txt", "test_large.txt", "luqi_projects.db",
    "PUSH_REMAINING.md", "PUSH_REMAINING_v24.3.md",
}

EXCLUDE_FILES = {"push_to_github.py"}


def should_include_file(rel_path: str) -> bool:
    if rel_path in EXCLUDE_FILES:
        return False
    for pattern in EXCLUDE_PATTERNS:
        if pattern in rel_path:
            return False
    allowed_extensions = {
        ".py", ".html", ".js", ".css", ".json", ".toml", ".yml", ".yaml",
        ".md", ".txt", ".conf", ".sh", ".ts", ".sql", ".dockerfile",
        ".png", ".jpg", ".jpeg", ".svg", ".ico", ".woff", ".woff2",
    }
    return any(rel_path.endswith(ext) for ext in allowed_extensions)


def discover_files() -> list:
    files = []
    for item in LOCAL_ROOT.rglob("*"):
        if not item.is_file():
            continue
        rel_path = str(item.relative_to(LOCAL_ROOT)).replace("\\", "/")
        if should_include_file(rel_path):
            files.append(rel_path)
    return sorted(files)


def get_token():
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        token = os.environ.get("GH_TOKEN", "").strip()
    if not token:
        print("No GITHUB_TOKEN found in environment.")
        print("Please create a Personal Access Token at:")
        print("  https://github.com/settings/tokens/new")
        print("Required scopes: repo")
        print()
        print("Then set it before running this script:")
        print("  Linux/Mac: export GITHUB_TOKEN=ghp_xxxxxxxx")
        print("  Windows PS: $env:GITHUB_TOKEN=\"ghp_xxxxxxxx\"")
        print("  Windows CMD: set GITHUB_TOKEN=ghp_xxxxxxxx")
        print()
        token = input("Enter your GitHub Personal Access Token: ").strip()
    return token


def github_api(token, path, method="GET", data=None):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Luqi-AI-Push-Script-v24",
    }
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    else:
        body = None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"  API Error: {e.code} - {error_body[:300]}")
        return None
    except Exception as e:
        print(f"  Network Error: {e}")
        return None


def create_blob(token, content_bytes):
    data = {
        "encoding": "base64",
        "content": base64.b64encode(content_bytes).decode("utf-8"),
    }
    result = github_api(token, "git/blobs", method="POST", data=data)
    return result["sha"] if result else None


def get_current_commit_sha(token):
    result = github_api(token, f"git/ref/heads/{BRANCH}")
    if result and "object" in result:
        return result["object"]["sha"]
    refs = github_api(token, "git/matching-refs/heads/")
    if refs:
        for ref in refs:
            if ref.get("ref", "").endswith(BRANCH):
                return ref["object"]["sha"]
    return None


def get_tree_sha(token, commit_sha):
    result = github_api(token, f"git/commits/{commit_sha}")
    return result["tree"]["sha"] if result else None


def create_tree(token, base_tree_sha, file_blobs):
    tree_items = []
    for file_path, blob_sha in file_blobs.items():
        tree_items.append({
            "path": file_path,
            "mode": "100644",
            "type": "blob",
            "sha": blob_sha,
        })
    data = {"base_tree": base_tree_sha, "tree": tree_items}
    result = github_api(token, "git/trees", method="POST", data=data)
    return result["sha"] if result else None


def create_commit(token, message, tree_sha, parent_sha):
    data = {"message": message, "tree": tree_sha, "parents": [parent_sha]}
    result = github_api(token, "git/commits", method="POST", data=data)
    return result["sha"] if result else None


def update_branch_ref(token, commit_sha):
    data = {"sha": commit_sha}
    result = github_api(token, f"git/refs/heads/{BRANCH}", method="PATCH", data=data)
    return result is not None


def push_files(token, files, commit_message):
    print(f"\n{'='*60}")
    print(f"Pushing {len(files)} files to {REPO_OWNER}/{REPO_NAME}:{BRANCH}")
    print(f"{'='*60}")

    print("\n[1/5] Getting current commit...")
    commit_sha = get_current_commit_sha(token)
    if not commit_sha:
        print("ERROR: Could not get current commit SHA")
        print("  - Check your token has 'repo' scope")
        print("  - Verify the branch name is correct")
        return False
    print(f"      Current commit: {commit_sha[:8]}")

    print("\n[2/5] Getting base tree...")
    tree_sha = get_tree_sha(token, commit_sha)
    if not tree_sha:
        print("ERROR: Could not get tree SHA")
        return False
    print(f"      Base tree: {tree_sha[:8]}")

    print(f"\n[3/5] Creating blobs ({len(files)} files)...")
    file_blobs = {}
    skipped = 0
    failed = 0
    for i, rel_path in enumerate(files, 1):
        local_path = LOCAL_ROOT / rel_path
        if not local_path.exists():
            print(f"      [{i}/{len(files)}] SKIP (not found): {rel_path}")
            skipped += 1
            continue
        content = local_path.read_bytes()
        blob_sha = create_blob(token, content)
        if blob_sha:
            file_blobs[rel_path] = blob_sha
            size_kb = len(content) / 1024
            print(f"      [{i}/{len(files)}] OK ({size_kb:.1f}KB): {rel_path}")
        else:
            print(f"      [{i}/{len(files)}] FAIL: {rel_path}")
            failed += 1

    if not file_blobs:
        print("ERROR: No blobs created - nothing to push")
        return False

    print(f"\n      Summary: {len(file_blobs)} created, {skipped} skipped, {failed} failed")

    print("\n[4/5] Creating tree...")
    new_tree_sha = create_tree(token, tree_sha, file_blobs)
    if not new_tree_sha:
        print("ERROR: Could not create tree (GitHub API may be rate-limited)")
        return False
    print(f"      New tree: {new_tree_sha[:8]}")

    print("\n[5/5] Creating commit and updating branch...")
    new_commit_sha = create_commit(token, commit_message, new_tree_sha, commit_sha)
    if not new_commit_sha:
        print("ERROR: Could not create commit")
        return False
    print(f"      New commit: {new_commit_sha[:8]}")

    if update_branch_ref(token, new_commit_sha):
        print(f"\n{'='*60}")
        print(f"SUCCESS! Pushed {len(file_blobs)} files")
        print(f"{'='*60}")
        print(f"Commit SHA: {new_commit_sha}")
        print(f"Branch:     {BRANCH}")
        print(f"View:       https://github.com/{REPO_OWNER}/{REPO_NAME}/commit/{new_commit_sha}")
        return True
    else:
        print("ERROR: Could not update branch ref")
        print("  The commit was created but the branch was not updated.")
        print(f"  Commit SHA: {new_commit_sha}")
        print("  You may need to manually fast-forward the branch.")
        return False


def print_file_summary(files):
    total_size = 0
    by_dir = {}
    for f in files:
        path = LOCAL_ROOT / f
        if path.exists():
            size = path.stat().st_size
            total_size += size
            dir_name = f.split("/")[0] if "/" in f else "(root)"
            if dir_name not in by_dir:
                by_dir[dir_name] = {"count": 0, "size": 0}
            by_dir[dir_name]["count"] += 1
            by_dir[dir_name]["size"] += size

    print(f"\n{'='*60}")
    print("FILES TO PUSH")
    print(f"{'='*60}")
    for dir_name in sorted(by_dir.keys()):
        info = by_dir[dir_name]
        print(f"  {dir_name:20s} {info['count']:4d} files  {info['size']/1024:8.1f} KB")
    print(f"  {'TOTAL':20s} {len(files):4d} files  {total_size/1024:8.1f} KB ({total_size/1024/1024:.2f} MB)")
    print()


def main():
    print("=" * 60)
    print("Luqi AI v24.3.0 - GitHub Push Script")
    print("Auto-discovers files, handles any size via Git Data API")
    print("=" * 60)

    token = get_token()
    if not token:
        print("ERROR: No token provided")
        sys.exit(1)

    print("\nVerifying token...")
    repo = github_api(token, "")
    if not repo:
        print("ERROR: Invalid token or no access to repository")
        print(f"  Repo: {REPO_OWNER}/{REPO_NAME}")
        print("  Make sure your token has 'repo' scope")
        sys.exit(1)
    print(f"Authenticated as: {repo.get('owner', {}).get('login', 'unknown')}")
    print(f"Repository:       {repo.get('full_name', 'unknown')}")
    print(f"Default branch:   {repo.get('default_branch', BRANCH)}")

    global BRANCH
    if repo.get("default_branch") and repo["default_branch"] != BRANCH:
        BRANCH = repo["default_branch"]
        print(f"Using branch:     {BRANCH}")

    print("\nScanning local files...")
    files = discover_files()
    if not files:
        print("ERROR: No files found to push")
        sys.exit(1)

    print_file_summary(files)

    if len(files) > 50:
        print(f"This will push {len(files)} files. This may take a few minutes.")
        confirm = input("Continue? [Y/n]: ").strip().lower()
        if confirm and confirm not in ("y", "yes"):
            print("Aborted.")
            sys.exit(0)

    success = push_files(
        token, files,
        "v24.3.0: Complete Luqi AI Platform\n\n"
        "Full production build with all modules:\n"
        "- v14-v20: Core SaaS, Africa-First, Law Studies\n"
        "- v21-v24: Knowledge Academy, PM, Digital Workspace\n"
        "- Infrastructure: CI/CD, middleware, cache, health checks\n"
        "- Digital Wellness: Fatigue prevention system\n"
        "- Branding: Limitless Telecoms corporate identity\n"
        "- Collab Service: Real-time collaboration with LiveKit\n"
        "\nPushed via Git Data API - handles files of any size.",
    )

    if success:
        print("\n" + "=" * 60)
        print("ALL FILES PUSHED SUCCESSFULLY!")
        print("=" * 60)
        print("\nPost-push steps:")
        print("  1. Set environment variables (see .env.example)")
        print("  2. pip install -r requirements.txt")
        print("  3. Run: uvicorn backend.router:app --host 0.0.0.0 --port 8000")
        print("  4. Visit: http://localhost:8000")
        print("\nFor production deployment, see DEPLOY.md")
        sys.exit(0)
    else:
        print("\nPush failed. Check errors above.")
        print("\nCommon fixes:")
        print("  - Verify GITHUB_TOKEN has 'repo' scope")
        print("  - Check internet connection")
        print("  - For large pushes (>100 files), try pushing in batches")
        print("  - If rate-limited, wait 1 hour and retry")
        sys.exit(1)


if __name__ == "__main__":
    main()
