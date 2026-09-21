#!/usr/bin/env python3
"""
intake_register.py — register a dropped raw item in the inbox manifest.

P0 fixes (AUDIT.md §3.5-3.9):
- Tags argument removed (was accepted but not stored).
- First-row placement corrected (no longer appends after explanatory sections).
- Substring filename matching replaced with exact match.

This script is a thin CLI shim that delegates to polder_research.scripts.intake.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "_intake_impl",
    REPO_ROOT / "src" / "polder_research" / "scripts" / "intake.py",
)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
sys.modules["_intake_impl"] = _mod
_spec.loader.exec_module(_mod)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="raw filename (as it appears in 90-inbox/raw/)")
    ap.add_argument("--kind", default="other")
    ap.add_argument("--owner", default="agent")
    ap.add_argument("--status", default="new")
    ap.add_argument("--outcome", default="—")
    ap.add_argument("--set", dest="set_file",
                    help="update an existing row by exact filename")
    ap.add_argument("--list", action="store_true", help="list current queue")
    args = ap.parse_args()
    return _mod.cmd_intake_register(
        file=args.file,
        kind=args.kind,
        owner=args.owner,
        status=args.status,
        outcome=args.outcome,
        set_file=args.set_file,
        list_=args.list,
    )


if __name__ == "__main__":
    sys.exit(main())
