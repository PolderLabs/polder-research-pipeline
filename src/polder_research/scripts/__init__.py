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
    return 2


if __name__ == "__main__":
    sys.exit(main())
