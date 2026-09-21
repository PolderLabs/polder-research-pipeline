#!/usr/bin/env python3
"""
vault_audit.py — whole-vault integrity audit for the Polder Video Pipeline vault.

The repo root IS the Obsidian vault. Run from the repo root:
    python3 skills/obsidian-knowledgebase-curator/scripts/vault_audit.py
    python3 skills/obsidian-knowledgebase-curator/scripts/vault_audit.py --json
    python3 skills/obsidian-knowledgebase-curator/scripts/vault_audit.py --quiet

Checks:
  1. Link integrity     every wikilink and markdown link resolves
  2. Frontmatter       required keys, allowed type/status values
  3. Orphans           pages with zero incoming links (excludes inbox/templates/stubs)
  4. Tags              kebab-case, near-duplicates, distribution
  5. Structure         every domain folder has a README or index
  6. Reachability      every file reachable from the dashboard seeds

`type` describes the KIND of note; the folder is its DOMAIN. They are orthogonal,
so a mismatch is reported as `type_mismatches` (informational) and excluded from
the failure total. Only real problems count toward TOTAL PROBLEMS.

Exit 0 = clean, 1 = problems found.
"""

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

VAULT_DIRS = [
    "00-home", "01-project", "02-research", "03-system",
    "04-decisions", "05-operations", "06-sources",
    "90-inbox", "99-templates",
]

REQUIRED_FM = ["type", "status", "tags"]
VALID_TYPE = {
    "index", "moc", "guide", "template", "inbox",
    "project", "research", "system", "decision",
    "operation", "experiment", "source",
}
VALID_STATUS = {"current", "draft", "stale", "superseded"}

# Domain folder -> conventional note type (informational only).
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

SKIP_PARTS = {".git", ".obsidian", ".wolf", ".claude", ".codex",
              "node_modules", ".venv", "dist", "build", "skills"}

# Folders whose contents are intentionally not linked into the graph
NO_ORPHAN_CHECK = {"90-inbox", "99-templates"}

# Root-level files excluded from orphan check — same set as durablePages()
DURABLE_EXCLUDE = {"AGENTS.md", "CLAUDE.md", "README.md"}

# Impl-dir README stubs (the dashboard's durablePages also filters these)
IMPL_DIRS = set()  # research pipeline has no impl folders


def _is_impl_stub(rel: str) -> bool:
    parts = rel.split("/")
    return len(parts) == 2 and parts[0] in IMPL_DIRS and parts[1] == "README.md"


def vault_md_files():
    out = []
    for p in REPO_ROOT.rglob("*.md"):
        rel = p.relative_to(REPO_ROOT)
        if any(part in SKIP_PARTS for part in rel.parts):
            continue
        # raw/ holds immutable dropped originals (PDFs, binaries); the drop-zone
        # README is the only vault note there.
        if rel.parts[:2] == ("90-inbox", "raw") and rel.name != "README.md":
            continue
        if rel.parts[:2] == ("90-inbox", "archive"):
            continue
        out.append(p)
    return sorted(out)


def strip_code(text):
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
    fm = {}
    for line in m.group(1).split("\n"):
        km = re.match(r"^(\w[\w-]*):\s*(.*)$", line)
        if km:
            fm[km.group(1)] = km.group(2).strip()
        elif line.strip().startswith("- "):
            keys = list(fm)
            if keys:
                last = keys[-1]
                if not isinstance(fm[last], list):
                    fm[last] = [fm[last]] if fm[last] else []
                fm[last].append(line.strip()[2:].strip())
    return fm


def resolve_link(raw, by_path, by_stem):
    raw = raw.strip().replace("\\|", "|")
    target = raw.split("|", 1)[0].split("#", 1)[0].strip()
    if not target:
        return "external"
    if target.startswith(("http://", "https://", "mailto:", "ftp://",
                          "tel:", "data:")):
        return "external"
    if ".." in target:
        return None

    def canon(v):
        return v if v.endswith(".md") else v + ".md"

    variants = [target]
    if target.endswith(".md"):
        variants.append(target[:-3])
    else:
        variants.append(target + ".md")
    for v in variants:
        if v in by_path:
            return canon(v)
    if not target.endswith(".md"):
        for v in (target + "/README.md", target + "/README"):
            if v in by_path:
                return canon(v)
    stem = target[:-3] if target.endswith(".md") else target.split("/")[-1]
    if "/" not in target and len(by_stem.get(stem, [])) == 1:
        return by_stem[stem][0]
    return None


def audit():
    files = vault_md_files()
    by_path, by_stem = {}, defaultdict(list)
    for p in files:
        rel = str(p.relative_to(REPO_ROOT))
        by_path[rel] = p
        if rel.endswith(".md"):
            by_path[rel[:-3]] = p
        by_stem[p.stem].append(rel)

    r = {
        "files": len(files),
        "link_issues": [], "frontmatter_issues": [], "orphans": [],
        "tags": {}, "tag_problems": [], "structure_issues": [],
        "unreachable": [], "type_mismatches": [],
    }

    inlinks = defaultdict(set)
    md_ok = md_bad = wiki_ok = wiki_bad = 0
    graph = defaultdict(set)

    for p in files:
        rel = str(p.relative_to(REPO_ROOT))
        text = strip_code(p.read_text(encoding="utf-8", errors="replace"))

        for m in re.finditer(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)", text):
            t = m.group(1)
            if t.startswith(("http://", "https://", "mailto:", "ftp://",
                             "tel:", "data:", "#")):
                continue
            tgt = t.split("#")[0]
            if not tgt:
                continue
            if os.path.exists(os.path.normpath(
                    os.path.join(os.path.dirname(p), tgt))):
                md_ok += 1
            else:
                md_bad += 1
                r["link_issues"].append(f"MD   {rel} -> {t}")

        for m in re.finditer(r"(?<!!)\[\[([^\]]+)\]\]", text):
            resolved = resolve_link(m.group(1), by_path, by_stem)
            if resolved == "external":
                continue
            if resolved:
                wiki_ok += 1
                inlinks[resolved].add(rel)
                graph[rel].add(resolved)
            else:
                wiki_bad += 1
                r["link_issues"].append(f"WIKI {rel} -> [[{m.group(1)}]]")

    r["links"] = {"md_ok": md_ok, "md_bad": md_bad,
                   "wiki_ok": wiki_ok, "wiki_bad": wiki_bad}

    # frontmatter + type/domain consistency (informational)
    for p in files:
        rel = str(p.relative_to(REPO_ROOT))
        fm = parse_frontmatter(p.read_text(encoding="utf-8", errors="replace"))
        if fm is None:
            r["frontmatter_issues"].append(f"{rel}: no frontmatter")
            continue
        for key in REQUIRED_FM:
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

    # orphans — same universe as the dashboard's durablePages()
    for p in files:
        rel = str(p.relative_to(REPO_ROOT))
        top = rel.split("/")[0]
        if rel == "index.md" or top in NO_ORPHAN_CHECK:
            continue
        if rel in DURABLE_EXCLUDE or _is_impl_stub(rel):
            continue
        if not inlinks.get(rel):
            r["orphans"].append(rel)

    # tags
    tagcount = Counter()
    for p in files:
        fm = parse_frontmatter(
            p.read_text(encoding="utf-8", errors="replace")) or {}
        tags = fm.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]
        for t in tags:
            t = t.strip().strip('"').lstrip("#")
            if t:
                tagcount[t] += 1
    r["tags"] = dict(tagcount.most_common())
    for t in tagcount:
        if t != t.lower():
            r["tag_problems"].append(f"'{t}': not lowercase")
        if " " in t or "_" in t:
            r["tag_problems"].append(f"'{t}': not kebab-case")
    keys = sorted(tagcount)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            if b.startswith(a + "-") or a.startswith(b + "-"):
                r["tag_problems"].append(f"near-duplicate: '{a}' vs '{b}'")

    # structure
    for d in VAULT_DIRS:
        folder = REPO_ROOT / d
        if not folder.is_dir():
            r["structure_issues"].append(f"missing folder: {d}/")
        elif d not in ("90-inbox", "99-templates"):
            if not any((folder / n).exists()
                       for n in ("README.md", "index.md", "_index.md")):
                r["structure_issues"].append(
                    f"{d}/ has no README.md or index.md")

    # reachability
    seeds = {"index.md", "README.md"}
    for d in ("01-project", "02-research", "03-system", "04-decisions",
              "05-operations", "06-sources", "99-templates"):
        folder = REPO_ROOT / d
        if folder.is_dir():
            for p in folder.glob("*.md"):
                seeds.add(str(p.relative_to(REPO_ROOT)))
    seen, stack = set(), list(seeds)
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        stack.extend(graph[cur] - seen)
    for p in files:
        rel = str(p.relative_to(REPO_ROOT))
        if rel not in seen:
            r["unreachable"].append(rel)

    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    r = audit()
    if args.json:
        print(json.dumps(r, indent=2))
        return 0

    L = r["links"]
    # type_mismatches are informational (type = kind, folder = domain; orthogonal)
    total = (L["md_bad"] + L["wiki_bad"] + len(r["orphans"])
             + len(r["frontmatter_issues"]) + len(r["tag_problems"])
             + len(r["structure_issues"]) + len(r["unreachable"]))

    print(f"VAULT AUDIT — {r['files']} vault .md files\n")
    print(f"Links        : {L['md_ok']} md ok / {L['md_bad']} bad"
          f"  ·  {L['wiki_ok']} wiki ok / {L['wiki_bad']} bad")
    print(f"Orphans      : {len(r['orphans'])}")
    print(f"Frontmatter  : {len(r['frontmatter_issues'])} issues")
    print(f"Tags         : {len(r['tags'])} distinct, {len(r['tag_problems'])} problems")
    print(f"Structure    : {len(r['structure_issues'])} issues")
    print(f"Unreachable  : {len(r['unreachable'])}")
    print(f"Type drift   : {len(r['type_mismatches'])} (informational)")

    if not args.quiet:
        for label, key in [
            ("LINK ISSUES", "link_issues"),
            ("ORPHANS", "orphans"),
            ("FRONTMATTER", "frontmatter_issues"),
            ("TAG PROBLEMS", "tag_problems"),
            ("STRUCTURE", "structure_issues"),
            ("UNREACHABLE", "unreachable"),
            ("TYPE DRIFT (informational)", "type_mismatches"),
        ]:
            items = r[key]
            if items:
                print(f"\n{label} ({len(items)}):")
                for it in items[:40]:
                    print(f"  {it}")
                if len(items) > 40:
                    print(f"  … {len(items) - 40} more")

    print(f"\nTOTAL PROBLEMS: {total}")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
