from __future__ import annotations

import os
import shutil
import subprocess
import tarfile
from pathlib import Path


def _write_executable(path: Path, contents: str) -> None:
    path.write_text(contents, encoding="utf-8")
    path.chmod(0o755)


def test_installer_uses_latest_release_unstable_branch_and_explicit_ref(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    archive = tmp_path / "source.tar.gz"
    curl_log = tmp_path / "curl.log"
    source_root = tmp_path / "archive-root"
    (source_root / "knowledge-base" / "01-project").mkdir(parents=True)
    (source_root / "knowledge-base" / "01-project" / "brief.md").write_text("source brief")
    with tarfile.open(archive, "w:gz") as bundle:
        bundle.add(source_root, arcname="polder-research-pipeline-test")

    _write_executable(
        fake_bin / "curl",
        """#!/bin/sh
set -eu
url=
output=
previous=
for arg in "$@"; do
  if [ "$previous" = output ]; then output=$arg; previous=; continue; fi
  case "$arg" in
    --output) previous=output ;;
    https://*) url=$arg ;;
  esac
done
case "$url" in
  */releases/latest)
    printf '%s\\n' "$url" >> "$CURL_LOG"
    printf '{"tag_name":"v9.8.7"}\\n'
    ;;
  */tar.gz/*)
    printf '%s\\n' "$url" >> "$CURL_LOG"
    cp "$ARCHIVE_STUB" "$output"
    ;;
  *) exit 9 ;;
esac
""",
    )
    real_python = shutil.which("python3")
    assert real_python is not None
    _write_executable(
        fake_bin / "python3",
        f"""#!/bin/sh
set -eu
if [ "${{1:-}}" = -c ]; then
  case "$2" in
    *json.load*) exec {real_python!s} "$@" ;;
    *'print("%d.%d"'*) printf '3.14\\n' ;;
    *'raise SystemExit(0 if sys.version_info'*) exit 0 ;;
  esac
fi
if [ "${{1:-}}" = -m ] && [ "${{2:-}}" = venv ]; then
  mkdir -p "$3/bin"
  printf '#!/bin/sh\\nexit 0\\n' > "$3/bin/python"
  printf '#!/bin/sh\\nexit 0\\n' > "$3/bin/polder-research"
  chmod +x "$3/bin/python" "$3/bin/polder-research"
  exit 0
fi
exec {real_python!s} "$@"
""",
    )

    env = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "CURL_LOG": str(curl_log),
        "ARCHIVE_STUB": str(archive),
        "POLDER_RESEARCH_REPOSITORY": "PolderLabs/polder-research-pipeline",
    }
    installer = Path(__file__).parents[1] / "install.sh"

    for target, options in (
        ("stable", []),
        ("unstable", ["--unstable"]),
        ("pinned", ["--ref", "fix-branch"]),
    ):
        subprocess.run(
            ["sh", str(installer), *options, "--target", str(tmp_path / target)],
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

    conflict_target = tmp_path / "invalid-combination"
    conflict = subprocess.run(
        [
            "sh",
            str(installer),
            "--unstable",
            "--ref",
            "fix-branch",
            "--target",
            str(conflict_target),
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    assert conflict.returncode != 0
    assert "cannot be combined" in conflict.stderr
    assert not conflict_target.exists()

    requests = curl_log.read_text(encoding="utf-8").splitlines()
    assert requests == [
        "https://api.github.com/repos/PolderLabs/polder-research-pipeline/releases/latest",
        "https://codeload.github.com/PolderLabs/polder-research-pipeline/tar.gz/v9.8.7",
        "https://codeload.github.com/PolderLabs/polder-research-pipeline/tar.gz/main",
        "https://codeload.github.com/PolderLabs/polder-research-pipeline/tar.gz/fix-branch",
    ]
