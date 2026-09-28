#!/usr/bin/env python3
"""
Production-grade script to batch push files or directories to GitHub
using the Git Data API + Git LFS for files exceeding 100MB.

Usage:
    export GITHUB_TOKEN=ghp_xxxxxxxx
    python3 push_large_file.py backend/ heavy_dataset.zip "Commit message"
"""

import os
import sys
import json
import stat
import time
import base64
import hashlib
import urllib.request
import urllib.error
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

REPO_OWNER = "ttmodupe-hash"
REPO_NAME = "omega-super-ai"
BRANCH = "main"
MAX_WORKERS = 8
LFS_THRESHOLD_BYTES = 100 * 1024 * 1024  # 100 MB limit for standard blobs


def get_token():
    token = os.environ.get("GITHUB_TOKEN", "").strip() or os.environ.get("GH_TOKEN", "").strip()
    if not token:
        print("ERROR: Missing token. Set GITHUB_TOKEN or GH_TOKEN.")
        sys.exit(1)
    return token


def github_api(token, path, method="GET", data=None, max_retries=3):
    """Issues API requests with exponential backoff."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Luqi-AI-Large-File-Push",
    }
    body = json.dumps(data).encode("utf-8") if data is not None else None
    if body:
        headers["Content-Type"] = "application/json"

    for attempt in range(1, max_retries + 1):
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_msg = e.read().decode("utf-8", errors="ignore")
            if e.code in (403, 429, 500, 502, 503, 504) and attempt < max_retries:
                wait_time = attempt * 2
                print(f"  [HTTP {e.code}] Retrying in {wait_time}s (Attempt {attempt}/{max_retries})...")
                time.sleep(wait_time)
                continue
            print(f"  API Error ({e.code}): {error_msg[:300]}")
            return None
        except urllib.error.URLError as e:
            if attempt < max_retries:
                time.sleep(2)
                continue
            print(f"  Network Error: {e.reason}")
            return None
    return None


def get_file_mode(file_path):
    """Detects executable mode (100755) vs regular file (100644)."""
    try:
        st_mode = file_path.stat().st_mode
        if st_mode & stat.S_IXUSR:
            return "100755"
    except Exception:
        pass
    return "100644"


def compute_sha256(file_path):
    """Computes SHA-256 hash required for Git LFS verification."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192 * 1024):  # Read 8MB chunks
            hasher.update(chunk)
    return hasher.hexdigest()


def upload_via_lfs(token, file_path):
    """Uploads files > 100MB using GitHub's Git LFS Batch API and returns an LFS pointer blob."""
    file_size = file_path.stat().st_size
    oid = compute_sha256(file_path)
    size_mb = file_size / (1024 * 1024)

    print(f"  [LFS API] Requesting LFS upload token for {file_path.name} ({size_mb:.2f} MB)...")

    # 1. Request LFS Batch Upload Action
    lfs_batch_url = f"https://github.com/{REPO_OWNER}/{REPO_NAME}.git/info/lfs/objects/batch"
    payload = {
        "operation": "upload",
        "transfers": ["basic"],
        "objects": [{"oid": oid, "size": file_size}],
    }

    req = urllib.request.Request(
        lfs_batch_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.git-lfs+json",
            "Content-Type": "application/vnd.git-lfs+json",
            "User-Agent": "Luqi-AI-Large-File-Push",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            lfs_resp = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"  [LFS ERROR] Batch API failed: {e.read().decode('utf-8', errors='ignore')}")
        return None

    obj = lfs_resp.get("objects", [{}])[0]
    actions = obj.get("actions", {})

    # 2. Upload file binary data to storage target if upload action exists
    if "upload" in actions:
        upload_info = actions["upload"]
        upload_url = upload_info["href"]
        upload_headers = upload_info.get("headers", {})

        print(f"  [LFS STORAGE] Uploading {file_path.name} to LFS backend...")
        with open(file_path, "rb") as f_data:
            up_req = urllib.request.Request(upload_url, data=f_data, headers=upload_headers, method="PUT")
            try:
                with urllib.request.urlopen(up_req, timeout=600):
                    print(f"  [LFS STORAGE] Upload complete: {file_path.name}")
            except urllib.error.HTTPError as e:
                print(f"  [LFS ERROR] Direct storage upload failed: {e.code}")
                return None
    else:
        print(f"  [LFS API] Object {oid[:8]} already exists in LFS store. Skipping raw upload.")

    # 3. Create a Git LFS Pointer Spec
    pointer_content = (
        f"version https://git-lfs.github.com/spec/v1\n"
        f"oid sha256:{oid}\n"
        f"size {file_size}\n"
    )

    # 4. Push pointer file as a standard Git blob
    b64_pointer = base64.b64encode(pointer_content.encode("utf-8")).decode("utf-8")
    blob_result = github_api(
        token,
        "git/blobs",
        method="POST",
        data={"encoding": "base64", "content": b64_pointer},
    )

    if blob_result and "sha" in blob_result:
        repo_path = get_relative_repo_path(file_path)
        return {
            "path": repo_path,
            "mode": get_file_mode(file_path),
            "type": "blob",
            "sha": blob_result["sha"],
        }
    return None


def create_standard_blob(token, file_path):
    """Handles standard Git blobs under 100MB."""
    try:
        content = file_path.read_bytes()
    except Exception as e:
        print(f"  ERROR reading {file_path}: {e}")
        return None

    size_mb = len(content) / (1024 * 1024)
    b64_content = base64.b64encode(content).decode("utf-8")
    data = {"encoding": "base64", "content": b64_content}
    result = github_api(token, "git/blobs", method="POST", data=data)

    if result and "sha" in result:
        repo_path = get_relative_repo_path(file_path)
        print(f"  Uploaded blob: {repo_path} ({size_mb:.2f} MB) -> {result['sha'][:8]}")
        return {
            "path": repo_path,
            "mode": get_file_mode(file_path),
            "type": "blob",
            "sha": result["sha"],
        }
    return None


def process_file(token, file_path):
    """Routes files to standard blob creation or LFS protocol depending on file size."""
    file_size = file_path.stat().st_size
    if file_size > LFS_THRESHOLD_BYTES:
        return upload_via_lfs(token, file_path)
    else:
        return create_standard_blob(token, file_path)


def collect_file_paths(paths):
    """Recursively collects valid files, ignoring hidden files/folders."""
    files_to_process = []
    for p_str in paths:
        p = Path(p_str)
        if p.is_file():
            files_to_process.append(p)
        elif p.is_dir():
            for entry in p.rglob("*"):
                if entry.is_file() and not any(part.startswith(".") for part in entry.parts):
                    files_to_process.append(entry)
        else:
            print(f"WARNING: Path not found or ignored: {p_str}")
    return sorted(list(set(files_to_process)))


def get_relative_repo_path(file_path):
    """Formats relative paths cleanly for Git API compatibility."""
    resolved = file_path.resolve()
    cwd = Path.cwd().resolve()
    try:
        rel = resolved.relative_to(cwd)
    except ValueError:
        rel = file_path
    return rel.as_posix().lstrip("/")


def push_batch(token, input_paths, commit_message):
    file_paths = collect_file_paths(input_paths)
    if not file_paths:
        print("ERROR: No valid files found to commit.")
        return False

    print(f"Preparing commit with {len(file_paths)} file(s) across {MAX_WORKERS} upload threads...")

    # 1. Fetch HEAD commit & base tree
    ref_info = github_api(token, f"git/ref/heads/{BRANCH}")
    if not ref_info:
        print(f"ERROR: Could not fetch ref heads/{BRANCH}")
        return False
    parent_commit_sha = ref_info["object"]["sha"]

    commit_info = github_api(token, f"git/commits/{parent_commit_sha}")
    if not commit_info:
        print("ERROR: Could not fetch parent commit details")
        return False
    base_tree_sha = commit_info["tree"]["sha"]

    # 2. Parallel Uploads (LFS + Standard Blobs)
    tree_items = []
    failed = False
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_file = {executor.submit(process_file, token, fp): fp for fp in file_paths}
        for future in as_completed(future_to_file):
            fp = future_to_file[future]
            res = future.result()
            if res is None:
                print(f"ERROR: Halting commit due to failed processing of {fp}")
                failed = True
            else:
                tree_items.append(res)

    if failed or len(tree_items) != len(file_paths):
        print("ERROR: Batch upload aborted because one or more files failed.")
        return False

    tree_items.sort(key=lambda item: item["path"])

    # 3. Create tree
    print("\nAssembling commit tree...")
    tree_data = {"base_tree": base_tree_sha, "tree": tree_items}
    tree_result = github_api(token, "git/trees", method="POST", data=tree_data)
    if not tree_result:
        print("ERROR: Failed to create tree")
        return False

    # 4. Create commit
    print("Creating commit...")
    commit_data = {
        "message": commit_message,
        "tree": tree_result["sha"],
        "parents": [parent_commit_sha],
    }
    commit_result = github_api(token, "git/commits", method="POST", data=commit_data)
    if not commit_result:
        print("ERROR: Failed to create commit")
        return False
    new_commit_sha = commit_result["sha"]

    # 5. Update branch reference
    ref_data = {"sha": new_commit_sha, "force": False}
    ref_result = github_api(token, f"git/refs/heads/{BRANCH}", method="PATCH", data=ref_data)

    if ref_result:
        print(f"\nSUCCESS! Pushed {len(tree_items)} file(s) in a single commit.")
        print(f"Commit SHA: {new_commit_sha[:8]}")
        print(f"Commit URL: https://github.com/{REPO_OWNER}/{REPO_NAME}/commit/{new_commit_sha}")
        return True

    print("ERROR: Failed to update branch reference")
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 push_large_file.py <file1_or_dir1> [file2_or_dir2 ...] [commit_message]")
        sys.exit(1)

    args = sys.argv[1:]
    if len(args) > 1 and not Path(args[-1]).exists():
        commit_msg = args[-1]
        target_paths = args[:-1]
    else:
        target_paths = args
        commit_msg = f"Add/update {len(target_paths)} target item(s)"

    auth_token = get_token()
    success = push_batch(auth_token, target_paths, commit_msg)
    sys.exit(0 if success else 1)
