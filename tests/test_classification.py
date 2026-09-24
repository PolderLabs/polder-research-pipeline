"""Contract tests for automatic taxonomy classification."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from polder_research.classification import classify_text, merge_proposals


def _repository(tmp_path: Path, *, provider: str = "rules", enabled: bool = True) -> Path:
    config_dir = tmp_path / "knowledge-base"
    config_dir.mkdir()
    config = {
        "classification": {
            "enabled": enabled,
            "provider": provider,
            "minimum_confidence": 0.75,
            "max_input_chars": 100,
            "taxonomy": {
                "version": "test-1",
                "categories": {
                    "research": {
                        "description": "research material",
                        "keywords": ["research", "paper"],
                    },
                    "other": {"description": "other material", "keywords": []},
                },
                "tags": {
                    "visual-models": {
                        "description": "visual models",
                        "keywords": ["vision model"],
                    }
                },
            },
        }
    }
    (config_dir / "research.config.yaml").write_text(yaml.safe_dump(config))
    (tmp_path / "schemas").mkdir()
    return tmp_path


def test_rules_classification_is_auditable_and_idempotent(tmp_path: Path):
    root = _repository(tmp_path)
    text = "A research paper evaluates a vision model."
    first = classify_text(text, target_kind="source", target_id="src-test", repository_root=root)
    second = classify_text(text, target_kind="source", target_id="src-test", repository_root=root)

    assert first is not None
    assert second == first
    assert first["disposition"] == "accepted"
    assert first["category"] == "research"
    assert first["proposed_tags"] == ["visual-models"]
    assert first["taxonomy_snapshot"]["version"] == "test-1"
    assert first["questions"]["category"]["type"] == "choice"
    persisted = json.loads(
        (root / ".research/classifications" / f"{first['id']}.json").read_text()
    )
    assert text not in json.dumps(persisted)
    assert persisted["input_sha256"] == first["input_sha256"]
    assert len(list((root / ".research/classifications").glob("cls_*.json"))) == 1


def test_merge_keeps_user_metadata_and_only_adds_classification_ids():
    record = {"id": "src-test", "topic": "human-topic", "tags": ["manual"]}
    result = {
        "id": "cls-test",
        "disposition": "accepted",
        "category": "model-output",
        "proposed_tags": ["manual", "visual-models"],
    }

    merged = merge_proposals(record, result)

    assert merged["topic"] == "human-topic"
    assert merged["tags"] == ["manual", "visual-models"]
    assert merged["classification_ids"] == ["cls-test"]


def test_disabled_classification_has_no_side_effect(tmp_path: Path):
    root = _repository(tmp_path, enabled=False)

    assert classify_text("research", target_kind="claim", target_id="clm-test", repository_root=root) is None
    assert not (root / ".research").exists()


def test_provider_failure_is_recorded_without_source_text(tmp_path: Path, monkeypatch):
    root = _repository(tmp_path, provider="jev")
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    text = "A confidential research passage that must not be stored."

    result = classify_text(text, target_kind="source", target_id="src-test", repository_root=root)

    assert result is not None
    assert result["disposition"] == "failed"
    content = json.dumps(result)
    assert text not in content
    assert "TYPESAFE_API_KEY is not set" in content
    assert result["taxonomy_sha256"]
