"""CLI adapters for classification replay, comparison, and evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..classification_ops import comparison_report, evaluate_gold, load_human_gold, replay_existing


def _emit(value: dict[str, Any], output: str | None) -> int:
    rendered = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


def cmd_classify_existing(
    *,
    root: str | None,
    kinds: list[str],
    dry_run: bool,
    limit: int | None,
    provider: str | None,
    resume: str | None,
) -> int:
    return _emit(
        replay_existing(
            root, kinds=kinds, dry_run=dry_run, limit=limit, provider=provider, resume_job_id=resume
        ),
        None,
    )


def cmd_classification_compare(*, root: str | None, output: str | None) -> int:
    return _emit(comparison_report(root), output)


def cmd_classification_evaluate(
    *, root: str | None, gold: str, provider: str | None, split: str, output: str | None
) -> int:
    return _emit(
        evaluate_gold(load_human_gold(gold), repository_root=root, provider=provider, split=split),
        output,
    )
