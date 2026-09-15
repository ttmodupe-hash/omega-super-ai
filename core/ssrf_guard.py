"""
OMEGA-LUQI Automation SSRF Guard

The automation engine executes arbitrary user-supplied endpoints. Without a
guard, any authenticated user could make the server reach cloud metadata
services (169.254.169.254), loopback admin panels, or internal network
services and exfiltrate data through the response channel.

Defense layers:
  1. Scheme allowlist (http/https only)
  2. Optional host allowlist via AUTOMATION_ALLOWED_HOSTS (comma-separated)
  3. DNS resolution + private/loopback/link-local/reserved range blocking
     (covers literal IPs AND hostnames that resolve to internal addresses)

Note: DNS rebinding (TOCTOU between this check and the request) is mitigated
in practice by short timeouts but cannot be fully eliminated for arbitrary
hostnames - the host allowlist is the strong control for sensitive networks.
"""
import os
import socket
import ipaddress
from urllib.parse import urlparse

from fastapi import HTTPException

_BLOCKED_NETWORKS = [
    ipaddress.ip_network(c) for c in (
        "127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
        "169.254.0.0/16", "0.0.0.0/8",
        "::1/128", "fc00::/7", "fe80::/10", "::/128",
    )
]
_ALLOWED_SCHEMES = {"http", "https"}


def assert_automation_url_allowed(url: str) -> None:
    """Raise 400/403 when the endpoint is not safe for server-side fetching."""
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES or not parsed.hostname:
        raise HTTPException(status_code=400, detail="Automation steps require a valid http(s) endpoint.")

    allowlist = [h.strip() for h in os.getenv("AUTOMATION_ALLOWED_HOSTS", "").split(",") if h.strip()]
    if allowlist and parsed.hostname not in allowlist:
        raise HTTPException(status_code=403, detail="Endpoint host not in AUTOMATION_ALLOWED_HOSTS.")

    try:
        resolved = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="Endpoint hostname does not resolve.")

    for info in resolved:
        ip = ipaddress.ip_address(info[4][0])
        if any(ip in net for net in _BLOCKED_NETWORKS):
            raise HTTPException(
                status_code=403,
                detail="SSRF guard: endpoint resolves to a non-public address - refused.",
            )
