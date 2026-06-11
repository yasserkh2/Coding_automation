"""Shared loader for project-level YAML configuration."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from .paths import ROOT


DEFAULT_PROJECT_CONFIG: dict[str, Any] = {
    "project": {
        "root": ".",
        "projects_dir": "projects",
    },
    "graph": {
        "entrypoint": "project_router",
        "routes": {
            "new": "new_project",
            "enhance": "enhance_project",
        },
        "required_inputs": {
            "new": ["task_status", "business_requirement", "task_md"],
            "enhance": ["task_status", "task_md"],
        },
    },
    "codex": {
        "model_provider": "openrouter",
        "model": "openai/gpt-5-codex",
        "provider_name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "env_key": "OPENROUTER_API_KEY",
        "timeout_seconds": 1800,
    },
}


def load_project_config(path: Path | None = None) -> dict[str, Any]:
    """Load ``config.yml`` and merge it over built-in defaults."""

    config_path = path or ROOT / "config.yml"
    config = deepcopy(DEFAULT_PROJECT_CONFIG)
    if not config_path.exists():
        return config

    loaded = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"{config_path} must contain a YAML mapping.")

    return merge_dicts(config, loaded)


def merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Return ``base`` recursively updated with ``override`` values."""

    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def resolve_config_path(value: str, root: Path = ROOT) -> Path:
    """Resolve a config path relative to the provided root directory."""

    path = Path(value)
    return path if path.is_absolute() else root / path
