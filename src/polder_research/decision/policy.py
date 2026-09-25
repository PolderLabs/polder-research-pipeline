"""Deterministic provider-output gating; raw scores remain provider-native."""

from __future__ import annotations

from typing import Any


def evaluate_field(
    answer: dict[str, Any] | None,
    *,
    provider: str,
    threshold: float | None,
    calibrated_correctness: float | None = None,
    abstained: bool = False,
) -> dict[str, Any]:
    if abstained or not isinstance(answer, dict):
        return {"decision": "review", "reason": "abstained", "provider": provider}
    signal = answer.get("answer_confidence") if provider == "laya" else answer.get("confidence")
    if not isinstance(signal, int | float) or not 0 <= signal <= 1:
        signal = None
    if calibrated_correctness is None or not 0 <= calibrated_correctness <= 1 or threshold is None:
        return {
            "decision": "review",
            "reason": "calibration_unavailable",
            "provider": provider,
            "provider_signal": signal,
        }
    if calibrated_correctness < threshold:
        return {
            "decision": "review",
            "reason": "below_target_correctness",
            "provider": provider,
            "provider_signal": signal,
            "calibrated_correctness": calibrated_correctness,
            "target_correctness": threshold,
        }
    return {
        "decision": "apply",
        "reason": "calibrated_target_met",
        "provider": provider,
        "provider_signal": signal,
        "calibrated_correctness": calibrated_correctness,
        "target_correctness": threshold,
    }
