#!/usr/bin/env python3
"""Compatibility entry point for the structured codex package."""

from codex.binary import CodexBinaryResolver
from codex.cli import main
from codex.service import run_codex_cli, speak_with_codex


def resolve_codex_binary() -> str:
    return CodexBinaryResolver().resolve()


if __name__ == "__main__":
    main()
