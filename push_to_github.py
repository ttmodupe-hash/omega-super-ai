#!/usr/bin/env python3
"""
Push local files to GitHub using the Git Data API.
Handles large files (>100KB) that the Content API cannot process.

Usage:
    export GITHUB_TOKEN=ghp_xxxxxxxx
    python3 push_to_github.py

If no GITHUB_TOKEN is set, the script will prompt for one.
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
LOCAL_ROOT = Path(__file__).parent

# Files to push (relative to project root)
FILES_TO_PUSH = [
    # Critical corrupted files
    "backend/router.py",
    "backend/__init__.py",
    # v14 modules
    "backend/subscriptions.py",
    "backend/developer.py",
    "backend/website_builder.py",
    "backend/dashboard.py",
    "backend/auto_upgrader.py",
    # v15 modules (large ones)
    "backend/cognitive_engine.py",
    "backend/education_system.py",
    "backend/voice_system.py",
    "backend/safety_alignment.py",
    "backend/physics_simulator.py",
    # v16 modules
    "backend/github_integration.py",
    "backend/notifications.py",
    "backend/data_portability.py",
    # v17 modules
    "backend/captainship.py",
    "backend/companionship.py",
    # v18 modules
    "backend/automotive.py",
    "backend/writing_assistant.py",
    # Launch critical
    "backend/stripe_integration.py",
    "backend/email_system.py",
    # Frontend
    "web/index.html",
    "web/admin.html",
    "web/manifest.json",
    "web/sw.js",
    # Root files
    "LAUNCH_CHECKLIST.md",
    "Dockerfile",
    "docker-compose.yml",
    "cli.py",
    "self_test.py",
    "start_server.py",
    "README.md",
]


def get_token():
    """Get GitHub token from env or prompt."""
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        token = os.environ.get("GH_TOKEN", "").strip()
    if not token:
        print("No GITHUB_TOKEN found in environment.")
        print("Please create a Personal Access Token at:")
        print("  https://github.com/settings/tokens/new")
        print("Required scopes: repo")
        token = input("\nEnter your GitHub Personal Access Token: ").strip()
    return token


def github_api(token, path, method="GET", data=None):
    """Make an authenticated GitHub API request."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Luqi-AI-Push-Script",
    }
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    else:
        body = None

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"  API Error: {e.code} - {error_body[:200]}")
        return None


def create_blob(token, content_bytes):
    """Create a Git blob from file content."""
    data = {
        "encoding": "base64",
        "content": base64.b64encode(content_bytes).decode("utf-8"),
    }
    result = github_api(token, "git/blobs", method="POST", data=data)
    return result["sha"] if result else None


def get_current_commit_sha(token):
    """Get the current commit SHA for the branch."""
    result = github_api(token, f"git/ref/heads/{BRANCH}")
    return result["object"]["sha"] if result else None


def get_tree_sha(token, commit_sha):
    """Get the tree SHA from a commit."""
    result = github_api(token, f"git/commits/{commit_sha}")
    return result["tree"]["sha"] if result else None


def create_tree(token, base_tree_sha, file_blobs):
    """Create a new tree with updated files."""
    tree_items = []
    for file_path, blob_sha in file_blobs.items():
        tree_items.append({
            "path": file_path,
            "mode": "100644",
            "type": "blob",
            "sha": blob_sha,
        })

    data = {
        "base_tree": base_tree_sha,
        "tree": tree_items,
    }
    result = github_api(token, "git/trees", method="POST", data=data)
    return result["sha"] if result else None


def create_commit(token, message, tree_sha, parent_sha):
    """Create a new commit."""
    data = {
        "message": message,
        "tree": tree_sha,
        "parents": [parent_sha],
    }
    result = github_api(token, "git/commits", method="POST", data=data)
    return result["sha"] if result else None


def update_branch_ref(token, commit_sha):
    """Update the branch reference to point to the new commit."""
    data = {"sha": commit_sha}
    result = github_api(token, f"git/refs/heads/{BRANCH}", method="PATCH", data=data)
    return result is not None


def push_files(token, files, commit_message):
    """Push multiple files to GitHub in a single commit."""
    print(f"\n{'='*60}")
    print(f"Pushing {len(files)} files to {REPO_OWNER}/{REPO_NAME}:{BRANCH}")
    print(f"{'='*60}")

    # 1. Get current commit
    print("\n[1/5] Getting current commit...")
    commit_sha = get_current_commit_sha(token)
    if not commit_sha:
        print("ERROR: Could not get current commit SHA")
        return False
    print(f"      Current commit: {commit_sha[:8]}")

    # 2. Get base tree
    print("\n[2/5] Getting base tree...")
    tree_sha = get_tree_sha(token, commit_sha)
    if not tree_sha:
        print("ERROR: Could not get tree SHA")
        return False
    print(f"      Base tree: {tree_sha[:8]}")

    # 3. Create blobs for each file
    print("\n[3/5] Creating blobs...")
    file_blobs = {}
    for i, rel_path in enumerate(files, 1):
        local_path = LOCAL_ROOT / rel_path
        if not local_path.exists():
            print(f"      [{i}/{len(files)}] SKIP (not found): {rel_path}")
            continue
        content = local_path.read_bytes()
        blob_sha = create_blob(token, content)
        if blob_sha:
            file_blobs[rel_path] = blob_sha
            size_kb = len(content) / 1024
            print(f"      [{i}/{len(files)}] OK ({size_kb:.1f}KB): {rel_path}")
        else:
            print(f"      [{i}/{len(files)}] FAIL: {rel_path}")

    if not file_blobs:
        print("ERROR: No blobs created")
        return False

    # 4. Create tree
    print("\n[4/5] Creating tree...")
    new_tree_sha = create_tree(token, tree_sha, file_blobs)
    if not new_tree_sha:
        print("ERROR: Could not create tree")
        return False
    print(f"      New tree: {new_tree_sha[:8]}")

    # 5. Create commit and update branch
    print("\n[5/5] Creating commit and updating branch...")
    new_commit_sha = create_commit(token, commit_message, new_tree_sha, commit_sha)
    if not new_commit_sha:
        print("ERROR: Could not create commit")
        return False
    print(f"      New commit: {new_commit_sha[:8]}")

    if update_branch_ref(token, new_commit_sha):
        print(f"\nSUCCESS: Pushed {len(file_blobs)} files!")
        print(f"         Commit: {new_commit_sha}")
        return True
    else:
        print("ERROR: Could not update branch ref")
        return False


def main():
    print("=" * 60)
    print("Luqi AI v18 - GitHub Push Script")
    print("Uses Git Data API to handle files of any size")
    print("=" * 60)

    token = get_token()
    if not token:
        print("ERROR: No token provided")
        sys.exit(1)

    # Verify token works
    print("\nVerifying token...")
    user = github_api(token, "")
    if not user:
        print("ERROR: Invalid token or no access to repository")
        sys.exit(1)
    print(f"Authenticated as: {user.get('login', 'unknown')}")

    # Check repo exists and we have access
    repo = github_api(token, "")
    if not repo:
        print(f"ERROR: Cannot access {REPO_OWNER}/{REPO_NAME}")
        sys.exit(1)
    print(f"Repository: {repo.get('full_name', 'unknown')}")
    print(f"Default branch: {repo.get('default_branch', 'main')}")

    # Push all files
    success = push_files(
        token,
        FILES_TO_PUSH,
        "v18.0.0 Launch: All modules + Stripe + Email + Automotive + Writing\n\n"
        "Pushed via Git Data API to handle large files:\n"
        "- backend/router.py (v18, all endpoints wired)\n"
        "- backend/stripe_integration.py (real Stripe checkout)\n"
        "- backend/email_system.py (8 email templates)\n"
        "- backend/cognitive_engine.py (307KB ASI engine)\n"
        "- backend/education_system.py (283KB K-PhD)\n"
        "- backend/automotive.py (269KB diagnostics)\n"
        "- backend/companionship.py (222KB emotional AI)\n"
        "- backend/physics_simulator.py (209KB simulations)\n"
        "- backend/writing_assistant.py (183KB grammar)\n"
        "- All v14-v18 endpoint modules, frontend, and config files",
    )

    if success:
        print("\n" + "=" * 60)
        print("ALL FILES PUSHED SUCCESSFULLY!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Set environment variables (OPENAI_API_KEY, STRIPE_SECRET_KEY)")
        print("  2. Run: cd /path/to/project && python3 -m pip install -r requirements.txt")
        print("  3. Run: python3 backend/stripe_integration.py (one-time Stripe setup)")
        print("  4. Run: uvicorn backend.router:app --host 0.0.0.0 --port 8000")
        print("  5. Visit http://localhost:8000")
        sys.exit(0)
    else:
        print("\nPush failed. Check errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
