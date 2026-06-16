"""Low-level Codex CLI command runner."""

from __future__ import annotations

import logging
import os
import subprocess
import threading
from pathlib import Path

from .binary import CodexBinaryResolver
from .config import CodexConfig
from .environment import DotenvLoader


logger = logging.getLogger(__name__)


class CodexCliRunner:
    """Build and execute non-interactive Codex CLI commands."""

    def __init__(
        self,
        config: CodexConfig | None = None,
        dotenv_loader: DotenvLoader | None = None,
        binary_resolver: CodexBinaryResolver | None = None,
        node_name: str | None = None,
    ) -> None:
        self.config = config or CodexConfig.from_project_config()
        self.dotenv_loader = dotenv_loader or DotenvLoader(self.config.env_file)
        self.binary_resolver = binary_resolver or CodexBinaryResolver()
        self.node_name = node_name or "codex_cli"

    def run(
        self,
        prompt: str,
        project_dir: str | Path | None = None,
        sandbox: str = "workspace-write",
        full_env: bool = False,
    ) -> str:
        """Execute Codex CLI for a prompt and return captured stdout."""

        self.dotenv_loader.load()
        self._require_api_key()
        self.config.codex_home.mkdir(exist_ok=True)

        resolved_project_dir = Path(project_dir or self.config.root).resolve()
        logger.info(
            "codex_cli[%s]: starting project_dir=%s sandbox=%s timeout_seconds=%s reasoning_effort=%s",
            self.node_name,
            resolved_project_dir,
            sandbox,
            self.config.timeout_seconds,
            self.config.reasoning_effort,
        )
        logger.info("codex_cli[%s] >>> prompt sent to Codex:\n%s", self.node_name, prompt)
        result = self._run_process(
            self._build_command(prompt, resolved_project_dir, sandbox, full_env),
            resolved_project_dir,
        )
        logger.info("codex_cli[%s]: finished with returncode=%s", self.node_name, result.returncode)

        if result.returncode != 0:
            raise RuntimeError(
                "Codex CLI failed.\n"
                f"STDOUT:\n{result.stdout}\n\n"
                f"STDERR:\n{result.stderr}"
            )

        return result.stdout

    def _run_process(self, command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            env=self._build_environment(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
        )
        stdout_lines: list[str] = []
        stderr_lines: list[str] = []

        def stream(pipe, lines: list[str], stream_name: str) -> None:
            if pipe is None:
                return
            for line in iter(pipe.readline, ""):
                lines.append(line)
                logger.info("codex_cli[%s] %s: %s", self.node_name, stream_name, line.rstrip())
            pipe.close()

        stdout_thread = threading.Thread(
            target=stream,
            args=(process.stdout, stdout_lines, "stdout"),
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=stream,
            args=(process.stderr, stderr_lines, "stderr"),
            daemon=True,
        )
        stdout_thread.start()
        stderr_thread.start()

        try:
            returncode = process.wait(timeout=self.config.timeout_seconds)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout_thread.join(timeout=1)
            stderr_thread.join(timeout=1)
            raise

        stdout_thread.join()
        stderr_thread.join()
        return subprocess.CompletedProcess(
            command,
            returncode,
            stdout="".join(stdout_lines),
            stderr="".join(stderr_lines),
        )

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
            f"reasoning_effort={self.config.reasoning_effort}",
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
