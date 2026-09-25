"""Pinned TypeSafe SDK adapter with a fixed first-party API boundary."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_API_ROOT = "https://api.typesafe.ai"


def predict(
    state: Any, questions: dict[str, Any], config: dict[str, Any], repository_root: Path | None
) -> dict[str, Any]:
    try:
        from typesafe_sdk import RetryPolicy, TypeSafeClient
    except ImportError as exc:
        raise RuntimeError(
            "Jev selected; install the optional dependency with `pip install 'polder-research-pipeline[jev]'`"
        ) from exc

    base_url = config.get("base_url", _API_ROOT)
    if base_url != _API_ROOT:
        raise ValueError("Jev SDK base URL is fixed to https://api.typesafe.ai")
    key_env = config.get("api_key_env", "TYPESAFE_API_KEY")
    api_key = os.environ.get(key_env)
    if not api_key:
        from ...classification import _saved_api_key

        api_key = _saved_api_key(key_env, repository_root)
    if not api_key:
        raise RuntimeError(f"Jev selected but {key_env} is not set")

    retries = config.get("max_retries", 2)
    budget = config.get("total_budget_seconds", 30)
    timeout = config.get("timeout_seconds", 30)
    if isinstance(retries, bool) or not isinstance(retries, int) or not 0 <= retries <= 5:
        raise ValueError("classification.jev.max_retries must be an integer from 0 to 5")
    if isinstance(timeout, bool) or not isinstance(timeout, int | float) or not 1 <= timeout <= 120:
        raise ValueError("classification.jev.timeout_seconds must be between 1 and 120")
    if isinstance(budget, bool) or not isinstance(budget, int | float) or not 1 <= budget <= 120:
        raise ValueError("classification.jev.total_budget_seconds must be between 1 and 120")
    model = config.get("model", "jev-1.13.0")
    try:
        with TypeSafeClient(
            api_key=api_key,
            base_url=_API_ROOT,
            model=model,
            retry=RetryPolicy(max_retries=retries, timeout=float(min(timeout, budget))),
        ) as client:
            response = client.system_one(state=state, questions=questions)
        result = response.model_dump(mode="json")
    except Exception as exc:
        # Never serialize provider response bodies or SDK debug data to the ledger.
        status = getattr(exc, "status", None)
        if status == 401:
            raise RuntimeError("Jev authentication failed (HTTP status 401)") from exc
        if status in {408, 429, 500, 502, 503, 504}:
            raise RuntimeError(f"Jev request failed (HTTP status {status})") from exc
        if isinstance(exc, TimeoutError):
            raise RuntimeError("Jev request timed out") from exc
        raise RuntimeError("Jev classification request failed") from exc
    if not isinstance(result, dict) or not isinstance(result.get("answers"), dict):
        raise RuntimeError("Jev returned an invalid System One response")
    result.setdefault("model", model)
    return result
