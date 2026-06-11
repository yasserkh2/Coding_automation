#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPT="${*:-Create a small Python CLI app here with tests and a README.}"

cd "$SCRIPT_DIR"
python3 -m codex.cli "$PROMPT" --project-dir "$SCRIPT_DIR"
