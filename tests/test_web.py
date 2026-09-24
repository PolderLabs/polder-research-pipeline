"""Tests for the local control panel's configuration and data boundary."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml

from polder_research.web import (
    _is_loopback_host,
    _patch_config,
    _save_secret,
    _secret_status,
    _validate_config,
    _write_config,
    dashboard_payload,
)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    shutil.copytree(Path(__file__).parents[1] / "schemas", tmp_path / "schemas")
    shutil.copytree(Path(__file__).parents[1] / "knowledge-base", tmp_path / "knowledge-base")
    return tmp_path


def test_dashboard_uses_real_empty_local_state(repo: Path):
    payload = dashboard_payload(repo)

    assert payload["system"]["config_valid"] is True
    assert payload["providers"]["selected"] == "rules"
    assert payload["research"]["corpus"]["sources"] == 0
    assert payload["research"]["corpus"]["classifications"] == 0
    assert len(payload["research"]["activity_30d"]) == 30
    assert payload["research"]["malformed_count"] == 0


def test_basic_settings_patch_preserves_comments_and_uses_revision(repo: Path):
    path = repo / "knowledge-base" / "research.config.yaml"
    raw = path.read_text()
    raw = raw.replace(
        "provider: rules # rules | jev | laya; switch here",
        "provider: rules # preserve this comment",
    )
    path.write_text(raw)

    result = _patch_config(
        repo,
        __import__("hashlib").sha256(raw.encode()).hexdigest(),
        {
            "classification.provider": "laya",
            "classification.minimum_confidence": 0.81,
        },
    )

    updated = path.read_text()
    assert result["config"]["classification"]["provider"] == "laya"
    assert "# preserve this comment" in updated
    with pytest.raises(RuntimeError, match="changed since it was loaded"):
        _patch_config(repo, "stale", {"classification.provider": "rules"})


def test_advanced_config_save_validates_before_atomic_write(repo: Path):
    path = repo / "knowledge-base" / "research.config.yaml"
    raw = path.read_text()
    revision = __import__("hashlib").sha256(raw.encode()).hexdigest()
    with pytest.raises(ValueError, match="minimum_confidence"):
        _write_config(
            repo, raw.replace("minimum_confidence: 0.75", "minimum_confidence: 2"), revision
        )
    assert path.read_text() == raw


def test_secret_store_is_owner_only_and_does_not_echo_secret(repo: Path, monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    secret = "ts_test_value_never_returned"
    _save_secret(repo, "TYPESAFE_API_KEY", secret)

    status = _secret_status(
        repo, yaml.safe_load((repo / "knowledge-base/research.config.yaml").read_text())
    )
    secret_path = repo / ".research" / "web-secrets.json"
    assert status == {"configured": True, "source": "local vault", "key_env": "TYPESAFE_API_KEY"}
    assert secret_path.stat().st_mode & 0o777 == 0o600
    assert json.loads(secret_path.read_text())["TYPESAFE_API_KEY"] == secret
    assert secret not in json.dumps(status)


def test_host_guard_accepts_only_loopback_hosts():
    assert _is_loopback_host("127.0.0.1:8765", 8765)
    assert _is_loopback_host("localhost", 8765)
    assert not _is_loopback_host("research.example", 8765)
    assert not _is_loopback_host("127.0.0.1:8766", 8765)


def test_yaml_editor_rejects_credentials_inside_config(repo: Path):
    config = yaml.safe_load((repo / "knowledge-base/research.config.yaml").read_text())
    config["classification"]["jev"]["api_key"] = "must-not-be-stored"

    with pytest.raises(ValueError, match="local secret store"):
        _validate_config(config)


def test_http_server_serves_dashboard_and_blocks_cross_origin_writes(repo: Path):
    import threading
    import urllib.error
    import urllib.request

    from polder_research.web import create_server

    server = create_server(repo, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with urllib.request.urlopen(base + "/") as response:
            assert response.status == 200
            assert b"Research control room" in response.read()
            assert response.headers["Content-Security-Policy"]
        with urllib.request.urlopen(base + "/api/overview") as response:
            payload = json.loads(response.read())
            assert payload["research"]["corpus"]["sources"] == 0
        request = urllib.request.Request(
            base + "/api/config/basic",
            data=b'{"revision":"irrelevant","updates":{"classification.provider":"jev"}}',
            headers={"Content-Type": "application/json", "Origin": "https://attacker.invalid"},
            method="PATCH",
        )
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(request)
        assert error.value.code == 403
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
