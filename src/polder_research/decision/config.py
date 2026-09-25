"""Validated, immutable decision configuration shared by decision clients."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml

from ..schemas import registry_for_root


@dataclass(frozen=True)
class DecisionConfig:
    default_provider: str
    remote_processing_require_explicit_approval: bool
    remote_processing_default_allowed: bool
    classification: dict[str, Any]
    policy_profiles: dict[str, Any] = field(default_factory=dict)
    provider_settings: dict[str, Any] = field(default_factory=dict)


def effective_classification(config: DecisionConfig) -> dict[str, Any]:
    """Merge decision-provider settings over legacy classification settings."""
    result = dict(config.classification)
    result["provider"] = config.default_provider
    result["remote_processing"] = {
        "require_explicit_approval": config.remote_processing_require_explicit_approval,
        "default_allowed": config.remote_processing_default_allowed,
    }
    result["policy_profiles"] = config.policy_profiles
    for provider, values in config.provider_settings.items():
        if provider not in {"jev", "laya"} or not isinstance(values, dict):
            continue
        result[provider] = {**result.get(provider, {}), **values}
        retry = values.get("retry")
        if provider == "jev" and isinstance(retry, dict):
            result[provider]["max_retries"] = retry.get("max_retries", 2)
            result[provider]["total_budget_seconds"] = retry.get("total_budget_seconds", 30)
    return result


def load_config(repository_root: str | Path) -> DecisionConfig:
    """Load and validate the repository configuration before side effects."""
    root = Path(repository_root)
    path = root / "knowledge-base" / "research.config.yaml"
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot read research config: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("research config must be a YAML mapping")
    return validate_config(value, root)


def validate_config(value: Any, repository_root: str | Path) -> DecisionConfig:
    """Validate an already parsed configuration with the canonical schema."""
    root = Path(repository_root)
    try:
        registry_for_root(root, allow_package_fallback=True).validate("research-config", value)
    except KeyError as exc:
        raise ValueError("research-config schema is not installed") from exc
    except Exception as exc:
        raise ValueError(f"invalid research config: {exc}") from exc

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

    def check_secrets(item: Any) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                normalized = str(key).casefold()
                if normalized in secret_fields or normalized.endswith(
                    ("_secret", "_token", "_password", "_credential")
                ):
                    raise ValueError("credentials belong in the local secret store")
                check_secrets(child)
        elif isinstance(item, list):
            for child in item:
                check_secrets(child)

    check_secrets(value)

    classification = value.get("classification", {})
    decision = value.get("decision", {})
    if not isinstance(classification, dict) or not isinstance(decision, dict):
        raise ValueError("classification and decision config must be mappings")
    provider = decision.get("default_provider", classification.get("provider", "rules"))
    if provider not in {"rules", "jev", "laya"}:
        raise ValueError("decision.default_provider must be rules, jev, or laya")
    if (
        decision.get("default_provider")
        and classification.get("provider")
        and decision["default_provider"] != classification["provider"]
    ):
        raise ValueError(
            "decision.default_provider must match classification.provider during migration"
        )
    remote = decision.get("remote_processing", {})
    if not isinstance(remote, dict):
        raise ValueError("decision.remote_processing must be a mapping")
    if classification.get("enabled", True) and provider == "jev":
        if remote.get("default_allowed", False) is not True:
            raise ValueError("Jev requires explicit remote-processing approval")
    if classification.get("routing", {}).get("sensitive_provider") == "jev":
        raise ValueError("sensitive classification cannot use a remote provider")
    providers = decision.get("providers", {})
    if not isinstance(providers, dict):
        raise ValueError("decision.providers must be a mapping")
    jev = {**classification.get("jev", {}), **(providers.get("jev", {}) or {})}
    if isinstance(jev, dict):
        if jev.get("base_url", "https://api.typesafe.ai") != "https://api.typesafe.ai":
            raise ValueError("Jev SDK base URL is fixed to the first-party API")
        model = jev.get("model", "jev-1.13.0")
        if not isinstance(model, str) or not re.fullmatch(r"jev-\d+\.\d+\.\d+", model):
            raise ValueError("Jev model must be pinned to an exact version")
        retry = jev.get("retry", {})
        if retry and not isinstance(retry, dict):
            raise ValueError("decision.providers.jev.retry must be a mapping")
        retries = retry.get("max_retries", jev.get("max_retries", 2))
        if isinstance(retries, bool) or not isinstance(retries, int) or not 0 <= retries <= 5:
            raise ValueError("Jev max_retries must be an integer from 0 to 5")
        budget = retry.get("total_budget_seconds", jev.get("total_budget_seconds", 30))
        if (
            isinstance(budget, bool)
            or not isinstance(budget, int | float)
            or not 1 <= budget <= 120
        ):
            raise ValueError("Jev total budget must be between 1 and 120 seconds")
    laya = {**classification.get("laya", {}), **(providers.get("laya", {}) or {})}
    if isinstance(laya, dict):
        model = laya.get("explicit_model") or laya.get("model", "english")
        if model not in {"english", "multilingual", "typed-decisions"}:
            raise ValueError("Laya model must be english, multilingual, or typed-decisions")
        if laya.get("route_mode", "auto") not in {"auto", "explicit"}:
            raise ValueError("Laya route_mode must be auto or explicit")
        if laya.get("transport", "inprocess") not in {"inprocess", "local-http"}:
            raise ValueError("Laya transport must be inprocess or local-http")
        if laya.get("route_mode") == "explicit" and laya.get(
            "explicit_model", laya.get("model")
        ) not in {"english", "multilingual", "typed-decisions"}:
            raise ValueError("explicit Laya route requires a supported model")
        if laya.get("transport") == "local-http":
            endpoint = laya.get("endpoint")
            parsed = urlsplit(endpoint) if isinstance(endpoint, str) else None
            if (
                parsed is None
                or parsed.scheme != "http"
                or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
            ):
                raise ValueError("Laya sidecar endpoint must use loopback HTTP")
        max_loaded = laya.get("max_loaded", 2)
        if (
            isinstance(max_loaded, bool)
            or not isinstance(max_loaded, int)
            or not 1 <= max_loaded <= 16
        ):
            raise ValueError("Laya max_loaded must be an integer from 1 to 16")
        for key in ("max_len", "head_max_len"):
            budget = laya.get(key)
            values = (
                budget.values()
                if isinstance(budget, dict)
                else [budget]
                if budget is not None
                else []
            )
            if any(
                isinstance(item, bool) or not isinstance(item, int) or item < 1 for item in values
            ):
                raise ValueError(f"Laya {key} values must be positive integers")
    return DecisionConfig(
        default_provider=provider,
        remote_processing_require_explicit_approval=remote.get("require_explicit_approval", True),
        remote_processing_default_allowed=remote.get("default_allowed", False),
        classification=classification,
        policy_profiles=decision.get("policy_profiles", {}),
        provider_settings=decision.get("providers", {}),
    )
