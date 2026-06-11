"""Codex CLI binary discovery."""

from __future__ import annotations

import os
import shutil
from pathlib import Path


class CodexBinaryResolver:
    """Resolve the Codex executable while avoiding known-bad candidates."""

    def __init__(self, env_var: str = "CODEX_BIN", home: Path | None = None) -> None:
        self.env_var = env_var
        self.home = home or Path.home()

    def resolve(self) -> str:
        configured = os.environ.get(self.env_var)
        if configured:
            return configured

        path_codex = shutil.which("codex")
        if path_codex and not path_codex.startswith("/snap/"):
            return path_codex

        bundled_codex = self._resolve_vscode_codex()
        if bundled_codex:
            return bundled_codex

        return path_codex or "codex"

    def _resolve_vscode_codex(self) -> str | None:
        candidates = sorted(
            self.home.glob(".vscode/extensions/openai.chatgpt-*/bin/linux-x86_64/codex"),
            reverse=True,
        )
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
        return None
