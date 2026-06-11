#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

SANDBOX="workspace-write"
FULL_ENV_ARGS=()

if [[ "${1:-}" == "--full-access" ]]; then
  SANDBOX="danger-full-access"
  FULL_ENV_ARGS=(--full-env)
  shift
fi

if [[ $# -lt 2 ]]; then
  echo "Usage:"
  echo "  ./scripts/create-project-with-codex.sh PROJECT_NAME \"PROMPT\""
  echo "  ./scripts/create-project-with-codex.sh --full-access PROJECT_NAME \"PROMPT\""
  echo
  echo "Example:"
  echo "  ./scripts/create-project-with-codex.sh todo-app \"Create a Python Flask todo app with tests and a README.\""
  echo "  ./scripts/create-project-with-codex.sh --full-access fullstack-app \"Create and run a full-stack app with dependencies.\""
  exit 1
fi

PROJECT_NAME="$1"
shift
PROMPT="$*"

PROJECT_DIR="$ROOT_DIR/projects/$PROJECT_NAME"
mkdir -p "$PROJECT_DIR"

cd "$ROOT_DIR"
python3 -m codex.cli "$PROMPT" \
  --project-dir "$PROJECT_DIR" \
  --sandbox "$SANDBOX" \
  "${FULL_ENV_ARGS[@]}"

echo
echo "Project directory:"
echo "$PROJECT_DIR"
