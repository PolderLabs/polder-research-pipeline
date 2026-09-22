"""Behavioral contracts for the P1 schema and template authorities."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from polder_research.schemas import SchemaError, SchemaRegistry
from polder_research.templates import TemplateRegistry


def test_schema_registry_loads_explicit_root_in_filename_order(tmp_path: Path):
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir()
    (schema_dir / "zeta.schema.json").write_text(
        json.dumps({"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "string"}),
        encoding="utf-8",
    )
    (schema_dir / "alpha.schema.json").write_text(
        json.dumps({"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "integer"}),
        encoding="utf-8",
    )

    registry = SchemaRegistry(tmp_path)

    assert registry.names() == ("alpha", "zeta")
    registry.validate("alpha", 3)
    with pytest.raises(SchemaError):
        registry.validate("alpha", "3")


def test_schema_registry_rejects_malformed_canonical_schema(tmp_path: Path):
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir()
    (schema_dir / "broken.schema.json").write_text("{", encoding="utf-8")

    with pytest.raises(SchemaError, match="cannot load schema"):
        SchemaRegistry(tmp_path)


def test_template_registry_is_derived_from_template_files(tmp_path: Path):
    template_dir = tmp_path / "knowledge-base" / "99-templates"
    template_dir.mkdir(parents=True)
    (template_dir / "README.md").write_text("not a template", encoding="utf-8")
    (template_dir / "zeta-template.md").write_text("zeta body", encoding="utf-8")
    (template_dir / "alpha-template.md").write_text("alpha body", encoding="utf-8")

    registry = TemplateRegistry(tmp_path / "knowledge-base")

    assert registry.names() == ("alpha", "zeta")
    assert [template.name for template in registry] == ["alpha", "zeta"]
    assert registry.resolve("alpha").text == "alpha body"
    assert registry.resolve("alpha").path == template_dir / "alpha-template.md"
    with pytest.raises(KeyError):
        registry.resolve("README")
