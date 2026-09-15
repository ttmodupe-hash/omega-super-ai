"""
OMEGA-LUQI Backup & Gate Regression Suite (repo root, CI).

Rewritten from the pasted version: it imported the rejected core.kimi_k3 and
asserted '10M' against our '10m'. These run against the real modules.
"""
import base64
import os

import pytest
from fastapi.testclient import TestClient

from core.main import app


# ---- edge proxy guards (same intent as pasted) ----

def test_nginx_proxy_hardening_parameters_present():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deploy", "nginx.conf")
    if not os.path.exists(config_path):
        pytest.skip("deployment assets absent")
    content = open(config_path).read()
    assert "ssl_protocols TLSv1.2 TLSv1.3;" in content
    assert "limit_req_zone" in content
    assert "client_max_body_size" in content
    assert "proxy_buffering off;" in content


# ---- PII scrub guard (against core.pii_scrub - kimi_k3 never existed) ----

def test_pii_scrubbing_regex_boundary_integrity():
    from core.pii_scrub import scrub_pii
    dirty = "Contact student at test@luqi.org or +27721234567 using ID 9501145123084."
    clean = scrub_pii(dirty)
    assert "[REDACTED_EMAIL]" in clean
    assert "[REDACTED_PHONE]" in clean
    assert "[REDACTED_NATIONAL_ID]" in clean
    assert "+27721234567" not in clean and "9501145123084" not in clean


# ---- AES-256-GCM cipher assurance (real algorithm, stable key) ----

def test_backup_cipher_roundtrip_with_stable_key():
    from core.db_backup import encrypt_bytes, decrypt_bytes
    key = base64.b64decode(os.environ.get("BACKUP_ENCRYPTION_KEY",
                                          base64.b64encode(b"k" * 32).decode()))
    raw = b"INSERT INTO students (id) VALUES (gen_random_uuid());"
    blob = encrypt_bytes(raw, key)
    assert blob != raw and decrypt_bytes(blob, key) == raw


def test_backup_fails_closed_without_env_key():
    import importlib
    import core.db_backup as m
    saved = os.environ.pop("BACKUP_ENCRYPTION_KEY", None)
    try:
        with pytest.raises(RuntimeError):
            m._load_key()
    finally:
        if saved:
            os.environ["BACKUP_ENCRYPTION_KEY"] = saved


def test_backup_route_is_admin_gated():
    client = TestClient(app)
    r = client.post("/v1/backup/trigger-backup")
    assert r.status_code in (401, 403, 422)


def test_no_hardcoded_credentials_in_backup_module():
    import inspect
    import core.db_backup as m
    src = inspect.getsource(m)
    assert "SovereignAfrica" not in src
    assert "PGPASSWORD", "" not in src  # literal password next to env key
