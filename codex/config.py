"""Configuration objects for Codex CLI execution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .paths import ROOT


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
