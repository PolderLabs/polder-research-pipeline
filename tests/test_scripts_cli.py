"""CLI workspace-root routing tests."""

from pathlib import Path

import polder_research.scripts as scripts


def test_workspace_root_option_works_before_or_after_command(tmp_path, monkeypatch):
    seen: list[Path] = []
    monkeypatch.setattr(scripts, "cmd_build_state", lambda root: seen.append(root) or 0)

    assert scripts.main(["--root", str(tmp_path), "state-build"]) == 0
    assert scripts.main(["state-build", "--root", str(tmp_path)]) == 0
    assert seen == [tmp_path.resolve(), tmp_path.resolve()]
