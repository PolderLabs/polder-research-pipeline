"""End-to-end tests for the public research-boundary commit hook."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK = REPO_ROOT / ".githooks" / "pre-commit"


def _run(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=repo,
        check=check,
        text=True,
        capture_output=True,
        env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1"},
    )


@pytest.fixture
def hook_repo(tmp_path: Path) -> Path:
    """Create an independent Git repository with the hook's real audit inputs."""
    repo = tmp_path / "repo"
    repo.mkdir()
    shutil.copy2(HOOK, repo / ".githooks-pre-commit")
    (repo / ".githooks").mkdir()
    (repo / ".githooks-pre-commit").replace(repo / ".githooks" / "pre-commit")
    shutil.copytree(REPO_ROOT / "skills", repo / "skills")
    shutil.copytree(REPO_ROOT / "src", repo / "src")
    shutil.copytree(REPO_ROOT / "knowledge-base", repo / "knowledge-base")
    shutil.copytree(REPO_ROOT / "schemas", repo / "schemas")
    for name in ("AGENTS.md", "CLAUDE.md"):
        shutil.copy2(REPO_ROOT / name, repo / name)

    _run(repo, "git", "init", "--quiet")
    _run(repo, "git", "config", "user.email", "test@example.invalid")
    _run(repo, "git", "config", "user.name", "Hook Test")
    _run(repo, "git", "add", "--all")
    _run(repo, "git", "commit", "--quiet", "-m", "initial")
    return repo


def _hook(repo: Path) -> subprocess.CompletedProcess[str]:
    return _run(repo, "bash", ".githooks/pre-commit", check=False)


def test_unrelated_edit_with_preexisting_fixture_id_passes(hook_repo: Path):
    fixture = hook_repo / "fixture.py"
    fixture.write_text('fixture_id = "src_" + "12345678-abcd"\n', encoding="utf-8")
    _run(hook_repo, "git", "add", "fixture.py")
    _run(hook_repo, "git", "commit", "--quiet", "-m", "fixture")

    (hook_repo / "safe.txt").write_text("ordinary staged edit\n", encoding="utf-8")
    _run(hook_repo, "git", "add", "safe.txt")

    result = _hook(hook_repo)

    assert result.returncode == 0, result.stderr


def test_new_private_identifier_fails(hook_repo: Path):
    (hook_repo / "safe.txt").write_text("src_" + "12345678-abcd\n", encoding="utf-8")
    _run(hook_repo, "git", "add", "safe.txt")

    result = _hook(hook_repo)

    assert result.returncode == 1
    assert "private research identifiers" in result.stderr


@pytest.mark.parametrize(
    "relative_path",
    [
        ".research/with spaces.json",
        "Research_1/line\nbreak.md",
        "Research_1/-leading-dash.md",
        "knowledge-base/90-inbox/with spaces\nand-newline.md",
    ],
)
def test_private_paths_with_special_filenames_fail(hook_repo: Path, relative_path: str):
    path = hook_repo / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("private\n", encoding="utf-8")
    _run(hook_repo, "git", "add", "--force", "--", relative_path)

    result = _hook(hook_repo)

    assert result.returncode == 1
    assert "BLOCKED:" in result.stderr


def test_safe_staged_change_reaches_real_vault_audit(hook_repo: Path):
    (hook_repo / "safe.txt").write_text("ordinary staged edit\n", encoding="utf-8")
    _run(hook_repo, "git", "add", "safe.txt")

    result = _hook(hook_repo)

    assert result.returncode == 0, result.stderr
