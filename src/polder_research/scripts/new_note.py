"""new-note command."""

from __future__ import annotations

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

VALID_TYPE = frozenset(
    {
        "index", "moc", "guide", "template", "inbox",
        "project", "research", "system", "decision",
        "operation", "experiment", "source",
    }
)
VALID_STATUS = frozenset({"current", "draft", "stale", "superseded"})


def slugify(title: str) -> str:
    s = title.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")


def cmd_new_note(
    domain: str,
    title: str,
    type_: str | None = None,
    status: str = "draft",
    topic: str | None = None,
    tags: list[str] | None = None,
    related: list[str] | None = None,
    dry_run: bool = False,
) -> int:
    if domain not in DOMAIN_TYPE:
        print(f"error: unknown domain '{domain}'", file=sys.stderr)
        print(f"valid: {', '.join(DOMAIN_TYPE)}", file=sys.stderr)
        return 2

    note_type = type_ or DOMAIN_TYPE[domain]
    if note_type not in VALID_TYPE:
        print(f"error: invalid type '{note_type}'; valid: {sorted(VALID_TYPE)}", file=sys.stderr)
        return 2
    if status not in VALID_STATUS:
        print(f"error: invalid status '{status}'; valid: {sorted(VALID_STATUS)}", file=sys.stderr)
        return 2

    slug = slugify(title)
    target = REPO_ROOT / domain / f"{slug}.md"
    if target.exists():
        print(f"error: {target.relative_to(REPO_ROOT)} already exists", file=sys.stderr)
        return 2

    today = datetime.date.today().isoformat()
    tlist = tags or ["knowledge-base"]
    tlist = [t.lstrip("#").lower().strip() for t in tlist]

    lines = ["---", f"type: {note_type}", f"status: {status}"]
    if topic:
        lines.append(f"topic: {topic}")
    lines.append("tags:")
    lines.extend(f"  - {t}" for t in tlist)
    lines.append(f"created: {today}")
    lines.append(f"updated: {today}")
    lines.append("---", "", f"# {title}", "")

    if related:
        lines.append("## Related")
        for r in related:
            lines.append(f"- [[{r}]]")

    content = "\n".join(lines) + "\n"
    if dry_run:
        print(content)
        return 0

    target.write_text(content, encoding="utf-8")
    print(f"created: {target.relative_to(REPO_ROOT)}")
    return 0
