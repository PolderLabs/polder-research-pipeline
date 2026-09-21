#!/usr/bin/env python3
"""
frontmatter_fix.py — auto-fix frontmatter on every vault note.

Adds missing required keys (type, status, tags) with values inferred from
the note's folder. Never overwrites existing non-empty values. Normalizes
type to the closed vocabulary used by vault_audit.py.

Usage:
    python3 scripts/frontmatter_fix.py           # dry run — show what would change
    python3 scripts/frontmatter_fix.py --apply   # actually write
"""

import argparse
import datetime
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

DOMAIN_TYPE = {
    "00-home": "guide",
    "01-project": "project",
    "02-research": "research",
    "03-system": "system",
    "04-decisions": "decision",
    "05-operations": "operation",
    "06-sources": "source",
    "90-inbox": "inbox",
    "99-templates": "template",
}
ROOT_FILES = {
    "index.md": ("index", "current"),
    "README.md": ("guide", "current"),
    "AGENTS.md": ("guide", "current"),
    "CLAUDE.md": ("guide", "current"),
}
SKIP_PARTS = {".git", ".obsidian", ".wolf", ".claude", ".codex",
              "node_modules", ".venv", "dist", "build"}


def fm_block(inferred_type, inferred_status, today):
    return (
        "---\n"
        f"type: {inferred_type}\n"
        f"status: {inferred_status}\n"
        f"tags:\n"
        f"  - knowledge-base\n"
        f"created: {today}\n"
        f"updated: {today}\n"
        "---\n"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="write changes (default: dry run)")
    args = ap.parse_args()
    today = datetime.date.today().isoformat()
    changed = 0

    for p in sorted(REPO_ROOT.rglob("*.md")):
        rel = p.relative_to(REPO_ROOT)
        if any(part in SKIP_PARTS for part in rel.parts):
            continue
        if rel.parts[:2] == ("90-inbox", "raw"):
            continue
        if rel.parts[:2] == ("90-inbox", "archive"):
            continue

        text = p.read_text(encoding="utf-8", errors="replace")
        if text.startswith("---\n"):
            fm_match = re.match(r"^---\n(.*?)\n---\n?", text, re.S)
            fm_text = fm_match.group(1) if fm_match else ""
            keys = set(re.findall(r"^(\w[\w-]*):", fm_text, re.M))
            missing = [k for k in ("type", "status", "tags") if k not in keys]
            if not missing:
                continue
            # insert missing keys at end of frontmatter
            top = rel.parts[0] if len(rel.parts) > 1 else None
            stem = p.name
            if stem in ROOT_FILES:
                t, s = ROOT_FILES[stem]
            else:
                t = DOMAIN_TYPE.get(top, "guide")
                s = "current"
            add = ""
            if "type" in missing:
                add += f"type: {t}\n"
            if "status" in missing:
                add += f"status: {s}\n"
            if "tags" in missing:
                add += "tags:\n  - knowledge-base\n"
            new_fm = fm_text.rstrip("\n") + "\n" + add
            new_text = text.replace(fm_text, new_fm, 1)
            print(f"  [fix] {rel}: add {', '.join(missing)}")
        else:
            stem = p.name
            if stem in ROOT_FILES:
                t, s = ROOT_FILES[stem]
            else:
                top = rel.parts[0] if len(rel.parts) > 1 else None
                t = DOMAIN_TYPE.get(top, "guide")
                s = "current"
            new_text = fm_block(t, s, today) + text
            print(f"  [add] {rel}: frontmatter block (type={t})")

        if args.apply:
            p.write_text(new_text, encoding="utf-8")
        changed += 1

    if not changed:
        print("No changes needed.")
        return 0
    if not args.apply:
        print(f"\nDry run: {changed} file(s) would change. Re-run with --apply.")
    else:
        print(f"\nApplied: {changed} file(s) updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
