"""Configuration objects for Codex CLI execution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .paths import ROOT
from .project_config import load_project_config, merge_dicts, resolve_config_path


@dataclass(frozen=True)
class CodexConfig:
    """Immutable settings needed to run Codex CLI."""

    root: Path = ROOT
    env_file: Path = ROOT / ".env"
    codex_home: Path = ROOT / ".codex-home"
    model_provider: str = "openrouter"
    model: str = "openai/gpt-5-codex"
    provider_name: str = "OpenRouter"
    base_url: str = "https://openrouter.ai/api/v1"
    env_key: str = "OPENROUTER_API_KEY"
    timeout_seconds: int = 1800
    reasoning_effort: str = "medium"

    @classmethod
    def from_project_config(cls, path: Path | None = None, node_name: str | None = None) -> "CodexConfig":
        """Build Codex settings from ``config.yml``."""

        project_config = load_project_config(path)
        project = project_config["project"]
        codex = project_config["codex"]
        node_configs = codex.get("nodes", {})
        if node_name and isinstance(node_configs, dict) and isinstance(node_configs.get(node_name), dict):
            codex = merge_dicts(codex, node_configs[node_name])
        config_root = path.parent if path else ROOT
        root = resolve_config_path(str(project["root"]), config_root)

        return cls(
            root=root,
            env_file=root / ".env",
            codex_home=root / ".codex-home",
            model_provider=str(codex["model_provider"]),
            model=str(codex["model"]),
            provider_name=str(codex["provider_name"]),
            base_url=str(codex["base_url"]),
            env_key=str(codex["env_key"]),
            timeout_seconds=int(codex["timeout_seconds"]),
            reasoning_effort=str(codex["reasoning_effort"]),
        )
