#!/usr/bin/env python3
"""
new_note.py — scaffold a correctly-structured vault note.

Creates a note in the right domain folder with valid frontmatter, the right
`type` for its folder, and a `## Related` stub. Enforces kebab-case filenames.

Usage:
    python3 scripts/new_note.py --domain 02-research --title "Foveated Rendering" \
        --tags rendering performance --status draft
    python3 scripts/new_note.py --domain 04-decisions --title "Choose Backend" \
        --type decision --tags backend decision --dry-run

Domains: 00-home 01-project 02-research 03-system 04-decisions
         05-operations 06-sources 90-inbox 99-templates
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
VALID_TYPE = {
    "index", "moc", "guide", "template", "inbox",
    "project", "research", "system", "decision",
    "operation", "experiment", "source",
}
VALID_STATUS = {"current", "draft", "stale", "superseded"}


def slugify(title):
    s = title.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--type", default=None)
    ap.add_argument("--status", default="draft")
    ap.add_argument("--topic", default=None)
    ap.add_argument("--tags", nargs="*", default=[])
    ap.add_argument("--related", nargs="*", default=[],
                    help="wikilink targets to seed the Related section")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.domain not in DOMAIN_TYPE:
        print(f"error: unknown domain '{args.domain}'", file=sys.stderr)
        print(f"valid: {', '.join(DOMAIN_TYPE)}", file=sys.stderr)
        return 2

    note_type = args.type or DOMAIN_TYPE[args.domain]
    if note_type not in VALID_TYPE:
        print(f"error: invalid type '{note_type}'; valid: {sorted(VALID_TYPE)}",
              file=sys.stderr)
        return 2
    if args.status not in VALID_STATUS:
        print(f"error: invalid status '{args.status}'; valid: {sorted(VALID_STATUS)}",
              file=sys.stderr)
        return 2

    slug = slugify(args.title)
    target = REPO_ROOT / args.domain / f"{slug}.md"
    if target.exists():
        print(f"error: {target.relative_to(REPO_ROOT)} already exists", file=sys.stderr)
        return 2

    today = datetime.date.today().isoformat()
    tags = args.tags or ["knowledge-base"]
    tags = [t.lstrip("#").lower().strip() for t in tags]

    lines = ["---", f"type: {note_type}", f"status: {args.status}"]
    if args.topic:
        lines.append(f"topic: {args.topic}")
    lines.append("tags:")
    lines.extend(f"  - {t}" for t in tags)
    lines.append(f"created: {today}")
    lines.append(f"updated: {today}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {args.title}")
    lines.append("")
    lines.append("<!-- One-paragraph summary: what this note establishes and why it matters. -->")
    lines.append("")
    lines.append("## Detail")
    lines.append("")
    lines.append("<!-- Body. Cite primary sources. Label claims Observed / Source-reported / Inference. -->")
    lines.append("")
    lines.append("## Related")
    lines.append("")
    if args.related:
        for r in args.related:
            lines.append(f"- [[{r}]]")
    else:
        lines.append("<!-- - [[domain/related-note|Related note]] -->")
    lines.append("")

    content = "\n".join(lines)

    rel = target.relative_to(REPO_ROOT)
    if args.dry_run:
        print(f"--- would create {rel} ---")
        print(content)
        return 0

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    print(f"created {rel}  (type={note_type}, status={args.status}, tags={tags})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
