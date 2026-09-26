"""Automatic, auditable taxonomy classification for research records.

Classification proposes metadata only. It never changes evidence or review
decisions, and low-confidence model results remain explicitly review-required.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..atomic import write_atomic
from ..decision.state_builders import canonical_json, clip_state, state_text
from ..locking import acquire_file_lock, release_file_lock
from ..paths import REPO_ROOT
from ..schemas import registry_for_root

JEv_URL = "https://api.typesafe.ai/v1/systemone"


def _probability(value: Any) -> float:
    score = float(value)
    if not math.isfinite(score) or not 0 <= score <= 1:
        raise ValueError("provider returned a probability outside [0, 1]")
    return score


def _root(repository_root: Path | None) -> Path:
    return Path(repository_root).resolve() if repository_root else REPO_ROOT


def _config(root: Path) -> dict[str, Any]:
    from ..decision.config import effective_classification, load_config

    return effective_classification(load_config(root))


def _hash(text: Any) -> str:
    encoded = canonical_json(text) if isinstance(text, dict | list) else str(text)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _taxonomy_hash(taxonomy: dict[str, Any]) -> str:
    return _hash(json.dumps(taxonomy, sort_keys=True, separators=(",", ":")))


def _question_hash(taxonomy: dict[str, Any]) -> str:
    return _hash(json.dumps(_questions(taxonomy), ensure_ascii=False, separators=(",", ":")))


def _requested_model(config: dict[str, Any], provider: str) -> str:
    provider_config = config.get(provider, {}) if provider != "rules" else {}
    if provider == "laya" and provider_config.get("route_mode", "auto") == "auto":
        return "auto"
    default = {"rules": "rules-v1", "laya": "english", "jev": "jev-1.13.0"}[provider]
    return str(provider_config.get("explicit_model") or provider_config.get("model") or default)


def _request_fingerprint(
    *,
    target_kind: str,
    target_id: str,
    state_hash: str,
    taxonomy: dict[str, Any],
    provider: str,
    requested_model: str,
    threshold: float,
    policy: dict[str, Any] | None,
    provider_settings: dict[str, Any] | None = None,
) -> str:
    parts = {
        "schema_version": 1,
        "target_kind": target_kind,
        "target_id": target_id,
        "state_builder_id": {
            "source": "source/metadata@1",
            "segment": "segment/default@1",
            "claim": "claim/default@1",
            "entity": "entity/default@1",
        }.get(target_kind, f"{target_kind}/default@1"),
        "state_sha256": state_hash,
        "question_set_sha256": _question_hash(taxonomy),
        "taxonomy_sha256": _taxonomy_hash(taxonomy),
        "provider": provider,
        "requested_model": requested_model,
        "provider_settings": {
            key: (value if isinstance(value, str | int | float | bool | type(None)) else value)
            for key, value in (provider_settings or {}).items()
            if key
            in {
                "route_mode",
                "explicit_model",
                "device",
                "transport",
                "max_len",
                "head_max_len",
                "token_budget",
            }
        },
        "policy_profile": {"minimum_confidence": threshold},
        "privacy": policy or {},
    }
    return _hash(json.dumps(parts, sort_keys=True, separators=(",", ":")))


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
    dimensions = taxonomy.get("dimensions", {})
    if not isinstance(dimensions, dict):
        raise ValueError("taxonomy.dimensions must be an object")
    for key, value in dimensions.items():
        if not isinstance(value, dict):
            raise ValueError(f"taxonomy dimension {key!r} must be an object")
        values = value.get("values", {})
        if not isinstance(values, dict) or not values:
            raise ValueError(f"taxonomy dimension {key!r} must define values")
        questions[f"dimension_{key}"] = {
            "type": "choice",
            "instructions": value.get("instructions")
            or f"Select the single best value for the {key.replace('_', ' ')} dimension.",
            "criteria": {
                label: entry.get("description", entry) if isinstance(entry, dict) else entry
                for label, entry in values.items()
            },
        }
    return questions


def _remote_call(
    state: Any,
    questions: dict[str, Any],
    config: dict[str, Any],
    *,
    repository_root: Path | None = None,
) -> dict[str, Any]:
    from ..decision.providers.jev import predict

    return predict(state, questions, config, repository_root)


def _saved_api_key(key_env: str, repository_root: Path | None = None) -> str | None:
    root = Path(repository_root) if repository_root is not None else REPO_ROOT
    path = root / ".research" / "web-secrets.json"
    try:
        values = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    value = values.get(key_env) if isinstance(values, dict) else None
    return value if isinstance(value, str) and value else None


def _local_call(state: Any, questions: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    try:
        if config.get("transport", "inprocess") == "local-http":
            from ..decision.providers.laya_http import predict

            result = predict(state, questions, config)
        elif config.get("transport", "inprocess") == "inprocess":
            from ..decision.providers.laya_inprocess import predict

            result = predict(state, questions, config)
        else:
            raise ValueError("Laya transport must be inprocess or local-http")
    except ImportError as exc:
        raise RuntimeError(
            "Laya selected; install the optional dependency with `pip install 'polder-research-pipeline[laya]'`"
        ) from exc
    except Exception as exc:
        raise RuntimeError("Laya classification request failed") from exc
    return _validated_laya_result(result, config)


_LAYA_LOCK = threading.RLock()
_LAYA_VERIFIED: set[tuple[str, str]] = set()


def _validated_laya_result(result: Any, config: dict[str, Any]) -> dict[str, Any]:
    """Validate and record a completed local inference, including batched ones."""
    if not isinstance(result, dict) or not isinstance(result.get("answers"), dict):
        raise RuntimeError("Laya returned an invalid System One response")
    routing = result.get("routing")
    resolved = result.get("model") or (routing.get("model") if isinstance(routing, dict) else None)
    if not isinstance(resolved, str):
        raise RuntimeError("Laya omitted routed model identity")
    with _LAYA_LOCK:
        _LAYA_VERIFIED.add((resolved, config.get("device", "auto")))
    return result


def laya_inference_verified(model: str, device: str = "auto") -> bool:
    """Return whether this process has completed inference for this setting."""
    with _LAYA_LOCK:
        return (model, device) in _LAYA_VERIFIED


def preload_laya_model(model: str, device: str = "auto") -> None:
    """Download and load one supported Laya checkpoint in this process."""
    with _LAYA_LOCK:
        try:
            from ..decision.providers.laya_inprocess import preload

            preload(model, device)
        except ImportError as exc:
            raise RuntimeError("Laya is not installed; install the optional laya extra") from exc


def _rules_call(state: Any, taxonomy: dict[str, Any]) -> dict[str, Any]:
    from ..decision.providers.rules import predict

    return predict(state, taxonomy)


def select_provider(
    config: dict[str, Any], target_kind: str, metadata: dict[str, Any] | None = None
) -> str:
    """Select a configured provider without sending sensitive records to cloud by default.

    ``classification.routing`` can set ``by_target_kind`` and an explicit
    ``sensitive_provider``. Sensitive records may only use ``laya`` or
    ``rules``; a Jev default without an explicit local-safe route fails closed.
    """
    provider = config.get("provider", "rules")
    routing = config.get("routing", {})
    if not isinstance(routing, dict):
        return provider
    values = metadata if isinstance(metadata, dict) else {}
    sensitive = _is_sensitive(values)
    if sensitive:
        candidate = routing.get("sensitive_provider", provider)
        if candidate not in {"laya", "rules"}:
            raise ValueError(
                "sensitive classification requires a local-safe laya or rules provider"
            )
        return candidate
    by_target_kind = routing.get("by_target_kind", {})
    if isinstance(by_target_kind, dict) and isinstance(by_target_kind.get(target_kind), str):
        return by_target_kind[target_kind]
    return provider


def _is_sensitive(metadata: dict[str, Any]) -> bool:
    """Treat every non-public source classification as local-only by default."""
    sensitivity = metadata.get("sensitivity")
    # Unknown labels fail closed too; a typo or newer sensitivity level must
    # never silently make content eligible for a hosted provider.
    return (
        bool(metadata.get("sensitive") or metadata.get("personal_data")) or sensitivity != "public"
    )


def _safe_failure_message(exc: Exception) -> str:
    """Keep persisted failures diagnostic without retaining provider text or credentials."""
    message = str(exc)
    safe_prefixes = (
        "Jev selected but ",
        "Jev selected; install the optional dependency",
        "Laya selected; install the optional dependency",
        "Laya is not installed;",
        "sensitive classification requires ",
        "sensitive classification cannot ",
    )
    return (
        message
        if message.startswith(safe_prefixes)
        else "classification provider or response failed"
    )


def _usage_counts(result: dict[str, Any]) -> dict[str, int] | None:
    """Retain bounded numeric usage counters without provider payload metadata."""
    usage = result.get("usage")
    if not isinstance(usage, dict):
        return None
    aliases = {
        "input_tokens": ("input_tokens", "input_tokens_total"),
        "output_tokens": ("output_tokens", "output_tokens_total"),
        "total_tokens": ("total_tokens", "total_tokens_total"),
        "requests": ("requests",),
    }
    counts: dict[str, int] = {}
    for key, options in aliases.items():
        value = next((usage[name] for name in options if name in usage), None)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            counts[key] = value
    return counts or None


def _provider_runtime(provider: str) -> dict[str, str | None]:
    package = {"jev": "typesafe-sdk", "laya": "laya"}.get(provider)
    try:
        package_version = importlib.metadata.version(package) if package else None
    except importlib.metadata.PackageNotFoundError:
        package_version = None
    try:
        polder_version = importlib.metadata.version("polder-research-pipeline")
    except importlib.metadata.PackageNotFoundError:
        polder_version = "0.2.0"
    return {
        "polder_version": polder_version,
        "provider_package": package,
        "provider_package_version": package_version,
    }


def _bounded_answers(answers: Any, questions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Persist only known answer fields and cap serialized provider output."""
    if not isinstance(answers, dict):
        raise ValueError("provider response has invalid answers")
    sanitized: dict[str, Any] = {}
    for key, question in questions.items():
        answer = answers.get(key)
        if not isinstance(answer, dict):
            sanitized[key] = answer
            continue
        allowed = {
            "choice": {
                "type",
                "choice",
                "confidence",
                "answer_confidence",
                "probabilities",
                "action",
            },
            "score": {
                "type",
                "score",
                "confidence",
                "answer_confidence",
                "probabilities",
                "action",
            },
            "noul": {"type", "noul", "confidence", "answer_confidence", "action"},
        }.get(question.get("type"), {"type"})
        sanitized[key] = {name: answer[name] for name in allowed if name in answer}
    try:
        size = len(json.dumps(sanitized, ensure_ascii=False, allow_nan=False).encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise ValueError("provider response contains non-JSON answer data") from exc
    if size > 512_000:
        raise ValueError("provider answer data exceeds the 512 KB limit")
    return sanitized


def _laya_routing_metadata(result: dict[str, Any]) -> dict[str, str] | None:
    """Keep a short allowlist of local routing facts for operational diagnostics."""
    routing = result.get("routing")
    if not isinstance(routing, dict):
        return None
    allowed = {
        "model",
        "language",
        "language_code",
        "device",
        "route_mode",
        "route_reason",
        "checkpoint",
        "repo_id",
        "max_len",
        "head_max_len",
        "checkpoint_revision",
    }
    metadata = {
        key: str(value)[:200]
        for key, value in routing.items()
        if key in allowed and isinstance(value, str | int | float | bool)
    }
    return metadata or None


def _field_decision(score: float, threshold: float) -> str:
    """Return a three-way decision for a probability of a positive label."""
    if score >= threshold:
        return "accepted"
    if score <= 1 - threshold:
        return "rejected"
    return "review_required"


def _validated_choice_probabilities(
    answer: dict[str, Any], values: dict[str, Any], field_name: str
) -> tuple[str, float, float | None]:
    choice = answer.get("choice")
    if choice not in values:
        raise ValueError(f"provider selected an invalid {field_name} value")
    probabilities = answer.get("probabilities")
    if not isinstance(probabilities, dict) or set(probabilities) != set(values):
        raise ValueError(f"provider {field_name} probabilities do not match the taxonomy")
    normalized = {label: _probability(value) for label, value in probabilities.items()}
    if not math.isclose(sum(normalized.values()), 1.0, rel_tol=0.0, abs_tol=0.01):
        raise ValueError(f"provider {field_name} probabilities are not normalized")
    selected_probability = normalized[choice]
    if selected_probability < max(normalized.values()):
        raise ValueError(f"provider selected a non-maximal {field_name} probability")
    reported_confidence = answer.get("confidence")
    if reported_confidence is not None:
        reported_confidence = _probability(reported_confidence)
    return choice, selected_probability, reported_confidence


def _validated_category(
    answer: Any, taxonomy: dict[str, Any], threshold: float
) -> tuple[str | None, float, dict[str, Any]]:
    if not isinstance(answer, dict):
        raise ValueError("provider response is missing the category answer")
    if answer.get("type") != "choice":
        raise ValueError("provider returned an invalid category answer type")
    categories = taxonomy.get("categories", {})
    if answer.get("choice") is None:
        reported_confidence = answer.get("confidence")
        if reported_confidence is not None:
            _probability(reported_confidence)
        return (
            None,
            0.0,
            {
                "status": "abstained",
                "value": None,
                "probability": None,
                "provider_confidence": reported_confidence,
            },
        )
    category, selected_probability, reported_confidence = _validated_choice_probabilities(
        answer, categories, "category"
    )
    decision = _field_decision(selected_probability, threshold)
    return (
        category if decision == "accepted" else None,
        selected_probability,
        {
            "status": decision,
            "value": category,
            "probability": selected_probability,
            "provider_confidence": reported_confidence,
        },
    )


def _validated_tags(
    answers: dict[str, Any], taxonomy: dict[str, Any], threshold: float
) -> tuple[list[str], dict[str, float], dict[str, dict[str, Any]]]:
    proposed: list[str] = []
    scores: dict[str, float] = {}
    decisions: dict[str, dict[str, Any]] = {}
    for key in taxonomy.get("tags", {}):
        answer = answers.get(f"tag_{key}")
        if not isinstance(answer, dict):
            raise ValueError(f"provider response is missing the tag_{key} answer")
        if answer.get("type") != "noul":
            raise ValueError(f"provider returned an invalid tag_{key} answer type")
        score = _probability(answer.get("noul"))
        status = _field_decision(score, threshold)
        scores[key] = score
        decisions[key] = {
            "status": status,
            "value": status == "accepted",
            "probability": score,
            "provider_confidence": None,
        }
        if status == "accepted":
            proposed.append(key)
    return proposed, scores, decisions


def _validated_dimensions(
    answers: dict[str, Any], taxonomy: dict[str, Any], threshold: float
) -> dict[str, dict[str, Any]]:
    decisions: dict[str, dict[str, Any]] = {}
    dimensions = taxonomy.get("dimensions", {})
    for key, entry in dimensions.items():
        values = entry.get("values", {}) if isinstance(entry, dict) else {}
        answer = answers.get(f"dimension_{key}")
        if not isinstance(answer, dict) or answer.get("type") != "choice":
            raise ValueError(f"provider response is missing a valid dimension_{key} answer")
        if answer.get("choice") is None:
            reported_confidence = answer.get("confidence")
            if reported_confidence is not None:
                _probability(reported_confidence)
            decisions[key] = {
                "status": "abstained",
                "value": None,
                "probability": None,
                "provider_confidence": reported_confidence,
            }
            continue
        choice, probability, reported_confidence = _validated_choice_probabilities(
            answer, values, f"dimension_{key}"
        )
        decisions[key] = {
            "status": _field_decision(probability, threshold),
            "value": choice,
            "probability": probability,
            "provider_confidence": reported_confidence,
        }
    return decisions


def _classify_text_unlocked(
    text: Any,
    *,
    target_kind: str,
    target_id: str,
    repository_root: Path | None = None,
    output_dir: Path | None = None,
    provider: str | None = None,
    metadata: dict[str, Any] | None = None,
    policy_metadata: dict[str, Any] | None = None,
    provider_result: dict[str, Any] | None = None,
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
    if metadata is not None and policy_metadata is not None:
        raise ValueError("pass policy metadata through either metadata or policy_metadata")
    policy = policy_metadata if policy_metadata is not None else metadata
    selected_provider = provider or select_provider(config, target_kind, policy)
    if policy is not None and not isinstance(policy, dict):
        raise ValueError("policy metadata must be an object")
    if selected_provider == "jev":
        from ..decision.privacy import preflight

        remote = config.get("remote_processing", {})
        project_allowed = isinstance(remote, dict) and remote.get("default_allowed") is True
        target_allowed = bool(policy and policy.get("remote_processing_allowed") is True)
        if not (project_allowed and target_allowed):
            raise ValueError("Jev requires explicit project and target remote-processing approval")
        if policy is None or _is_sensitive(policy):
            raise ValueError("sensitive or unclassified data cannot use the Jev provider")
        if preflight(state_text(text)):
            raise ValueError("local privacy preflight blocked remote processing")
        if config.get("jev", {}).get("model", "jev-1.13.0") == "jev-latest":
            raise ValueError("Jev production classification requires a pinned model version")
    if selected_provider not in {"rules", "jev", "laya"}:
        raise ValueError(f"unsupported classification provider: {selected_provider!r}")
    if (
        not taxonomy.get("categories")
        and not taxonomy.get("tags")
        and not taxonomy.get("dimensions")
    ):
        return None
    clipped = clip_state(text, int(config.get("max_input_chars", 12000)))
    state_hash = _hash(clipped)
    tax_hash = _taxonomy_hash(taxonomy)
    provider_config = config.get(selected_provider, {}) if selected_provider != "rules" else {}
    requested_model = _requested_model(config, selected_provider)
    threshold = float(config.get("minimum_confidence", 0.75))
    if not 0 <= threshold <= 1:
        raise ValueError("classification.minimum_confidence must be between 0 and 1")
    questions = _questions(taxonomy)
    question_set_hash = _question_hash(taxonomy)
    record_key = _request_fingerprint(
        target_kind=target_kind,
        target_id=target_id,
        state_hash=state_hash,
        taxonomy=taxonomy,
        provider=selected_provider,
        requested_model=requested_model,
        threshold=threshold,
        policy=policy,
        provider_settings=provider_config,
    )
    directory = Path(output_dir) if output_dir else root / ".research" / "classifications"
    directory.mkdir(parents=True, exist_ok=True)
    prior_attempts: list[dict[str, Any]] = []
    for path in directory.glob("cls_*.json"):
        try:
            old = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if old.get("record_key") == record_key:
            prior_attempts.append(old)
            if old.get("disposition") in {"accepted", "review_required"}:
                return old
    previous = max(prior_attempts, key=lambda item: int(item.get("attempt", 1)), default=None)
    attempt_number = int(previous.get("attempt", 1)) + 1 if previous else 1
    started = time.monotonic()
    try:
        if provider_result is not None:
            if selected_provider != "laya":
                raise ValueError("precomputed provider results are supported only for Laya")
            result = _validated_laya_result(provider_result, config.get("laya", {}))
        elif selected_provider == "rules":
            result = _rules_call(clipped, taxonomy)
        elif selected_provider == "jev":
            result = _remote_call(clipped, questions, config.get("jev", {}), repository_root=root)
        else:
            result = _local_call(clipped, questions, config.get("laya", {}))
        answers = _bounded_answers(result["answers"], questions)
        category: str | None = None
        category_confidence = 0.0
        category_decision: dict[str, Any] | None = None
        if taxonomy.get("categories"):
            category, category_confidence, category_decision = _validated_category(
                answers.get("category"), taxonomy, threshold
            )
        tags, tag_scores, tag_decisions = _validated_tags(answers, taxonomy, threshold)
        dimension_decisions = _validated_dimensions(answers, taxonomy, threshold)
        field_decisions: dict[str, dict[str, Any]] = {
            **({"category": category_decision} if category_decision is not None else {}),
            **{f"tag_{key}": value for key, value in tag_decisions.items()},
            **{f"dimension_{key}": value for key, value in dimension_decisions.items()},
        }
        if selected_provider != "rules":
            for decision in field_decisions.values():
                decision["status"] = "review_required"
        decisions = list(field_decisions.values())
        has_review = any(item["status"] == "review_required" for item in decisions)
        record = {
            "id": f"cls_{uuid.uuid7()}",
            "schema_version": 2,
            "record_key": record_key,
            "attempt": attempt_number,
            "retry_of": previous.get("id") if previous else None,
            "input_provenance": {
                "original_sha256": _hash(text),
                "submitted_sha256": state_hash,
                "submitted_chars": len(state_text(clipped)),
            },
            "provider_runtime": _provider_runtime(selected_provider),
            "target_kind": target_kind,
            "target_id": target_id,
            "input_sha256": state_hash,
            "taxonomy_sha256": tax_hash,
            "taxonomy_version": taxonomy.get("version", "1"),
            "taxonomy_snapshot": taxonomy,
            "question_set_sha256": question_set_hash,
            "provider": selected_provider,
            "requested_model": requested_model,
            "model": result.get("model")
            or result.get("routing", {}).get("model")
            or requested_model,
            "endpoint_identity": "typesafe-api"
            if selected_provider == "jev"
            else ("local-process" if selected_provider == "laya" else "built-in"),
            "questions": questions,
            "usage_counts": _usage_counts(result),
            "routing_metadata": _laya_routing_metadata(result)
            if selected_provider == "laya"
            else None,
            "category": category if category_confidence >= threshold else None,
            "category_confidence": category_confidence,
            "tag_probabilities": tag_scores,
            "proposed_tags": tags,
            "category_decision": category_decision,
            "tag_decisions": tag_decisions,
            "field_decisions": field_decisions,
            "threshold": threshold,
            "answers": answers,
            "disposition": "review_required" if has_review else "accepted",
            "elapsed_ms": round((time.monotonic() - started) * 1000),
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
    except Exception as exc:
        record = {
            "id": f"cls_{uuid.uuid7()}",
            "schema_version": 2,
            "record_key": record_key,
            "attempt": attempt_number,
            "retry_of": previous.get("id") if previous else None,
            "input_provenance": {
                "original_sha256": _hash(text),
                "submitted_sha256": state_hash,
                "submitted_chars": len(state_text(clipped)),
            },
            "provider_runtime": _provider_runtime(selected_provider),
            "target_kind": target_kind,
            "target_id": target_id,
            "input_sha256": state_hash,
            "taxonomy_sha256": tax_hash,
            "taxonomy_version": taxonomy.get("version", "1"),
            "taxonomy_snapshot": taxonomy,
            "question_set_sha256": question_set_hash,
            "provider": selected_provider,
            "requested_model": requested_model,
            "model": requested_model,
            "endpoint_identity": "typesafe-api"
            if selected_provider == "jev"
            else ("local-process" if selected_provider == "laya" else "built-in"),
            "questions": questions,
            "usage_counts": None,
            "routing_metadata": None,
            "category": None,
            "category_confidence": 0,
            "tag_probabilities": {},
            "proposed_tags": [],
            "category_decision": None,
            "tag_decisions": {},
            "field_decisions": {},
            "threshold": float(config.get("minimum_confidence", 0.75)),
            "answers": {},
            "disposition": "failed",
            "error": _safe_failure_message(exc),
            "elapsed_ms": round((time.monotonic() - started) * 1000),
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
    schema_root = root / "schemas"
    if schema_root.exists():
        write_atomic(
            directory / f"{record['id']}.json",
            record,
            schema_name="classification",
            registry=registry_for_root(root, allow_package_fallback=True),
        )
    else:
        (directory / f"{record['id']}.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def classify_text(
    text: Any,
    *,
    target_kind: str,
    target_id: str,
    repository_root: Path | None = None,
    output_dir: Path | None = None,
    provider: str | None = None,
    metadata: dict[str, Any] | None = None,
    policy_metadata: dict[str, Any] | None = None,
    provider_result: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Serialize identical target/input work across threads and processes."""
    root = _root(repository_root)
    config = _config(root)
    if not config.get("enabled", True):
        return None
    maximum = int(config.get("max_input_chars", 12000))
    clipped_state = clip_state(text, maximum)
    effective_hash = _hash(clipped_state)
    selected_provider = provider or select_provider(
        config, target_kind, policy_metadata or metadata
    )
    provider_config = config.get(selected_provider, {}) if selected_provider != "rules" else {}
    requested_model = _requested_model(config, selected_provider)
    taxonomy = config.get("taxonomy", {})
    lock_key = _request_fingerprint(
        target_kind=target_kind,
        target_id=target_id,
        state_hash=effective_hash,
        taxonomy=taxonomy,
        provider=selected_provider,
        requested_model=requested_model,
        threshold=float(config.get("minimum_confidence", 0.75)),
        policy=policy_metadata or metadata,
        provider_settings=provider_config,
    )
    lock = acquire_file_lock(
        root / ".research" / "locks" / f"classification-{lock_key}.lock", wait=True
    )
    try:
        return _classify_text_unlocked(
            text,
            target_kind=target_kind,
            target_id=target_id,
            repository_root=root,
            output_dir=output_dir,
            provider=provider,
            metadata=metadata,
            policy_metadata=policy_metadata,
            provider_result=provider_result,
        )
    finally:
        release_file_lock(lock)


def merge_proposals(record: dict[str, Any], result: dict[str, Any] | None) -> dict[str, Any]:
    """Retain the immutable result reference; effective metadata is projected separately."""
    if not result or result.get("disposition") not in {"accepted", "review_required"}:
        return record
    record["classification_ids"] = list(
        dict.fromkeys(record.get("classification_ids", []) + [result["id"]])
    )
    return record
