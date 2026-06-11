"""Interfaces exposed by the Codex CLI adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class CodexSpeaker(Protocol):
    """Minimal interface the graph layer should depend on."""

    def speak(
        self,
        prompt: str,
        project_dir: str | Path | None = None,
        full_access: bool = False,
    ) -> str:
        """Send a prompt to Codex and return its final response."""
