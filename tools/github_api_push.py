"""GitHub API push - terminal-free upload of the engine tree.

Usage (run by the build agent, not the user):
    python -m tools.github_api_push --token <PAT> --owner ttmodupe-hash --repo omega-super-ai

Creates blobs -> tree -> commit -> ref over HTTPS. No git binary needed.
Respects .gitignore. Creates the release tag. Prints verification URLs.
"""
import argparse
import base64
import json
import os
import sys
import urllib.request
import urllib.error

API = "https://api.github.com"
VERSION = "v5.29.0"


def _ignores(path, rules):
    parts = path.split("/")
    for rule in rules:
        rule = rule.strip()
        if not rule or rule.startswith("#"):
            continue
        negate = rule.startswith("!")
        if negate:
            rule = rule[1:]
        if rule.endswith("/"):
            rule = rule[:-1]
            hit = rule in parts or any(p.startswith(rule) for p in parts)
        elif rule.startswith("*."):
            hit = any(p.endswith(rule[1:]) for p in parts)
        elif "/" not in rule:
            hit = rule in parts or any(p == rule for p in parts)
        else:
            hit = path == rule or path.startswith(rule + "/")
        if hit:
            return not negate
    return False


def collect(root):
    rules = open(os.path.join(root, ".gitignore")).read().splitlines()
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        if rel_dir == ".":
            rel_dir = ""
        dirnames[:] = [d for d in dirnames if not _ignores(
            os.path.join(rel_dir, d), rules)]
        for fn in filenames:
            rel = os.path.join(rel_dir, fn) if rel_dir else fn
            if _ignores(rel, rules):
                continue
            full = os.path.join(dirpath, fn)
            files.append((rel.replace(os.sep, "/"), full))
    return sorted(files)


def api(method, url, token, payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=body, method=method, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "luqi-ai-api-push",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode()), r.status
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode()[:300]}, e.code


def push(root, token, owner, repo, dry_run=False):
    files = collect(root)
    total_bytes = sum(os.path.getsize(f) for _, f in files)
    print(f"manifest: {len(files)} files, {total_bytes} bytes")
    for rel, _ in files[:5]:
        print("  ", rel)
    print("   ...")
    if dry_run:
        return {"dry_run": True, "files": len(files)}

    base = f"{API}/repos/{owner}/{repo}"

    # repo must exist and be reachable
    repo_info, code = api("GET", base, token)
    if code != 200:
        return {"error": f"repo unreachable: {repo_info}", "code": code}
    default_branch = repo_info.get("default_branch", "main")

    blobs = []
    for i, (rel, full) in enumerate(files, 1):
        content = open(full, "rb").read()
        payload = {"content": base64.b64encode(content).decode(), "encoding": "base64"}
        resp, code = api("POST", f"{base}/git/blobs", token, payload)
        if code != 201:
            return {"error": f"blob failed for {rel}: {resp}", "code": code}
        blobs.append({"path": rel, "mode": "100644", "type": "blob", "sha": resp["sha"]})
        if i % 25 == 0:
            print(f"  blobs: {i}/{len(files)}")

    # base tree = current branch head (or empty for fresh repo)
    ref_resp, code = api("GET", f"{base}/git/refs/heads/{default_branch}", token)
    base_sha = ref_resp.get("object", {}).get("sha") if code == 200 else None

    tree_payload = {"tree": blobs}
    if base_sha:
        tree_payload["base_tree"] = base_sha
    tree, code = api("POST", f"{base}/git/trees", token, tree_payload)
    if code != 201:
        return {"error": f"tree failed: {tree}", "code": code}

    commit, code = api("POST", f"{base}/git/commits", token, {
        "message": f"release: {VERSION} unified engine consolidation",
        "tree": tree["sha"],
        **({"parents": [base_sha]} if base_sha else {}),
    })
    if code != 201:
        return {"error": f"commit failed: {commit}", "code": code}

    ref_update, code = api("PATCH", f"{base}/git/refs/heads/{default_branch}", token,
                           {"sha": commit["sha"], "force": False})
    if code not in (200, 201):
        # branch may not exist yet on a fresh repo
        ref_update, code = api("POST", f"{base}/git/refs", token,
                               {"ref": f"refs/heads/{default_branch}", "sha": commit["sha"]})
        if code not in (200, 201):
            return {"error": f"ref update failed: {ref_update}", "code": code}

    tag, code = api("POST", f"{base}/git/refs", token, {
        "ref": f"refs/tags/{VERSION}",
        "sha": commit["sha"],
    })
    tag_ok = code in (200, 201)

    return {
        "pushed": True, "files": len(files), "commit": commit["sha"][:10],
        "branch": default_branch, "tag": VERSION if tag_ok else "FAILED",
        "verify": f"https://github.com/{owner}/{repo}/commit/{commit['sha']}",
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", default=os.getenv("GITHUB_TOKEN", ""))
    ap.add_argument("--owner", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    result = push(args.root, args.token, args.owner, args.repo, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("pushed") or result.get("dry_run") else 1)
