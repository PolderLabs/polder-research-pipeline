"""new-note command."""

from __future__ import annotations

import datetime
import re
import sys
import unicodedata
from pathlib import Path

from ..paths import DOMAIN_TYPE, REPO_ROOT, VALID_STATUS, VALID_TYPE
from ..templates import TemplateRegistry, registry

# kind (canonical note type) → canonical template name in 99-templates/.
# Every entry must match a ``*-template.md`` file under that directory;
# missing templates surface as :class:`KeyError` from the registry.
TEMPLATE_BY_KIND: dict[str, str] = {
    "research": "research-note",
    "experiment": "experiment",
    "decision": "decision-record",
    "source": "source-entry",
    "guide": "research-note",
    "project": "research-note",
    "system": "research-note",
    "operation": "research-note",
    "inbox": "intake-record",
    "template": "research-note",
    "index": "research-note",
    "moc": "research-note",
}


def slugify(title: str) -> str:
    """Return a filesystem-safe ASCII slug derived from ``title``.

    The slug is built by:

    1. ``unicodedata.normalize('NFKD', ...)`` — separates base characters
       from combining accents so ``é`` decomposes to ``e`` + combining acute.
    2. Encoding to ASCII with ``errors="ignore"`` — drops the combining
       marks, leaving only the base ASCII characters.
    3. Lowercasing and collapsing any non-alphanumeric run to ``-``.

    The result is stable across Unicode input (``"Café — Étude"`` →
    ``"cafe-etude"``) while remaining filesystem-portable.
    """
    decomposed = unicodedata.normalize("NFKD", title)
    ascii_folded = decomposed.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_folded.lower().strip()
    collapsed = re.sub(r"[^a-z0-9]+", "-", lowered)
    return re.sub(r"-+", "-", collapsed).strip("-")


def resolve_template(
    kind: str,
    *,
    template_registry: TemplateRegistry | None = None,
) -> str:
    """Return the canonical template text for ``kind`` via the registry."""
    name = TEMPLATE_BY_KIND.get(kind, "research-note")
    reg = template_registry if template_registry is not None else registry(REPO_ROOT)
    return reg.resolve(name).text


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

    # Resolve template body through the canonical registry; fall back to a
    # minimal scaffold if the registry cannot find a template for the kind.
    template_text = resolve_template(note_type)

    lines = ["---", f"type: {note_type}", f"status: {status}"]
    if topic:
        lines.append(f"topic: {topic}")
    lines.append("tags:")
    lines.extend(f"  - {t}" for t in tlist)
    lines.append(f"created: {today}")
    lines.append(f"updated: {today}")
    lines.extend(["---", "", f"# {title}", ""])

    if template_text.strip():
        lines.append(template_text.rstrip())

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


__all__ = [
    "DOMAIN_TYPE",
    "TEMPLATE_BY_KIND",
    "cmd_new_note",
    "resolve_template",
    "slugify",
]