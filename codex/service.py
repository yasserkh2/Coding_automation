"""High-level Codex use cases."""

from __future__ import annotations

from pathlib import Path

from .runner import CodexCliRunner


class CodexService:
    """Application-facing service for speaking with Codex."""

    def __init__(self, runner: CodexCliRunner | None = None) -> None:
        self.runner = runner or CodexCliRunner()

    def run_codex_cli(
        self,
        prompt: str,
        project_dir: str | Path | None = None,
        sandbox: str = "workspace-write",
        full_env: bool = False,
    ) -> str:
        return self.runner.run(prompt, project_dir, sandbox, full_env)

    def speak(
        self,
        prompt: str,
        project_dir: str | Path | None = None,
        full_access: bool = False,
    ) -> str:
        sandbox = "danger-full-access" if full_access else "workspace-write"
        return self.run_codex_cli(prompt, project_dir, sandbox, full_access)


def run_codex_cli(
    prompt: str,
    project_dir: str | Path | None = None,
    sandbox: str = "workspace-write",
    full_env: bool = False,
) -> str:
    return CodexService().run_codex_cli(prompt, project_dir, sandbox, full_env)


def speak_with_codex(
    prompt: str,
    project_dir: str | Path | None = None,
    full_access: bool = False,
) -> str:
    return CodexService().speak(prompt, project_dir, full_access)
