"""Register raw intake items in the manifest and canonical source registry."""

from __future__ import annotations

import csv
import datetime
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from ..atomic import write_atomic
from ..evidence import (
    acquire_source,
    compute_content_hash,
    find_duplicate_source,
    register_source,
)
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
from ..schemas import registry_for_root
from ..urls import normalize_url

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
_MEDIA_TYPES = frozenset(
    {
        "pdf",
        "html",
        "markdown",
        "text",
        "json",
        "csv",
        "image",
        "audio",
        "video",
        "git",
        "api",
        "other",
    }
)
_TAG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


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


def _find_intake_record_by_filename(intake_dir: Path, filename: str) -> Path | None:
    """Return the canonical intake record path whose ``filename`` matches.

    The record ID is derived from the content hash, so the record cannot be
    recomputed from the manifest row alone; locate it by its recorded
    ``filename`` field instead. Returns ``None`` when the item was never
    registered as a structured record (for example a hand-written row).
    """
    if not intake_dir.is_dir():
        return None
    for path in sorted(intake_dir.glob("int_*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if record.get("filename") == filename:
            return path
    return None


def _sync_intake_record_status(
    record_path: Path,
    *,
    status: str,
    outcome: str,
) -> None:
    """Mirror a manifest status/outcome update onto the canonical record.

    The manifest is a human projection; the record under ``.research/intake``
    is authoritative. Updating only the projection leaves the two
    disagreeing, so every lifecycle transition must be written to both.
    ``owner`` is deliberately left alone: ``--set`` does not change it in the
    manifest either, so both surfaces stay in step.
    """
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["status"] = status
    if outcome != "—":
        record["outcome"] = outcome
    write_atomic(record_path, record, schema_name="intake")


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
    title: str | None = None,
    source_type: str | None = None,
    media_type: str | None = None,
    canonical_url: str | None = None,
    source_class: str | None = None,
    tags: list[str] | None = None,
    retrieved_at: str | None = None,
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
    if canonical_url:
        duplicate = find_duplicate_source(canonical_url=canonical_url, repository_root=repo)
        if duplicate:
            from ..evidence import assert_record_exists

            source = assert_record_exists(
                duplicate,
                prefix="src",
                default_dir=Path(".research/sources"),
                directory_name="sources",
                repository_root=repo,
            )
            if (
                source.get(
                    "acquisition_status",
                    "unacquired" if source.get("source_status") == "unacquired" else "acquired",
                )
                == "unacquired"
            ):
                acquire_source(
                    duplicate,
                    raw_bytes,
                    raw_location=raw_location,
                    retrieved_at=retrieved_at,
                    repository_root=repo,
                )
            return duplicate, content_sha256, raw_location
    duplicate = find_duplicate_source(
        content_sha256=content_sha256,
        raw_location=raw_location,
        repository_root=repo,
    )
    if duplicate:
        return duplicate, content_sha256, raw_location

    inferred_type, inferred_media_type = _kind_to_source_type(kind)
    source_id = register_source(
        title=title or filename,
        source_type=source_type or inferred_type,
        media_type=media_type or inferred_media_type,
        raw_bytes=raw_bytes,
        content_sha256=content_sha256,
        raw_location=raw_location,
        byte_size=len(raw_bytes),
        canonical_url=canonical_url,
        source_class=source_class,
        tags=tags,
        retrieved_at=retrieved_at,
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


@dataclass(frozen=True)
class _ManifestItem:
    row_number: int
    title: str
    source_type: str
    media_type: str
    canonical_url: str | None
    local_file: str | None
    source_class: str | None
    tags: tuple[str, ...]
    retrieved_at: str
    notes: str
    raw_bytes: bytes | None

    @property
    def display_item(self) -> str:
        if self.local_file:
            return self.local_file
        return f"{self.title} ({self.canonical_url})"


def _manifest_rows(path: Path) -> list[tuple[int, dict[str, object]]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise ValueError("manifest is missing a CSV header")
            if len(set(reader.fieldnames)) != len(reader.fieldnames):
                raise ValueError("manifest has duplicate CSV column names")
            return [
                (reader.line_num, {key: value or "" for key, value in row.items() if key})
                for row in reader
            ]
    if suffix in {".jsonl", ".ndjson"}:
        rows = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"row {line_number}: expected a JSON object")
            rows.append((line_number, value))
        return rows
    raise ValueError("manifest must have a .csv, .jsonl, or .ndjson extension")


def _parse_manifest_item(
    row_number: int,
    values: dict[str, object],
    *,
    raw_dir: Path,
    registry,
) -> _ManifestItem:
    allowed = {
        "title",
        "canonical_url",
        "local_file",
        "source_type",
        "media_type",
        "retrieved_at",
        "discovered_at",
        "tags",
        "notes",
        "source_class",
    }
    unknown = set(values) - allowed
    if unknown:
        raise ValueError(f"row {row_number}: unknown columns: {', '.join(sorted(unknown))}")

    def get_text(name: str) -> str:
        value = values.get(name, "")
        if isinstance(value, list) and name == "tags":
            return ""
        if not isinstance(value, str):
            raise ValueError(f"row {row_number}: {name} must be a string")
        return value.strip()

    title = get_text("title")
    raw_url = get_text("canonical_url")
    local_file = get_text("local_file")
    if not title:
        raise ValueError(f"row {row_number}: title is required")
    if bool(raw_url) == bool(local_file):
        raise ValueError(f"row {row_number}: provide exactly one of canonical_url or local_file")
    canonical_url = normalize_url(raw_url) if raw_url else None
    if canonical_url:
        parsed = urlsplit(canonical_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"row {row_number}: invalid canonical_url {raw_url!r}")

    raw_bytes = None
    if local_file:
        candidate = Path(local_file)
        if candidate.is_absolute():
            raise ValueError(f"row {row_number}: local_file must be relative to 90-inbox/raw")
        resolved = (raw_dir / candidate).resolve()
        try:
            resolved.relative_to(raw_dir.resolve())
        except ValueError as exc:
            raise ValueError(f"row {row_number}: local_file escapes 90-inbox/raw") from exc
        if not resolved.is_file():
            raise ValueError(f"row {row_number}: local_file not found: {local_file}")
        raw_bytes = resolved.read_bytes()

    source_type = get_text("source_type") or ("webpage" if canonical_url else "other")
    default_media = (
        "html"
        if canonical_url
        else {
            ".pdf": "pdf",
            ".html": "html",
            ".htm": "html",
            ".md": "markdown",
            ".txt": "text",
            ".json": "json",
            ".csv": "csv",
        }.get(Path(local_file).suffix.lower(), "other")
    )
    media_type = get_text("media_type") or default_media
    if source_type not in _CANONICAL_SOURCE_TYPES:
        raise ValueError(f"row {row_number}: invalid source_type '{source_type}'")
    if media_type not in _MEDIA_TYPES:
        raise ValueError(f"row {row_number}: invalid media_type '{media_type}'")

    source_class = get_text("source_class") or None
    if source_class is not None and len(source_class) > 64:
        raise ValueError(f"row {row_number}: source_class must be at most 64 characters")
    raw_tags = values.get("tags", "")
    if isinstance(raw_tags, str):
        tags = tuple(tag.strip() for tag in re.split(r"[;,]", raw_tags) if tag.strip())
    elif isinstance(raw_tags, list) and all(isinstance(tag, str) for tag in raw_tags):
        tags = tuple(tag.strip() for tag in raw_tags if tag.strip())
    else:
        raise ValueError(f"row {row_number}: tags must be text or a list of strings")
    invalid_tag = next((tag for tag in tags if not _TAG_PATTERN.fullmatch(tag)), None)
    if invalid_tag is not None:
        raise ValueError(f"row {row_number}: invalid tag '{invalid_tag}'")

    retrieved_at = get_text("retrieved_at")
    discovered_at = get_text("discovered_at")
    if raw_url and retrieved_at and discovered_at:
        raise ValueError(f"row {row_number}: use only one of retrieved_at or discovered_at")
    recorded_at = (
        (discovered_at if raw_url else retrieved_at)
        or retrieved_at
        or (
            datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        )
    )
    try:
        parsed_date = datetime.datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(
            f"row {row_number}: invalid discovery/retrieval timestamp '{recorded_at}'"
        ) from exc
    if parsed_date.tzinfo is None:
        raise ValueError(f"row {row_number}: discovery/retrieval timestamp must include a timezone")

    probe: dict[str, object] = {
        "id": "src_00000000-0000-7000-8000-000000000001",
        "schema_version": 1,
        "source_status": "current",
        "acquisition_status": "acquired" if raw_bytes is not None else "unacquired",
        "source_type": source_type,
        "media_type": media_type,
        "title": title,
    }
    if raw_bytes is not None:
        probe["content_sha256"] = compute_content_hash(raw_bytes)
        probe["retrieved_at"] = recorded_at
    else:
        probe["discovered_at"] = recorded_at
    if canonical_url:
        probe["canonical_url"] = canonical_url
    if source_class:
        probe["source_class"] = source_class
    if tags:
        probe["tags"] = list(tags)
    try:
        registry.validate("source", probe)
    except Exception as exc:
        raise ValueError(f"row {row_number}: invalid source record: {exc}") from exc

    return _ManifestItem(
        row_number=row_number,
        title=title,
        source_type=source_type,
        media_type=media_type,
        canonical_url=canonical_url,
        local_file=local_file or None,
        source_class=source_class,
        tags=tags,
        retrieved_at=recorded_at,
        notes=get_text("notes"),
        raw_bytes=raw_bytes,
    )


def _register_manifest(
    manifest: Path,
    *,
    repository_root: Path,
    owner: str,
    status: str,
    dry_run: bool,
) -> int:
    vault = repository_root / "knowledge-base"
    raw_dir = vault / "90-inbox" / "raw"
    registry = registry_for_root(repository_root, allow_package_fallback=True)
    try:
        rows = _manifest_rows(manifest)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: invalid manifest: {exc}", file=sys.stderr)
        return 2
    items = []
    errors = []
    for row_number, values in rows:
        try:
            items.append(
                _parse_manifest_item(row_number, values, raw_dir=raw_dir, registry=registry)
            )
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(str(exc))
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 2
    if not items:
        print("manifest has no rows")
        return 0

    planned: list[tuple[_ManifestItem, str | None, str]] = []
    seen_identities: dict[str, int] = {}
    for item in items:
        content_hash = compute_content_hash(item.raw_bytes) if item.raw_bytes is not None else None
        duplicate = find_duplicate_source(
            canonical_url=item.canonical_url,
            content_sha256=content_hash,
            repository_root=repository_root,
        )
        identity_keys = []
        if item.canonical_url:
            identity_keys.append(f"url:{item.canonical_url}")
        if content_hash:
            identity_keys.append(f"hash:{content_hash}")
        previous_row = next(
            (seen_identities[key] for key in identity_keys if key in seen_identities), None
        )
        action = (
            f"reuse {duplicate}"
            if duplicate
            else (f"reuse manifest row {previous_row}" if previous_row is not None else "register")
        )
        planned.append((item, duplicate, action))
        for key in identity_keys:
            seen_identities.setdefault(key, item.row_number)
    for item, _, action in planned:
        source_kind = "unacquired" if item.raw_bytes is None else "acquired"
        print(
            f"row {item.row_number}: {action} {source_kind} source "
            f"{item.title!r} ({item.canonical_url or item.local_file})"
        )
    if dry_run:
        print(f"dry run: {len(items)} row(s); no records or manifest rows written")
        return 0

    manifest_path = vault / "90-inbox" / "manifest.md"
    if not manifest_path.is_file():
        print(f"error: manifest not found at {manifest_path}", file=sys.stderr)
        return 2
    manifest_text = manifest_path.read_text(encoding="utf-8")
    existing_rows = parse_rows(manifest_text)
    today = datetime.date.today().isoformat()
    additions = []
    registered = 0
    existing_items = {row[0] for row in existing_rows if row}
    for item, duplicate, _ in planned:
        if item.raw_bytes is None:
            source_id = duplicate or find_duplicate_source(
                canonical_url=item.canonical_url, repository_root=repository_root
            )
            if source_id is None:
                source_id = register_source(
                    title=item.title,
                    source_type=item.source_type,
                    media_type=item.media_type,
                    canonical_url=item.canonical_url,
                    acquisition_status="unacquired",
                    source_class=item.source_class,
                    tags=list(item.tags),
                    retrieved_at=item.retrieved_at,
                    repository_root=repository_root,
                )
        else:
            source_id, content_hash, raw_location = _canonical_source_for_raw(
                item.local_file or "",
                kind=item.source_type,
                source_type=item.source_type,
                media_type=item.media_type,
                title=item.title,
                canonical_url=item.canonical_url,
                source_class=item.source_class,
                tags=list(item.tags),
                retrieved_at=item.retrieved_at,
                repository_root=repository_root,
            )
            intake_kind = item.source_type if item.source_type in VALID_KIND else "other"
            item_id = intake_id(content_sha256=content_hash, kind=intake_kind)
            record_path = _intake_record_path(repository_root / ".research" / "intake", item_id)
            if not record_path.exists():
                write_atomic(
                    record_path,
                    _build_intake_record(
                        item_id=item_id,
                        filename=item.local_file or "",
                        raw_location=raw_location,
                        content_sha256=content_hash,
                        kind=intake_kind,
                        source_id=source_id,
                        owner=owner,
                        status=status,
                        outcome=item.notes or "—",
                        added_on=today,
                    ),
                    schema_name="intake",
                )
        if item.display_item not in existing_items:
            outcome = item.notes or (item.canonical_url or "—")
            safe_cells = [
                item.display_item,
                item.source_type,
                today,
                status,
                owner,
                outcome,
            ]
            additions.append(
                "| " + " | ".join(cell.replace("|", "\\|") for cell in safe_cells) + " |\n"
            )
            existing_items.add(item.display_item)
        registered += 1
    for row in additions:
        manifest_text = _append_row(manifest_text, row)
    if additions:
        manifest_path.write_text(manifest_text, encoding="utf-8")
    print(f"registered {registered} manifest row(s); added {len(additions)} new queue row(s)")
    return 0


def cmd_intake_register(
    file: str | None,
    kind: str = "other",
    owner: str = "agent",
    status: str = "new",
    outcome: str = "—",
    set_file: str | None = None,
    list_: bool = False,
    repository_root: Path | None = None,
    manifest: str | None = None,
    dry_run: bool = False,
) -> int:
    repo = Path(repository_root) if repository_root is not None else REPO_ROOT
    if repo.name == "knowledge-base":
        repo = repo.parent
    if manifest is not None:
        if file or set_file or list_:
            print(
                "error: --manifest cannot be combined with --file, --set, or --list",
                file=sys.stderr,
            )
            return 2
        if status not in VALID_STATUS:
            print(f"error: invalid status '{status}'", file=sys.stderr)
            return 2
        return _register_manifest(
            Path(manifest).expanduser(),
            repository_root=repo.resolve(),
            owner=owner,
            status=status,
            dry_run=dry_run,
        )
    if dry_run:
        print("error: --dry-run requires --manifest", file=sys.stderr)
        return 2
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
                    intake_dir = repo / RESEARCH_INTAKE_DIR.relative_to(REPO_ROOT)
                    record_path = _find_intake_record_by_filename(intake_dir, set_file)
                    if record_path is None:
                        print(
                            f"warning: no canonical intake record for '{set_file}'; "
                            "the manifest row is authoritative for this item",
                            file=sys.stderr,
                        )
                    else:
                        _sync_intake_record_status(record_path, status=status, outcome=outcome)
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


def cmd_source_acquire(
    source_id: str,
    file: str,
    *,
    repository_root: Path,
) -> int:
    """Acquire a registered URL source from a file in the raw inbox."""
    raw_dir = (Path(repository_root) / "knowledge-base" / "90-inbox" / "raw").resolve()
    candidate = Path(file)
    if candidate.is_absolute():
        print("error: --file must be relative to knowledge-base/90-inbox/raw", file=sys.stderr)
        return 2
    resolved = (raw_dir / candidate).resolve()
    try:
        resolved.relative_to(raw_dir)
    except ValueError:
        print("error: --file escapes knowledge-base/90-inbox/raw", file=sys.stderr)
        return 2
    if not resolved.is_file():
        print(f"error: file not found: {file}", file=sys.stderr)
        return 2
    try:
        digest = acquire_source(
            source_id,
            resolved.read_bytes(),
            raw_location=str(resolved.relative_to(Path(repository_root).resolve())),
            repository_root=repository_root,
        )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"acquired {source_id} ({digest})")
    return 0


__all__ = [
    "VALID_KIND",
    "VALID_STATUS",
    "canonical_source_for_raw",
    "cmd_intake_register",
    "intake_id",
    "parse_rows",
]
