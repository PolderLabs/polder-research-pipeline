#!/usr/bin/env python3
"""
frontmatter_fix.py — fill missing frontmatter fields (P0-corrected).

Implements AUDIT.md §3.13-3.16:
- Uses shared scan scope (SKIP_PARTS) from polder_research.paths
- Never overwrites existing non-empty values
- Renamed/clarified behavior: this script FILLS missing fields, does not
  normalize existing values
- Use the same scan universe as vault_audit.py
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

from polder_research.paths import (
    DOMAIN_TYPE,
    REPO_ROOT,
    SKIP_PARTS,
    VAULT_DIRS,
    in_skipped_prefix,
)

VAULT_DOMAIN_DIRS: tuple[str, ...] = tuple(d.split("/", 1)[1] for d in VAULT_DIRS)


def parse_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    return m.group(1) if m else None


def infer_type(path: Path, repository_root: Path | None = None) -> str:
    """Return the conventional type for ``path`` based on its vault domain.

    Works both before the vault move (domain is the first path segment)
    and after (domain is the second segment under ``knowledge-base/``).
    """
    root = repository_root or REPO_ROOT
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        parts = path.parts
    if not parts:
        return ""
    domain = parts[0]
    if domain == "knowledge-base" and len(parts) >= 2:
        domain = parts[1]
    if domain == "knowledge-base":
        return ""
    if domain == "90-inbox" and path.name == "raw":
        return "guide"
    if domain == "90-inbox" and "raw" in parts:
        return "inbox"
    # Try the bare domain first (legacy layout), then the vault-prefixed key.
    if domain in DOMAIN_TYPE:
        return DOMAIN_TYPE[domain]
    if len(parts) >= 2:
        vault_key = f"{parts[0]}/{parts[1]}"
        if vault_key in DOMAIN_TYPE:
            return DOMAIN_TYPE[vault_key]
    return ""


def fm_block(inferred_type: str, today: str) -> str:
    lines = ["---", f"type: {inferred_type}", "status: draft", "tags:"]
    lines.append("  - knowledge-base")
    lines.append(f"created: {today}")
    lines.append(f"updated: {today}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def needs_frontmatter(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False
    return parse_frontmatter(text) is None


def build_minimal_frontmatter(path: Path, today: str, repository_root: Path | None = None) -> str:
    inferred = infer_type(path, repository_root) or "guide"
    return fm_block(inferred, today)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=None, help="Research workspace root")
    ap.add_argument("--apply", action="store_true", help="write changes")
    args = ap.parse_args(argv)
    root = args.root.resolve() if args.root is not None else REPO_ROOT

    today = datetime.date.today().isoformat()
    pending = []

    for p in root.rglob("*.md"):
        rel = p.relative_to(root)
        if any(part in SKIP_PARTS for part in rel.parts):
            continue
        if in_skipped_prefix(rel):
            continue
        # The vault root is the first path segment (``knowledge-base``);
        # its children are the canonical domain folders from VAULT_DIRS.
        if rel.parts and rel.parts[0] != "knowledge-base":
            continue
        # Reject anything that isn't a direct child of the vault root
        # (e.g. ``knowledge-base/.obsidian/...``).
        if len(rel.parts) >= 2 and f"{rel.parts[0]}/{rel.parts[1]}" not in VAULT_DIRS:
            continue
        if needs_frontmatter(p):
            pending.append(p)

    if not pending:
        print("no notes need frontmatter")
        return 0

    if not args.apply:
        print(f"would fill frontmatter in {len(pending)} note(s) (dry run):")
        for p in pending[:20]:
            print(f"  {p.relative_to(root)}")
        if len(pending) > 20:
            print(f"  ... and {len(pending) - 20} more")
        return 0

    written = 0
    for p in pending:
        try:
            body = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        frontmatter = build_minimal_frontmatter(p, today, root)
        new_text = frontmatter + "\n" + body.lstrip()
        p.write_text(new_text, encoding="utf-8")
        written += 1

    print(f"wrote frontmatter in {written} note(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
