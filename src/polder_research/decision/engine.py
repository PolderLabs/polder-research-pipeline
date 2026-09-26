"""Execute a bounded decision request, persist its attempt, then evaluate policy."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import re
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..atomic import write_atomic
from ..classification import _bounded_answers
from ..decision.config import effective_classification, load_config
from ..decision.models import DecisionRequest, PolicyResult, ProviderAttempt
from ..decision.policy import evaluate_field
from ..decision.privacy import preflight, remote_eligibility
from ..decision.question_packs import QuestionPack
from ..decision.state_builders import canonical_json, clip_state, state_text
from ..schemas import SchemaError, registry_for_root


def _hash(value: Any) -> str:
    encoded = canonical_json(value) if isinstance(value, dict | list) else str(value)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _safe_error_category(exc: Exception) -> str:
    message = str(exc).casefold()
    if "401" in message or "auth" in message:
        return "authentication"
    if "timeout" in message or isinstance(exc, TimeoutError):
        return "timeout"
    if "429" in message or "rate" in message:
        return "rate_limited"
    if "invalid" in message or "malformed" in message:
        return "invalid_response"
    if "configuration" in message or isinstance(exc, ValueError):
        return "configuration"
    return "provider_failure"


def _runtime(provider: str) -> dict[str, str | None]:
    package = {"jev": "typesafe-sdk", "laya": "laya"}.get(provider)
    try:
        version = importlib.metadata.version(package) if package else None
    except importlib.metadata.PackageNotFoundError:
        version = None
    try:
        polder = importlib.metadata.version("polder-research-pipeline")
    except importlib.metadata.PackageNotFoundError:
        polder = "0.2.0"
    return {
        "polder_version": polder,
        "provider_package": package,
        "provider_package_version": version,
    }


def _provider_config(config: dict[str, Any], provider: str) -> dict[str, Any]:
    return config.get("jev" if provider == "jev" else "laya", {})


def _predict(
    provider: str, state: Any, pack: QuestionPack, config: dict[str, Any], repository_root: Path
) -> dict[str, Any]:
    settings = _provider_config(config, provider)
    if provider == "jev":
        from .providers.jev import predict

        return predict(state, pack.questions, settings, repository_root)
    if provider == "laya":
        if settings.get("transport", "inprocess") == "local-http":
            from .providers.laya_http import predict

            return predict(state, pack.questions, settings)
        from .providers.laya_inprocess import predict

        return predict(state, pack.questions, settings)
    raise ValueError(f"provider {provider!r} cannot execute this question pack")


def _answers(result: dict[str, Any], pack: QuestionPack) -> dict[str, Any]:
    answers = _bounded_answers(result.get("answers"), pack.questions)
    for name, question in pack.questions.items():
        answer = answers.get(name)
        if not isinstance(answer, dict):
            continue
        kind = question.get("type")
        if kind == "choice":
            criteria = question.get("criteria", {})
            if answer.get("choice") is not None and answer["choice"] not in criteria:
                raise ValueError(f"provider returned an invalid choice for {name}")
            probabilities = answer.get("probabilities")
            if probabilities is not None and (
                not isinstance(probabilities, dict) or set(probabilities) != set(criteria)
            ):
                raise ValueError(f"provider returned invalid probabilities for {name}")
        elif kind == "noul":
            score = answer.get("noul")
            if not isinstance(score, int | float) or not 0 <= score <= 1:
                raise ValueError(f"provider returned an invalid Noul score for {name}")
    return answers


def run_decision(
    request: DecisionRequest,
    pack: QuestionPack,
    *,
    repository_root: str | Path,
) -> tuple[ProviderAttempt, PolicyResult]:
    """Run one request and append immutable provider and policy records.

    Provider scores are stored as features. Without a held-out calibration value,
    policy returns review for every field.
    """
    root = Path(repository_root).resolve()
    parsed = load_config(root)
    config = effective_classification(parsed)
    provider = request.provider
    if request.question_pack_id != pack.id:
        raise ValueError("DecisionRequest question pack does not match the compiled pack")
    pack.validate_provider(provider)
    settings = dict(_provider_config(config, provider))
    requested_model = request.requested_model or (
        "auto"
        if provider == "laya" and settings.get("route_mode", "auto") == "auto"
        else str(settings.get("model", "jev-1.13.0" if provider == "jev" else "english"))
    )
    if request.requested_model:
        if provider == "jev":
            settings["model"] = requested_model
        elif provider == "laya" and requested_model != "auto":
            settings["route_mode"] = "explicit"
            settings["explicit_model"] = requested_model
    maximum = int(config.get("max_input_chars", 12000))
    submitted_state = clip_state(request.state, maximum)
    original_hash = _hash(request.state)
    submitted_hash = _hash(submitted_state)
    if request.state_sha256 and request.state_sha256 != original_hash:
        raise ValueError("DecisionRequest state hash does not match its state")
    if request.question_set_sha256 and request.question_set_sha256 != pack.sha256:
        raise ValueError("DecisionRequest question hash does not match its question pack")
    if provider == "jev" and not re.fullmatch(r"jev-\d+\.\d+\.\d+", requested_model):
        raise ValueError("Jev decision requests require a pinned model version")
    if (
        provider == "laya"
        and requested_model != "auto"
        and requested_model not in {"english", "multilingual", "typed-decisions"}
    ):
        raise ValueError("Laya decision requests require a supported model route")
    text = state_text(submitted_state)
    privacy = {
        "sensitivity": request.sensitivity,
        "personal_data": request.personal_data,
        "remote_processing_allowed": request.remote_processing_allowed,
    }
    project_remote = parsed.remote_processing_default_allowed
    eligible = (
        provider != "jev"
        or remote_eligibility(
            privacy,
            text,
            project_allowed=project_remote,
            question_pack_allows_remote=pack.remote_processing_allowed,
            require_explicit_approval=parsed.remote_processing_require_explicit_approval,
        ).allowed
    )
    if provider == "jev" and preflight(text):
        eligible = False
    request_fingerprint = _hash(
        {
            "target_kind": request.target_kind,
            "target_id": request.target_id,
            "purpose": request.purpose,
            "question_pack_id": pack.id,
            "question_pack_sha256": pack.sha256,
            "state_builder_id": request.state_builder_id,
            "submitted_state_sha256": submitted_hash,
            "provider": provider,
            "requested_model": requested_model,
            "provider_settings": {
                key: value
                for key, value in settings.items()
                if key
                in {
                    "route_mode",
                    "explicit_model",
                    "device",
                    "transport",
                    "max_len",
                    "head_max_len",
                }
            },
            "privacy": privacy,
            "project_remote_allowed": project_remote,
            "runtime": _runtime(provider),
            "consequence_class": request.consequence_class,
            "policy_profile": request.policy_profile,
            "policy_profile_sha256": _hash(parsed.policy_profiles.get(request.policy_profile, {})),
        }
    )

    registry = registry_for_root(root, allow_package_fallback=True)
    attempts_dir = root / ".research" / "decision_attempts"
    prior: list[dict[str, Any]] = []
    for path in sorted(attempts_dir.glob("dpa_*.json")) if attempts_dir.exists() else []:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            registry.validate_filename_identity("provider-attempt", path.name, record)
        except (OSError, UnicodeError, json.JSONDecodeError, SchemaError):
            continue
        if record.get("request_fingerprint") == request_fingerprint:
            prior.append(record)
            if record.get("status") == "completed":
                policy_dir = root / ".research" / "decision_policy_results"
                for policy_path in (
                    sorted(policy_dir.glob("dpr_*.json")) if policy_dir.exists() else []
                ):
                    try:
                        policy_record = json.loads(policy_path.read_text(encoding="utf-8"))
                        registry.validate_filename_identity(
                            "decision-policy-result", policy_path.name, policy_record
                        )
                    except (OSError, UnicodeError, json.JSONDecodeError, SchemaError):
                        continue
                    if policy_record.get("attempt_id") == record["id"]:
                        return _attempt_model(record), _policy_model(policy_record)

    previous = max(prior, key=lambda item: item["attempt"], default=None)
    attempt_id = f"dpa_{uuid.uuid7()}"
    started = time.monotonic()
    status = "blocked" if not eligible else "completed"
    error_category = "privacy_blocked" if not eligible else None
    result: dict[str, Any] = {}
    safe_answers: dict[str, Any] = {}
    try:
        if not eligible:
            raise PermissionError("remote processing policy denied this request")
        result = _predict(provider, submitted_state, pack, config, root)
        safe_answers = _answers(result, pack)
    except Exception as exc:
        status = "blocked" if isinstance(exc, PermissionError) else "failed"
        error_category = (
            "privacy_blocked" if isinstance(exc, PermissionError) else _safe_error_category(exc)
        )

    routing = result.get("routing") if isinstance(result.get("routing"), dict) else None
    usage = result.get("usage") if isinstance(result.get("usage"), dict) else None
    resolved_model = result.get("model") or (routing or {}).get("model")
    if not isinstance(resolved_model, str):
        resolved_model = requested_model if provider == "jev" else None
    attempt_record = {
        "id": attempt_id,
        "schema_version": 1,
        "request_fingerprint": request_fingerprint,
        "attempt": int(previous["attempt"]) + 1 if previous else 1,
        "retry_of": previous["id"] if previous else None,
        "provider": provider,
        "transport": "typesafe-sdk"
        if provider == "jev"
        else settings.get("transport", "inprocess"),
        "requested_model": requested_model,
        "resolved_model": resolved_model,
        "runtime": _runtime(provider),
        "input": {
            "original_sha256": original_hash,
            "submitted_sha256": submitted_hash,
            "submitted_chars": len(text),
            "token_budget": {
                key: settings[key] for key in ("max_len", "head_max_len") if key in settings
            },
        },
        "question_pack_id": pack.id,
        "question_pack_sha256": pack.sha256,
        "answers": safe_answers,
        "routing": routing,
        "usage": usage,
        "elapsed_ms": round((time.monotonic() - started) * 1000),
        "status": status,
        "created_at": _now(),
    }
    if error_category is not None:
        attempt_record["error_category"] = error_category
    write_atomic(
        attempts_dir / f"{attempt_id}.json",
        attempt_record,
        schema_name="provider-attempt",
        registry=registry,
    )

    profile = parsed.policy_profiles.get(request.policy_profile, {})
    field_profiles = profile.get("fields", {}) if isinstance(profile, dict) else {}
    policy_fields = {}
    for name, answer in safe_answers.items():
        target = (
            field_profiles.get(name, {}).get("target_correctness")
            if isinstance(field_profiles, dict)
            else None
        )
        if status != "completed":
            policy_fields[name] = {
                "decision": "review",
                "reason": error_category or "provider_failed",
                "provider": provider,
            }
        else:
            policy_fields[name] = evaluate_field(
                answer if isinstance(answer, dict) else None,
                provider=provider,
                threshold=target if isinstance(target, int | float) else None,
                calibrated_correctness=None,
                abstained=not isinstance(answer, dict) or answer.get("abstain") is True,
            )
    policy_record = {
        "id": f"dpr_{uuid.uuid7()}",
        "schema_version": 1,
        "attempt_id": attempt_id,
        "policy_profile_id": request.policy_profile,
        "policy_sha256": _hash(profile),
        "fields": policy_fields,
        "created_at": _now(),
    }
    write_atomic(
        root / ".research" / "decision_policy_results" / f"{policy_record['id']}.json",
        policy_record,
        schema_name="decision-policy-result",
        registry=registry,
    )
    return _attempt_model(attempt_record), _policy_model(policy_record)


def _attempt_model(record: dict[str, Any]) -> ProviderAttempt:
    return ProviderAttempt(
        id=record["id"],
        request_fingerprint=record["request_fingerprint"],
        attempt=record["attempt"],
        provider=record["provider"],
        requested_model=record["requested_model"],
        resolved_model=record.get("resolved_model"),
        status=record["status"],
        answers=record.get("answers", {}),
        error_category=record.get("error_category"),
        retry_of=record.get("retry_of"),
    )


def _policy_model(record: dict[str, Any]) -> PolicyResult:
    return PolicyResult(
        id=record["id"],
        attempt_id=record["attempt_id"],
        policy_profile_id=record["policy_profile_id"],
        policy_sha256=record["policy_sha256"],
        fields=record["fields"],
    )
