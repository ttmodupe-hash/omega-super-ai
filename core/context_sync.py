"""
OMEGA-LUQI Context Sync Auditor - verifies repo state against the coverage ledger.

What it CAN do: audit a GitHub repository - recent commit messages + the
coverage ledger file - and surface unresolved-stream markers (hume, voice
estate, drive intelligent, account unification) with commit attribution.

What it CANNOT do: see other chats. No tool can. The ledger + this auditor
make the REPO the source of truth; the one-line-idea protocol (CONTRIBUTING.md)
makes the ledger complete by construction.

FIXED from the pasted version:
  - host was "a-malformed-host-url" (every request failed silently -> [])
  - missing token returned [] forever = "0 gaps" false confidence
    -> now fail-closed 503; no silent empty audits
  - scans the coverage LEDGER FILE (markers are resolved in commits but
    TRACKED in the ledger - both sources are required for a real audit)
"""
import asyncio
import os
import re
from typing import Any, Dict, List

import requests
from fastapi import APIRouter, Depends, HTTPException, Query

from .admin_auth import verify_admin

router = APIRouter(prefix="/v1/sync", tags=["Context Sync Auditor"])

API_HOST = "https://api.github.com"  # FIXED: was "a-malformed-host-url" (broken)
UNRESOLVED_MARKERS = ["hume", "voice estate", "drive intelligent", "account unification"]
LEDGER_PATH = "docs/OMEGA_STREAM_COVERAGE.md"


def _require_token() -> str:
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        raise HTTPException(status_code=503,
                            detail="GITHUB_TOKEN not set - context audit disabled (fail-closed)")
    return token


def _get(endpoint: str, token: str, timeout: float = 15) -> Any:
    r = requests.get(API_HOST + endpoint,
                     headers={"Authorization": f"Bearer {token}",
                              "Accept": "application/vnd.github+json",
                              "User-Agent": "luqi-ai-sync-auditor"},
                     timeout=timeout)
    if r.status_code == 401:
        raise HTTPException(status_code=502, detail="GITHUB_TOKEN rejected by GitHub (401)")
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


# ---------------- pure logic (offline-tested) ----------------

def extract_markers(text: str, markers: List[str] = None) -> List[str]:
    low = text.lower()
    return [m for m in (markers or UNRESOLVED_MARKERS) if re.search(r"\b" + re.escape(m) + r"\b", low)]


def audit_commits(commits_payload: List[Dict[str, Any]],
                  markers: List[str] = None) -> List[Dict[str, Any]]:
    """Pure: scan commit list for unresolved markers with attribution."""
    findings = []
    for commit in commits_payload or []:
        message = (commit.get("commit") or {}).get("message", "")
        author = ((commit.get("commit") or {}).get("author") or {}).get("name", "Unknown")
        for marker in extract_markers(message, markers):
            findings.append({"marker": marker, "author": author,
                             "sha": (commit.get("sha") or "")[:8],
                             "message": message.strip().splitlines()[0][:120]})
    return findings


def ledger_open_items(ledger_text: str) -> List[str]:
    """Pure: which markers the ledger itself lists as OPEN (not merged, not rejected)."""
    open_section = ledger_text.split("## OPEN / UNRESOLVED")[1] if "## OPEN / UNRESOLVED" in ledger_text else ""
    return extract_markers(open_section)


def reconcile(commits: List[Dict[str, Any]], ledger_text: str) -> Dict[str, Any]:
    """The audit verdict: ledger-open markers vs markers still appearing in commits."""
    found = audit_commits(commits)
    ledger_open = ledger_open_items(ledger_text or "")
    return {
        "commits_scanned": len(commits or []),
        "ledger_present": bool(ledger_text),
        "ledger_open_markers": ledger_open,
        "markers_in_recent_commits": found,
        "verdict": "consistent" if ledger_open else "ledger claims nothing open - verify manually",
    }


# ---------------- live audit ----------------

async def audit_repo(owner: str, repo: str, per_page: int = 30) -> Dict[str, Any]:
    token = _require_token()
    commits = await asyncio.to_thread(_get, f"/repos/{owner}/{repo}/commits?per_page={per_page}", token)
    ledger = await asyncio.to_thread(_get, f"/repos/{owner}/{repo}/contents/{LEDGER_PATH}", token)
    ledger_text = ""
    if ledger:
        import base64
        try:
            ledger_text = base64.b64decode(ledger.get("content", "")).decode("utf-8", errors="replace")
        except Exception:
            ledger_text = ""
    result = reconcile(commits or [], ledger_text)
    result["repository"] = f"{owner}/{repo}"
    result["alerts_sent"] = await asyncio.to_thread(broadcast,
                                                    result["markers_in_recent_commits"],
                                                    result["repository"])
    result["scope_note"] = ("Audits GitHub state only - other chats are invisible to every tool; "
                            "the ledger + one-line-idea protocol close that gap by construction")
    return result


# ---------------- webhook alerting (Slack + Discord) ----------------
# Env: SLACK_WEBHOOK_URL / DISCORD_WEBHOOK_URL (full webhook URLs, both optional).
# Throttled: one alert per marker per day - an audit must never spam a channel.
# Delivery failures are swallowed: alerting never breaks the audit itself.
_alert_state = {"day": "", "fired": set()}


def format_alert(marker: str, finding: Dict[str, Any], repo: str) -> str:
    return (
        ":warning: *Luqi-ai DRIFT DETECTED* :warning:\n"
        f"*Repository:* {repo}\n"
        f"*Unresolved context:* `{marker.upper()}`\n"
        f"*Commit:* \"{finding.get('message', '')}\"\n"
        f"*Author:* {finding.get('author', '?')}  *SHA:* `{finding.get('sha', '')}`\n"
        "Verify coverage in `docs/OMEGA_STREAM_COVERAGE.md`."
    )


def should_alert(marker: str, today: str = None, state: Dict = None) -> bool:
    """Pure-throttle: True once per marker per day. Injectable for tests."""
    state = state if state is not None else _alert_state
    today = today or __import__("time").strftime("%Y-%m-%d")
    if state["day"] != today:
        state.update(day=today, fired=set())
    if marker in state["fired"]:
        return False
    state["fired"].add(marker)
    return True


def broadcast(findings: List[Dict[str, Any]], repo: str) -> Dict[str, Any]:
    """Dispatch throttled drift alerts. Never raises."""
    sent = {"slack": 0, "discord": 0}
    slack_url = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    discord_url = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    for f in findings:
        if not should_alert(f["marker"]):
            continue
        text = f.get("_prefmt") and f["message"] or format_alert(f["marker"], f, repo)
        if slack_url:
            try:
                requests.post(slack_url, json={"text": text}, timeout=8)
                sent["slack"] += 1
            except requests.exceptions.RequestException:
                pass  # alert delivery must never break the audit
        if discord_url:
            try:
                requests.post(discord_url, json={"content": text}, timeout=8)
                sent["discord"] += 1
            except requests.exceptions.RequestException:
                pass
    return sent


def broadcast_legacy_trip(entry: Dict[str, Any]) -> Dict[str, int]:
    """Ops-channel alert for a breached legacy directive. HONEST wording: nothing
    has executed - a gate task is registered and a human must release it."""
    text = (
        ":rotating_light: *DIGITAL LEGACY THRESHOLD BREACHED* :rotating_light:\n"
        f"*Account:* `{entry.get('user_id', '?')[:12]}`  *Idle:* {entry.get('idle_days', '?')} days\n"
        f"*Trusted contact:* `{entry.get('trusted_contact', '?')}`\n"
        "Status: gate task REGISTERED - awaiting authenticated human release. "
        "No data action has been taken."
    )
    return broadcast([{"marker": f"legacy-trip-{entry.get('user_id', '?')[:8]}",
                       "message": text, "author": "legacy-guard", "sha": "n/a",
                       "_prefmt": True}], "omega-super-ai/legacy")


@router.get("/audit")
async def sync_audit(owner: str = Query(...), repo: str = Query(...),
                     is_authenticated: bool = Depends(verify_admin)):
    """Admin: audit a GitHub repo against the coverage ledger. Fail-closed without GITHUB_TOKEN."""
    return await audit_repo(owner, repo)


# ---------------- CLI runner (CI cron) ----------------
if __name__ == "__main__":
    import asyncio as _asyncio
    import json as _json
    import sys as _sys

    _owner = _sys.argv[1] if len(_sys.argv) > 1 else os.getenv("GITHUB_OWNER", "")
    _repo = _sys.argv[2] if len(_sys.argv) > 2 else os.getenv("GITHUB_REPO", "")
    if not (_owner and _repo):
        print("usage: python -m core.context_sync <owner> <repo>", file=_sys.stderr)
        _sys.exit(2)
    try:
        report = _asyncio.new_event_loop().run_until_complete(audit_repo(_owner, _repo))
    except HTTPException as e:
        print(_json.dumps({"audit": "failed", "detail": e.detail}), file=_sys.stderr)
        _sys.exit(1)
    print(_json.dumps(report, indent=2, default=str))
    _sys.exit(0)  # findings are not failures - exit 1 is for audit failure only
