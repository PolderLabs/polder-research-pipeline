"""Conservative remote-processing eligibility and local preflight helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_SENSITIVE_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"\b(?:\+?\d[\d .()-]{7,}\d)\b"),
)


@dataclass(frozen=True)
class PrivacyDecision:
    allowed: bool
    reason: str
    sensitivity: str
    personal_data: bool


def preflight(text: str, forbidden_patterns: list[str] | None = None) -> tuple[str, ...]:
    """Return category-only matches; never return the matched secret or PII."""
    categories = [
        name
        for name, pattern in zip(
            ("private-key", "email", "phone"), _SENSITIVE_PATTERNS, strict=True
        )
        if pattern.search(text)
    ]
    for pattern in forbidden_patterns or []:
        if re.search(pattern, text):
            categories.append("project-forbidden-pattern")
    return tuple(categories)


def remote_eligibility(
    state: dict[str, Any],
    text: str,
    *,
    project_allowed: bool,
    question_pack_allows_remote: bool = True,
    require_explicit_approval: bool = True,
) -> PrivacyDecision:
    sensitivity = str(state.get("sensitivity", "unknown"))
    personal_data = bool(state.get("personal_data", False))
    if sensitivity != "public" or personal_data:
        return PrivacyDecision(False, "sensitive_or_personal", sensitivity, personal_data)
    if not project_allowed:
        return PrivacyDecision(False, "project_approval_missing", sensitivity, personal_data)
    if not question_pack_allows_remote:
        return PrivacyDecision(False, "question_pack_disallows_remote", sensitivity, personal_data)
    if require_explicit_approval and state.get("remote_processing_allowed") is not True:
        return PrivacyDecision(False, "target_approval_missing", sensitivity, personal_data)
    if preflight(text):
        return PrivacyDecision(False, "local_preflight_flagged", sensitivity, personal_data)
    return PrivacyDecision(True, "eligible", sensitivity, personal_data)
