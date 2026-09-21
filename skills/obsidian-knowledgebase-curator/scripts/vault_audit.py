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
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# ── shared registry ────────────────────────────────────────────────────────
from polder_research.paths import (
    DOMAIN_TYPE,
    DURABLE_EXCLUDE,
    NO_ORPHAN_CHECK,
    REQUIRED_FM_KEYS,
    REPO_ROOT,
    SKIP_PARTS,
    VALID_STATUS,
    VALID_TYPE,
)

VAULT_DIRS = (
    "00-home", "01-project", "02-research", "03-system",
    "04-decisions", "05-operations", "06-sources",
    "90-inbox", "99-templates",
)


def _is_impl_stub(rel: str) -> bool:
    parts = rel.split("/")
    return len(parts) == 2 and parts[0] in ("03-system",) and parts[1] == "README.md"


def vault_md_files():
    """All .md files that are part of the vault graph.

    Includes content-domain notes (under VAULT_DIRS) and root durable pages
    (index.md, README.md, AUDIT.md, etc.). Root pages are included so their
    outbound wikilinks populate the inlink graph for reachability checks, but
    they are excluded from orphan checks via DURABLE_EXCLUDE.
    """
    out = []
    for p in REPO_ROOT.rglob("*.md"):
        rel = p.relative_to(REPO_ROOT)
        if any(part in SKIP_PARTS for part in rel.parts):
            continue
        if len(rel.parts) == 1:
            # root-level .md file (index.md, README.md, AUDIT.md...) —
            # include it so its outbound links feed the graph.
            out.append(p)
        elif rel.parts[0] in VAULT_DIRS:
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
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return None
    block = m.group(1)
    fm: dict = {}
    cur_key = None
    for line in block.splitlines():
        if not line.strip():
            continue
        if re.match(r"^\s+-\s+", line):
            if cur_key and cur_key in fm and isinstance(fm[cur_key], list):
                fm[cur_key].append(line.strip().lstrip("-").strip())
            continue
        if ":" in line:
            k, _, v = line.partition(":")
            k = k.strip()
            v = v.strip()
            if not v:
                fm[k] = []
                cur_key = k
            elif v == "[]":
                fm[k] = []
                cur_key = k
            elif v.startswith("[") and v.endswith("]"):
                items = [x.strip().strip("'\"") for x in v[1:-1].split(",") if x.strip()]
                fm[k] = items
                cur_key = k
            else:
                fm[k] = v.strip('"').strip("'")
                cur_key = k
    return fm


def resolve_link(raw, by_path, by_stem):
    if "://" in raw:
        return "external"

    if "|" in raw:
        raw = raw.split("|", 1)[0].strip()
    if "#" in raw:
        raw = raw.split("#", 1)[0]
    candidates = []
    if raw.endswith(".md"):
        candidates.append(raw)
    else:
        candidates.append(raw + ".md")
    for c in candidates:
        if c in by_path:
            return c
        if raw in by_stem:
            return by_stem[raw]
    return None


def audit():
    files = vault_md_files()
    # Root-level .md files (index.md, README.md, AGENTS.md, AUDIT.md) are
    # durable but live outside the content domains. Seed by_path/by_stem so
    # wikilinks like `[[index]]` and `[[AGENTS]]` resolve, even though they
    # are excluded from the orphan/unreachable content scan.
    by_path = {str(p.relative_to(REPO_ROOT)) for p in files}
    by_stem = {p.stem: str(p.relative_to(REPO_ROOT)) for p in files}
    # Also index root-level durable .md files (e.g. index.md, AGENTS.md) so
    # their wikilink targets resolve without including them in the orphan
    # scan (they are excluded by DURABLE_EXCLUDE).
    for name in ("index.md", "README.md", "AGENTS.md", "CLAUDE.md", "AUDIT.md"):
        if (REPO_ROOT / name).is_file():
            by_path.add(name)
            by_stem[name[:-3]] = name

    r: dict = {
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

    for p in files:
        rel = str(p.relative_to(REPO_ROOT))
        # 99-templates/ files intentionally contain placeholder wikilink/MD-link
        # stubs (``[[path/to/source]]``) that demonstrate link syntax to users.
        # Skip link resolution for them, but still validate frontmatter below.
        is_template = rel.startswith("99-templates/")
        text = strip_code(p.read_text(encoding="utf-8", errors="replace"))

        if not is_template:
            # Markdown links
            for m in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", text):
                target = m.group(2).split("#", 1)[0].strip()
                if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                resolved = resolve_link(target, by_path, by_stem)
                if resolved and resolved != "external":
                    md_ok += 1
                elif resolved == "external":
                    continue
                else:
                    md_bad += 1
                    r["link_issues"].append(f"MD {rel} -> {target}")

            # Wikilinks
            for m in re.finditer(r"(?<!!)\[\[([^\]]+)\]\]", text):
                target = m.group(1)
                resolved = resolve_link(target, by_path, by_stem)
                if resolved == "external":
                    continue
                if resolved:
                    wiki_ok += 1
                    inlinks[resolved].add(rel)
                    graph[rel].add(resolved)
                else:
                    wiki_bad += 1
                    r["link_issues"].append(f"WIKI {rel} -> [[{target}]]")

    r["links"] = {"md_ok": md_ok, "md_bad": md_bad,
                   "wiki_ok": wiki_ok, "wiki_bad": wiki_bad}

    # frontmatter + type/domain consistency
    for p in files:
        rel = str(p.relative_to(REPO_ROOT))
        fm = parse_frontmatter(p.read_text(encoding="utf-8", errors="replace"))
        if fm is None:
            r["frontmatter_issues"].append(f"{rel}: no frontmatter")
            continue
        for key in REQUIRED_FM_KEYS:
            if key not in fm or not fm[key]:
                r["frontmatter_issues"].append(f"{rel}: missing '{key}'")
        t = str(fm.get("type", "")).strip().strip('"')
        if t and t not in VALID_TYPE:
            r["frontmatter_issues"].append(
                f"{rel}: type='{t}' not in {sorted(VALID_TYPE)}")
        s = str(fm.get("status", "")).strip().strip('"')
        if s and s not in VALID_STATUS:
            r["frontmatter_issues"].append(
                f"{rel}: status='{s}' not in {sorted(VALID_STATUS)}")
        top = rel.split("/")[0]
        if top in DOMAIN_TYPE and t and t != DOMAIN_TYPE[top]:
            if not (p.name == "README.md" and t == "moc"):
                r["type_mismatches"].append(
                    f"{rel}: type='{t}', {top}/ conventionally '{DOMAIN_TYPE[top]}'")

        # tag check
        tags = fm.get("tags") or []
        if not isinstance(tags, list):
            tags = [str(tags)]
        for tag in tags:
            tag_str = str(tag).strip()
            if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", tag_str):
                r["tag_issues"].append(f"{rel}: bad tag '{tag_str}'")

    # orphans: durable notes with no incoming links
    for p in files:
        rel = str(p.relative_to(REPO_ROOT))
        top = rel.split("/")[0]
        if top in NO_ORPHAN_CHECK:
            continue
        if rel in DURABLE_EXCLUDE or _is_impl_stub(rel):
            continue
        if not inlinks.get(rel):
            r["orphans"].append(rel)

    # reachability: seeded BFS from index.md, README.md, and every top-level
    # .md in the content domains. Anything not reached from a seed is
    # "unreachable" (AUDIT.md §33).
    seeds = {"index.md", "README.md", "AUDIT.md", "AGENTS.md", "CLAUDE.md"}
    for d in ("00-home", "01-project", "02-research", "03-system",
              "04-decisions", "05-operations", "06-sources", "99-templates"):
        folder = REPO_ROOT / d
        if folder.is_dir():
            for sp in folder.glob("*.md"):
                seeds.add(str(sp.relative_to(REPO_ROOT)))
    seen: set[str] = set()
    stack = list(seeds)
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        stack.extend(graph.get(cur, set()) - seen)
    for p in files:
        rel = str(p.relative_to(REPO_ROOT))
        if rel not in seen:
            r["unreachable"].append(rel)

    # structure check: required folders present
    for d in VAULT_DIRS:
        if not (REPO_ROOT / d).is_dir():
            r["structure_issues"].append(f"missing vault dir: {d}/")

    return r


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    r = audit()

    if args.json:
        print(json.dumps(r, indent=2, ensure_ascii=False))
        return 0

    files = vault_md_files()
    n_files = len(files)
    print(f"VAULT AUDIT — {n_files} vault .md files")
    print(f"Links        : {r['links']['md_ok']} md ok / {r['links']['md_bad']} bad  ·  "
          f"{r['links']['wiki_ok']} wiki ok / {r['links']['wiki_bad']} bad")
    print(f"Orphans      : {len(r['orphans'])}")
    print(f"Unreachable  : {len(r['unreachable'])}")
    print(f"Frontmatter  : {len(r['frontmatter_issues'])} issues")
    print(f"Tags         : {len(r['tag_issues'])} problems")
    print(f"Structure    : {len(r['structure_issues'])} issues")
    print(f"Type drift   : {len(r['type_mismatches'])} (informational)")

    if r["orphans"]:
        print("\nORPHANS:")
        for x in r["orphans"]:
            print(f"  {x}")
    if r["unreachable"]:
        print("\nUNREACHABLE:")
        for x in r["unreachable"]:
            print(f"  {x}")
    if r["frontmatter_issues"]:
        print("\nFRONTMATTER:")
        for x in r["frontmatter_issues"]:
            print(f"  {x}")
    if r["tag_issues"]:
        print("\nTAGS:")
        for x in r["tag_issues"]:
            print(f"  {x}")
    if r["link_issues"]:
        print("\nLINKS:")
        for x in r["link_issues"]:
            print(f"  {x}")
    if r["structure_issues"]:
        print("\nSTRUCTURE:")
        for x in r["structure_issues"]:
            print(f"  {x}")
    if r["type_mismatches"]:
        print("\nTYPE DRIFT (informational):")
        for x in r["type_mismatches"]:
            print(f"  {x}")
    # Total blocks CI: frontmatter, tag, link, structure, orphan, unreachable.
    # Type drift is informational (it's a coverage map, not a defect).
    blocking = (
        len(r["frontmatter_issues"]) + len(r["tag_issues"]) +
        len(r["link_issues"]) + len(r["structure_issues"]) +
        len(r["orphans"]) + len(r["unreachable"])
    )
    print(f"\nTOTAL PROBLEMS: {blocking}")
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
