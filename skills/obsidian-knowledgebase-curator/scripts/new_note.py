#!/usr/bin/env python3
"""new_note.py — CLI shim delegating to polder_research.scripts.new_note."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "_new_note_impl",
    REPO_ROOT / "src" / "polder_research" / "scripts" / "new_note.py",
)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
sys.modules["_new_note_impl"] = _mod
_spec.loader.exec_module(_mod)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--type", default=None)
    ap.add_argument("--status", default="draft")
    ap.add_argument("--topic", default=None)
    ap.add_argument("--tags", nargs="*", default=[])
    ap.add_argument("--related", nargs="*", default=[])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    return _mod.cmd_new_note(
        domain=args.domain,
        title=args.title,
        type_=args.type,
        status=args.status,
        topic=args.topic,
        tags=args.tags,
        related=args.related,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    sys.exit(main())
