"""Bounded reusable workflows built from versioned decision question packs."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from ..engine import run_decision
from ..models import DecisionRequest, PolicyResult, ProviderAttempt
from ..question_packs import (
    EXTRACTION_QUALITY,
    INTAKE_TRIAGE,
    REVIEW_PRIORITY,
    SOURCE_PRIORITY,
    QuestionPack,
    task_routing_pack,
)
from ..state_builders import canonical_json


def run_workflow(
    name: str,
    state: Any,
    *,
    target_kind: str,
    target_id: str,
    repository_root: str | Path,
    provider: str = "laya",
    roles: list[str] | None = None,
    sensitivity: str = "unknown",
    personal_data: bool = False,
    remote_processing_allowed: bool = False,
    research_method: str = "continuous_intelligence",
) -> tuple[ProviderAttempt, PolicyResult]:
    """Build and execute one bounded workflow request."""
    packs: dict[str, QuestionPack] = {
        "intake-triage": INTAKE_TRIAGE,
        "extraction-quality": EXTRACTION_QUALITY,
        "source-priority": SOURCE_PRIORITY,
        "review-priority": REVIEW_PRIORITY,
    }
    if name == "task-routing":
        pack = task_routing_pack(roles or [])
    else:
        try:
            pack = packs[name]
        except KeyError as exc:
            raise ValueError(f"unknown decision workflow: {name!r}") from exc
    if name == "source-priority" and research_method != "continuous_intelligence":
        raise ValueError(
            "source prioritization cannot screen or exclude systematic-review candidates"
        )
    state_hash = hashlib.sha256(canonical_json(state).encode("utf-8")).hexdigest()
    request = DecisionRequest(
        purpose=pack.purpose,
        question_pack_id=pack.id,
        target_kind=target_kind,
        target_id=target_id,
        state_builder_id=f"{name}/default@1",
        state=state,
        state_sha256=state_hash,
        questions=pack.questions,
        question_set_sha256=pack.sha256,
        sensitivity=sensitivity,
        personal_data=personal_data,
        remote_processing_allowed=remote_processing_allowed,
        consequence_class=pack.consequence_class,
        policy_profile=f"{pack.purpose}/default",
        provider=provider,
    )
    return run_decision(request, pack, repository_root=repository_root)


def task_route_is_permitted(role: str, *, permitted_roles: list[str], action: str) -> bool:
    """Revalidate the proposal against both shortlist and deterministic role policy."""
    if role not in permitted_roles:
        return False
    from ...agents import role_can

    return role_can(role, action)


__all__ = ["run_workflow", "task_route_is_permitted"]
