"""Provider-neutral immutable contracts for auditable decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class DecisionRequest:
    purpose: str
    question_pack_id: str
    target_kind: str
    target_id: str
    state_builder_id: str
    state: Any = field(repr=False)
    state_sha256: str = ""
    questions: dict[str, Any] = field(default_factory=dict, repr=False)
    question_set_sha256: str = ""
    sensitivity: str = "unknown"
    personal_data: bool = False
    remote_processing_allowed: bool = False
    consequence_class: str = "metadata-low"
    policy_profile: str = "taxonomy/default"
    provider: str = "laya"
    requested_model: str | None = None


@dataclass(frozen=True)
class ProviderAttempt:
    id: str
    request_fingerprint: str
    attempt: int
    provider: str
    requested_model: str
    resolved_model: str | None
    status: Literal["completed", "failed", "blocked"]
    answers: dict[str, Any] = field(default_factory=dict)
    error_category: str | None = None
    retry_of: str | None = None


@dataclass(frozen=True)
class PolicyResult:
    id: str
    attempt_id: str
    policy_profile_id: str
    policy_sha256: str
    fields: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class ReviewDecision:
    id: str
    target_id: str
    status: Literal["active", "superseded", "adjudicated"]
    reviewer_namespace: str
    resolutions: dict[str, Any]
    supersedes_review_id: str | None = None
    adjudicator: str | None = None
