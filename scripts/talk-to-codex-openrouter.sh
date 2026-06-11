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
  exit 1
fi

mkdir -p "$CODEX_HOME_DIR"
CODEX_BIN="$(cd "$ROOT_DIR" && python3 -c 'from codex import CodexBinaryResolver; print(CodexBinaryResolver().resolve())')"

cd "$ROOT_DIR"
CODEX_HOME="$CODEX_HOME_DIR" "$CODEX_BIN" \
  --sandbox danger-full-access \
  -c model_provider=openrouter \
  -c model='openai/gpt-5-codex' \
  -c model_providers.openrouter.name=OpenRouter \
  -c model_providers.openrouter.base_url='https://openrouter.ai/api/v1' \
  -c model_providers.openrouter.env_key=OPENROUTER_API_KEY \
  -c shell_environment_policy.inherit=all
