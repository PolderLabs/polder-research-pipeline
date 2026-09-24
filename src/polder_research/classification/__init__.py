"""Automatic, auditable taxonomy classification for research records.

Classification proposes metadata only. It never changes evidence or review
decisions, and low-confidence model results remain explicitly review-required.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from ..atomic import write_atomic
from ..paths import REPO_ROOT

JEv_URL = "https://api.typesafe.ai/v1/systemone"


def _probability(value: Any) -> float:
    score = float(value)
    if not 0 <= score <= 1:
        raise ValueError("provider returned a probability outside [0, 1]")
    return score


def _root(repository_root: Path | None) -> Path:
    return Path(repository_root).resolve() if repository_root else REPO_ROOT


def _config(root: Path) -> dict[str, Any]:
    try:
        config = yaml.safe_load((root / "knowledge-base" / "research.config.yaml").read_text())
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot read classification config: {exc}") from exc
    decision = config.get("classification", {}) if isinstance(config, dict) else {}
    return decision if isinstance(decision, dict) else {}


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _taxonomy_hash(taxonomy: dict[str, Any]) -> str:
    return _hash(json.dumps(taxonomy, sort_keys=True, separators=(",", ":")))


def _questions(taxonomy: dict[str, Any]) -> dict[str, dict[str, Any]]:
    categories = taxonomy.get("categories", {})
    tags = taxonomy.get("tags", {})
    questions: dict[str, dict[str, Any]] = {}
    if categories:
        questions["category"] = {
            "type": "choice",
            "instructions": "Select the single best knowledge-base category for this research record.",
            "criteria": {key: value["description"] for key, value in categories.items()},
        }
    for key, value in tags.items():
        questions[f"tag_{key}"] = {
            "type": "noul",
            "instructions": f"Does this record substantially concern {value['description']}?",
        }
    return questions


def _remote_call(state: str, questions: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    endpoint = config.get("endpoint", JEv_URL)
    if endpoint != JEv_URL:
        raise ValueError("Jev provider endpoint is fixed to https://api.typesafe.ai/v1/systemone")
    key_env = config.get("api_key_env", "TYPESAFE_API_KEY")
    api_key = os.environ.get(key_env) or _saved_api_key(key_env)
    if not api_key:
        raise RuntimeError(f"Jev selected but {key_env} is not set")
    payload = json.dumps(
        {"state": state, "model": config.get("model", "jev-latest"), "questions": questions}
    ).encode()
    request = urllib.request.Request(
        endpoint,
        payload,
        {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    try:
        opener = urllib.request.build_opener(_NoRedirect())
        with opener.open(request, timeout=float(config.get("timeout_seconds", 30))) as response:
            result = json.loads(response.read(2_000_001))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Jev classification request failed: {exc}") from exc
    if not isinstance(result, dict) or not isinstance(result.get("answers"), dict):
        raise RuntimeError("Jev returned an invalid System One response")
    return result


def _saved_api_key(key_env: str) -> str | None:
    path = REPO_ROOT / ".research" / "web-secrets.json"
    try:
        values = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    value = values.get(key_env) if isinstance(values, dict) else None
    return value if isinstance(value, str) and value else None


def _local_call(state: str, questions: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    try:
        with _LAYA_LOCK:
            result = _laya_router(config.get("device", "auto")).predict(
                state, questions, model=config.get("model", "multilingual")
            )
    except ImportError as exc:
        raise RuntimeError(
            "Laya selected; install the optional dependency with `pip install 'polder-research-pipeline[laya]'`"
        ) from exc
    if not isinstance(result, dict) or not isinstance(result.get("answers"), dict):
        raise RuntimeError("Laya returned an invalid System One response")
    return result


_LAYA_ROUTER: Any = None
_LAYA_ROUTER_DEVICE: str | None = None
_LAYA_LOCK = threading.RLock()


def _laya_router(device: str) -> Any:
    global _LAYA_ROUTER, _LAYA_ROUTER_DEVICE
    from laya import Router

    if _LAYA_ROUTER is None or _LAYA_ROUTER_DEVICE != device:
        options = {} if device == "auto" else {"device": device}
        _LAYA_ROUTER = Router(**options)
        _LAYA_ROUTER_DEVICE = device
    return _LAYA_ROUTER


def preload_laya_model(model: str, device: str = "auto") -> None:
    """Download and load one supported Laya checkpoint in this process."""
    with _LAYA_LOCK:
        try:
            router = _laya_router(device)
        except ImportError as exc:
            raise RuntimeError("Laya is not installed; install the optional laya extra") from exc
        router.preload([model])


def _rules_call(state: str, taxonomy: dict[str, Any]) -> dict[str, Any]:
    normalized = state.casefold()
    categories: dict[str, float] = {}
    for key, entry in taxonomy.get("categories", {}).items():
        terms = [str(term).casefold() for term in entry.get("keywords", [])]
        categories[key] = float(any(term in normalized for term in terms))
    chosen = max(categories, key=categories.get) if categories else ""
    if chosen and not categories[chosen]:
        chosen = ""
    answers: dict[str, Any] = {}
    if categories:
        answers["category"] = {
            "type": "choice",
            "choice": chosen or "other",
            "confidence": 1.0 if chosen else 0.0,
            "probabilities": categories,
        }
    for key, entry in taxonomy.get("tags", {}).items():
        terms = [str(term).casefold() for term in entry.get("keywords", [])]
        score = 1.0 if any(term in normalized for term in terms) else 0.0
        answers[f"tag_{key}"] = {"type": "noul", "noul": score}
    return {"model": "rules-v1", "answers": answers}


def classify_text(
    text: str,
    *,
    target_kind: str,
    target_id: str,
    repository_root: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any] | None:
    """Classify input using configured provider and persist an immutable result.

    Disabled classification returns ``None``. Human-supplied metadata should be
    merged by the caller and must never be overwritten by this proposal.
    """
    root = _root(repository_root)
    config = _config(root)
    if not config.get("enabled", True):
        return None
    taxonomy = config.get("taxonomy", {})
    provider = config.get("provider", "rules")
    if provider not in {"rules", "jev", "laya"}:
        raise ValueError(f"unsupported classification provider: {provider!r}")
    if not taxonomy.get("categories") and not taxonomy.get("tags"):
        return None
    clipped = text[: int(config.get("max_input_chars", 12000))]
    state_hash = _hash(clipped)
    tax_hash = _taxonomy_hash(taxonomy)
    provider_config = config.get(provider, {}) if provider != "rules" else {}
    requested_model = provider_config.get(
        "model", "rules-v1" if provider == "rules" else "jev-latest"
    )
    threshold = float(config.get("minimum_confidence", 0.75))
    if not 0 <= threshold <= 1:
        raise ValueError("classification.minimum_confidence must be between 0 and 1")
    questions = _questions(taxonomy)
    record_key = _hash(
        f"{target_kind}:{target_id}:{state_hash}:{tax_hash}:{provider}:{requested_model}:{threshold}"
    )
    directory = Path(output_dir) if output_dir else root / ".research" / "classifications"
    directory.mkdir(parents=True, exist_ok=True)
    for path in directory.glob("cls_*.json"):
        try:
            old = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if old.get("record_key") == record_key:
            return old
    started = time.monotonic()
    try:
        if provider == "rules":
            result = _rules_call(clipped, taxonomy)
        elif provider == "jev":
            result = _remote_call(clipped, questions, config.get("jev", {}))
        else:
            result = _local_call(clipped, questions, config.get("laya", {}))
        answers = result["answers"]
        category_answer = answers.get("category", {})
        category = category_answer.get("choice")
        if category not in taxonomy.get("categories", {}):
            category = None
        category_confidence = _probability(category_answer.get("confidence", 0))
        if not category_confidence and isinstance(category_answer.get("probabilities"), dict):
            category_confidence = max(
                (_probability(value) for value in category_answer["probabilities"].values()),
                default=0,
            )
        tags = []
        tag_scores = {}
        for key in taxonomy.get("tags", {}):
            answer = answers.get(f"tag_{key}", {})
            score = _probability(answer.get("noul", 0))
            tag_scores[key] = score
            if score >= threshold:
                tags.append(key)
        accepted = bool(category and category_confidence >= threshold) or bool(tags)
        record = {
            "id": f"cls_{uuid.uuid7()}",
            "schema_version": 1,
            "record_key": record_key,
            "target_kind": target_kind,
            "target_id": target_id,
            "input_sha256": state_hash,
            "taxonomy_sha256": tax_hash,
            "taxonomy_version": taxonomy.get("version", "1"),
            "taxonomy_snapshot": taxonomy,
            "provider": provider,
            "requested_model": requested_model,
            "model": result.get("model")
            or result.get("routing", {}).get("model")
            or requested_model,
            "endpoint_identity": "typesafe-api"
            if provider == "jev"
            else ("local-process" if provider == "laya" else "built-in"),
            "questions": questions,
            "category": category if category_confidence >= threshold else None,
            "category_confidence": category_confidence,
            "tag_probabilities": tag_scores,
            "proposed_tags": tags,
            "threshold": threshold,
            "answers": answers,
            "disposition": "accepted" if accepted else "review_required",
            "elapsed_ms": round((time.monotonic() - started) * 1000),
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
    except Exception as exc:
        record = {
            "id": f"cls_{uuid.uuid7()}",
            "schema_version": 1,
            "record_key": record_key,
            "target_kind": target_kind,
            "target_id": target_id,
            "input_sha256": state_hash,
            "taxonomy_sha256": tax_hash,
            "taxonomy_version": taxonomy.get("version", "1"),
            "taxonomy_snapshot": taxonomy,
            "provider": provider,
            "requested_model": requested_model,
            "model": requested_model,
            "endpoint_identity": "typesafe-api"
            if provider == "jev"
            else ("local-process" if provider == "laya" else "built-in"),
            "questions": questions,
            "category": None,
            "category_confidence": 0,
            "tag_probabilities": {},
            "proposed_tags": [],
            "threshold": float(config.get("minimum_confidence", 0.75)),
            "answers": {},
            "disposition": "failed",
            "error": str(exc)[:500],
            "elapsed_ms": round((time.monotonic() - started) * 1000),
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
    schema_root = root / "schemas"
    if schema_root.exists():
        write_atomic(directory / f"{record['id']}.json", record, schema_name="classification")
    else:
        (directory / f"{record['id']}.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def merge_proposals(record: dict[str, Any], result: dict[str, Any] | None) -> dict[str, Any]:
    """Merge accepted model proposals without deleting existing user values."""
    if not result or result.get("disposition") not in {"accepted", "review_required"}:
        return record
    if (
        result.get("category")
        and "topic" not in record
        and record.get("id", "").startswith(("src_", "clm_", "seg_"))
    ):
        record["topic"] = result["category"]
    existing = list(record.get("tags", []))
    record["tags"] = list(dict.fromkeys(existing + result.get("proposed_tags", [])))
    record["classification_ids"] = list(
        dict.fromkeys(record.get("classification_ids", []) + [result["id"]])
    )
    return record
