"""Loopback-only client for an optional Laya System One sidecar."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlsplit


def predict(state: Any, questions: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    endpoint = config.get("endpoint")
    parsed = urlsplit(endpoint) if isinstance(endpoint, str) else None
    if (
        parsed is None
        or parsed.scheme != "http"
        or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Laya sidecar endpoint must use a loopback HTTP address")
    envelope = {"state": state, "questions": questions}
    for key in ("max_len", "head_max_len"):
        if isinstance(config.get(key), int):
            envelope[key] = config[key]
    if config.get("route_mode") == "explicit":
        envelope["model"] = config.get("explicit_model") or config.get("model", "english")
    payload = json.dumps(envelope, ensure_ascii=False).encode()

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    request = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        with opener.open(request, timeout=float(config.get("timeout_seconds", 60))) as response:
            body = response.read(512_001)
            if len(body) > 512_000:
                raise RuntimeError("Laya sidecar response exceeds the 512 KB limit")
        result = json.loads(body)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Laya sidecar failed (HTTP status {exc.code})") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError("Laya sidecar request failed") from exc
    if not isinstance(result, dict) or not isinstance(result.get("answers"), dict):
        raise RuntimeError("Laya sidecar returned an invalid System One response")
    return result
