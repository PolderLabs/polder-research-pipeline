"""Scripts that project structured state into the Obsidian vault and back.

The CLI here is the user-facing surface for:
- vault_audit
- frontmatter_fix
- intake_register
- new_note
- state build / health build
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..paths import default_workspace_root
from ..web import serve
from .classification import (
    cmd_classification_compare,
    cmd_classification_evaluate,
    cmd_classify_existing,
)
from .decision import cmd_decision_run
from .intake import cmd_intake_register, cmd_source_acquire
from .new_note import cmd_new_note
from .state import cmd_build_health, cmd_build_state


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="polder-research")
    parser.add_argument(
        "--root",
        dest="workspace_root",
        default=None,
        help="Research workspace root (default: checkout root or current directory)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("vault-audit", help="Audit vault for link/frontmatter/orphan issues")
    fix = sub.add_parser("frontmatter-fix", help="Fill missing frontmatter fields")
    fix.add_argument("--apply", action="store_true")
    intake = sub.add_parser("intake-register", help="Register a raw intake item")
    intake.add_argument("--file")
    intake.add_argument("--manifest", help="Bulk registration manifest (.csv or .jsonl)")
    intake.add_argument(
        "--dry-run", action="store_true", help="Show a bulk intake plan without writing"
    )
    intake.add_argument("--kind", default="other")
    intake.add_argument("--owner", default="agent")
    intake.add_argument("--status", default="new")
    intake.add_argument("--outcome", default="—")
    intake.add_argument("--set", dest="set_file")
    intake.add_argument("--list", action="store_true")
    acquire = sub.add_parser("source-acquire", help="Acquire content for a registered URL source")
    acquire.add_argument("--source-id", required=True)
    acquire.add_argument("--file", required=True, help="File relative to 90-inbox/raw")
    new = sub.add_parser("new-note", help="Scaffold a vault note")
    new.add_argument("--domain", required=True)
    new.add_argument("--title", required=True)
    new.add_argument("--type", default=None)
    new.add_argument("--status", default="draft")
    new.add_argument("--topic", default=None)
    new.add_argument("--tags", nargs="*", default=[])
    new.add_argument("--related", nargs="*", default=[])
    new.add_argument("--dry-run", action="store_true")
    sub.add_parser("state-build", help="Rebuild .research/state.json")
    sub.add_parser("health-build", help="Rebuild .research/health.json")
    web = sub.add_parser("serve", help="Open the local research control panel")
    web.add_argument("--port", type=int, default=8765)
    replay = sub.add_parser(
        "classify-existing", help="Replay classification over existing evidence"
    )
    replay.add_argument(
        "--kind",
        dest="kinds",
        action="append",
        choices=("source", "segment", "claim", "entity"),
        help="Evidence kind to replay; repeatable",
    )
    replay.add_argument(
        "--dry-run", action="store_true", help="List selected targets without calling a provider"
    )
    replay.add_argument("--limit", type=int, default=None)
    replay.add_argument(
        "--provider",
        choices=("rules", "jev", "laya"),
        default=None,
        help="Deliberately replay with one provider",
    )
    replay.add_argument(
        "--resume", default=None, help="Resume pending or failed targets from a replay job ID"
    )
    compare = sub.add_parser("classification-compare", help="Compare existing provider predictions")
    compare.add_argument("--output", default=None, help="Optional JSON report destination")
    evaluate = sub.add_parser(
        "classification-evaluate", help="Evaluate predictions against human gold JSONL"
    )
    evaluate.add_argument("--gold", required=True, help="Human-authored gold JSON Lines file")
    evaluate.add_argument("--provider", choices=("rules", "jev", "laya"), default=None)
    evaluate.add_argument("--split", choices=("tuning", "held_out"), default="held_out")
    evaluate.add_argument("--output", default=None, help="Optional JSON report destination")
    decision = sub.add_parser("decision-run", help="Run and persist one bounded decision workflow")
    decision.add_argument(
        "--workflow",
        required=True,
        choices=(
            "intake-triage",
            "task-routing",
            "extraction-quality",
            "source-priority",
            "review-priority",
        ),
    )
    decision.add_argument("--target-kind", required=True)
    decision.add_argument("--target-id", required=True)
    decision.add_argument("--state-json", required=True, dest="state_file")
    decision.add_argument("--provider", choices=("laya", "jev"), default="laya")
    decision.add_argument("--role", action="append", dest="roles", default=[])
    decision.add_argument(
        "--sensitivity",
        choices=("unknown", "public", "internal", "confidential", "restricted"),
        default="unknown",
    )
    decision.add_argument("--personal-data", action="store_true")
    decision.add_argument("--remote-processing-allowed", action="store_true")
    decision.add_argument(
        "--research-method",
        choices=("continuous_intelligence", "systematic_evidence_review"),
        default="continuous_intelligence",
    )

    for command_parser in sub.choices.values():
        command_parser.add_argument(
            "--root",
            dest="workspace_root",
            default=argparse.SUPPRESS,
            help="Research workspace root",
        )

    args = parser.parse_args(argv)
    root = (
        Path(args.workspace_root).expanduser().resolve()
        if args.workspace_root
        else default_workspace_root()
    )
    if not root.is_dir():
        parser.error(f"workspace root is not a directory: {root}")

    if args.cmd == "vault-audit":
        from .audit import cmd_vault_audit

        return cmd_vault_audit(root)
    if args.cmd == "frontmatter-fix":
        from .frontmatter import cmd_frontmatter_fix

        return cmd_frontmatter_fix(apply=args.apply, repository_root=root)
    if args.cmd == "intake-register":
        return cmd_intake_register(
            file=args.file,
            kind=args.kind,
            owner=args.owner,
            status=args.status,
            outcome=args.outcome,
            set_file=args.set_file,
            list_=args.list,
            repository_root=root,
            manifest=args.manifest,
            dry_run=args.dry_run,
        )
    if args.cmd == "source-acquire":
        return cmd_source_acquire(args.source_id, args.file, repository_root=root)
    if args.cmd == "new-note":
        return cmd_new_note(
            domain=args.domain,
            title=args.title,
            type_=args.type,
            status=args.status,
            topic=args.topic,
            tags=args.tags,
            related=args.related,
            dry_run=args.dry_run,
            repository_root=root,
        )
    if args.cmd == "state-build":
        return cmd_build_state(root)
    if args.cmd == "health-build":
        return cmd_build_health(root)
    if args.cmd == "serve":
        if not 0 <= args.port <= 65535:
            parser.error("--port must be between 0 and 65535")
        serve(repository_root=root, port=args.port)
        return 0
    if args.cmd == "classify-existing":
        return cmd_classify_existing(
            root=str(root),
            kinds=args.kinds or ["source", "segment", "claim", "entity"],
            dry_run=args.dry_run,
            limit=args.limit,
            provider=args.provider,
            resume=args.resume,
        )
    if args.cmd == "classification-compare":
        return cmd_classification_compare(root=str(root), output=args.output)
    if args.cmd == "classification-evaluate":
        return cmd_classification_evaluate(
            root=str(root),
            gold=args.gold,
            provider=args.provider,
            split=args.split,
            output=args.output,
        )
    if args.cmd == "decision-run":
        return cmd_decision_run(
            workflow=args.workflow,
            target_kind=args.target_kind,
            target_id=args.target_id,
            state_file=args.state_file,
            root=str(root),
            provider=args.provider,
            roles=args.roles,
            sensitivity=args.sensitivity,
            personal_data=args.personal_data,
            remote_processing_allowed=args.remote_processing_allowed,
            research_method=args.research_method,
        )
    return 2


if __name__ == "__main__":
    sys.exit(main())
