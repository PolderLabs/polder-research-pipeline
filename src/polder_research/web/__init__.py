"""Loopback-only research control panel and read-only analytics API."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import tempfile
import threading
import urllib.parse
from collections import Counter
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from ..classification import preload_laya_model
from ..maintenance import build_health, evaluate_maintenance
from ..paths import REPO_ROOT
from ..workflow import _read_records, build_state

_CONFIG_LOCK = threading.RLock()
_DOWNLOAD_LOCK = threading.Lock()
_DOWNLOAD: dict[str, Any] = {
    "status": "idle",
    "model": None,
    "started_at": None,
    "finished_at": None,
    "error": None,
}
_MAX_BODY = 1_000_000
_ALLOWED_MODELS = {"english", "multilingual", "typed-decisions"}
_BASIC_PATHS = {
    ("classification", "enabled"),
    ("classification", "provider"),
    ("classification", "minimum_confidence"),
    ("classification", "max_input_chars"),
    ("classification", "jev", "model"),
    ("classification", "jev", "timeout_seconds"),
    ("classification", "jev", "api_key_env"),
    ("classification", "laya", "model"),
    ("classification", "laya", "device"),
}
_MODEL_REPOS = {
    "english": "convaiinnovations/laya",
    "multilingual": "convaiinnovations/laya-multilingual",
    "typed-decisions": "convaiinnovations/laya-typed-decisions",
}


def _config_path(root: Path) -> Path:
    return root / "knowledge-base" / "research.config.yaml"


def _config_text(root: Path) -> str:
    return _config_path(root).read_text(encoding="utf-8")


def _revision(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _secret_path(root: Path) -> Path:
    return root / ".research" / "web-secrets.json"


def _secret_status(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    key_env = config.get("classification", {}).get("jev", {}).get("api_key_env", "TYPESAFE_API_KEY")
    env_set = bool(os.environ.get(key_env))
    file_set = False
    try:
        values = json.loads(_secret_path(root).read_text(encoding="utf-8"))
        file_set = isinstance(values, dict) and bool(values.get(key_env))
    except (OSError, json.JSONDecodeError):
        pass
    return {
        "configured": env_set or file_set,
        "source": "environment" if env_set else "local vault" if file_set else "missing",
        "key_env": key_env,
    }


def _write_config(root: Path, raw: str, expected_revision: str) -> dict[str, Any]:
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > _MAX_BODY:
        raise ValueError("Configuration must be valid YAML under 1 MB")
    with _CONFIG_LOCK:
        path = _config_path(root)
        current = path.read_text(encoding="utf-8")
        if _revision(current) != expected_revision:
            raise RuntimeError("Configuration changed since it was loaded. Reload before saving.")
        try:
            parsed = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid YAML: {exc}") from exc
        _validate_config(parsed)
        _atomic_text(
            path, raw if raw.endswith("\n") else raw + "\n", mode=path.stat().st_mode & 0o777
        )
        return {"revision": _revision(_config_text(root)), "config": parsed}


def _patch_config(root: Path, expected_revision: str, updates: Any) -> dict[str, Any]:
    if not isinstance(updates, dict) or not updates or len(updates) > len(_BASIC_PATHS):
        raise ValueError("Provide one or more supported basic setting updates")
    with _CONFIG_LOCK:
        path = _config_path(root)
        raw = path.read_text(encoding="utf-8")
        if _revision(raw) != expected_revision:
            raise RuntimeError("Configuration changed since it was loaded. Reload before saving.")
        edits: list[tuple[int, int, str]] = []
        for dotted_path, value in updates.items():
            key_path = tuple(str(dotted_path).split("."))
            if key_path not in _BASIC_PATHS:
                raise ValueError(f"Unsupported basic setting: {dotted_path}")
            node = yaml.compose(raw)
            for key in key_path:
                if not isinstance(node, yaml.MappingNode):
                    raise ValueError(
                        f"Cannot update {dotted_path}: configuration structure is invalid"
                    )
                pair = next((pair for pair in node.value if pair[0].value == key), None)
                if pair is None:
                    raise ValueError(f"Configuration key is missing: {dotted_path}")
                node = pair[1]
            if not isinstance(node, yaml.ScalarNode):
                raise ValueError(f"Basic setting is not a scalar: {dotted_path}")
            if isinstance(value, str):
                scalar = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, bool):
                scalar = "true" if value else "false"
            elif isinstance(value, int | float) and not isinstance(value, bool):
                scalar = str(value)
            else:
                raise ValueError(
                    f"Basic setting must be a string, number, or boolean: {dotted_path}"
                )
            edits.append((node.start_mark.index, node.end_mark.index, scalar))
        for start, end, scalar in sorted(edits, reverse=True):
            raw = raw[:start] + scalar + raw[end:]
        parsed = yaml.safe_load(raw)
        _validate_config(parsed)
        _atomic_text(
            path, raw if raw.endswith("\n") else raw + "\n", mode=path.stat().st_mode & 0o777
        )
        return {"revision": _revision(raw), "config": parsed}


def _validate_config(config: Any) -> None:
    if not isinstance(config, dict):
        raise ValueError("Configuration must be a YAML mapping")

    secret_fields = {
        "api_key",
        "api_key_value",
        "access_token",
        "bearer_token",
        "client_secret",
        "credential",
        "password",
        "private_key",
    }

    def reject_inline_secrets(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                normalized = str(key).casefold()
                if normalized in secret_fields or normalized.endswith(
                    ("_secret", "_token", "_password", "_credential")
                ):
                    raise ValueError(
                        "Credentials belong in the local secret store, not research.config.yaml"
                    )
                reject_inline_secrets(child)
        elif isinstance(value, list):
            for child in value:
                reject_inline_secrets(child)

    reject_inline_secrets(config)
    classification = config.get("classification", {})
    if not isinstance(classification, dict):
        raise ValueError("classification must be a mapping")
    provider = classification.get("provider", "rules")
    if provider not in {"rules", "jev", "laya"}:
        raise ValueError("classification.provider must be rules, jev, or laya")
    confidence = classification.get("minimum_confidence", 0.75)
    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, int | float)
        or not 0 <= confidence <= 1
    ):
        raise ValueError("classification.minimum_confidence must be between 0 and 1")
    input_limit = classification.get("max_input_chars", 12000)
    if (
        isinstance(input_limit, bool)
        or not isinstance(input_limit, int)
        or not 1 <= input_limit <= 500_000
    ):
        raise ValueError("classification.max_input_chars must be an integer from 1 to 500000")
    jev = classification.get("jev", {})
    if not isinstance(jev, dict):
        raise ValueError("classification.jev must be a mapping")
    if (
        jev.get("endpoint", "https://api.typesafe.ai/v1/systemone")
        != "https://api.typesafe.ai/v1/systemone"
    ):
        raise ValueError("Jev endpoint is fixed to the official TypeSafe API")
    timeout = jev.get("timeout_seconds", 30)
    if isinstance(timeout, bool) or not isinstance(timeout, int | float) or not 1 <= timeout <= 120:
        raise ValueError("classification.jev.timeout_seconds must be between 1 and 120")
    key_env = jev.get("api_key_env", "TYPESAFE_API_KEY")
    if not isinstance(key_env, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{1,63}", key_env):
        raise ValueError("classification.jev.api_key_env must be a valid environment variable name")
    laya = classification.get("laya", {})
    if not isinstance(laya, dict) or laya.get("model", "multilingual") not in _ALLOWED_MODELS:
        raise ValueError(
            "classification.laya.model must be english, multilingual, or typed-decisions"
        )
    if laya.get("device", "auto") not in {"auto", "cpu", "cuda", "mps"}:
        raise ValueError("classification.laya.device must be auto, cpu, cuda, or mps")
    if not isinstance(classification.get("enabled", True), bool):
        raise ValueError("classification.enabled must be a boolean")
    jev_model = jev.get("model", "jev-latest")
    if not isinstance(jev_model, str) or not re.fullmatch(r"[a-zA-Z0-9._-]{1,80}", jev_model):
        raise ValueError("classification.jev.model contains unsupported characters")
    taxonomy = classification.get("taxonomy", {})
    if not isinstance(taxonomy, dict):
        raise ValueError("classification.taxonomy must be a mapping")
    for dimension in ("categories", "tags"):
        labels = taxonomy.get(dimension, {})
        if not isinstance(labels, dict):
            raise ValueError(f"classification.taxonomy.{dimension} must be a mapping")
        for key, item in labels.items():
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", str(key)) or not isinstance(
                item, dict
            ):
                raise ValueError(f"Invalid taxonomy entry: {key!r}")
            if not isinstance(item.get("description"), str) or not item["description"].strip():
                raise ValueError(f"Taxonomy entry {key!r} requires a description")
            keywords = item.get("keywords", [])
            if not isinstance(keywords, list) or not all(
                isinstance(word, str) for word in keywords
            ):
                raise ValueError(f"Taxonomy entry {key!r} keywords must be a list of strings")


def _atomic_text(path: Path, content: str, *, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def _save_secret(root: Path, key_env: str, secret: str | None) -> None:
    if secret is not None and (
        not isinstance(secret, str) or len(secret) > 2048 or "\n" in secret or "\r" in secret
    ):
        raise ValueError("API key must be a single line under 2048 characters")
    path = _secret_path(root)
    values: dict[str, str] = {}
    try:
        current = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(current, dict):
            values = {str(k): str(v) for k, v in current.items()}
    except (OSError, json.JSONDecodeError):
        pass
    if secret:
        values[key_env] = secret
    else:
        values.pop(key_env, None)
    if values:
        _atomic_text(path, json.dumps(values, indent=2) + "\n", mode=0o600)
    else:
        path.unlink(missing_ok=True)


def _records(root: Path, collection: str, schema_name: str) -> tuple[list[dict[str, Any]], int]:
    directory = root / ".research" / collection
    schema_path = root / "schemas" / f"{schema_name}.schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [], 0
    validator = jsonschema.Draft202012Validator(schema)
    rows: list[dict[str, Any]] = []
    malformed = 0
    for path in sorted(directory.glob("*.json")) if directory.exists() else []:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            malformed += 1
            continue
        if not validator.is_valid(record):
            malformed += 1
            continue
        rows.append(record)
    return rows, malformed


def _provider_health(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    classification = config.get("classification", {})
    provider = classification.get("provider", "rules")
    laya_installed = importlib.util.find_spec("laya") is not None
    model = classification.get("laya", {}).get("model", "multilingual")
    cached = False
    cache_path = None
    if model in _MODEL_REPOS:
        try:
            from huggingface_hub import constants, try_to_load_from_cache

            cached_file = try_to_load_from_cache(_MODEL_REPOS[model], "model.safetensors")
            cached = isinstance(cached_file, str) and Path(cached_file).is_file()
            cache_path = str(constants.HF_HUB_CACHE) if cached else None
        except (ImportError, OSError, ValueError):
            pass
    key = _secret_status(root, classification)
    with _DOWNLOAD_LOCK:
        download = dict(_DOWNLOAD)
    enabled = bool(classification.get("enabled", True))
    laya_ready = laya_installed and (cached or download.get("status") == "ready")
    selected_ready = (
        not enabled
        or provider == "rules"
        or (provider == "jev" and key["configured"])
        or (provider == "laya" and laya_ready)
    )
    return {
        "selected": provider,
        "enabled": enabled,
        "ready": selected_ready,
        "minimum_confidence": classification.get("minimum_confidence", 0.75),
        "taxonomy_version": classification.get("taxonomy", {}).get("version", "1"),
        "typesafe": {"ready": key["configured"], **key},
        "laya": {
            "installed": laya_installed,
            "model": model,
            "device": classification.get("laya", {}).get("device", "auto"),
            "cached": cached,
            "ready": laya_ready,
            "cache_path": cache_path,
            "job": download,
        },
    }


def _analytics(root: Path) -> dict[str, Any]:
    evidence = {}
    malformed = 0
    for name, schema in (
        ("sources", "source"),
        ("segments", "segment"),
        ("claims", "claim"),
        ("entities", "entity"),
        ("gaps", "gap"),
        ("conflicts", "conflict"),
        ("edges", "evidence"),
    ):
        evidence[name], invalid = _records(root, name, schema)
        malformed += invalid
    records, workflow_malformed = _read_records(root)
    malformed += len(workflow_malformed)
    evidence["classifications"] = records["classifications"]
    states = build_state(root)
    operational = build_health(root)
    sources = evidence["sources"]
    classifications = evidence["classifications"]
    topic_counts: Counter[str] = Counter()
    tag_counts: Counter[str] = Counter()
    for collection in evidence.values():
        for record in collection:
            if record.get("topic"):
                topic_counts[str(record["topic"])] += 1
            tag_counts.update(tag for tag in record.get("tags", []) if isinstance(tag, str))
    source_types = Counter(str(source.get("source_type", "unknown")) for source in sources)
    source_statuses = Counter(str(source.get("source_status", "unknown")) for source in sources)
    classification_status = Counter(
        str(item.get("disposition", "unknown")) for item in classifications
    )
    providers = Counter(str(item.get("provider", "unknown")) for item in classifications)
    by_day: dict[str, dict[str, int]] = {}
    today = datetime.now(UTC).date()
    for offset in range(29, -1, -1):
        day = today - timedelta(days=offset)
        by_day[day.isoformat()] = {"sources": 0, "classifications": 0}
    for record, key, field in (
        *((item, "sources", "retrieved_at") for item in sources),
        *((item, "classifications", "created_at") for item in classifications),
    ):
        timestamp = record.get(field)
        if not isinstance(timestamp, str):
            continue
        try:
            day_key = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            continue
        if day_key in by_day:
            by_day[day_key][key] += 1
    method_records = {
        name: len(records.get(name, []))
        for name in (
            "protocols",
            "searches",
            "candidates",
            "screenings",
            "extractions",
            "appraisals",
        )
    }
    research = {
        "corpus": {name: len(items) for name, items in evidence.items()},
        "source_types": dict(sorted(source_types.items())),
        "source_statuses": dict(sorted(source_statuses.items())),
        "topics": dict(sorted(topic_counts.items())),
        "tags": dict(sorted(tag_counts.items())),
        "classifications": {
            "by_disposition": dict(sorted(classification_status.items())),
            "by_provider": dict(sorted(providers.items())),
            "review_required": [
                item["id"]
                for item in classifications
                if item.get("disposition") == "review_required"
            ],
            "failed": [
                item["id"] for item in classifications if item.get("disposition") == "failed"
            ],
        },
        "method_records": method_records,
        "activity_30d": [{"date": day, **counts} for day, counts in by_day.items()],
        "malformed_count": malformed,
        "operational_health": operational,
        "workflow_state": states,
    }
    return research


def dashboard_payload(repository_root: Path | None = None) -> dict[str, Any]:
    root = Path(repository_root or REPO_ROOT).resolve()
    raw = _config_text(root)
    config = yaml.safe_load(raw)
    _validate_config(config)
    disk = shutil.disk_usage(root)
    research = _analytics(root)
    maintenance = evaluate_maintenance(root)
    overall = research["operational_health"]["overall"]
    providers = _provider_health(root, config)
    if research["malformed_count"] or not providers["ready"]:
        overall = "degraded"
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "repository": str(root),
        "system": {
            "health": overall,
            "python": os.sys.version.split()[0],
            "disk_free_bytes": disk.free,
            "disk_total_bytes": disk.total,
            "config_revision": _revision(raw),
            "config_valid": True,
            "maintenance": maintenance,
        },
        "providers": providers,
        "research": research,
    }


def _is_loopback_host(value: str, port: int) -> bool:
    try:
        parsed = urllib.parse.urlsplit(f"//{value}")
        hostname = (parsed.hostname or "").lower()
        requested_port = parsed.port
    except ValueError:
        return False
    if hostname not in {"localhost", "127.0.0.1", "::1"}:
        return False
    return requested_port in {None, port}


class _ControlHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def create_server(repository_root: Path | None = None, *, port: int = 8765) -> _ControlHTTPServer:
    root = Path(repository_root or REPO_ROOT).resolve()
    host = "127.0.0.1"

    class Handler(BaseHTTPRequestHandler):
        server_version = "PolderControl/1"
        sys_version = ""

        def log_message(self, fmt: str, *args: Any) -> None:
            # Do not log request bodies, query strings, API keys, or user research.
            safe_path = urllib.parse.urlsplit(self.path).path
            print(f"polder-control {self.client_address[0]} {self.command} {safe_path}")

        @property
        def root(self) -> Path:
            return self.server.repository_root  # type: ignore[attr-defined]

        def _headers(
            self, status: int, content_type: str = "application/json; charset=utf-8"
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cache-Control", "no-store")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
            )
            self.end_headers()

        def _json(self, status: int, payload: Any) -> None:
            data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
            self._headers(status)
            self.wfile.write(data)

        def _host_ok(self) -> bool:
            return _is_loopback_host(self.headers.get("Host", ""), self.server.server_port)

        def _origin_ok(self) -> bool:
            origin = self.headers.get("Origin")
            if origin and not _is_loopback_host(
                urllib.parse.urlsplit(origin).netloc, self.server.server_port
            ):
                return False
            site = self.headers.get("Sec-Fetch-Site", "")
            return site in {"", "none", "same-origin"}

        def _body(self) -> bytes:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError as exc:
                raise ValueError("Invalid Content-Length") from exc
            if length < 0 or length > _MAX_BODY:
                raise ValueError("Request body exceeds 1 MB")
            return self.rfile.read(length)

        def _api(self, method: str, path: str) -> bool:
            try:
                if method == "GET" and path == "/api/overview":
                    self._json(200, dashboard_payload(self.root))
                    return True
                if method == "GET" and path == "/api/config":
                    raw = _config_text(self.root)
                    config = yaml.safe_load(raw)
                    self._json(
                        200,
                        {
                            "config": config,
                            "config_yaml": raw,
                            "revision": _revision(raw),
                            "provider": _provider_health(self.root, config),
                        },
                    )
                    return True
                if method == "GET" and path == "/api/laya/status":
                    config = yaml.safe_load(_config_text(self.root))
                    self._json(200, _provider_health(self.root, config)["laya"])
                    return True
                if method == "PUT" and path == "/api/config":
                    payload = json.loads(self._body())
                    result = _write_config(
                        self.root, payload.get("config_yaml"), payload.get("revision", "")
                    )
                    self._json(200, {"revision": result["revision"], "saved": True})
                    return True
                if method == "PATCH" and path == "/api/config/basic":
                    payload = json.loads(self._body())
                    result = _patch_config(
                        self.root, payload.get("revision", ""), payload.get("updates")
                    )
                    self._json(200, {"revision": result["revision"], "saved": True})
                    return True
                if method == "PUT" and path == "/api/secrets/typesafe":
                    payload = json.loads(self._body())
                    config = yaml.safe_load(_config_text(self.root))
                    key_env = (
                        config.get("classification", {})
                        .get("jev", {})
                        .get("api_key_env", "TYPESAFE_API_KEY")
                    )
                    _save_secret(self.root, key_env, payload.get("secret"))
                    self._json(
                        200,
                        {
                            "saved": bool(payload.get("secret")),
                            "status": _secret_status(self.root, config),
                        },
                    )
                    return True
                if method == "POST" and path == "/api/laya/download":
                    self._body()
                    _start_laya_download(self.root)
                    with _DOWNLOAD_LOCK:
                        status = dict(_DOWNLOAD)
                    self._json(202, {"accepted": True, "status": status})
                    return True
                if method == "POST" and path == "/api/providers/test":
                    payload = json.loads(self._body())
                    result = _test_provider(self.root, str(payload.get("provider", "")))
                    self._json(200 if result["ok"] else 503, result)
                    return True
                return False
            except RuntimeError as exc:
                self._json(409, {"error": str(exc)})
                return True
            except (ValueError, json.JSONDecodeError, UnicodeError) as exc:
                self._json(400, {"error": str(exc)})
                return True
            except Exception:
                self._json(
                    500,
                    {"error": "The request could not be completed. Check the local server log."},
                )
                return True

        def do_GET(self) -> None:  # noqa: N802
            if not self._host_ok():
                self._json(403, {"error": "Use the local Polder address shown by the server."})
                return
            path = urllib.parse.urlsplit(self.path).path
            if self._api("GET", path):
                return
            static = Path(__file__).parent / "static"
            names = {"/": "index.html", "/app.css": "app.css", "/app.js": "app.js"}
            name = names.get(path)
            if name:
                content_types = {
                    "index.html": "text/html; charset=utf-8",
                    "app.css": "text/css; charset=utf-8",
                    "app.js": "text/javascript; charset=utf-8",
                }
                try:
                    data = (static / name).read_bytes()
                except OSError:
                    self._json(
                        500, {"error": "Dashboard assets are missing from this installation."}
                    )
                    return
                self._headers(200, content_types[name])
                self.wfile.write(data)
                return
            self._json(404, {"error": "Not found"})

        def do_PUT(self) -> None:  # noqa: N802
            if not self._host_ok() or not self._origin_ok():
                self._json(403, {"error": "Cross-origin configuration writes are blocked."})
                return
            if not self._api("PUT", urllib.parse.urlsplit(self.path).path):
                self._json(404, {"error": "Not found"})

        def do_POST(self) -> None:  # noqa: N802
            if not self._host_ok() or not self._origin_ok():
                self._json(403, {"error": "Cross-origin actions are blocked."})
                return
            if not self._api("POST", urllib.parse.urlsplit(self.path).path):
                self._json(404, {"error": "Not found"})

        def do_PATCH(self) -> None:  # noqa: N802
            if not self._host_ok() or not self._origin_ok():
                self._json(403, {"error": "Cross-origin configuration writes are blocked."})
                return
            if not self._api("PATCH", urllib.parse.urlsplit(self.path).path):
                self._json(404, {"error": "Not found"})

    server = _ControlHTTPServer((host, port), Handler)
    server.repository_root = root  # type: ignore[attr-defined]
    return server


def _start_laya_download(root: Path) -> None:
    with _DOWNLOAD_LOCK:
        if _DOWNLOAD["status"] == "downloading":
            raise RuntimeError("A Laya model download is already in progress.")
        config = yaml.safe_load(_config_text(root))
        model = config.get("classification", {}).get("laya", {}).get("model", "multilingual")
        if model not in _ALLOWED_MODELS:
            raise ValueError("The configured Laya checkpoint is not supported.")
        if not importlib.util.find_spec("laya"):
            raise ValueError(
                "Install the optional laya dependency and restart the server before downloading a checkpoint."
            )
        _DOWNLOAD.update(
            status="downloading",
            model=model,
            started_at=datetime.now(UTC).isoformat(),
            finished_at=None,
            error=None,
        )

    def download() -> None:
        try:
            device = config.get("classification", {}).get("laya", {}).get("device", "auto")
            preload_laya_model(model, device)
        except Exception as exc:
            with _DOWNLOAD_LOCK:
                _DOWNLOAD.update(
                    status="failed", finished_at=datetime.now(UTC).isoformat(), error=str(exc)[:500]
                )
        else:
            with _DOWNLOAD_LOCK:
                _DOWNLOAD.update(
                    status="ready", finished_at=datetime.now(UTC).isoformat(), error=None
                )

    threading.Thread(target=download, name="polder-laya-download", daemon=True).start()


def _test_provider(root: Path, provider: str) -> dict[str, Any]:
    config = yaml.safe_load(_config_text(root)).get("classification", {})
    if provider == "jev":
        from ..classification import _remote_call

        try:
            _remote_call(
                "Polder provider connectivity check. This contains no research material.",
                {
                    "reachable": {
                        "type": "noul",
                        "instructions": "Respond yes if this API request is valid.",
                    }
                },
                config.get("jev", {}),
            )
            return {
                "provider": "jev",
                "ok": True,
                "message": "TypeSafe API returned a valid response.",
            }
        except Exception as exc:
            return {"provider": "jev", "ok": False, "message": str(exc)[:300]}
    if provider == "laya":
        if not importlib.util.find_spec("laya"):
            return {
                "provider": "laya",
                "ok": False,
                "message": "Install the optional Laya dependency first.",
            }
        with _DOWNLOAD_LOCK:
            if _DOWNLOAD.get("status") != "ready":
                return {
                    "provider": "laya",
                    "ok": False,
                    "message": "Download and load the selected Laya model first.",
                }
        return {
            "provider": "laya",
            "ok": True,
            "message": "Laya model is loaded for local inference.",
        }
    if provider == "rules":
        return {"provider": "rules", "ok": True, "message": "Built-in rules are available locally."}
    return {"provider": provider, "ok": False, "message": "Unknown provider."}


def serve(*, repository_root: Path | None = None, port: int = 8765) -> None:
    server = create_server(repository_root, port=port)
    print(f"Polder Research Control Panel: http://127.0.0.1:{server.server_port}")
    print("Local-only server. Press Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Polder control panel.")
    finally:
        server.server_close()
