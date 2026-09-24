"""CI and security configuration invariants (AUDIT.md §42, §43).

These tests assert consumer-visible properties of the CI/security
configuration: SHA-pinning, minimum permissions, secret-scanning presence,
Dependabot presence, and absence of duplicate editable installs. They do
NOT execute the workflow; they read the on-disk configuration files.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CI_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"
DEPENDABOT_PATH = REPO_ROOT / ".github" / "dependabot.yml"
GITLEAKS_PATH = REPO_ROOT / ".gitleaks.toml"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
RUFF_PATH = REPO_ROOT / "ruff.toml"

# matches `- uses: owner/repo@<sha> # <comment>`
USES_PIN_RE = re.compile(r"^\s*-\s*uses:\s+([\w.-]+/[\w.-]+)@([0-9a-f]{40})(?:\s+#\s*(.*))?$")

REQUIRED_JOBS = (
    "lint",
    "test",
    "vault-audit",
    "schema-validate",
    "secret-scan",
    "implementation-status",
)


@pytest.fixture(scope="module")
def ci_yaml() -> dict:
    return yaml.safe_load(CI_PATH.read_text())


@pytest.fixture(scope="module")
def ci_text() -> str:
    return CI_PATH.read_text()


@pytest.fixture(scope="module")
def dependabot_yaml() -> dict:
    return yaml.safe_load(DEPENDABOT_PATH.read_text())


def test_ci_yaml_parses(ci_yaml: dict) -> None:
    assert isinstance(ci_yaml, dict)
    assert ci_yaml.get("name") == "ci"


def test_workflow_top_level_permissions_are_minimal(ci_yaml: dict) -> None:
    perms = ci_yaml.get("permissions")
    assert isinstance(perms, dict), "workflow must declare top-level permissions"
    assert set(perms.keys()) == {"contents"}, "top-level permissions must be contents: read only"
    assert perms["contents"] == "read"


def test_jobs_declare_minimum_permissions(ci_yaml: dict) -> None:
    jobs = ci_yaml.get("jobs") or {}
    assert jobs, "workflow must declare at least one job"
    for name, job in jobs.items():
        perms = job.get("permissions")
        assert isinstance(perms, dict), f"job {name!r} must declare permissions"
        assert set(perms.keys()) == {"contents"}, (
            f"job {name!r} permissions must be contents: read only, got {set(perms)}"
        )
        assert perms["contents"] == "read", f"job {name!r} must declare contents: read"


def test_concurrency_cancels_stale_runs(ci_yaml: dict) -> None:
    conc = ci_yaml.get("concurrency") or {}
    assert conc.get("cancel-in-progress") is True, (
        "concurrency.cancel-in-progress must be true for stale-run cancellation"
    )


def test_all_actions_pinned_to_full_sha(ci_text: str) -> None:
    uses_lines = [
        line
        for line in ci_text.splitlines()
        if "uses:" in line and re.search(r"^\s*-\s*uses:", line)
    ]
    assert uses_lines, "workflow must use at least one action"
    for line in uses_lines:
        m = USES_PIN_RE.match(line)
        assert m is not None, f"action must be pinned to a 40-char SHA: {line!r}"
        sha = m.group(2)
        assert re.fullmatch(r"[0-9a-f]{40}", sha), f"invalid SHA pin on line: {line!r}"


def test_required_jobs_present(ci_yaml: dict) -> None:
    jobs = ci_yaml.get("jobs") or {}
    missing = [name for name in REQUIRED_JOBS if name not in jobs]
    assert not missing, f"missing required CI jobs: {missing}"


@pytest.mark.parametrize("job_name", REQUIRED_JOBS)
def test_required_job_is_well_formed(ci_yaml: dict, job_name: str) -> None:
    job = ci_yaml["jobs"][job_name]
    assert job.get("runs-on")
    steps = job.get("steps")
    assert isinstance(steps, list) and steps, f"job {job_name!r} must declare steps"


def test_no_duplicate_editable_install(ci_yaml: dict) -> None:
    """Each job installs the editable package at most once."""
    for name, job in ci_yaml["jobs"].items():
        commands = [
            step["run"] for step in job.get("steps", []) if isinstance(step, dict) and "run" in step
        ]
        install_count = sum(command.count('pip install -e ".[dev]"') for command in commands)
        assert install_count <= 1, f"job {name!r} performs duplicate editable package installs"


def test_dependabot_present(dependabot_yaml: dict) -> None:
    updates = dependabot_yaml.get("updates") or []
    ecosystems = {u.get("package-ecosystem") for u in updates}
    assert "pip" in ecosystems, "Dependabot must cover pip"
    assert "github-actions" in ecosystems, "Dependabot must cover github-actions"


def test_gitleaks_config_present() -> None:
    assert GITLEAKS_PATH.is_file(), "gitleaks config must exist"
    text = GITLEAKS_PATH.read_text()
    assert "[extend]" in text, "gitleaks config must extend defaults"
    assert "useDefault" in text, "gitleaks config must declare useDefault"


def test_secret_scan_job_installs_pinned_gitleaks_cli(ci_yaml: dict) -> None:
    """Use the CLI so organization license requirements cannot disable scans."""
    steps = ci_yaml["jobs"]["secret-scan"]["steps"]
    commands = [step.get("run", "") for step in steps]
    assert any(
        "go install github.com/zricethezav/gitleaks/v8@v8.30.1" in command for command in commands
    )
    assert any("gitleaks git --redact --no-banner" in command for command in commands)
    assert all("GITLEAKS_LICENSE" not in command for command in commands)


def test_pyproject_declares_supported_python() -> None:
    text = PYPROJECT_PATH.read_text()
    m = re.search(r'^requires-python\s*=\s*"([^"]+)"\s*$', text, re.MULTILINE)
    assert m is not None, "pyproject.toml must declare requires-python"
    spec = m.group(1)
    floor = re.match(r"^>=?(\d+)\.(\d+)", spec)
    assert floor is not None, f"unparseable requires-python spec: {spec!r}"
    major, minor = int(floor.group(1)), int(floor.group(2))
    assert (major, minor) >= (3, 11), f"requires-python must support >=3.11, got {spec!r}"


def test_ruff_targets_supported_python() -> None:
    text = RUFF_PATH.read_text()
    m = re.search(r'^target-version\s*=\s*"py(\d)(\d+)"\s*$', text, re.MULTILINE)
    assert m is not None, "ruff.toml must declare target-version"
    major, minor = int(m.group(1)), int(m.group(2))
    assert (major, minor) >= (3, 11), (
        f"ruff target-version must be py311 or newer, got py{major}{minor}"
    )


def test_dev_extras_are_pinned() -> None:
    """dev dependencies must be pinned for deterministic CI setup."""
    text = PYPROJECT_PATH.read_text()
    block = re.search(r"dev\s*=\s*\[([^\]]+)\]", text, re.DOTALL)
    assert block is not None, "pyproject.toml must define [dev] extras"
    for raw in block.group(1).split(","):
        line = raw.strip().strip('"').strip("'")
        if not line:
            continue
        # pinned form: name==X.Y.Z
        assert "==" in line, f"dev extra must be pinned with == for deterministic install: {line!r}"


REQUIREMENTS_CI_PATH = REPO_ROOT / "requirements-ci.txt"


def test_requirements_ci_present_and_pinned() -> None:
    """CI must consume a fully-pinned requirements-ci.txt — no floating pins."""
    assert REQUIREMENTS_CI_PATH.is_file(), "requirements-ci.txt must exist"
    for raw in REQUIREMENTS_CI_PATH.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # Pinned form: name==X.Y.Z (no extras, no env markers after the pin)
        assert "==" in line and ">" not in line and "<" not in line, (
            f"requirements-ci.txt entry must be exactly pinned (==X.Y.Z): {line!r}"
        )


def test_ci_installs_from_requirements_ci(ci_text: str) -> None:
    """Every CI install step must pull from requirements-ci.txt, not float."""
    assert "pip install -r requirements-ci.txt" in ci_text, (
        "CI must install pinned toolchain via requirements-ci.txt"
    )
    # The pre-lockfile floating ruff install must be gone.
    assert "ruff>=0.1" not in ci_text, "CI must not perform a floating ruff install"


def test_drift_check_present(ci_text: str) -> None:
    assert "Generated-state deterministic smoke check" in ci_text


def test_schema_validation_step_present(ci_text: str) -> None:
    assert "Validate JSON schemas" in ci_text, "workflow must include schema validation"
