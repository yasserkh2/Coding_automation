"""Environment loading helpers."""

from __future__ import annotations

import os
from pathlib import Path


class DotenvLoader:
    """Load simple KEY=VALUE pairs without taking a dependency on python-dotenv."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> None:
        """Load environment variables from the configured dotenv file."""

        if not self.path.exists():
            return

        for raw_line in self.path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if key and key not in os.environ:
                os.environ[key] = value
