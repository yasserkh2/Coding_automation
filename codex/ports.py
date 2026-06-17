"""Interfaces exposed by the Codex CLI adapter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class CodexSessionResult:
    """Result returned when Codex is run as a resumable thread."""

    response: str
    session_id: str | None = None
    raw_events: tuple[dict[str, Any], ...] = ()


class CodexSpeaker(Protocol):
    """Minimal interface the graph layer should depend on."""

    def speak(
        self,
        prompt: str,
        project_dir: str | Path | None = None,
        full_access: bool = False,
    ) -> str:
        """Send a prompt to Codex and return its final response."""


class CodexSessionSpeaker(CodexSpeaker, Protocol):
    """Codex speaker that can continue the same persisted Codex thread."""

    def speak_in_session(
        self,
        prompt: str,
        project_dir: str | Path | None = None,
        full_access: bool = False,
        session_id: str | None = None,
    ) -> CodexSessionResult:
        """Send a prompt to Codex and return the response plus session id."""
