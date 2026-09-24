#!/bin/sh
set -eu

REPOSITORY_URL=${POLDER_RESEARCH_REPOSITORY_URL:-https://github.com/PolderLabs/polder-research-pipeline.git}
REF=main
TARGET=
WITH_DEV=0
WITH_LAYA=0

usage() {
  cat <<'EOF'
Install Polder Research Pipeline into a new project directory.

Usage:
  curl -fsSL https://raw.githubusercontent.com/PolderLabs/polder-research-pipeline/main/install.sh | sh -s -- --target ./my-research

Options:
  --target DIR   New directory for the complete pipeline and research workspace (required)
  --ref REF      Git branch, tag, or commit to install (default: main)
  --with-dev     Also install pytest and Ruff
  --with-laya    Also install the optional local Laya classifier (large ML dependencies)
  -h, --help     Show this help

The installer clones the agents, schemas, knowledge base, pipeline, and dashboard,
creates a project-local .venv, and installs the polder-research command there.
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
command -v git >/dev/null 2>&1 || fail 'Git is required; install Git and retry'
command -v python3 >/dev/null 2>&1 || fail 'Python 3.14 or newer is required; python3 was not found'

PYTHON_VERSION=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 14) else 1)' || fail "Python 3.14 or newer is required; found $PYTHON_VERSION"

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
rmdir "$STAGING"
cleanup() {
  if [ -d "$STAGING" ]; then
    rm -rf "$STAGING"
  fi
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM

printf 'Cloning Polder Research Pipeline (%s)…\n' "$REF"
git clone --depth 1 --branch "$REF" "$REPOSITORY_URL" "$STAGING"
mv "$STAGING" "$TARGET_PATH"

printf 'Creating project environment…\n'
python3 -m venv "$TARGET_PATH/.venv"
EXTRAS=
[ "$WITH_DEV" -eq 0 ] || EXTRAS=dev
[ "$WITH_LAYA" -eq 0 ] || EXTRAS=${EXTRAS:+$EXTRAS,}laya
SPEC=.
[ -z "$EXTRAS" ] || SPEC=.["$EXTRAS"]
"$TARGET_PATH/.venv/bin/python" -m pip install -e "$TARGET_PATH/$SPEC"

printf '\nPolder Research Pipeline installed at %s\n' "$TARGET_PATH"
printf 'Dashboard: cd %s && .venv/bin/polder-research serve\n' "$TARGET_PATH"
printf 'Optional local Laya model: install with --with-laya, then download it from the dashboard Configuration view.\n'
printf 'The dashboard listens on 127.0.0.1 and prints its local URL.\n'
