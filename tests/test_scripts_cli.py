"""CLI workspace-root routing tests."""

from dataclasses import dataclass
from pathlib import Path

import pytest

import polder_research.scripts as scripts
import polder_research.scripts.decision as decision_cli


def test_workspace_root_option_works_before_or_after_command(tmp_path, monkeypatch):
    seen: list[Path] = []
    monkeypatch.setattr(scripts, "cmd_build_state", lambda root: seen.append(root) or 0)

    assert scripts.main(["--root", str(tmp_path), "state-build"]) == 0
    assert scripts.main(["state-build", "--root", str(tmp_path)]) == 0
    assert seen == [tmp_path.resolve(), tmp_path.resolve()]


def test_intake_manifest_cli_options_reach_workspace(tmp_path, capsys):
    inbox = tmp_path / "knowledge-base" / "90-inbox"
    (inbox / "raw").mkdir(parents=True)
    (inbox / "manifest.md").write_text(
        "---\ntype: inbox\nstatus: current\ntags: [intake]\n---\n\n"
        "# Intake\n\n## Queue\n\n"
        "| Item | Kind | Added | Status | Owner | Outcome |\n"
        "|---|---|---|---|---|---|\n\n## Status lifecycle\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "seed.csv"
    manifest.write_text("title,canonical_url\nReference,https://example.com\n", encoding="utf-8")

    assert (
        scripts.main(
            [
                "--root",
                str(tmp_path),
                "intake-register",
                "--manifest",
                str(manifest),
                "--dry-run",
            ]
        )
        == 0
    )
    assert "dry run" in capsys.readouterr().out
    assert not (tmp_path / ".research").exists()


@pytest.mark.parametrize(("status", "expected"), [("completed", 0), ("failed", 1), ("blocked", 2)])
def test_decision_run_exit_code_surfaces_attempt_status(
    tmp_path, monkeypatch, capsys, status, expected
):
    @dataclass
    class Attempt:
        status: str

    @dataclass
    class Policy:
        fields: dict

    monkeypatch.setattr(
        decision_cli, "run_workflow", lambda *args, **kwargs: (Attempt(status), Policy({}))
    )
    state_file = tmp_path / "state.json"
    state_file.write_text("{}", encoding="utf-8")

    result = decision_cli.cmd_decision_run(
        workflow="intake-triage",
        target_kind="source",
        target_id="src_example",
        state_file=str(state_file),
        root=str(tmp_path),
        provider="laya",
        roles=[],
        sensitivity="public",
        personal_data=False,
        remote_processing_allowed=False,
        research_method="continuous_intelligence",
    )

    assert result == expected
    assert f'"status": "{status}"' in capsys.readouterr().out
