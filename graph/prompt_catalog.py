"""Centralized prompt template loading for graph nodes."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


PROMPTS_PATH = Path(__file__).with_name("prompts.json")


@lru_cache(maxsize=1)
def load_prompts() -> dict[str, Any]:
    """Load prompt templates from the package JSON catalog."""

    return json.loads(PROMPTS_PATH.read_text(encoding="utf-8"))


def prompt_template(key: str) -> str:
    """Return a prompt template by dotted key."""

    current: Any = load_prompts()
    for part in key.split("."):
        current = current[part]
    if not isinstance(current, str):
        raise TypeError(f"Prompt key {key!r} does not resolve to a string.")
    return current


def render_prompt(key: str, **values: object) -> str:
    """Render a prompt template by dotted key."""

    return prompt_template(key).format(**values)
