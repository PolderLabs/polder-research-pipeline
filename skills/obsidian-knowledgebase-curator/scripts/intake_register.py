#!/usr/bin/env python3
"""
intake_register.py — register a dropped raw item in the inbox manifest.

Implements the "register BEFORE processing" rule from the intake contract.
Appends one row to the manifest table and never touches the raw file.

Usage:
    python3 scripts/intake_register.py --file report.pdf --kind pdf \
        --owner curator --tags audio latency
    python3 scripts/intake_register.py --list          # show current queue
    python3 scripts/intake_register.py --set report.pdf --status filed \
        --outcome 02-research/foveated-rendering

Statuses: new triaged processing filed rejected blocked
Kinds:    pdf repository article paper log transcript media url-list other
"""

import argparse
import datetime
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST = REPO_ROOT / "90-inbox" / "manifest.md"
RAW_DIR = REPO_ROOT / "90-inbox" / "raw"

VALID_STATUS = {"new", "triaged", "processing", "filed", "rejected", "blocked"}
VALID_KIND = {"pdf", "repository", "article", "paper", "log", "transcript",
              "media", "url-list", "other"}


def parse_rows(text):
    """Return (header_lines, rows) where rows are the manifest table data rows."""
    rows = []
    for line in text.splitlines():
        if line.startswith("|") and not re.match(r"^\|[\s\-|]+\|$", line):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if cells and cells[0] not in ("Item", "Column"):
                rows.append(cells)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="raw filename (as it appears in 90-inbox/raw/)")
    ap.add_argument("--kind", default="other")
    ap.add_argument("--owner", default="agent")
    ap.add_argument("--tags", nargs="*", default=[])
    ap.add_argument("--status", default="new")
    ap.add_argument("--outcome", default="—")
    ap.add_argument("--set", dest="set_file", help="update an existing row by filename")
    ap.add_argument("--list", action="store_true", help="list current queue")
    args = ap.parse_args()

    if not MANIFEST.exists():
        print(f"error: manifest not found at {MANIFEST}", file=sys.stderr)
        return 2

    text = MANIFEST.read_text(encoding="utf-8")

    if args.list:
        rows = parse_rows(text)
        if not rows:
            print("queue is empty")
            return 0
        print(f"{'Item':<40} {'Kind':<12} {'Status':<12} {'Owner':<12} Outcome")
        for r in rows:
            if len(r) >= 6:
                print(f"{r[0]:<40} {r[1]:<12} {r[3]:<12} {r[4]:<12} {r[5]}")
        return 0

    if args.set_file:
        if args.status not in VALID_STATUS:
            print(f"error: invalid status '{args.status}'", file=sys.stderr)
            return 2
        found = False
        out = []
        for line in text.splitlines(True):
            if line.startswith("|") and args.set_file in line:
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                while len(cells) < 6:
                    cells.append("—")
                cells[3] = args.status
                if args.outcome != "—":
                    cells[5] = args.outcome
                line = "| " + " | ".join(cells) + " |\n"
                found = True
            out.append(line)
        if not found:
            print(f"error: no manifest row for '{args.set_file}'", file=sys.stderr)
            return 2
        MANIFEST.write_text("".join(out), encoding="utf-8")
        print(f"updated {args.set_file} -> status={args.status}")
        return 0

    if not args.file:
        print("error: --file required (or use --list / --set)", file=sys.stderr)
        return 2
    if args.kind not in VALID_KIND:
        print(f"error: invalid kind '{args.kind}'; valid: {sorted(VALID_KIND)}",
              file=sys.stderr)
        return 2
    if args.status not in VALID_STATUS:
        print(f"error: invalid status '{args.status}'", file=sys.stderr)
        return 2

    today = datetime.date.today().isoformat()
    row = f"| {args.file} | {args.kind} | {today} | {args.status} | {args.owner} | {args.outcome} |\n"

    # append after the last existing data row in the Queue table
    lines = text.splitlines(True)
    last_row = -1
    for i, line in enumerate(lines):
        if line.startswith("|") and not re.match(r"^\|[\s\-|]+\|$", line) \
                and not line.startswith("| Item |"):
            last_row = i
    if last_row >= 0:
        lines.insert(last_row + 1, row)
    else:
        lines.append(row)
    MANIFEST.write_text("".join(lines), encoding="utf-8")

    warn = ""
    if not (RAW_DIR / args.file).exists():
        warn = f"  (warning: {args.file} not present in 90-inbox/raw/ yet)"
    print(f"registered {args.file}  kind={args.kind} status={args.status}{warn}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
