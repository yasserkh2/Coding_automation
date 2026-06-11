#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROMPT="${*:-Create a small Python CLI app here with tests and a README.}"

cd "$ROOT_DIR"
python3 -m codex.cli "$PROMPT" --project-dir "$ROOT_DIR"
