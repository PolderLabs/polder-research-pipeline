"""CLI adapter for bounded decision workflows."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from ..decision.workflows import run_workflow


def cmd_decision_run(
    *,
    workflow: str,
    target_kind: str,
    target_id: str,
    state_file: str,
    root: str | None,
    provider: str,
    roles: list[str],
    sensitivity: str,
    personal_data: bool,
    remote_processing_allowed: bool,
    research_method: str,
) -> int:
    state = json.loads(Path(state_file).read_text(encoding="utf-8"))
    attempt, policy = run_workflow(
        workflow,
        state,
        target_kind=target_kind,
        target_id=target_id,
        repository_root=root or ".",
        provider=provider,
        roles=roles,
        sensitivity=sensitivity,
        personal_data=personal_data,
        remote_processing_allowed=remote_processing_allowed,
        research_method=research_method,
    )
    print(json.dumps({"attempt": asdict(attempt), "policy_result": asdict(policy)}, indent=2))
    return 0
