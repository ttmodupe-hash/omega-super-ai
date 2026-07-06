"""
Luqi AI - GitHub Integration Module
====================================

A comprehensive GitHub API integration for the developer workspace.
Handles authentication, repository management, code operations,
pull requests, code review, and project publishing.

Author: Luqi AI Team
Version: 1.0.0
"""

import base64
import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import quote, urljoin

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("luqi.github")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
    )
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GITHUB_API_BASE = "https://api.github.com"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com"
DEFAULT_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
RETRY_BACKOFF = 1.5  # exponential backoff factor
RETRY_STATUS_FORCELIST = [429, 500, 502, 503, 504]

# File extensions considered source code for code review
SOURCE_CODE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs",
    ".c", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php", ".swift",
    ".kt", ".scala", ".r", ".m", ".mm", ".lua", ".sh", ".bash",
    ".ps1", ".sql", ".html", ".css", ".scss", ".sass", ".less",
    ".vue", ".svelte", ".dart", ".erl", ".ex", ".exs", ".clj",
    ".hs", ".lhs", ".fs", ".fsx", ".ml", ".mli", ".nim",
}

README_PATTERNS = [
    "README.md", "README.rst", "README.txt", "README",
    "readme.md", "Readme.md", "README.MD",
]

# ---------------------------------------------------------------------------
# Session Factory
# ---------------------------------------------------------------------------

def _create_session() -> requests.Session:
    """Create a requests session with retry logic and sensible defaults."""
    session = requests.Session()
    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=RETRY_BACKOFF,
        status_forcelist=RETRY_STATUS_FORCELIST,
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# Global session (can be overridden for testing)
_session = _create_session()


def _get_session() -> requests.Session:
    """Return the current session instance."""
    return _session


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def get_auth_headers(pat: str) -> Dict[str, str]:
    """
    Get headers for authenticated GitHub API requests.

    Args:
        pat: GitHub Personal Access Token.

    Returns:
        Dictionary with Authorization and Accept headers.
    """
    return {
        "Authorization": f"token {pat}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Luqi-AI-GitHub-Integration/1.0",
    }


def auth_with_pat(pat: str) -> Dict[str, Any]:
    """
    Verify a GitHub Personal Access Token and return user info.

    Args:
        pat: GitHub Personal Access Token.

    Returns:
        Dictionary with keys:
            - authenticated (bool): Whether the token is valid.
            - username (str): GitHub login/username.
            - avatar_url (str): URL to user's avatar image.
            - repos_url (str): API URL for user's repos.
            - name (str): User's display name.
            - email (str): User's public email.
            - error (str): Error message if authentication failed.
    """
    if not pat or not pat.strip():
        return {
            "authenticated": False,
            "username": None,
            "avatar_url": None,
            "repos_url": None,
            "name": None,
            "email": None,
            "error": "Personal Access Token is empty",
        }

    try:
        headers = get_auth_headers(pat)
        response = _get_session().get(
            f"{GITHUB_API_BASE}/user",
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
        )

        # Handle rate limiting
        if response.status_code == 403:
            remaining = response.headers.get("X-RateLimit-Remaining", "0")
            if remaining == "0":
                reset_ts = int(response.headers.get("X-RateLimit-Reset", 0))
                reset_dt = datetime.fromtimestamp(reset_ts, tz=timezone.utc)
                logger.warning("GitHub rate limit exceeded. Resets at %s", reset_dt)
                return {
                    "authenticated": False,
                    "username": None,
                    "avatar_url": None,
                    "repos_url": None,
                    "name": None,
                    "email": None,
                    "error": f"GitHub rate limit exceeded. Resets at {reset_dt.isoformat()}",
                }

        if response.status_code == 401:
            logger.warning("Invalid GitHub PAT provided")
            return {
                "authenticated": False,
                "username": None,
                "avatar_url": None,
                "repos_url": None,
                "name": None,
                "email": None,
                "error": "Invalid Personal Access Token (401 Unauthorized)",
            }

        response.raise_for_status()
        data = response.json()

        logger.info("Authenticated as GitHub user: %s", data.get("login"))
        return {
            "authenticated": True,
            "username": data.get("login"),
            "avatar_url": data.get("avatar_url"),
            "repos_url": data.get("repos_url"),
            "name": data.get("name"),
            "email": data.get("email"),
            "error": None,
        }

    except requests.exceptions.Timeout:
        logger.error("Timeout while verifying GitHub PAT")
        return {
            "authenticated": False,
            "username": None,
            "avatar_url": None,
            "repos_url": None,
            "name": None,
            "email": None,
            "error": "Request timed out while connecting to GitHub API",
        }
    except requests.exceptions.ConnectionError:
        logger.error("Connection error while verifying GitHub PAT")
        return {
            "authenticated": False,
            "username": None,
            "avatar_url": None,
            "repos_url": None,
            "name": None,
            "email": None,
            "error": "Connection error. Check network connectivity.",
        }
    except requests.exceptions.RequestException as exc:
        logger.error("Request error during PAT verification: %s", exc)
        return {
            "authenticated": False,
            "username": None,
            "avatar_url": None,
            "repos_url": None,
            "name": None,
            "email": None,
            "error": f"Request error: {str(exc)}",
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _github_request(
    method: str,
    endpoint: str,
    pat: str,
    json_data: Optional[Dict] = None,
    params: Optional[Dict] = None,
    expected_status: Optional[Union[int, Tuple[int, ...]]] = None,
) -> Dict[str, Any]:
    """
    Execute a GitHub API request with comprehensive error handling.

    Args:
        method: HTTP method (GET, POST, PUT, PATCH, DELETE).
        endpoint: API endpoint path (e.g. '/user/repos').
        pat: Personal Access Token for authentication.
        json_data: Optional JSON body for POST/PUT/PATCH.
        params: Optional query parameters.
        expected_status: Expected HTTP status code(s).

    Returns:
        Standardized response dict with keys:
            - success (bool)
            - status_code (int)
            - data (dict or list)
            - error (str or None)
            - headers (dict)
    """
    url = f"{GITHUB_API_BASE}{endpoint}" if endpoint.startswith("/") else endpoint
    headers = get_auth_headers(pat)

    try:
        logger.debug("GitHub API %s %s", method.upper(), url)
        response = _get_session().request(
            method=method.upper(),
            url=url,
            headers=headers,
            json=json_data,
            params=params,
            timeout=DEFAULT_TIMEOUT,
        )

        # Log rate limit info
        remaining = response.headers.get("X-RateLimit-Remaining")
        limit = response.headers.get("X-RateLimit-Limit")
        if remaining and limit:
            logger.debug("Rate limit: %s/%s remaining", remaining, limit)

        # Check expected status
        if expected_status:
            if isinstance(expected_status, int):
                expected_status = (expected_status,)
            if response.status_code not in expected_status:
                # Try to extract error message from response
                error_msg = f"Unexpected status {response.status_code}"
                try:
                    error_body = response.json()
                    if "message" in error_body:
                        error_msg = f"GitHub API error: {error_body['message']}"
                    if "errors" in error_body:
                        error_msg += f" | Details: {error_body['errors']}"
                except (ValueError, KeyError):
                    error_msg = f"GitHub API error: {response.text[:500]}"

                return {
                    "success": False,
                    "status_code": response.status_code,
                    "data": None,
                    "error": error_msg,
                    "headers": dict(response.headers),
                }

        # Parse response body
        try:
            data = response.json() if response.text else {}
        except ValueError:
            data = {"raw": response.text}

        # Check for HTTP error status (4xx/5xx) if not already handled
        if not expected_status and response.status_code >= 400:
            error_msg = data.get("message", f"HTTP {response.status_code}")
            return {
                "success": False,
                "status_code": response.status_code,
                "data": data,
                "error": error_msg,
                "headers": dict(response.headers),
            }

        return {
            "success": True,
            "status_code": response.status_code,
            "data": data,
            "error": None,
            "headers": dict(response.headers),
        }

    except requests.exceptions.Timeout:
        logger.error("Request timeout: %s %s", method.upper(), url)
        return {
            "success": False,
            "status_code": 0,
            "data": None,
            "error": f"Request timed out after {DEFAULT_TIMEOUT}s",
            "headers": {},
        }
    except requests.exceptions.ConnectionError as exc:
        logger.error("Connection error: %s %s - %s", method.upper(), url, exc)
        return {
            "success": False,
            "status_code": 0,
            "data": None,
            "error": "Connection error. Please check network connectivity.",
            "headers": {},
        }
    except requests.exceptions.RequestException as exc:
        logger.error("Request exception: %s %s - %s", method.upper(), url, exc)
        return {
            "success": False,
            "status_code": 0,
            "data": None,
            "error": str(exc),
            "headers": {},
        }


def _check_pat_and_result(pat: str, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Check if the PAT is valid and the API call succeeded.
    Returns an error dict if something went wrong, None otherwise.
    """
    if not pat or not pat.strip():
        return {"error": "Personal Access Token is required", "success": False}
    if not result["success"]:
        return result
    return None


# ---------------------------------------------------------------------------
# Repository Management
# ---------------------------------------------------------------------------

def list_repos(pat: str, page: int = 1, per_page: int = 30) -> List[Dict[str, Any]]:
    """
    List user's GitHub repositories.

    Args:
        pat: GitHub Personal Access Token.
        page: Page number for pagination.
        per_page: Number of repos per page (max 100).

    Returns:
        List of repository dicts with keys:
            id, name, full_name, description, language,
            stars, forks, updated_at, url
    """
    per_page = min(max(per_page, 1), 100)
    result = _github_request(
        "GET",
        "/user/repos",
        pat,
        params={
            "sort": "updated",
            "direction": "desc",
            "page": page,
            "per_page": per_page,
            "affiliation": "owner,collaborator,organization_member",
        },
    )

    error = _check_pat_and_result(pat, result)
    if error:
        logger.error("Failed to list repos: %s", error.get("error"))
        return []

    repos = []
    for item in result.get("data", []):
        repos.append({
            "id": item.get("id"),
            "name": item.get("name"),
            "full_name": item.get("full_name"),
            "description": item.get("description") or "",
            "language": item.get("language") or "Unknown",
            "stars": item.get("stargazers_count", 0),
            "forks": item.get("forks_count", 0),
            "updated_at": item.get("updated_at"),
            "url": item.get("html_url"),
            "private": item.get("private", False),
        })

    logger.info("Listed %d repositories (page %d, per_page %d)", len(repos), page, per_page)
    return repos


def create_repo(
    pat: str,
    name: str,
    description: str = "",
    private: bool = False,
    auto_init: bool = True,
    gitignore_template: str = "",
) -> Dict[str, Any]:
    """
    Create a new GitHub repository.

    Args:
        pat: GitHub Personal Access Token.
        name: Repository name.
        description: Repository description.
        private: Whether the repo should be private.
        auto_init: Initialize with a README.
        gitignore_template: Gitignore template (e.g. 'Python', 'Node').

    Returns:
        Dict with keys:
            success, id, name, full_name, html_url, clone_url,
            ssh_url, created, error
    """
    if not name or not name.strip():
        return {
            "success": False,
            "id": None,
            "name": None,
            "full_name": None,
            "html_url": None,
            "clone_url": None,
            "ssh_url": None,
            "created": False,
            "error": "Repository name is required",
        }

    # Validate repo name per GitHub rules
    if not re.match(r"^[a-zA-Z0-9._-]+$", name):
        return {
            "success": False,
            "id": None,
            "name": None,
            "full_name": None,
            "html_url": None,
            "clone_url": None,
            "ssh_url": None,
            "created": False,
            "error": (
                "Invalid repository name. Use only letters, numbers, "
                "hyphens, underscores, and periods."
            ),
        }

    payload: Dict[str, Any] = {
        "name": name,
        "description": description,
        "private": private,
        "auto_init": auto_init,
    }
    if gitignore_template:
        payload["gitignore_template"] = gitignore_template

    result = _github_request("POST", "/user/repos", pat, json_data=payload)

    error = _check_pat_and_result(pat, result)
    if error:
        return {
            "success": False,
            "id": None,
            "name": name,
            "full_name": None,
            "html_url": None,
            "clone_url": None,
            "ssh_url": None,
            "created": False,
            "error": error.get("error", "Unknown error"),
        }

    data = result.get("data", {})
    logger.info("Created repository: %s", data.get("full_name", name))
    return {
        "success": True,
        "id": data.get("id"),
        "name": data.get("name"),
        "full_name": data.get("full_name"),
        "html_url": data.get("html_url"),
        "clone_url": data.get("clone_url"),
        "ssh_url": data.get("ssh_url"),
        "created": True,
        "error": None,
    }


def get_repo(pat: str, owner: str, repo: str) -> Dict[str, Any]:
    """
    Get repository details.

    Args:
        pat: GitHub Personal Access Token.
        owner: Repository owner (user or org).
        repo: Repository name.

    Returns:
        Dict with repository details or error info.
    """
    if not owner or not repo:
        return {"success": False, "error": "Owner and repo name are required", "data": None}

    result = _github_request("GET", f"/repos/{quote(owner, safe='')}/{quote(repo, safe='')}", pat)

    error = _check_pat_and_result(pat, result)
    if error:
        return {"success": False, "error": error.get("error"), "data": None}

    data = result.get("data", {})
    return {
        "success": True,
        "error": None,
        "data": {
            "id": data.get("id"),
            "name": data.get("name"),
            "full_name": data.get("full_name"),
            "description": data.get("description") or "",
            "language": data.get("language") or "Unknown",
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "open_issues": data.get("open_issues_count", 0),
            "private": data.get("private", False),
            "html_url": data.get("html_url"),
            "clone_url": data.get("clone_url"),
            "ssh_url": data.get("ssh_url"),
            "default_branch": data.get("default_branch", "main"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "size": data.get("size", 0),
            "topics": data.get("topics", []),
            "license": (data.get("license") or {}).get("name"),
        },
    }


def delete_repo(pat: str, owner: str, repo: str) -> Dict[str, Any]:
    """
    Delete a repository.

    Args:
        pat: GitHub Personal Access Token.
        owner: Repository owner.
        repo: Repository name.

    Returns:
        Dict with success status and message.
    """
    if not owner or not repo:
        return {"success": False, "error": "Owner and repo name are required"}

    result = _github_request(
        "DELETE",
        f"/repos/{quote(owner, safe='')}/{quote(repo, safe='')}",
        pat,
        expected_status=(204, 404),
    )

    error = _check_pat_and_result(pat, result)
    if error:
        return {"success": False, "error": error.get("error")}

    if result["status_code"] == 404:
        logger.warning("Repository %s/%s not found for deletion", owner, repo)
        return {
            "success": False,
            "error": f"Repository {owner}/{repo} not found or you don't have permission to delete it.",
        }

    logger.info("Deleted repository: %s/%s", owner, repo)
    return {
        "success": True,
        "error": None,
        "message": f"Repository {owner}/{repo} deleted successfully.",
    }


# ---------------------------------------------------------------------------
# Code Operations
# ---------------------------------------------------------------------------

def get_file_contents(
    pat: str,
    owner: str,
    repo: str,
    path: str,
    branch: str = "main",
) -> Dict[str, Any]:
    """
    Get file contents from a repository.

    Args:
        pat: GitHub Personal Access Token.
        owner: Repository owner.
        repo: Repository name.
        path: File path within the repo.
        branch: Branch name.

    Returns:
        Dict with:
            - success (bool)
            - content (str): Decoded file content.
            - sha (str): Blob SHA for updates.
            - size (int): File size in bytes.
            - error (str): Error message if failed.
    """
    if not owner or not repo or not path:
        return {
            "success": False,
            "content": None,
            "sha": None,
            "size": 0,
            "error": "Owner, repo, and path are required",
        }

    encoded_path = quote(path.lstrip("/"), safe="/")
    result = _github_request(
        "GET",
        f"/repos/{quote(owner, safe='')}/{quote(repo, safe='')}/contents/{encoded_path}",
        pat,
        params={"ref": branch},
    )

    error = _check_pat_and_result(pat, result)
    if error:
        return {
            "success": False,
            "content": None,
            "sha": None,
            "size": 0,
            "error": error.get("error"),
        }

    data = result.get("data", {})

    # Handle directory listing
    if isinstance(data, list):
        return {
            "success": True,
            "content": None,
            "sha": None,
            "size": 0,
            "is_directory": True,
            "entries": [{"name": e.get("name"), "type": e.get("type"), "path": e.get("path")} for e in data],
            "error": None,
        }

    encoded_content = data.get("content", "")
    try:
        decoded = base64.b64decode(encoded_content.replace("\n", "")).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        logger.warning("Failed to decode content for %s: %s", path, exc)
        decoded = encoded_content

    return {
        "success": True,
        "content": decoded,
        "sha": data.get("sha"),
        "size": data.get("size", 0),
        "is_directory": False,
        "error": None,
    }


def push_files(
    pat: str,
    owner: str,
    repo: str,
    files: List[Dict[str, str]],
    message: str = "Update from Luqi AI",
    branch: str = "main",
) -> Dict[str, Any]:
    """
    Push multiple files to a repository in a single commit.

    Uses the Git Tree API to create a commit with multiple files efficiently.

    Args:
        pat: GitHub Personal Access Token.
        owner: Repository owner.
        repo: Repository name.
        files: List of dicts with 'path' and 'content' keys.
        message: Commit message.
        branch: Target branch name.

    Returns:
        Dict with:
            - success (bool)
            - commit_sha (str)
            - tree_sha (str)
            - message (str)
            - files_pushed (int)
            - error (str)
    """
    if not files:
        return {
            "success": False,
            "commit_sha": None,
            "tree_sha": None,
            "message": message,
            "files_pushed": 0,
            "error": "No files provided to push",
        }

    # Validate file entries
    for i, f in enumerate(files):
        if "path" not in f or "content" not in f:
            return {
                "success": False,
                "commit_sha": None,
                "tree_sha": None,
                "message": message,
                "files_pushed": 0,
                "error": f"File entry at index {i} missing 'path' or 'content'",
            }

    owner_safe = quote(owner, safe="")
    repo_safe = quote(repo, safe="")
    repo_ref = f"{owner_safe}/{repo_safe}"

    # 1. Get the current commit SHA for the branch
    ref_result = _github_request(
        "GET", f"/repos/{repo_ref}/git/ref/heads/{branch}", pat
    )
    error = _check_pat_and_result(pat, ref_result)
    if error:
        # Try 'master' if 'main' fails
        if branch == "main":
            logger.info("Branch 'main' not found, trying 'master'")
            return push_files(pat, owner, repo, files, message, branch="master")
        return {
            "success": False,
            "commit_sha": None,
            "tree_sha": None,
            "message": message,
            "files_pushed": 0,
            "error": f"Failed to get branch ref: {error.get('error')}",
        }

    base_commit_sha = ref_result["data"]["object"]["sha"]

    # 2. Get the base tree
    commit_result = _github_request(
        "GET", f"/repos/{repo_ref}/git/commits/{base_commit_sha}", pat
    )
    error = _check_pat_and_result(pat, commit_result)
    if error:
        return {
            "success": False,
            "commit_sha": None,
            "tree_sha": None,
            "message": message,
            "files_pushed": 0,
            "error": f"Failed to get base commit: {error.get('error')}",
        }

    base_tree_sha = commit_result["data"]["tree"]["sha"]

    # 3. Create tree entries for all files
    tree_entries = []
    for f in files:
        content = f["content"]
        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
        else:
            content_bytes = content
        tree_entries.append({
            "path": f["path"].lstrip("/"),
            "mode": "100644",
            "type": "blob",
            "content": content_bytes.decode("utf-8"),
        })

    tree_result = _github_request(
        "POST",
        f"/repos/{repo_ref}/git/trees",
        pat,
        json_data={"base_tree": base_tree_sha, "tree": tree_entries},
    )
    error = _check_pat_and_result(pat, tree_result)
    if error:
        return {
            "success": False,
            "commit_sha": None,
            "tree_sha": None,
            "message": message,
            "files_pushed": 0,
            "error": f"Failed to create tree: {error.get('error')}",
        }

    new_tree_sha = tree_result["data"]["sha"]

    # 4. Create the commit
    commit_payload = {
        "message": message,
        "tree": new_tree_sha,
        "parents": [base_commit_sha],
    }
    new_commit_result = _github_request(
        "POST", f"/repos/{repo_ref}/git/commits", pat, json_data=commit_payload
    )
    error = _check_pat_and_result(pat, new_commit_result)
    if error:
        return {
            "success": False,
            "commit_sha": None,
            "tree_sha": new_tree_sha,
            "message": message,
            "files_pushed": 0,
            "error": f"Failed to create commit: {error.get('error')}",
        }

    new_commit_sha = new_commit_result["data"]["sha"]

    # 5. Update the branch reference
    update_result = _github_request(
        "PATCH",
        f"/repos/{repo_ref}/git/refs/heads/{branch}",
        pat,
        json_data={"sha": new_commit_sha, "force": False},
    )
    error = _check_pat_and_result(pat, update_result)
    if error:
        return {
            "success": False,
            "commit_sha": new_commit_sha,
            "tree_sha": new_tree_sha,
            "message": message,
            "files_pushed": len(files),
            "error": f"Commit created but branch update failed: {error.get('error')}",
        }

    logger.info(
        "Pushed %d files to %s/%s on branch %s (commit: %s)",
        len(files), owner, repo, branch, new_commit_sha[:7],
    )
    return {
        "success": True,
        "commit_sha": new_commit_sha,
        "tree_sha": new_tree_sha,
        "message": message,
        "files_pushed": len(files),
        "error": None,
    }


def create_branch(
    pat: str,
    owner: str,
    repo: str,
    branch: str,
    from_branch: str = "main",
) -> Dict[str, Any]:
    """
    Create a new branch from an existing branch.

    Args:
        pat: GitHub Personal Access Token.
        owner: Repository owner.
        repo: Repository name.
        branch: Name for the new branch.
        from_branch: Source branch to create from.

    Returns:
        Dict with success, ref, sha, and error.
    """
    if not branch or not branch.strip():
        return {"success": False, "ref": None, "sha": None, "error": "Branch name is required"}

    owner_safe = quote(owner, safe="")
    repo_safe = quote(repo, safe="")
    repo_ref = f"{owner_safe}/{repo_safe}"

    # Get the SHA of the source branch
    ref_result = _github_request(
        "GET", f"/repos/{repo_ref}/git/ref/heads/{from_branch}", pat
    )
    error = _check_pat_and_result(pat, ref_result)
    if error:
        # Try 'master' if 'main' fails
        if from_branch == "main":
            logger.info("Source branch 'main' not found, trying 'master'")
            return create_branch(pat, owner, repo, branch, from_branch="master")
        return {
            "success": False,
            "ref": None,
            "sha": None,
            "error": f"Failed to get source branch '{from_branch}': {error.get('error')}",
        }

    base_sha = ref_result["data"]["object"]["sha"]

    # Create the new branch ref
    create_result = _github_request(
        "POST",
        f"/repos/{repo_ref}/git/refs",
        pat,
        json_data={"ref": f"refs/heads/{branch}", "sha": base_sha},
    )
    error = _check_pat_and_result(pat, create_result)
    if error:
        if create_result.get("status_code") == 422:
            return {
                "success": False,
                "ref": None,
                "sha": None,
                "error": f"Branch '{branch}' already exists.",
            }
        return {
            "success": False,
            "ref": None,
            "sha": None,
            "error": f"Failed to create branch: {error.get('error')}",
        }

    data = create_result.get("data", {})
    logger.info("Created branch '%s' from '%s' in %s/%s", branch, from_branch, owner, repo)
    return {
        "success": True,
        "ref": data.get("ref"),
        "sha": data.get("object", {}).get("sha"),
        "error": None,
    }


def create_pull_request(
    pat: str,
    owner: str,
    repo: str,
    title: str,
    head: str,
    base: str = "main",
    body: str = "",
) -> Dict[str, Any]:
    """
    Create a pull request.

    Args:
        pat: GitHub Personal Access Token.
        owner: Repository owner.
        repo: Repository name.
        title: PR title.
        head: Branch containing changes.
        base: Branch to merge into.
        body: PR description.

    Returns:
        Dict with success, number, html_url, state, and error.
    """
    if not title or not title.strip():
        return {
            "success": False,
            "number": None,
            "html_url": None,
            "state": None,
            "error": "Pull request title is required",
        }

    payload = {
        "title": title,
        "head": head,
        "base": base,
        "body": body,
    }

    result = _github_request(
        "POST",
        f"/repos/{quote(owner, safe='')}/{quote(repo, safe='')}/pulls",
        pat,
        json_data=payload,
    )

    error = _check_pat_and_result(pat, result)
    if error:
        if result.get("status_code") == 422:
            # Parse validation errors
            err_data = result.get("data", {})
            if "errors" in err_data:
                errors = err_data["errors"]
                if isinstance(errors, list) and errors:
                    return {
                        "success": False,
                        "number": None,
                        "html_url": None,
                        "state": None,
                        "error": f"Validation error: {errors[0].get('message', str(errors))}",
                    }
            return {
                "success": False,
                "number": None,
                "html_url": None,
                "state": None,
                "error": f"Invalid PR parameters: {err_data.get('message', 'Unknown validation error')}",
            }
        return {
            "success": False,
            "number": None,
            "html_url": None,
            "state": None,
            "error": error.get("error"),
        }

    data = result.get("data", {})
    logger.info("Created PR #%d: %s", data.get("number", 0), data.get("html_url"))
    return {
        "success": True,
        "number": data.get("number"),
        "html_url": data.get("html_url"),
        "state": data.get("state"),
        "title": data.get("title"),
        "error": None,
    }


# ---------------------------------------------------------------------------
# Code Review
# ---------------------------------------------------------------------------

def get_repo_tree(
    pat: str,
    owner: str,
    repo: str,
    branch: str = "main",
) -> List[Dict[str, Any]]:
    """
    Get file tree of a repository recursively.

    Args:
        pat: GitHub Personal Access Token.
        owner: Repository owner.
        repo: Repository name.
        branch: Branch or tree SHA.

    Returns:
        List of file entries with path, type, size, and sha.
    """
    result = _github_request(
        "GET",
        (
            f"/repos/{quote(owner, safe='')}/{quote(repo, safe='')}"
            f"/git/trees/{quote(branch, safe='')}?recursive=1"
        ),
        pat,
    )

    error = _check_pat_and_result(pat, result)
    if error:
        # Try 'master' if 'main' fails
        if branch == "main":
            logger.info("Branch 'main' not found for tree, trying 'master'")
            return get_repo_tree(pat, owner, repo, branch="master")
        logger.error("Failed to get repo tree: %s", error.get("error"))
        return []

    tree = result.get("data", {}).get("tree", [])
    files = []
    for entry in tree:
        files.append({
            "path": entry.get("path"),
            "type": entry.get("type"),  # 'blob' or 'tree'
            "size": entry.get("size", 0),
            "sha": entry.get("sha"),
            "mode": entry.get("mode"),
        })

    logger.info("Retrieved repo tree: %d entries from %s/%s", len(files), owner, repo)
    return files


def review_repo(
    pat: str,
    owner: str,
    repo: str,
) -> Dict[str, Any]:
    """
    Analyze a repository and provide code review suggestions.

    Fetches key files (README, main source files) and generates
    a structured review report with quality metrics.

    Args:
        pat: GitHub Personal Access Token.
        owner: Repository owner.
        repo: Repository name.

    Returns:
        Dict with:
            - repo_info: Basic repository metadata.
            - file_analysis: Per-file analysis results.
            - suggestions: List of actionable suggestions.
            - quality_score: Overall quality score (0-100).
            - languages: Detected programming languages.
            - structure: Repository structure summary.
    """
    # Get repo info
    repo_info_result = get_repo(pat, owner, repo)
    if not repo_info_result.get("success"):
        return {
            "repo_info": None,
            "file_analysis": [],
            "suggestions": [],
            "quality_score": 0,
            "languages": [],
            "structure": {},
            "error": repo_info_result.get("error", "Failed to fetch repo info"),
        }

    repo_data = repo_info_result["data"]

    # Get file tree
    tree = get_repo_tree(pat, owner, repo, branch=repo_data.get("default_branch", "main"))

    # Categorize files
    source_files = [f for f in tree if f["type"] == "blob"]
    directories = [f for f in tree if f["type"] == "tree"]

    # Find README
    readme_info = {"found": False, "path": None, "word_count": 0}
    for readme_candidate in README_PATTERNS:
        for f in source_files:
            if f["path"].lower() == readme_candidate.lower():
                readme_result = get_file_contents(
                    pat, owner, repo, f["path"],
                    branch=repo_data.get("default_branch", "main"),
                )
                if readme_result.get("success"):
                    content = readme_result.get("content", "")
                    readme_info = {
                        "found": True,
                        "path": f["path"],
                        "word_count": len(content.split()) if content else 0,
                    }
                break
        if readme_info["found"]:
            break

    # Analyze source files by extension
    extension_counts: Dict[str, int] = {}
    total_code_lines = 0
    file_analysis = []

    # Limit analysis to a reasonable number of files
    analysis_limit = 50
    analyzed_files = 0

    for f in source_files:
        _, ext = os.path.splitext(f["path"])
        if ext:
            extension_counts[ext] = extension_counts.get(ext, 0) + 1

        if analyzed_files >= analysis_limit:
            continue

        # Analyze source code files
        if ext in SOURCE_CODE_EXTENSIONS:
            file_result = get_file_contents(
                pat, owner, repo, f["path"],
                branch=repo_data.get("default_branch", "main"),
            )
            if file_result.get("success") and file_result.get("content"):
                content = file_result["content"]
                lines = content.splitlines()
                line_count = len(lines)
                total_code_lines += line_count

                # Basic code quality checks
                issues = []

                # Check for very long lines
                long_lines = [i + 1 for i, line in enumerate(lines) if len(line) > 120]
                if long_lines:
                    issues.append(f"{len(long_lines)} lines exceed 120 characters")

                # Check for TODO/FIXME comments
                todo_count = sum(1 for line in lines if "TODO" in line or "FIXME" in line)
                if todo_count > 0:
                    issues.append(f"{todo_count} TODO/FIXME comments found")

                # Check for trailing whitespace
                trailing_ws = [i + 1 for i, line in enumerate(lines) if line != line.rstrip()]
                if trailing_ws:
                    issues.append(f"{len(trailing_ws)} lines have trailing whitespace")

                # Check for missing final newline
                if content and not content.endswith("\n"):
                    issues.append("Missing final newline")

                # Check for debugger/print statements
                if ext == ".py":
                    debug_lines = [i + 1 for i, line in enumerate(lines)
                                   if re.search(r"\b(print|breakpoint|pdb\.set_trace)\b", line)]
                    if debug_lines:
                        issues.append(f"Potential debug statements on lines: {debug_lines}")

                file_analysis.append({
                    "path": f["path"],
                    "language": ext.lstrip(".").upper(),
                    "lines": line_count,
                    "size": f["size"],
                    "issues": issues,
                    "issue_count": len(issues),
                })
                analyzed_files += 1

    # Generate suggestions
    suggestions = []

    if not readme_info["found"]:
        suggestions.append({
            "severity": "high",
            "category": "documentation",
            "message": "Add a README.md file to describe your project",
        })
    elif readme_info["word_count"] < 50:
        suggestions.append({
            "severity": "medium",
            "category": "documentation",
            "message": "README.md is very brief. Add more details about usage and setup.",
        })

    # Check for common project files
    has_gitignore = any(f["path"] == ".gitignore" for f in source_files)
    has_license = any(f["path"].lower().startswith("license") for f in source_files)
    has_tests = any("test" in f["path"].lower() for f in source_files)
    has_ci = any(f["path"].startswith(".github/workflows/") for f in source_files)
    has_requirements = any(f["path"].lower() in ("requirements.txt", "pyproject.toml", "setup.py", "package.json", "cargo.toml", "gemfile") for f in source_files)

    if not has_gitignore:
        suggestions.append({
            "severity": "medium",
            "category": "configuration",
            "message": "Add a .gitignore file to exclude build artifacts and dependencies",
        })
    if not has_license:
        suggestions.append({
            "severity": "low",
            "category": "documentation",
            "message": "Consider adding a LICENSE file",
        })
    if not has_tests:
        suggestions.append({
            "severity": "high",
            "category": "testing",
            "message": "No test files detected. Consider adding unit tests.",
        })
    if not has_ci:
        suggestions.append({
            "severity": "medium",
            "category": "ci_cd",
            "message": "Consider adding GitHub Actions CI/CD workflows",
        })
    if not has_requirements:
        suggestions.append({
            "severity": "medium",
            "category": "dependencies",
            "message": "No dependency manifest found (requirements.txt, package.json, etc.)",
        })

    # Add per-file suggestions
    for fa in file_analysis:
        for issue in fa["issues"]:
            suggestions.append({
                "severity": "low",
                "category": "code_quality",
                "file": fa["path"],
                "message": issue,
            })

    # Calculate quality score (0-100)
    score = 50  # Base score
    if readme_info["found"]:
        score += 10
        if readme_info["word_count"] > 100:
            score += 5
    if has_gitignore:
        score += 10
    if has_license:
        score += 5
    if has_tests:
        score += 15
    if has_ci:
        score += 10
    if has_requirements:
        score += 5

    # Penalize for issues
    total_issues = sum(fa["issue_count"] for fa in file_analysis)
    score = max(0, min(100, score - min(total_issues, 20)))

    languages = sorted(
        [{"language": ext.lstrip(".").upper(), "files": count}
         for ext, count in extension_counts.items()],
        key=lambda x: x["files"],
        reverse=True,
    )[:10]

    structure = {
        "total_files": len(source_files),
        "total_directories": len(directories),
        "analyzed_files": analyzed_files,
        "total_code_lines": total_code_lines,
        "has_readme": readme_info["found"],
        "has_gitignore": has_gitignore,
        "has_license": has_license,
        "has_tests": has_tests,
        "has_ci": has_ci,
        "has_dependencies": has_requirements,
    }

    logger.info(
        "Completed repo review for %s/%s. Quality score: %d/100, Suggestions: %d",
        owner, repo, score, len(suggestions),
    )

    return {
        "repo_info": {
            "name": repo_data.get("name"),
            "full_name": repo_data.get("full_name"),
            "description": repo_data.get("description"),
            "language": repo_data.get("language"),
            "stars": repo_data.get("stars"),
            "forks": repo_data.get("forks"),
            "open_issues": repo_data.get("open_issues"),
            "private": repo_data.get("private"),
            "html_url": repo_data.get("html_url"),
            "default_branch": repo_data.get("default_branch"),
            "license": repo_data.get("license"),
        },
        "file_analysis": file_analysis,
        "suggestions": suggestions,
        "quality_score": score,
        "languages": languages,
        "structure": structure,
        "error": None,
    }


# ---------------------------------------------------------------------------
# GitHub Integration Functions
# ---------------------------------------------------------------------------

def push_project(
    pat: str,
    owner: str,
    repo_name: str,
    project_files: List[Dict[str, str]],
    description: str = "",
    private: bool = False,
) -> Dict[str, Any]:
    """
    One-click: create repo + push all project files.

    Args:
        pat: GitHub Personal Access Token.
        owner: Repository owner (must match authenticated user).
        repo_name: Name for the new repository.
        project_files: List of dicts with 'path' and 'content' keys.
        description: Repository description.
        private: Whether the repo should be private.

    Returns:
        Dict with:
            - success (bool)
            - repo_url (str)
            - files_pushed (int)
            - commit_sha (str)
            - error (str)
    """
    if not project_files:
        return {
            "success": False,
            "repo_url": None,
            "files_pushed": 0,
            "commit_sha": None,
            "error": "No project files provided",
        }

    # Step 1: Create the repository
    logger.info("Creating repository '%s' for project push", repo_name)
    create_result = create_repo(
        pat=pat,
        name=repo_name,
        description=description,
        private=private,
        auto_init=True,
    )

    if not create_result.get("success"):
        # Check if repo already exists
        if "already exists" in (create_result.get("error") or "").lower():
            logger.info("Repository already exists, proceeding with file push")
            existing = get_repo(pat, owner, repo_name)
            if existing.get("success"):
                create_result["full_name"] = existing["data"]["full_name"]
                create_result["html_url"] = existing["data"]["html_url"]
            else:
                return {
                    "success": False,
                    "repo_url": None,
                    "files_pushed": 0,
                    "commit_sha": None,
                    "error": f"Repository exists but cannot access it: {existing.get('error')}",
                }
        else:
            return {
                "success": False,
                "repo_url": None,
                "files_pushed": 0,
                "commit_sha": None,
                "error": f"Failed to create repository: {create_result.get('error')}",
            }

    # Small delay to ensure repo is fully initialized
    time.sleep(1.5)

    # Step 2: Push all files
    logger.info("Pushing %d files to %s", len(project_files), create_result.get("full_name"))
    push_result = push_files(
        pat=pat,
        owner=owner,
        repo=repo_name,
        files=project_files,
        message=f"Initialize project: {repo_name}",
    )

    if not push_result.get("success"):
        return {
            "success": False,
            "repo_url": create_result.get("html_url"),
            "files_pushed": push_result.get("files_pushed", 0),
            "commit_sha": push_result.get("commit_sha"),
            "error": f"Repository created but file push failed: {push_result.get('error')}",
        }

    logger.info(
        "Successfully pushed project '%s' with %d files to %s",
        repo_name, push_result["files_pushed"], create_result["html_url"],
    )
    return {
        "success": True,
        "repo_url": create_result["html_url"],
        "files_pushed": push_result["files_pushed"],
        "commit_sha": push_result["commit_sha"],
        "error": None,
    }


def import_repo_for_review(
    pat: str,
    owner: str,
    repo: str,
) -> Dict[str, Any]:
    """
    Import a GitHub repo and prepare for code review.

    Fetches README and main source files for analysis.

    Args:
        pat: GitHub Personal Access Token.
        owner: Repository owner.
        repo: Repository name.

    Returns:
        Dict with:
            - files: List of fetched file contents.
            - languages: Detected programming languages.
            - structure: Repository structure info.
            - ready_for_review: Whether enough files were fetched.
            - error: Error message if failed.
    """
    # Get repo info first
    repo_info = get_repo(pat, owner, repo)
    if not repo_info.get("success"):
        return {
            "files": [],
            "languages": [],
            "structure": {},
            "ready_for_review": False,
            "error": repo_info.get("error", "Failed to fetch repository"),
        }

    repo_data = repo_info["data"]
    default_branch = repo_data.get("default_branch", "main")

    # Get file tree
    tree = get_repo_tree(pat, owner, repo, branch=default_branch)
    if not tree:
        return {
            "files": [],
            "languages": [],
            "structure": {},
            "ready_for_review": False,
            "error": "Failed to fetch repository file tree",
        }

    source_files = [f for f in tree if f["type"] == "blob"]

    # Identify languages
    extension_counts: Dict[str, int] = {}
    for f in source_files:
        _, ext = os.path.splitext(f["path"])
        if ext:
            extension_counts[ext] = extension_counts.get(ext, 0) + 1

    languages = sorted(
        [{"language": ext.lstrip(".").upper(), "files": count}
         for ext, count in extension_counts.items()],
        key=lambda x: x["files"],
        reverse=True,
    )

    # Fetch README
    files_fetched = []
    readme_fetched = False

    for readme_candidate in README_PATTERNS:
        readme_result = get_file_contents(pat, owner, repo, readme_candidate, branch=default_branch)
        if readme_result.get("success") and not readme_result.get("is_directory"):
            files_fetched.append({
                "path": readme_candidate,
                "content": readme_result["content"],
                "type": "readme",
            })
            readme_fetched = True
            break

    # Fetch key source files (up to 20)
    source_files_to_fetch = [
        f for f in source_files
        if os.path.splitext(f["path"])[1] in SOURCE_CODE_EXTENSIONS
    ][:20]

    for f in source_files_to_fetch:
        file_result = get_file_contents(pat, owner, repo, f["path"], branch=default_branch)
        if file_result.get("success") and file_result.get("content"):
            files_fetched.append({
                "path": f["path"],
                "content": file_result["content"],
                "type": "source",
                "size": f["size"],
            })

    # Fetch dependency manifests
    dep_manifests = [
        "requirements.txt", "pyproject.toml", "setup.py", "setup.cfg",
        "Pipfile", "poetry.lock",
        "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
        "Gemfile", "Gemfile.lock",
        "Cargo.toml", "Cargo.lock",
        "go.mod", "go.sum",
        "pom.xml", "build.gradle",
        "composer.json", "composer.lock",
    ]

    for dep_file in dep_manifests:
        dep_result = get_file_contents(pat, owner, repo, dep_file, branch=default_branch)
        if dep_result.get("success") and dep_result.get("content"):
            files_fetched.append({
                "path": dep_file,
                "content": dep_result["content"],
                "type": "dependencies",
            })

    structure = {
        "total_files": len(source_files),
        "total_directories": len([f for f in tree if f["type"] == "tree"]),
        "source_files_analyzed": len(source_files_to_fetch),
        "files_fetched": len(files_fetched),
        "has_readme": readme_fetched,
        "primary_language": repo_data.get("language"),
        "default_branch": default_branch,
    }

    ready_for_review = readme_fetched and len(source_files_to_fetch) > 0

    logger.info(
        "Imported %s/%s for review: %d files fetched, ready=%s",
        owner, repo, len(files_fetched), ready_for_review,
    )

    return {
        "files": files_fetched,
        "languages": languages,
        "structure": structure,
        "ready_for_review": ready_for_review,
        "error": None,
    }


# ---------------------------------------------------------------------------
# Utility / Helper Functions
# ---------------------------------------------------------------------------

def check_rate_limit(pat: str) -> Dict[str, Any]:
    """
    Check current GitHub API rate limit status.

    Args:
        pat: GitHub Personal Access Token.

    Returns:
        Dict with limit, remaining, reset timestamp, and usage percentage.
    """
    result = _github_request("GET", "/rate_limit", pat)
    if not result.get("success"):
        return {
            "success": False,
            "limit": 0,
            "remaining": 0,
            "reset": None,
            "usage_percent": 100,
            "error": result.get("error"),
        }

    data = result.get("data", {})
    core = data.get("resources", {}).get("core", {})
    limit = core.get("limit", 0)
    remaining = core.get("remaining", 0)
    reset_ts = core.get("reset", 0)

    usage = ((limit - remaining) / limit * 100) if limit > 0 else 0

    return {
        "success": True,
        "limit": limit,
        "remaining": remaining,
        "reset": datetime.fromtimestamp(reset_ts, tz=timezone.utc).isoformat() if reset_ts else None,
        "usage_percent": round(usage, 1),
        "error": None,
    }


def list_branches(pat: str, owner: str, repo: str, page: int = 1, per_page: int = 30) -> List[Dict[str, Any]]:
    """
    List branches in a repository.

    Args:
        pat: GitHub Personal Access Token.
        owner: Repository owner.
        repo: Repository name.
        page: Page number.
        per_page: Results per page.

    Returns:
        List of branch dicts with name, sha, and protected status.
    """
    result = _github_request(
        "GET",
        f"/repos/{quote(owner, safe='')}/{quote(repo, safe='')}/branches",
        pat,
        params={"page": page, "per_page": per_page},
    )

    error = _check_pat_and_result(pat, result)
    if error:
        logger.error("Failed to list branches: %s", error.get("error"))
        return []

    branches = []
    for b in result.get("data", []):
        branches.append({
            "name": b.get("name"),
            "sha": b.get("commit", {}).get("sha"),
            "protected": b.get("protected", False),
        })
    return branches


def get_latest_commit(
    pat: str,
    owner: str,
    repo: str,
    branch: str = "main",
) -> Dict[str, Any]:
    """
    Get the latest commit on a branch.

    Args:
        pat: GitHub Personal Access Token.
        owner: Repository owner.
        repo: Repository name.
        branch: Branch name.

    Returns:
        Dict with sha, message, author, date, and url.
    """
    result = _github_request(
        "GET",
        f"/repos/{quote(owner, safe='')}/{quote(repo, safe='')}/commits/{quote(branch, safe='')}",
        pat,
    )

    error = _check_pat_and_result(pat, result)
    if error:
        if branch == "main":
            return get_latest_commit(pat, owner, repo, branch="master")
        return {"success": False, "error": error.get("error"), "sha": None}

    data = result.get("data", {})
    commit = data.get("commit", {})
    author = commit.get("author", {})

    return {
        "success": True,
        "error": None,
        "sha": data.get("sha"),
        "message": commit.get("message"),
        "author": author.get("name"),
        "email": author.get("email"),
        "date": author.get("date"),
        "url": data.get("html_url"),
    }


# ---------------------------------------------------------------------------
# Module validation
# ---------------------------------------------------------------------------

__all__ = [
    # Authentication
    "auth_with_pat",
    "get_auth_headers",
    # Repository Management
    "list_repos",
    "create_repo",
    "get_repo",
    "delete_repo",
    # Code Operations
    "push_files",
    "create_branch",
    "create_pull_request",
    "get_file_contents",
    # Code Review
    "get_repo_tree",
    "review_repo",
    # Integration
    "push_project",
    "import_repo_for_review",
    # Utilities
    "check_rate_limit",
    "list_branches",
    "get_latest_commit",
]
