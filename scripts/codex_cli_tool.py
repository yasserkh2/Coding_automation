#!/usr/bin/env python3
"""Compatibility entry point for the structured codex package."""

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from codex.binary import CodexBinaryResolver
from codex.cli import main
from codex.service import run_codex_cli, speak_with_codex


def resolve_codex_binary() -> str:
    """Return the Codex executable path selected by the package resolver."""

    return CodexBinaryResolver().resolve()


if __name__ == "__main__":
    main()
