#!/bin/sh
set -eu

REPOSITORY=${POLDER_RESEARCH_REPOSITORY:-PolderLabs/polder-research-pipeline}
REF=main
TARGET=
WITH_DEV=0
WITH_LAYA=1

usage() {
  cat <<'EOF'
Install Polder Research Pipeline as a new, independent research workspace.

Usage:
  curl -fsSL https://raw.githubusercontent.com/PolderLabs/polder-research-pipeline/main/install.sh | sh -s -- --target ./my-research

Options:
  --target DIR   New directory for the complete pipeline and research workspace (required)
  --ref REF      GitHub branch, tag, or commit to use as the template (default: main)
  --with-dev     Also install pytest and Ruff
  --with-laya    Install the default local Laya classifier (kept for compatibility)
  --without-laya Skip Laya and its machine-learning dependencies
  -h, --help     Show this help

The installer downloads the complete source archive without cloning Git history,
installs the application in a project-local .venv, initializes local research
state and a new Git repository, and leaves the new repository without a remote.
EOF
}

fail() {
  printf 'Polder installer: %s\n' "$1" >&2
  exit 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --target)
      [ "$#" -ge 2 ] || fail '--target requires a directory'
      TARGET=$2
      shift 2
      ;;
    --ref)
      [ "$#" -ge 2 ] || fail '--ref requires a branch, tag, or commit'
      REF=$2
      shift 2
      ;;
    --with-dev)
      WITH_DEV=1
      shift
      ;;
    --with-laya)
      WITH_LAYA=1
      shift
      ;;
    --without-laya)
      WITH_LAYA=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "unknown option: $1 (try --help)"
      ;;
  esac
done

[ -n "$TARGET" ] || fail 'choose an install location with --target DIR'
command -v curl >/dev/null 2>&1 || fail 'curl is required to download the source archive'
command -v git >/dev/null 2>&1 || fail 'Git is required to initialize the local workspace'
command -v python3 >/dev/null 2>&1 || fail 'Python 3.14 or newer is required; python3 was not found'
PYTHON_VERSION=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 14) else 1)' || fail "Python 3.14 or newer is required; found $PYTHON_VERSION"

case "$REF" in
  ''|/*|-*|*..*|*//*|*/|*[!A-Za-z0-9._/-]*) fail 'ref may contain only letters, digits, dot, underscore, hyphen, and slash; path traversal is not allowed' ;;
esac
REPOSITORY_OWNER=${REPOSITORY%%/*}
REPOSITORY_NAME=${REPOSITORY#*/}
case "$REPOSITORY" in
  */*) ;;
  *) fail 'POLDER_RESEARCH_REPOSITORY must use the OWNER/REPOSITORY format' ;;
esac
case "$REPOSITORY_NAME" in
  ''|*/*|*[!A-Za-z0-9._-]*) fail 'repository name is invalid' ;;
esac
case "$REPOSITORY_OWNER" in
  ''|*[!A-Za-z0-9._-]*) fail 'repository owner is invalid' ;;
esac

TARGET_PARENT=$(dirname "$TARGET")
TARGET_NAME=$(basename "$TARGET")
[ "$TARGET_NAME" != . ] && [ "$TARGET_NAME" != .. ] && [ "$TARGET_NAME" != / ] || fail 'target must be a new directory path, not . or /'
mkdir -p "$TARGET_PARENT"
TARGET_PARENT=$(CDPATH= cd -- "$TARGET_PARENT" && pwd -P)
TARGET_PATH=$TARGET_PARENT/$TARGET_NAME
if [ -e "$TARGET_PATH" ]; then
  [ -d "$TARGET_PATH" ] || fail "target exists and is not a directory: $TARGET_PATH"
  [ -z "$(find "$TARGET_PATH" -mindepth 1 -maxdepth 1 -print -quit)" ] || fail "target directory must be empty: $TARGET_PATH"
  rmdir "$TARGET_PATH"
fi

STAGING=$(mktemp -d "$TARGET_PARENT/.${TARGET_NAME}.polder-install.XXXXXX")
TARGET_CREATED=0
INSTALL_COMPLETE=0
cleanup() {
  status=$?
  trap - EXIT
  if [ "$INSTALL_COMPLETE" -eq 0 ] && [ "$TARGET_CREATED" -eq 1 ]; then rm -rf "$TARGET_PATH"; fi
  if [ -d "$STAGING" ]; then rm -rf "$STAGING"; fi
  exit "$status"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM

ARCHIVE_URL=https://codeload.github.com/$REPOSITORY/tar.gz/$REF
ARCHIVE=$STAGING/source.tar.gz
EXTRACT_DIR=$STAGING/extracted
mkdir "$EXTRACT_DIR"
printf 'Downloading complete source archive (%s, %s)…\n' "$REPOSITORY" "$REF"
curl --fail --location --silent --show-error "$ARCHIVE_URL" --output "$ARCHIVE" || fail 'source archive download failed'

SOURCE_ROOT=$(python3 - "$ARCHIVE" "$EXTRACT_DIR" <<'PY'
import pathlib
import sys
import tarfile

archive, destination = map(pathlib.Path, sys.argv[1:])
with tarfile.open(archive, mode="r:gz") as bundle:
    members = bundle.getmembers()
    roots = set()
    for member in members:
        path = pathlib.PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise SystemExit("archive contains an unsafe path")
        roots.add(path.parts[0])
        if not (member.isdir() or member.isfile()):
            raise SystemExit("archive contains an unsupported link or special file")
    if len(roots) != 1:
        raise SystemExit("archive must contain one repository root directory")
    bundle.extractall(destination, filter="data")
print(roots.pop())
PY
) || fail 'source archive is invalid or unsafe'
mv "$EXTRACT_DIR/$SOURCE_ROOT" "$TARGET_PATH"
TARGET_CREATED=1

cat > "$TARGET_PATH/knowledge-base/01-project/brief.md" <<'EOF'
---
type: project
status: draft
tags:
  - project
  - brief
  - goals
---

# Research Project Brief

## Research question or topic

<!-- Replace this prompt with the question, topic, and scope for this workspace. -->

## Purpose and intended use

Describe who needs this research and what decisions or understanding it should support.

## Scope

- Include:
- Exclude:
- Relevant dates, populations, systems, or contexts:

## Research approach

Choose bounded continuous intelligence for ongoing discovery, or a systematic evidence review when a prespecified, reproducible search and screening process is needed. For systematic reviews, create and freeze the protocol before searching.

## Constraints and priorities

- Sources or evidence types to prioritize:
- Known limitations or risks:
- Completion criteria:

## Notes

Keep source-backed findings in the research knowledge base and follow the documented evidence and provenance standards.
EOF

printf 'Creating project environment…\n'
python3 -m venv "$TARGET_PATH/.venv"
EXTRAS=
[ "$WITH_DEV" -eq 0 ] || EXTRAS=dev
if [ "$WITH_LAYA" -eq 1 ]; then
  if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi --query-gpu=name --format=csv,noheader >/dev/null 2>&1; then
    TORCH_INDEX=https://download.pytorch.org/whl/cu130
    printf 'NVIDIA GPU detected; installing the CUDA 13.0 PyTorch wheel…\n'
  else
    TORCH_INDEX=https://download.pytorch.org/whl/cpu
    printf 'No usable NVIDIA GPU detected; installing the CPU PyTorch wheel…\n'
  fi
  "$TARGET_PATH/.venv/bin/python" -m pip install torch==2.14.0 --index-url "$TORCH_INDEX"
  EXTRAS=${EXTRAS:+$EXTRAS,}laya
fi
SPEC=$TARGET_PATH
[ -z "$EXTRAS" ] || SPEC=$TARGET_PATH["$EXTRAS"]
"$TARGET_PATH/.venv/bin/python" -m pip install -e "$SPEC"

mkdir -p "$TARGET_PATH/.research"
"$TARGET_PATH/.venv/bin/polder-research" state-build
"$TARGET_PATH/.venv/bin/polder-research" health-build

printf 'Initializing independent local Git history…\n'
git -C "$TARGET_PATH" init --quiet
git -C "$TARGET_PATH" branch -M main
git -C "$TARGET_PATH" add -A
git -C "$TARGET_PATH" -c user.name='Polder Research Workspace' -c user.email='workspace@localhost' -c commit.gpgsign=false commit -m 'Initialize local research workspace' >/dev/null
INSTALL_COMPLETE=1

printf '\nPolder Research workspace installed at %s\n' "$TARGET_PATH"
printf 'Dashboard: cd %s && .venv/bin/polder-research serve\n' "$TARGET_PATH"
printf 'Local Git repository initialized without an upstream remote.\n'
if [ "$WITH_LAYA" -eq 1 ]; then
  printf 'Laya is the default classifier; download model weights from the dashboard Configuration view.\n'
fi
printf 'The dashboard listens on 127.0.0.1 and prints its local URL.\n'
