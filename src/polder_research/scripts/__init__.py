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

from ..web import serve
from .audit import cmd_vault_audit
from .classification import (
    cmd_classification_compare,
    cmd_classification_evaluate,
    cmd_classify_existing,
)
from .frontmatter import cmd_frontmatter_fix
from .intake import cmd_intake_register
from .new_note import cmd_new_note
from .state import cmd_build_health, cmd_build_state


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="polder-research")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("vault-audit", help="Audit vault for link/frontmatter/orphan issues")
    fix = sub.add_parser("frontmatter-fix", help="Fill missing frontmatter fields")
    fix.add_argument("--apply", action="store_true")
    intake = sub.add_parser("intake-register", help="Register a raw intake item")
    intake.add_argument("--file")
    intake.add_argument("--kind", default="other")
    intake.add_argument("--owner", default="agent")
    intake.add_argument("--status", default="new")
    intake.add_argument("--outcome", default="—")
    intake.add_argument("--set", dest="set_file")
    intake.add_argument("--list", action="store_true")
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
    replay = sub.add_parser("classify-existing", help="Replay classification over existing evidence")
    replay.add_argument("--root", default=None, help="Repository root (default: current directory)")
    replay.add_argument("--kind", dest="kinds", action="append", choices=("source", "segment", "claim", "entity"), help="Evidence kind to replay; repeatable")
    replay.add_argument("--dry-run", action="store_true", help="List selected targets without calling a provider")
    replay.add_argument("--limit", type=int, default=None)
    replay.add_argument("--provider", choices=("rules", "jev", "laya"), default=None, help="Deliberately replay with one provider")
    replay.add_argument("--resume", default=None, help="Resume pending or failed targets from a replay job ID")
    compare = sub.add_parser("classification-compare", help="Compare existing provider predictions")
    compare.add_argument("--root", default=None)
    compare.add_argument("--output", default=None, help="Optional JSON report destination")
    evaluate = sub.add_parser("classification-evaluate", help="Evaluate predictions against human gold JSONL")
    evaluate.add_argument("--root", default=None)
    evaluate.add_argument("--gold", required=True, help="Human-authored gold JSON Lines file")
    evaluate.add_argument("--provider", choices=("rules", "jev", "laya"), default=None)
    evaluate.add_argument("--split", choices=("tuning", "held_out"), default="held_out")
    evaluate.add_argument("--output", default=None, help="Optional JSON report destination")

    args = parser.parse_args(argv)

    if args.cmd == "vault-audit":
        return cmd_vault_audit()
    if args.cmd == "frontmatter-fix":
        return cmd_frontmatter_fix(apply=args.apply)
    if args.cmd == "intake-register":
        return cmd_intake_register(
            file=args.file,
            kind=args.kind,
            owner=args.owner,
            status=args.status,
            outcome=args.outcome,
            set_file=args.set_file,
            list_=args.list,
        )
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
        )
    if args.cmd == "state-build":
        return cmd_build_state()
    if args.cmd == "health-build":
        return cmd_build_health()
    if args.cmd == "serve":
        if not 0 <= args.port <= 65535:
            parser.error("--port must be between 0 and 65535")
        serve(port=args.port)
        return 0
    if args.cmd == "classify-existing":
        return cmd_classify_existing(root=args.root, kinds=args.kinds or ["source", "segment", "claim", "entity"], dry_run=args.dry_run, limit=args.limit, provider=args.provider, resume=args.resume)
    if args.cmd == "classification-compare":
        return cmd_classification_compare(root=args.root, output=args.output)
    if args.cmd == "classification-evaluate":
        return cmd_classification_evaluate(root=args.root, gold=args.gold, provider=args.provider, split=args.split, output=args.output)
    return 2


if __name__ == "__main__":
    sys.exit(main())
