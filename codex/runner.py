"""Low-level Codex CLI command runner."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .binary import CodexBinaryResolver
from .config import CodexConfig
from .environment import DotenvLoader


class CodexCliRunner:
    """Build and execute non-interactive Codex CLI commands."""

    def __init__(
        self,
        config: CodexConfig | None = None,
        dotenv_loader: DotenvLoader | None = None,
        binary_resolver: CodexBinaryResolver | None = None,
    ) -> None:
        self.config = config or CodexConfig()
        self.dotenv_loader = dotenv_loader or DotenvLoader(self.config.env_file)
        self.binary_resolver = binary_resolver or CodexBinaryResolver()

    def run(
        self,
        prompt: str,
        project_dir: str | Path | None = None,
        sandbox: str = "workspace-write",
        full_env: bool = False,
    ) -> str:
        self.dotenv_loader.load()
        self._require_api_key()
        self.config.codex_home.mkdir(exist_ok=True)

        resolved_project_dir = Path(project_dir or self.config.root).resolve()
        result = subprocess.run(
            self._build_command(prompt, resolved_project_dir, sandbox, full_env),
            cwd=str(resolved_project_dir),
            env=self._build_environment(),
            text=True,
            capture_output=True,
            timeout=self.config.timeout_seconds,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                "Codex CLI failed.\n"
                f"STDOUT:\n{result.stdout}\n\n"
                f"STDERR:\n{result.stderr}"
            )

        return result.stdout

    def _build_command(
        self,
        prompt: str,
        project_dir: Path,
        sandbox: str,
        full_env: bool,
    ) -> list[str]:
        command = [
            self.binary_resolver.resolve(),
            "exec",
            "--skip-git-repo-check",
            "--sandbox",
            sandbox,
            "--cd",
            str(project_dir),
            "-c",
            f"model_provider={self.config.model_provider}",
            "-c",
            f"model={self.config.model}",
            "-c",
            f"model_providers.{self.config.model_provider}.name={self.config.provider_name}",
            "-c",
            f"model_providers.{self.config.model_provider}.base_url={self.config.base_url}",
            "-c",
            f"model_providers.{self.config.model_provider}.env_key={self.config.env_key}",
        ]

        if full_env:
            command.extend(["-c", "shell_environment_policy.inherit=all"])

        command.append(prompt)
        return command

    def _build_environment(self) -> dict[str, str]:
        env = os.environ.copy()
        env["CODEX_HOME"] = str(self.config.codex_home)
        return env

    def _require_api_key(self) -> None:
        if not os.environ.get(self.config.env_key):
            raise RuntimeError(f"{self.config.env_key} is missing. Add it to {self.config.env_file}")
