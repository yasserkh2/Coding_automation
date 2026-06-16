"""High-level Codex use cases."""

from __future__ import annotations

import logging
from pathlib import Path

from .config import CodexConfig
from .runner import CodexCliRunner


logger = logging.getLogger(__name__)


class CodexService:
    """Application-facing service for speaking with Codex."""

    def __init__(
        self,
        runner: CodexCliRunner | None = None,
        config_path: Path | None = None,
        node_name: str | None = None,
    ) -> None:
        self.node_name = node_name or "codex"
        config = CodexConfig.from_project_config(config_path, node_name) if runner is None else None
        self.runner = runner or CodexCliRunner(config=config, node_name=self.node_name)

    def run_codex_cli(
        self,
        prompt: str,
        project_dir: str | Path | None = None,
        sandbox: str = "workspace-write",
        full_env: bool = False,
    ) -> str:
        """Run Codex CLI through the configured runner."""

        logger.info(
            "codex_service[%s]: sending prompt to Codex project_dir=%s sandbox=%s full_env=%s prompt_chars=%s",
            self.node_name,
            project_dir,
            sandbox,
            full_env,
            len(prompt),
        )
        logger.info("codex_service[%s] >>> prompt:\n%s", self.node_name, prompt)
        response = self.runner.run(prompt, project_dir, sandbox, full_env)
        logger.info(
            "codex_service[%s]: received response from Codex response_chars=%s",
            self.node_name,
            len(response),
        )
        logger.info("codex_service[%s] <<< response:\n%s", self.node_name, response)
        return response

    def speak(
        self,
        prompt: str,
        project_dir: str | Path | None = None,
        full_access: bool = False,
    ) -> str:
        """Send a prompt to Codex with the selected access level."""

        sandbox = "danger-full-access" if full_access else "workspace-write"
        return self.run_codex_cli(prompt, project_dir, sandbox, full_access)


def run_codex_cli(
    prompt: str,
    project_dir: str | Path | None = None,
    sandbox: str = "workspace-write",
    full_env: bool = False,
) -> str:
    """Run Codex CLI once using the default service."""

    return CodexService().run_codex_cli(prompt, project_dir, sandbox, full_env)


def speak_with_codex(
    prompt: str,
    project_dir: str | Path | None = None,
    full_access: bool = False,
) -> str:
    """Send a prompt to Codex using the default service."""

    return CodexService().speak(prompt, project_dir, full_access)
