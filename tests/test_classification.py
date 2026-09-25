"""Contract tests for automatic taxonomy classification."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml

from polder_research import classification
from polder_research.classification import classify_text, merge_proposals


def _repository(tmp_path: Path, *, provider: str = "rules", enabled: bool = True) -> Path:
    config_dir = tmp_path / "knowledge-base"
    config_dir.mkdir()
    config = {
        "schema_version": 1,
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
        },
    }
    if provider == "jev":
        # Jev is remote: reach the provider call (not the approval gate) so the
        # failure path records the missing-key error without source text.
        config["decision"] = {"remote_processing": {"default_allowed": True}}
    (config_dir / "research.config.yaml").write_text(yaml.safe_dump(config))
    shutil.copytree(Path(__file__).parents[1] / "schemas", tmp_path / "schemas")
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
    persisted = json.loads((root / ".research/classifications" / f"{first['id']}.json").read_text())
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

    # Human metadata is never rewritten by a model proposal; the immutable
    # classification id is the only thing merged (effective tags are projected).
    assert merged["topic"] == "human-topic"
    assert merged["tags"] == ["manual"]
    assert merged["classification_ids"] == ["cls-test"]


def test_merge_ignores_proposals_that_were_not_accepted():
    record = {"id": "src-test", "tags": ["manual"]}

    for result in (None, {"id": "cls-test", "disposition": "failed"}):
        assert merge_proposals(dict(record), result) == record


def test_disabled_classification_has_no_side_effect(tmp_path: Path):
    root = _repository(tmp_path, enabled=False)

    assert (
        classify_text("research", target_kind="claim", target_id="clm-test", repository_root=root)
        is None
    )
    assert not (root / ".research").exists()


def test_saved_api_keys_are_scoped_to_repository(tmp_path: Path) -> None:
    credential_root = tmp_path / "credential-repository"
    secret_path = credential_root / ".research/web-secrets.json"
    secret_path.parent.mkdir(parents=True)
    secret_path.write_text(json.dumps({"TYPESAFE_API_KEY": "synthetic-test-key"}))
    other_repository = tmp_path / "other-repository"
    other_repository.mkdir()
    other_root = _repository(other_repository, provider="jev")

    assert (
        classification._saved_api_key("TYPESAFE_API_KEY", credential_root) == "synthetic-test-key"
    )
    assert classification._saved_api_key("TYPESAFE_API_KEY", other_root) is None


def test_provider_failure_is_recorded_without_source_text(tmp_path: Path, monkeypatch):
    root = _repository(tmp_path, provider="jev")
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    text = "A confidential research passage that must not be stored."

    def unavailable(state, questions, config, *, repository_root=None):
        raise RuntimeError("Jev selected but TYPESAFE_API_KEY is not set")

    # The recorded-failure contract must hold whether or not the optional
    # typesafe-sdk extra happens to be installed in this environment.
    monkeypatch.setattr(classification, "_remote_call", unavailable)

    result = classify_text(
        text,
        target_kind="source",
        target_id="src-test",
        repository_root=root,
        policy_metadata={"sensitivity": "public", "remote_processing_allowed": True},
    )

    assert result is not None
    assert result["disposition"] == "failed"
    content = json.dumps(result)
    assert text not in content
    assert "TYPESAFE_API_KEY is not set" in content
    assert result["taxonomy_sha256"]


@pytest.mark.parametrize(
    "message",
    [
        "Jev selected but TYPESAFE_API_KEY is not set",
        "Jev selected; install the optional dependency with `pip install "
        "'polder-research-pipeline[jev]'`",
        "Laya selected; install the optional dependency",
        "Laya is not installed; install the optional laya extra",
        "sensitive classification requires a local provider",
    ],
)
def test_safe_failure_message_keeps_diagnosable_provider_errors(message: str) -> None:
    assert classification._safe_failure_message(RuntimeError(message)) == message


def test_safe_failure_message_redacts_unrecognized_errors() -> None:
    """An unknown provider error must not leak payload text into a record."""
    assert (
        classification._safe_failure_message(
            RuntimeError("HTTP 500 from provider with echoed source text")
        )
        == "classification provider or response failed"
    )
