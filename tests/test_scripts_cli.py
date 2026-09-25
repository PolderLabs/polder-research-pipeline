"""CLI workspace-root routing tests."""

from pathlib import Path

import polder_research.scripts as scripts


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
