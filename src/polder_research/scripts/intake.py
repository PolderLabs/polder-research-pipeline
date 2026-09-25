"""Register raw intake items in the manifest and canonical source registry."""

from __future__ import annotations

import datetime
import re
import sys
from pathlib import Path

from ..atomic import write_atomic
from ..evidence import compute_content_hash, find_duplicate_source, register_source
from ..paths import (
    INTAKE_MANIFEST,
    INTAKE_RAW_DIR,
    REPO_ROOT,
    RESEARCH_INTAKE_DIR,
    VAULT_ROOT,
)
from ..paths import (
    INTAKE_VALID_KIND as VALID_KIND,
)
from ..paths import (
    INTAKE_VALID_STATUS as VALID_STATUS,
)

_CANONICAL_SOURCE_TYPES = frozenset(
    {
        "paper",
        "documentation",
        "repository",
        "webpage",
        "article",
        "dataset",
        "benchmark",
        "video",
        "audio",
        "transcript",
        "book",
        "standard",
        "issue",
        "discussion",
        "other",
    }
)


def parse_rows(text: str) -> list[list[str]]:
    """Parse manifest table data rows, skipping header and separator rows."""
    rows = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        stripped = line.strip()
        if re.match(r"^\|(?:\|?[-: ]+)+\|$", stripped):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if cells and cells[0] not in ("Item", "Column"):
            rows.append(cells)
    return rows


def _find_row(rows: list[list[str]], filename: str) -> tuple[int, list[str]] | None:
    """Find a row by exact Item column match (not substring — §3.7)."""
    for index, cells in enumerate(rows):
        if cells and cells[0] == filename:
            return index, cells
    return None


def _kind_to_source_type(kind: str) -> tuple[str, str]:
    """Map intake kind to canonical source_type and media_type."""
    if kind in {"pdf", "article", "paper", "book"}:
        media_type = "pdf"
    elif kind in {"video", "audio"}:
        media_type = kind
    elif kind == "transcript":
        media_type = "text"
    elif kind == "repository":
        media_type = "git"
    elif kind in {"dataset", "benchmark", "log"}:
        media_type = "json"
    elif kind in {"documentation", "webpage"}:
        media_type = "html"
    elif kind == "media":
        media_type = "image"
    elif kind in {"url-list", "issue", "discussion", "standard"}:
        media_type = "markdown"
    else:
        media_type = "other"
    return (kind if kind in _CANONICAL_SOURCE_TYPES else "other"), media_type


def intake_id(*, content_sha256: str, kind: str) -> str:
    """Return the stable intake ID derived from content hash + kind.

    IDs are intentionally stable across absolute-path moves and filename
    renames: only the immutable raw bytes (SHA-256) and the declared intake
    kind participate. The canonical intake record can therefore follow the
    raw item even when ``90-inbox/raw/`` is reorganised.
    """
    return f"int_{content_sha256[:16]}_{kind}"


def _intake_record_path(intake_dir: Path, item_id: str) -> Path:
    """Return the canonical intake record path for ``item_id``."""
    return intake_dir / f"{item_id}.json"


def _build_intake_record(
    *,
    item_id: str,
    filename: str,
    raw_location: str,
    content_sha256: str,
    kind: str,
    source_id: str,
    owner: str,
    status: str,
    outcome: str,
    added_on: str,
) -> dict[str, object]:
    """Build the canonical structured intake document for ``write_atomic``."""
    return {
        "id": item_id,
        "schema_version": 1,
        "filename": filename,
        "raw_location": raw_location,
        "content_sha256": content_sha256,
        "kind": kind,
        "source_id": source_id,
        "owner": owner,
        "status": status,
        "outcome": outcome,
        "added_on": added_on,
    }


def _canonical_source_for_raw(
    filename: str,
    *,
    kind: str,
    repository_root: Path | None = None,
) -> tuple[str, str, str]:
    """Create or resolve the canonical source; return ``(source_id, content_sha256, raw_location)``.

    The auxiliary values power the stable intake ID derivation without
    re-reading or re-hashing the raw item.
    """
    repo = Path(repository_root) if repository_root is not None else REPO_ROOT
    vault = repo if repo.name == "knowledge-base" else repo / "knowledge-base"
    raw_dir = (vault / INTAKE_RAW_DIR.relative_to(VAULT_ROOT)).resolve()
    raw_file = (raw_dir / filename).resolve()
    try:
        raw_file.relative_to(raw_dir)
    except ValueError as exc:
        raise ValueError(f"raw item is outside raw directory: {filename}") from exc
    if not raw_file.is_file():
        raise ValueError(f"raw item not found: {filename}")

    raw_bytes = raw_file.read_bytes()
    content_sha256 = compute_content_hash(raw_bytes)
    raw_location = str(raw_file.relative_to(vault))
    duplicate = find_duplicate_source(
        content_sha256=content_sha256,
        raw_location=raw_location,
        repository_root=repo,
    )
    if duplicate:
        return duplicate, content_sha256, raw_location

    source_type, media_type = _kind_to_source_type(kind)
    source_id = register_source(
        title=filename,
        source_type=source_type,
        media_type=media_type,
        raw_bytes=raw_bytes,
        content_sha256=content_sha256,
        raw_location=raw_location,
        byte_size=len(raw_bytes),
        repository_root=repo,
    )
    return source_id, content_sha256, raw_location


def canonical_source_for_raw(
    filename: str,
    *,
    kind: str,
    repository_root: Path | None = None,
) -> str:
    """Create or resolve the canonical source for an existing immutable raw item."""
    source_id, _, _ = _canonical_source_for_raw(
        filename, kind=kind, repository_root=repository_root
    )
    return source_id


def _append_row(text: str, row: str) -> str:
    """Insert row after the last Queue data row, retaining the Queue table."""
    lines = text.splitlines(True)
    last_data = -1
    seen_data = False
    for index, line in enumerate(lines):
        if (
            line.startswith("|")
            and not re.match(r"^\|[\s\-]+\|$", line)
            and not line.startswith("| Item |")
        ):
            seen_data = True
            last_data = index
        elif seen_data:
            break

    if last_data >= 0:
        lines.insert(last_data + 1, row)
        return "".join(lines)

    for index, line in enumerate(lines):
        if re.match(r"^##\s+", line) and index > 0:
            lines.insert(index, row)
            return "".join(lines)
    return text + row


def cmd_intake_register(
    file: str | None,
    kind: str = "other",
    owner: str = "agent",
    status: str = "new",
    outcome: str = "—",
    set_file: str | None = None,
    list_: bool = False,
    repository_root: Path | None = None,
) -> int:
    repo = Path(repository_root) if repository_root is not None else REPO_ROOT
    vault = repo if repo.name == "knowledge-base" else repo / "knowledge-base"
    manifest_path = vault / INTAKE_MANIFEST.relative_to(VAULT_ROOT)
    if not manifest_path.exists():
        print(f"error: manifest not found at {manifest_path}", file=sys.stderr)
        return 2

    text = manifest_path.read_text(encoding="utf-8")
    if list_:
        rows = parse_rows(text)
        if not rows:
            print("queue is empty")
            return 0
        print(f"{'Item':<40} {'Kind':<14} {'Status':<12} {'Owner':<12} Outcome")
        for row in rows:
            if len(row) >= 6:
                print(f"{row[0]:<40} {row[1]:<14} {row[3]:<12} {row[4]:<12} {row[5]}")
        return 0

    if set_file:
        if status not in VALID_STATUS:
            print(f"error: invalid status '{status}'", file=sys.stderr)
            return 2
        rows = parse_rows(text)
        found = _find_row(rows, set_file)
        if found is None:
            print(f"error: no manifest row for '{set_file}'", file=sys.stderr)
            return 2
        data_index, cells = found
        while len(cells) < 6:
            cells.append("—")
        cells[3] = status
        if outcome != "—":
            cells[5] = outcome

        lines = text.splitlines(True)
        data_count = 0
        for index, line in enumerate(lines):
            if (
                line.startswith("|")
                and not re.match(r"^\|[\s\-]+\|$", line)
                and not line.startswith("| Item |")
            ):
                if data_count == data_index:
                    lines[index] = "| " + " | ".join(cells) + " |\n"
                    manifest_path.write_text("".join(lines), encoding="utf-8")
                    print(f"updated {set_file} -> status={status}")
                    return 0
                data_count += 1
        print(f"error: could not locate row for '{set_file}'", file=sys.stderr)
        return 2

    if not file:
        print("error: --file required (or use --list / --set)", file=sys.stderr)
        return 2
    if kind not in VALID_KIND:
        print(f"error: invalid kind '{kind}'; valid: {sorted(VALID_KIND)}", file=sys.stderr)
        return 2
    if status not in VALID_STATUS:
        print(f"error: invalid status '{status}'", file=sys.stderr)
        return 2

    try:
        source_id, content_sha256, raw_location = _canonical_source_for_raw(
            file, kind=kind, repository_root=repo
        )
    except Exception as exc:  # Source registration must precede manifest projection.
        print(f"error: source registration failed: {exc}", file=sys.stderr)
        return 2

    intake_dir = repo / RESEARCH_INTAKE_DIR.relative_to(REPO_ROOT)
    item_id = intake_id(content_sha256=content_sha256, kind=kind)
    record_path = _intake_record_path(intake_dir, item_id)
    already_registered = record_path.exists()
    if not already_registered:
        write_atomic(
            record_path,
            _build_intake_record(
                item_id=item_id,
                filename=file,
                raw_location=raw_location,
                content_sha256=content_sha256,
                kind=kind,
                source_id=source_id,
                owner=owner,
                status=status,
                outcome=outcome,
                added_on=datetime.date.today().isoformat(),
            ),
            schema_name="intake",
        )

    if _find_row(parse_rows(text), file) is not None:
        # Manifest already lists this item; the canonical record may still be new.
        print(f"registered (idempotent): {file} [id={item_id}] [source={source_id}]")
        return 0

    today = datetime.date.today().isoformat()
    manifest_path.write_text(
        _append_row(text, f"| {file} | {kind} | {today} | {status} | {owner} | {outcome} |\n"),
        encoding="utf-8",
    )
    print(f"registered: {file} [id={item_id}] [source={source_id}] [{kind}] {status} by {owner}")
    return 0


__all__ = [
    "VALID_KIND",
    "VALID_STATUS",
    "canonical_source_for_raw",
    "cmd_intake_register",
    "intake_id",
    "parse_rows",
]
