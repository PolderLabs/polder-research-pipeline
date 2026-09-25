"""Loopback-only research control panel and read-only analytics API."""

from __future__ import annotations

import hashlib
import importlib.metadata
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

import yaml

from ..classification import (
    _local_call,
    _probability,
    _remote_call,
    laya_inference_verified,
    preload_laya_model,
)
from ..classification_review import active_review_ids, record_review, review_records_audit
from ..decision.config import validate_config as validate_decision_config
from ..decision.projection import build_effective_projection
from ..locking import acquire_file_lock, release_file_lock
from ..maintenance import build_health, evaluate_maintenance
from ..paths import REPO_ROOT
from ..schemas import SchemaError, registry_for_root
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
        _validate_config(parsed, root)
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
            if key_path == ("classification", "provider"):
                decision_node = yaml.compose(raw)
                for key in ("decision", "default_provider"):
                    if not isinstance(decision_node, yaml.MappingNode):
                        raise ValueError("Cannot synchronize decision.default_provider")
                    pair = next(
                        (pair for pair in decision_node.value if pair[0].value == key), None
                    )
                    if pair is None:
                        raise ValueError("Configuration key is missing: decision.default_provider")
                    decision_node = pair[1]
                if not isinstance(decision_node, yaml.ScalarNode):
                    raise ValueError("decision.default_provider must be a scalar")
                edits.append((decision_node.start_mark.index, decision_node.end_mark.index, scalar))
        for start, end, scalar in sorted(edits, reverse=True):
            raw = raw[:start] + scalar + raw[end:]
        parsed = yaml.safe_load(raw)
        _validate_config(parsed, root)
        _atomic_text(
            path, raw if raw.endswith("\n") else raw + "\n", mode=path.stat().st_mode & 0o777
        )
        return {"revision": _revision(raw), "config": parsed}


def _validate_config(config: Any, repository_root: Path | None = None) -> None:
    if not isinstance(config, dict):
        raise ValueError("Configuration must be a YAML mapping")
    try:
        validate_decision_config(config, repository_root or REPO_ROOT)
    except Exception as exc:
        raise ValueError(
            f"Configuration does not match research-config.schema.json: {exc}"
        ) from exc

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
    if laya.get("route_mode", "auto") not in {"auto", "explicit"}:
        raise ValueError("classification.laya.route_mode must be auto or explicit")
    if (
        laya.get("route_mode", "auto") == "explicit"
        and laya.get("explicit_model", laya.get("model", "multilingual")) not in _ALLOWED_MODELS
    ):
        raise ValueError("explicit Laya routing requires a supported model")
    if laya.get("transport", "inprocess") not in {"inprocess", "local-http"}:
        raise ValueError("classification.laya.transport must be inprocess or local-http")
    if laya.get("transport") == "local-http":
        endpoint = laya.get("endpoint")
        parsed = urllib.parse.urlsplit(endpoint) if isinstance(endpoint, str) else None
        if (
            parsed is None
            or parsed.scheme != "http"
            or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
        ):
            raise ValueError("classification.laya.endpoint must use loopback HTTP")
    if not isinstance(classification.get("enabled", True), bool):
        raise ValueError("classification.enabled must be a boolean")
    routing = classification.get("routing", {})
    if not isinstance(routing, dict):
        raise ValueError("classification.routing must be a mapping")
    sensitive_provider = routing.get("sensitive_provider")
    if sensitive_provider is not None and sensitive_provider not in {"rules", "jev", "laya"}:
        raise ValueError("classification.routing.sensitive_provider must be rules, jev, or laya")
    if sensitive_provider == "jev":
        raise ValueError("sensitive_provider cannot be Jev; sensitive data must stay local")
    by_target_kind = routing.get("by_target_kind", {})
    if not isinstance(by_target_kind, dict):
        raise ValueError("classification.routing.by_target_kind must be a mapping")
    for target_kind, routed_provider in by_target_kind.items():
        if target_kind not in {"source", "segment", "claim", "entity", "note"}:
            raise ValueError(f"Unsupported classification routing target kind: {target_kind!r}")
        if routed_provider not in {"rules", "jev", "laya"}:
            raise ValueError("Classification routing providers must be rules, jev, or laya")
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
    dimensions = taxonomy.get("dimensions", {})
    if not isinstance(dimensions, dict):
        raise ValueError("classification.taxonomy.dimensions must be a mapping")
    for key, dimension in dimensions.items():
        if not re.fullmatch(r"[a-z0-9]+(?:[-_][a-z0-9]+)*", str(key)) or not isinstance(
            dimension, dict
        ):
            raise ValueError(f"Invalid taxonomy dimension: {key!r}")
        if (
            not isinstance(dimension.get("instructions"), str)
            or not dimension["instructions"].strip()
        ):
            raise ValueError(f"Taxonomy dimension {key!r} requires instructions")
        values = dimension.get("values")
        if not isinstance(values, dict) or not values:
            raise ValueError(f"Taxonomy dimension {key!r} requires a non-empty values mapping")
        for value_key, value in values.items():
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", str(value_key)) or not isinstance(
                value, dict
            ):
                raise ValueError(f"Invalid taxonomy dimension value: {value_key!r}")
            if not isinstance(value.get("description"), str) or not value["description"].strip():
                raise ValueError(f"Taxonomy dimension value {value_key!r} requires a description")
            keywords = value.get("keywords", [])
            if not isinstance(keywords, list) or not all(
                isinstance(word, str) for word in keywords
            ):
                raise ValueError(
                    f"Taxonomy dimension value {value_key!r} keywords must be a list of strings"
                )


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
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            pass
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
    lock = acquire_file_lock(root / ".research" / "locks" / "web-secrets.lock", wait=True)
    try:
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
    finally:
        release_file_lock(lock)


def _records(root: Path, collection: str, schema_name: str) -> tuple[list[dict[str, Any]], int]:
    directory = root / ".research" / collection
    try:
        validator = registry_for_root(root, allow_package_fallback=True).validator(schema_name)
    except (OSError, SchemaError, KeyError):
        return [], 0
    rows: list[dict[str, Any]] = []
    malformed = 0
    for path in sorted(directory.glob("*.json")) if directory.exists() else []:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            malformed += 1
            continue
        if (
            not validator.is_valid(record)
            or not isinstance(record, dict)
            or path.name != f"{record.get('id')}.json"
        ):
            malformed += 1
            continue
        rows.append(record)
    return rows, malformed


def _provider_health(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    classification = config.get("classification", {})
    provider = classification.get("provider", "rules")
    routing_config = classification.get("routing", {})
    has_routing = isinstance(routing_config, dict) and bool(
        routing_config.get("sensitive_provider") or routing_config.get("by_target_kind")
    )
    laya_installed = importlib.util.find_spec("laya") is not None
    laya_config = classification.get("laya", {})
    model = laya_config.get("explicit_model") or laya_config.get("model", "english")
    device = laya_config.get("device", "auto")
    laya_version = None
    try:
        laya_version = importlib.metadata.version("laya")
    except importlib.metadata.PackageNotFoundError:
        pass
    torch_version = None
    cuda_runtime = None
    cuda_available = False
    gpu_name = None
    try:
        import torch

        torch_version = torch.__version__
        cuda_runtime = torch.version.cuda
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            gpu_name = torch.cuda.get_device_name(0)
    except (ImportError, OSError, RuntimeError):
        pass
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
    laya_loaded = laya_inference_verified(model, device)
    device_ready = device != "cuda" or cuda_available
    laya_ready = laya_installed and laya_loaded and device_ready
    routes = {"default": provider}
    sensitive_provider = (
        routing_config.get("sensitive_provider") if isinstance(routing_config, dict) else None
    )
    if sensitive_provider:
        routes["sensitive"] = sensitive_provider
    by_kind = routing_config.get("by_target_kind", {}) if isinstance(routing_config, dict) else {}
    if isinstance(by_kind, dict):
        routes.update({f"target:{kind}": value for kind, value in by_kind.items()})
    readiness = {
        "rules": True,
        "jev": key["configured"],
        "laya": laya_ready,
    }
    route_status = {
        name: {"provider": route_provider, "ready": readiness.get(route_provider, False)}
        for name, route_provider in routes.items()
    }
    selected_ready = not enabled or all(item["ready"] for item in route_status.values())
    return {
        "selected": provider,
        "enabled": enabled,
        "ready": selected_ready,
        "minimum_confidence": classification.get("minimum_confidence", 0.75),
        "taxonomy_version": classification.get("taxonomy", {}).get("version", "1"),
        "routing": {
            "mode": "policy-based" if has_routing else "single-provider",
            "routes": route_status,
            "detail": (
                "One or more configured provider routes are not ready."
                if not selected_ready and enabled
                else "Sensitive and target-kind routing rules are active."
                if has_routing
                else "New records use the selected provider. Per-record routing policy is not configured."
            ),
        },
        "replay": {
            "available": True,
            "detail": "Durable replay is available from the CLI: run `polder-research classify-existing --dry-run`, then `polder-research classify-existing`; resume interrupted jobs with `--resume <job_id>`. The dashboard does not start replay jobs.",
        },
        "typesafe": {"ready": key["configured"], **key},
        "laya": {
            "installed": laya_installed,
            "version": laya_version,
            "model": model,
            "route_mode": laya_config.get("route_mode", "auto"),
            "device": device,
            "torch_version": torch_version,
            "cuda_runtime": cuda_runtime,
            "cuda_available": cuda_available,
            "gpu_name": gpu_name,
            "max_loaded": laya_config.get("max_loaded", 1),
            "cached": cached,
            "loaded": laya_loaded,
            "inference_verified": laya_loaded,
            "ready": laya_ready,
            "cache_path": cache_path,
            "job": download,
        },
    }


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _latency_summary(values: list[float]) -> dict[str, int | None]:
    if not values:
        return {"count": 0, "mean_ms": None, "p50_ms": None, "p95_ms": None, "max_ms": None}
    ordered = sorted(values)

    def percentile(fraction: float) -> int:
        index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * fraction)))
        return round(ordered[index])

    return {
        "count": len(ordered),
        "mean_ms": round(sum(ordered) / len(ordered)),
        "p50_ms": percentile(0.5),
        "p95_ms": percentile(0.95),
        "max_ms": round(ordered[-1]),
    }


def _classification_analytics(
    classifications: list[dict[str, Any]], reviews: list[dict[str, Any]]
) -> dict[str, Any]:
    """Return privacy-preserving operational metrics for immutable classification records."""
    by_disposition = Counter(str(item.get("disposition", "unknown")) for item in classifications)
    by_provider = Counter(str(item.get("provider", "unknown")) for item in classifications)
    by_target_kind = Counter(str(item.get("target_kind", "unknown")) for item in classifications)
    category_status = Counter()
    tag_status = Counter()
    dimension_status = Counter()
    by_field_status: dict[str, Counter[str]] = {}
    tag_coverage = Counter()
    confidence_bands = Counter()
    latency_values: list[float] = []
    review_queue: list[dict[str, Any]] = []
    failed_queue: list[dict[str, Any]] = []
    reviewed_fields: dict[str, dict[str, dict[str, Any]]] = {}
    active_ids = active_review_ids(reviews)
    for review in reviews:
        if review.get("id") not in active_ids:
            continue
        classification_id = review.get("classification_id")
        resolutions = review.get("resolutions")
        if not isinstance(classification_id, str) or not isinstance(resolutions, dict):
            continue
        destination = reviewed_fields.setdefault(classification_id, {})
        for field, resolution in resolutions.items():
            if isinstance(field, str) and isinstance(resolution, dict):
                destination[field] = resolution

    for item in classifications:
        disposition = str(item.get("disposition", "unknown"))
        decisions = item.get("field_decisions")
        if not isinstance(decisions, dict):
            decisions = {}
        safe_decisions: dict[str, dict[str, Any]] = {}
        for field, raw_decision in list(decisions.items())[:30]:
            if not isinstance(field, str) or not isinstance(raw_decision, dict):
                continue
            value = raw_decision.get("value")
            probability = _number(raw_decision.get("probability"))
            status = raw_decision.get("status")
            if not isinstance(status, str):
                continue
            safe_decisions[field] = {
                "status": status,
                "value": value if isinstance(value, str | bool) or value is None else None,
                "probability": probability,
            }
            taxonomy = item.get("taxonomy_snapshot")
            if field == "category" and isinstance(taxonomy, dict):
                options = list(taxonomy.get("categories", {}))
            elif field.startswith("tag_"):
                options = [False, True]
            elif field.startswith("dimension_") and isinstance(taxonomy, dict):
                dimension = field.removeprefix("dimension_")
                dimensions = taxonomy.get("dimensions", {})
                entry = dimensions.get(dimension, {}) if isinstance(dimensions, dict) else {}
                values = entry.get("values", {}) if isinstance(entry, dict) else {}
                options = list(values) if isinstance(values, dict) else []
            else:
                options = []
            safe_decisions[field]["options"] = (
                [None, *options] if not field.startswith("tag_") else options
            )
        pending_decisions = {
            field: decision
            for field, decision in safe_decisions.items()
            if decision["status"] == "review_required"
            and field not in reviewed_fields.get(str(item.get("id", "")), {})
        }
        target = {
            "id": str(item.get("id", "unknown")),
            "target_kind": str(item.get("target_kind", "unknown")),
            "target_id": str(item.get("target_id", "unknown")),
            "field_decisions": pending_decisions,
            "reviewed_fields": sorted(reviewed_fields.get(str(item.get("id", "")), {})),
        }
        if disposition == "review_required" and pending_decisions:
            review_queue.append(target)
        elif disposition == "failed":
            failed_queue.append(target)

        elapsed = _number(item.get("elapsed_ms"))
        if elapsed is not None and elapsed >= 0:
            latency_values.append(elapsed)

        threshold = _number(item.get("threshold"))
        threshold = threshold if threshold is not None else 0.75
        scores: list[float] = []
        if safe_decisions:
            for field, decision in safe_decisions.items():
                status = decision["status"]
                by_field_status.setdefault(field, Counter())[status] += 1
                if field == "category":
                    category_status[status] += 1
                elif field.startswith("tag_"):
                    tag_status[status] += 1
                    if status == "accepted":
                        tag_coverage[field.removeprefix("tag_")] += 1
                elif field.startswith("dimension_"):
                    dimension_status[status] += 1
                score = decision["probability"]
                if score is not None:
                    scores.append(score)
        else:
            questions = item.get("questions") if isinstance(item.get("questions"), dict) else {}
            category_asked = "category" in questions or "category_confidence" in item
            if disposition == "failed":
                category_status["failed"] += 1
            elif not category_asked:
                category_status["not_evaluated"] += 1
            elif isinstance(item.get("category"), str) and item["category"]:
                category_status["accepted"] += 1
            elif disposition == "review_required":
                category_status["review_required"] += 1
            else:
                category_status["abstained"] += 1
            category_confidence = _number(item.get("category_confidence"))
            if category_confidence is not None:
                scores.append(category_confidence)
            probabilities = item.get("tag_probabilities")
            if not isinstance(probabilities, dict):
                probabilities = {}
            proposed = {str(tag) for tag in item.get("proposed_tags", []) if isinstance(tag, str)}
            if disposition == "failed":
                tag_status["failed"] += 1
            elif not probabilities:
                tag_status["not_evaluated"] += 1
            else:
                for tag, raw_score in probabilities.items():
                    score = _number(raw_score)
                    if score is None:
                        continue
                    scores.append(score)
                    if str(tag) in proposed:
                        tag_status["proposed"] += 1
                        tag_coverage[str(tag)] += 1
                    elif abs(score - threshold) <= 0.05:
                        tag_status["near_threshold"] += 1
                    else:
                        tag_status["not_applied"] += 1
        for score in scores:
            if abs(score - threshold) <= 0.05:
                confidence_bands["near_threshold"] += 1
            elif score >= threshold:
                confidence_bands["above_threshold"] += 1
            else:
                confidence_bands["below_threshold"] += 1

    return {
        "by_disposition": dict(sorted(by_disposition.items())),
        "by_provider": dict(sorted(by_provider.items())),
        "by_target_kind": dict(sorted(by_target_kind.items())),
        "field_status": {
            "category": dict(sorted(category_status.items())),
            "tags": dict(sorted(tag_status.items())),
            "dimensions": dict(sorted(dimension_status.items())),
        },
        "by_field_status": {
            field: dict(sorted(statuses.items()))
            for field, statuses in sorted(by_field_status.items())
        },
        "tag_coverage": dict(sorted(tag_coverage.items())),
        "confidence_bands": dict(sorted(confidence_bands.items())),
        "latency_ms": _latency_summary(latency_values),
        "queues": {
            "review_required": review_queue[:50],
            "review_required_count": len(review_queue),
            "failed": failed_queue[:50],
            "failed_count": len(failed_queue),
        },
        "human_reviews": {
            "record_count": len(reviews),
            "resolved_field_count": sum(len(fields) for fields in reviewed_fields.values()),
        },
    }


def _classification_preview(root: Path, kind: str, target_id: str) -> dict[str, Any]:
    """Read a short local preview for human review without persisting it in predictions."""
    directories = {
        "source": "sources",
        "segment": "segments",
        "claim": "claims",
        "entity": "entities",
    }
    directory = directories.get(kind)
    if (
        not directory
        or not target_id.startswith(
            {"source": "src_", "segment": "seg_", "claim": "clm_", "entity": "ent_"}[kind]
        )
        or Path(target_id).name != target_id
        or "/" in target_id
        or "\\" in target_id
    ):
        return {
            "title": "Record unavailable",
            "text": "The linked local evidence record could not be resolved.",
        }
    try:
        record = json.loads(
            (root / ".research" / directory / f"{target_id}.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return {
            "title": "Record unavailable",
            "text": "The linked local evidence record could not be read.",
        }
    title = str(record.get("title") or record.get("name") or record.get("id") or target_id)
    body = record.get("text") or record.get("statement") or record.get("description") or ""
    if kind == "source":
        body = " · ".join(
            str(value)
            for value in (
                record.get("source_type"),
                record.get("media_type"),
                record.get("canonical_url"),
            )
            if value
        )
    return {
        "title": title[:240],
        "text": str(body)[:2000],
        "sensitivity": str(record.get("sensitivity", "unspecified")),
        "personal_data": bool(record.get("personal_data", False)),
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
    projection = build_effective_projection(root)["records"]
    target_collections = {
        "sources": "source",
        "segments": "segment",
        "claims": "claim",
        "entities": "entity",
    }
    for collection, kind in target_collections.items():
        projected_rows = []
        for record in evidence[collection]:
            view = dict(record)
            metadata = projection.get(f"{kind}:{record['id']}", {})
            view["topic"] = metadata.get("topic")
            view["tags"] = metadata.get("tags", record.get("tags", []))
            view["classification_dimensions"] = metadata.get(
                "dimensions", record.get("classification_dimensions", {})
            )
            projected_rows.append(view)
        evidence[collection] = projected_rows
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
    reviews, review_errors = review_records_audit(root)
    malformed += len(review_errors)
    classification_metrics = _classification_analytics(classifications, reviews)
    for item in classification_metrics["queues"]["review_required"]:
        item["preview"] = _classification_preview(root, item["target_kind"], item["target_id"])
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
            **classification_metrics,
            # Compatibility aliases for pre-existing dashboard clients.
            "review_required": [
                item["id"] for item in classification_metrics["queues"]["review_required"]
            ],
            "failed": [item["id"] for item in classification_metrics["queues"]["failed"]],
        },
        "method_records": method_records,
        "activity_30d": [{"date": day, **counts} for day, counts in by_day.items()],
        "malformed_count": malformed,
        "classification_review_integrity": {
            "malformed_count": len(review_errors),
            "malformed_records": review_errors,
        },
        "operational_health": operational,
        "workflow_state": states,
    }
    return research


def dashboard_payload(repository_root: Path | None = None) -> dict[str, Any]:
    root = Path(repository_root or REPO_ROOT).resolve()
    raw = _config_text(root)
    config = yaml.safe_load(raw)
    _validate_config(config, root)
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
                    config = None
                    provider_status = None
                    validation_error = None
                    try:
                        config = yaml.safe_load(raw)
                        _validate_config(config, self.root)
                        provider_status = _provider_health(self.root, config)
                    except (yaml.YAMLError, ValueError) as exc:
                        validation_error = str(exc)[:500]
                    self._json(
                        200,
                        {
                            "config": config,
                            "config_yaml": raw,
                            "revision": _revision(raw),
                            "provider": provider_status,
                            "validation_error": validation_error,
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
                if method == "POST" and path == "/api/classifications/review":
                    payload = json.loads(self._body())
                    review = record_review(
                        str(payload.get("classification_id", "")),
                        reviewer=payload.get("reviewer"),
                        resolutions=payload.get("resolutions"),
                        repository_root=self.root,
                        reviewer_namespace=payload.get("reviewer_namespace", "local-user"),
                        reason=payload.get("reason"),
                        supersedes_review_id=payload.get("supersedes_review_id"),
                        policy_result_id=payload.get("policy_result_id"),
                        adjudicator=payload.get("adjudicator"),
                    )
                    self._json(
                        201,
                        {
                            "saved": True,
                            "review_id": review["id"],
                            "classification_id": review["classification_id"],
                        },
                    )
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
        try:
            response = _remote_call(
                "Polder provider connectivity check. This contains no research material.",
                {
                    "reachable": {
                        "type": "noul",
                        "instructions": "Respond yes if this API request is valid.",
                    }
                },
                config.get("jev", {}),
                repository_root=root,
            )
            answer = response["answers"].get("reachable")
            if not isinstance(answer, dict) or answer.get("type") != "noul":
                raise ValueError("provider returned no valid reachable Noul answer")
            _probability(answer.get("noul"))
            return {
                "provider": "jev",
                "ok": True,
                "message": "TypeSafe API returned a valid Noul response for the connectivity prompt.",
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
        try:
            result = _local_call(
                "Polder local classifier check. This contains no research material.",
                {
                    "reachable": {
                        "type": "noul",
                        "instructions": "Is this a local classifier connectivity check?",
                    }
                },
                config.get("laya", {}),
            )
            answer = result["answers"].get("reachable")
            if not isinstance(answer, dict) or answer.get("type") != "noul":
                raise ValueError("local model returned no valid reachable Noul answer")
            _probability(answer.get("noul"))
            return {
                "provider": "laya",
                "ok": True,
                "message": "Laya completed a valid local inference probe.",
            }
        except Exception as exc:
            return {"provider": "laya", "ok": False, "message": str(exc)[:300]}
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
