#!/usr/bin/env python3
"""
vault_audit.py — full vault integrity check (AUDIT.md §33, §43).

This script is the single authoritative vault integrity check. It reads
the scan scope from ``polder_research.paths`` so it cannot disagree with
``frontmatter_fix.py`` about what is in scope.

Exit code:
- 0  : clean (no errors)
- 1  : errors found
- 2  : internal failure

Categories:
- links      : Markdown links + wikilinks resolve
- orphans    : durable notes with no incoming links
- frontmatter: required keys present; type/status in vocabulary
- tags       : kebab-case, lowercase
- structure  : directory layout
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

from polder_research.paths import (
    DOMAIN_TYPE,
    DURABLE_EXCLUDE,
    NO_ORPHAN_CHECK,
    SKIP_PARTS,
    VALID_STATUS,
    VALID_TYPE,
    VAULT_DIRS,
)
from polder_research.paths import (
    REPO_ROOT as CANONICAL_REPO_ROOT,
)
from polder_research.schemas import registry as schema_registry

# Retained as the script's default target so existing callers can override it.
REPO_ROOT = CANONICAL_REPO_ROOT


# Vault paths live under knowledge-base/ (Obsidian root). The first path
# segment of any in-scope Markdown file is therefore "knowledge-base";
# the segment that identifies the domain (00-home, 01-project, ...) is
# the second segment.
VAULT_PREFIX = "knowledge-base"


def _vault_domain(rel: str) -> str:
    """Return the in-vault domain folder (00-home, 01-project, ...) for ``rel``.

    Returns an empty string for files outside the vault or unvaulted roots
    (AGENTS.md, CLAUDE.md).
    """
    parts = rel.split("/")
    if len(parts) >= 2 and parts[0] == VAULT_PREFIX:
        return parts[1]
    return ""


def _is_impl_stub(rel: str) -> bool:
    parts = rel.split("/")
    if len(parts) < 2:
        return False
    return parts[0] == "knowledge-base" and parts[1] == "03-system" and parts[-1] == "README.md"


def _is_vault_path(rel: Path) -> bool:
    """Return True if ``rel`` is a vault note path.

    Handles both the pre-move layout (``00-home/foo.md``) and the post-move
    layout (``knowledge-base/00-home/foo.md``). The vault prefix segment is
    stripped so callers can use the bare domain segment for lookups.
    """
    parts = rel.parts
    if len(parts) == 1:
        return False
    first = parts[0]
    if first == VAULT_PREFIX:
        return True
    # Pre-move test fixtures: bare domain folder at repo root.
    if first in VAULT_DIRS or first in DOMAIN_TYPE:
        return True
    return False


def vault_md_files(repo_root: Path | str | None = None):
    """All Markdown files that are part of the vault graph."""
    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    out = []
    for p in root.rglob("*.md"):
        rel = p.relative_to(root)
        if any(part in SKIP_PARTS for part in rel.parts):
            continue
        if _is_vault_path(rel):
            out.append(p)
    return sorted(out)


def strip_code(text):
    """Strip fenced code blocks and inline code spans."""
    out, fence = [], False
    for line in text.splitlines(True):
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        out.append(re.sub(r"`[^`]*`", "", line))
    return "".join(out)


def parse_frontmatter(text):
    """Parse a YAML frontmatter mapping.

    ``None`` means the document has no frontmatter. Invalid YAML, a missing
    closing delimiter, duplicate keys, or a non-mapping document raises
    ``ValueError`` so the audit can report a blocking issue instead of
    silently accepting a partial hand-written parse.
    """
    if not text.startswith("---\n"):
        return None
    match = re.match(r"^---\n(.*?)\n---(?:\n|$)", text, re.S)
    if not match:
        raise ValueError("frontmatter has no closing delimiter")

    class _UniqueKeyLoader(yaml.SafeLoader):
        pass

    def _mapping(loader, node, deep=False):
        mapping = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if key in mapping:
                raise ValueError(f"duplicate frontmatter key '{key}'")
            mapping[key] = loader.construct_object(value_node, deep=deep)
        return mapping

    _UniqueKeyLoader.add_constructor(  # type: ignore[attr-defined]
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        _mapping,
    )
    document = yaml.load(match.group(1), Loader=_UniqueKeyLoader)
    if document is None:
        return None
    if not isinstance(document, dict):
        raise ValueError("frontmatter must be a YAML mapping")
    # Frontmatter values are plain data strings, not code: "no" must stay the
    # string "no" (YAML 1.1 would coerce it to False) and dates must not
    # become datetime objects.
    return {
        key: value if isinstance(value, str | list | dict | type(None)) else str(value)
        for key, value in document.items()
    }


def resolve_link(raw, by_path, by_stem):
    """Resolve a Markdown link or wikilink to a known in-scope path.

    Returns the resolved relative path as a string, the literal ``"external"``
    if the target is recognised as off-vault, or ``None`` if unresolved.
    """
    if "://" in raw:
        return "external"
    if raw.startswith(("http://", "https://", "mailto:", "#")):
        return "external"
    candidates = [raw]
    if raw.endswith(".md"):
        candidates.append(raw[: -len(".md")])
    head, _, anchor = raw.partition("#")
    if head and head != raw:
        candidates.append(head)
        if head.endswith(".md"):
            candidates.append(head[: -len(".md")])
    for c in candidates:
        if c in by_path:
            return by_path[c]
        if raw in by_stem:
            return by_stem[raw]
    return None


def audit(repo_root: Path | str | None = None):
    """Audit one repository vault and return the structured findings."""
    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    files = vault_md_files(root)
    by_path: dict[str, str] = {str(p.relative_to(root)): str(p.relative_to(root)) for p in files}
    by_stem = {p.stem: str(p.relative_to(root)) for p in files}
    # Wikilinks inside the vault are written in vault-relative form
    # (``[[00-home/foo]]``); add bare-domain aliases so those resolve.
    for prefixed in list(by_path):
        if prefixed.startswith("knowledge-base/"):
            alias = prefixed[len("knowledge-base/") :]
            by_path[alias] = prefixed
            by_path[alias.removesuffix(".md")] = prefixed
            by_stem.setdefault(
                prefixed.rsplit("/", 1)[-1].removesuffix(".md"),
                prefixed,
            )
    # Root files: AGENTS.md/CLAUDE.md stay at the repo root; dashboard,
    # README and audit live under the vault root after the split.
    for name in (
        "AGENTS.md",
        "CLAUDE.md",
        "knowledge-base/index.md",
        "knowledge-base/README.md",
        "knowledge-base/AUDIT.md",
    ):
        if (root / name).is_file():
            by_path[name] = name
            base = name[:-3]
            by_stem[base.rsplit("/", 1)[-1]] = name

    result: dict = {
        "links": {"md_ok": 0, "md_bad": 0, "wiki_ok": 0, "wiki_bad": 0},
        "frontmatter_issues": [],
        "type_mismatches": [],
        "orphans": [],
        "unreachable": [],
        "tag_issues": [],
        "structure_issues": [],
        "link_issues": [],
    }
    graph: dict[str, set[str]] = defaultdict(set)
    inlinks: dict[str, set[str]] = defaultdict(set)
    md_ok = md_bad = wiki_ok = wiki_bad = 0

    for path in files:
        rel = str(path.relative_to(root))
        is_template = rel.startswith("knowledge-base/99-templates/")
        text = strip_code(path.read_text(encoding="utf-8", errors="replace"))
        if is_template:
            continue
        for match in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", text):
            target = match.group(2).split("#", 1)[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            resolved = resolve_link(target, by_path, by_stem)
            if resolved and resolved != "external":
                md_ok += 1
                inlinks[resolved].add(rel)
                graph[rel].add(resolved)
            elif resolved != "external":
                md_bad += 1
                result["link_issues"].append(f"MD {rel} -> {target}")
        for match in re.finditer(r"(?<!!)\[\[([^\]]+)\]\]", text):
            target = match.group(1)
            alias_sep = target.find("|")
            if alias_sep >= 0:
                target = target[:alias_sep]
            target = target.strip()
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = resolve_link(target, by_path, by_stem)
            if resolved:
                wiki_ok += 1
                inlinks[resolved].add(rel)
                graph[rel].add(resolved)
            else:
                wiki_bad += 1
                result["link_issues"].append(f"WIKI {rel} -> [[{target}]]")

    result["links"] = {
        "md_ok": md_ok,
        "md_bad": md_bad,
        "wiki_ok": wiki_ok,
        "wiki_bad": wiki_bad,
    }

    frontmatter_registry = schema_registry()
    for path in files:
        rel = str(path.relative_to(root))
        try:
            frontmatter = parse_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
        except ValueError as exc:
            result["frontmatter_issues"].append(f"{rel}: {exc}")
            continue
        if frontmatter is None:
            result["frontmatter_issues"].append(f"{rel}: no frontmatter")
            continue
        try:
            frontmatter_registry.validate("frontmatter", frontmatter)
        except Exception as exc:
            result["frontmatter_issues"].append(
                f"{rel}: canonical frontmatter schema rejected: {exc}"
            )

        note_type = frontmatter.get("type")
        if isinstance(note_type, str) and note_type not in VALID_TYPE:
            result["frontmatter_issues"].append(
                f"{rel}: type='{note_type}' not in {sorted(VALID_TYPE)}"
            )
        status = frontmatter.get("status")
        if isinstance(status, str) and status not in VALID_STATUS:
            result["frontmatter_issues"].append(
                f"{rel}: status='{status}' not in {sorted(VALID_STATUS)}"
            )

        domain = _vault_domain(rel)
        if (
            domain in DOMAIN_TYPE
            and isinstance(note_type, str)
            and note_type != DOMAIN_TYPE[domain]
            and not (path.name == "README.md" and note_type == "moc")
        ):
            result["type_mismatches"].append(
                f"{rel}: type='{note_type}', {domain}/ conventionally '{DOMAIN_TYPE[domain]}'"
            )

        tags = frontmatter.get("tags")
        if isinstance(tags, list):
            for tag in tags:
                if not isinstance(tag, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", tag):
                    result["tag_issues"].append(f"{rel}: bad tag '{tag}'")

    for path in files:
        rel = str(path.relative_to(root))
        domain = _vault_domain(rel)
        if (
            f"knowledge-base/{domain}" in NO_ORPHAN_CHECK
            or rel in DURABLE_EXCLUDE
            or _is_impl_stub(rel)
        ):
            continue
        if not inlinks.get(rel):
            result["orphans"].append(rel)

    seeds = {
        "knowledge-base/index.md",
        "knowledge-base/README.md",
        "knowledge-base/AUDIT.md",
        "AGENTS.md",
        "CLAUDE.md",
    }
    for directory in (
        "knowledge-base/00-home",
        "knowledge-base/01-project",
        "knowledge-base/02-research",
        "knowledge-base/03-system",
        "knowledge-base/04-decisions",
        "knowledge-base/05-operations",
        "knowledge-base/06-sources",
        "knowledge-base/99-templates",
    ):
        folder = root / directory
        if folder.is_dir():
            for seed in folder.glob("*.md"):
                seeds.add(str(seed.relative_to(root)))
    seen: set[str] = set()
    stack = list(seeds)
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        stack.extend(graph.get(current, set()) - seen)
    for path in files:
        rel = str(path.relative_to(root))
        if rel not in seen:
            result["unreachable"].append(rel)

    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="exit code only, no output")
    args = ap.parse_args(argv)
    r = audit()
    # Total blocks CI: frontmatter, tag, link, structure, orphan, unreachable.
    # Type drift is informational (it's a coverage map, not a defect).
    blocking = sum(
        len(r[key])
        for key in (
            "frontmatter_issues",
            "tag_issues",
            "link_issues",
            "structure_issues",
            "orphans",
            "unreachable",
        )
    )
    if args.json:
        json.dump(r, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 1 if blocking else 0
    print(f"Md links      : {r['links']['md_ok']} ok / {r['links']['md_bad']} bad")
    print(f"Wiki links    : {r['links']['wiki_ok']} ok / {r['links']['wiki_bad']} bad")
    print(f"Frontmatter   : {len(r['frontmatter_issues'])} issues")
    print(f"Tags          : {len(r['tag_issues'])} problems")
    print(f"Structure     : {len(r['structure_issues'])} issues")
    print(f"Type drift    : {len(r['type_mismatches'])} (informational)")
    print(f"Orphans       : {len(r['orphans'])}")
    print(f"Unreachable   : {len(r['unreachable'])}")
    if args.quiet:
        return 1 if blocking else 0
    if blocking:
        print()
        print("--- details ---")
        for label, items in (
            ("FRONT", r["frontmatter_issues"]),
            ("TAG", r["tag_issues"]),
            ("LINK", r["link_issues"]),
            ("STRUCT", r["structure_issues"]),
            ("ORPHAN", r["orphans"]),
            ("UNREACH", r["unreachable"]),
        ):
            for x in items:
                print(f"  {label} {x}")
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
