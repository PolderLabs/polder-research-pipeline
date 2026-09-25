"""Versioned deterministic builders shared by initial classification and replay."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


def _digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def clip_state(value: Any, maximum_chars: int) -> Any:
    """Clip text fields in traversal order without flattening the state shape."""
    remaining = maximum_chars

    def visit(item: Any) -> Any:
        nonlocal remaining
        if isinstance(item, str):
            clipped = item[:remaining]
            remaining = max(0, remaining - len(clipped))
            return clipped
        if isinstance(item, dict):
            return {key: visit(child) for key, child in item.items()}
        if isinstance(item, list):
            return [visit(child) for child in item]
        return item

    return visit(value)


def state_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(state_text(child) for child in value.values())
    if isinstance(value, list):
        return " ".join(state_text(child) for child in value)
    return str(value) if value is not None else ""


@dataclass(frozen=True)
class BuiltState:
    state: dict[str, Any]
    original_hash: str
    submitted_hash: str
    builder_id: str
    excluded_fields: tuple[str, ...] = ()
    privacy_flags: tuple[str, ...] = ()


def build_source_metadata(record: dict[str, Any]) -> BuiltState:
    state = {
        "source": {
            "title": record.get("title", ""),
            "kind": record.get("source_type", ""),
            "media_type": record.get("media_type", ""),
            "language": record.get("language", ""),
        }
    }
    return BuiltState(state, _digest(record), _digest(state), "source/metadata@1")


def build_segment_default(record: dict[str, Any]) -> BuiltState:
    state = {"segment": {"text": record.get("text", "")}}
    return BuiltState(state, _digest(record), _digest(state), "segment/default@1")


def build_claim_default(record: dict[str, Any]) -> BuiltState:
    state = {"claim": {"statement": record.get("statement", "")}}
    return BuiltState(state, _digest(record), _digest(state), "claim/default@1")


def build_entity_default(record: dict[str, Any]) -> BuiltState:
    state = {
        "entity": {
            "name": record.get("name", ""),
            "description": record.get("description", ""),
            "aliases": record.get("aliases", []),
        }
    }
    return BuiltState(state, _digest(record), _digest(state), "entity/default@1")


def build_state_for_target(kind: str, record: dict[str, Any]) -> BuiltState:
    builders = {
        "source": build_source_metadata,
        "segment": build_segment_default,
        "claim": build_claim_default,
        "entity": build_entity_default,
    }
    try:
        return builders[kind](record)
    except KeyError as exc:
        raise ValueError(f"unsupported decision target kind: {kind!r}") from exc
