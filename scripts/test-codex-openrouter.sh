#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CODEX_HOME_DIR="$ROOT_DIR/.codex-home"

if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  source "$ROOT_DIR/.env"
  set +a
fi

if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
  echo "OPENROUTER_API_KEY is not set."
  echo "Add it to: $ROOT_DIR/.env"
  echo "Example: OPENROUTER_API_KEY=\"sk-or-xxxxx\""
  exit 1
fi

cd "$ROOT_DIR"
python3 -m codex.cli "Reply with OK only." --sandbox read-only
