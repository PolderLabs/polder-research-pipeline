"""intake-register command — P0-corrected version (AUDIT.md §3.5-3.9)."""

from __future__ import annotations

import datetime
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST = REPO_ROOT / "90-inbox" / "manifest.md"

# Canonical vocabulary — aligned with research.config.yaml
VALID_STATUS = frozenset(
    {"new", "triaged", "processing", "distilled", "filed", "rejected", "blocked"}
)
VALID_KIND = frozenset(
    {
        "pdf", "repository", "article", "paper", "log", "transcript",
        "media", "url-list", "documentation", "webpage", "dataset",
        "benchmark", "video", "audio", "book", "standard", "issue",
        "discussion", "other",
    }
)


def parse_rows(text: str) -> list[list[str]]:
    """Parse manifest table data rows, skipping header and separator rows."""
    rows = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        stripped = line.strip()
        # Separator rows: every non-pipe, non-whitespace char is a dash
        if re.match(r"^\|(?:\|?[-: ]+)+\|$", stripped):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells and cells[0] not in ("Item", "Column"):
            rows.append(cells)
    return rows


def _find_row(rows: list[list[str]], filename: str) -> tuple[int, list[str]] | None:
    """Find a row by exact Item column match (not substring — §3.7)."""
    for i, cells in enumerate(rows):
        if cells and cells[0] == filename:
            return i, cells
    return None


def cmd_intake_register(
    file: str | None,
    kind: str = "other",
    owner: str = "agent",
    status: str = "new",
    outcome: str = "—",
    set_file: str | None = None,
    list_: bool = False,
) -> int:
    if not MANIFEST.exists():
        print(f"error: manifest not found at {MANIFEST}", file=sys.stderr)
        return 2

    text = MANIFEST.read_text(encoding="utf-8")

    if list_:
        rows = parse_rows(text)
        if not rows:
            print("queue is empty")
            return 0
        print(f"{'Item':<40} {'Kind':<14} {'Status':<12} {'Owner':<12} Outcome")
        for r in rows:
            if len(r) >= 6:
                print(f"{r[0]:<40} {r[1]:<14} {r[3]:<12} {r[4]:<12} {r[5]}")
        return 0

    if set_file:
        if status not in VALID_STATUS:
            print(f"error: invalid status '{status}'", file=sys.stderr)
            return 2
        rows = parse_rows(text)
        found_idx = _find_row(rows, set_file)
        if found_idx is None:
            print(f"error: no manifest row for '{set_file}'", file=sys.stderr)
            return 2

        idx, cells = found_idx
        while len(cells) < 6:
            cells.append("—")
        cells[3] = status
        if outcome != "—":
            cells[5] = outcome

        # Rebuild: find line numbers and replace exactly
        lines = text.splitlines(True)
        data_line_num = -1
        data_count = 0
        for i, line in enumerate(lines):
            if line.startswith("|") and not re.match(r"^\|[\s\-]+\|$", line) \
                    and not line.startswith("| Item |"):
                if data_count == idx:
                    data_line_num = i
                    break
                data_count += 1

        if data_line_num < 0:
            print(f"error: could not locate row for '{set_file}'", file=sys.stderr)
            return 2

        lines[data_line_num] = "| " + " | ".join(cells) + " |\n"
        MANIFEST.write_text("".join(lines), encoding="utf-8")
        print(f"updated {set_file} -> status={status}")
        return 0

    if not file:
        print("error: --file required (or use --list / --set)", file=sys.stderr)
        return 2

    if kind not in VALID_KIND:
        print(f"error: invalid kind '{kind}'; valid: {sorted(VALID_KIND)}", file=sys.stderr)
        return 2

    if status not in VALID_STATUS:
        print(f"error: invalid status '{status}'", file=sys.stderr)
        return 2

    today = datetime.date.today().isoformat()
    row = f"| {file} | {kind} | {today} | {status} | {owner} | {outcome} |\n"

    lines = text.splitlines(True)
    # Find last data row — scan past header+separator into actual rows
    last_data = -1
    seen_data = False
    for i, line in enumerate(lines):
        if line.startswith("|") and not re.match(r"^\|[\s\-]+\|$", line) \
                and not line.startswith("| Item |"):
            seen_data = True
            last_data = i
        elif seen_data and line.startswith("|"):
            # separator after data — stop
            break
        elif seen_data and not line.startswith("|"):
            break

    if last_data >= 0:
        lines.insert(last_data + 1, row)
    else:
        # No data rows — find the closing "##" or "---" after the Queue table header
        # and insert before it
        for i, line in enumerate(lines):
            if re.match(r"^##\s+", line) and i > 0:
                lines.insert(i, row)
                break
        else:
            lines.append(row)

    MANIFEST.write_text("".join(lines), encoding="utf-8")
    print(f"registered: {file} [{kind}] {status} by {owner}")
    return 0
