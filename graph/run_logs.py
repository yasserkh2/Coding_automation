"""Structured JSONL logging for graph runs."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def build_graph_run_id() -> str:
    """Return a timestamp-based graph run id."""

    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")


def graph_log_path(project_dir: str | Path | None, run_id: str) -> Path | None:
    """Return the JSONL log path for a project run."""

    if not project_dir:
        return None
    return Path(project_dir) / "Logs" / f"graph_run_{run_id}.jsonl"


def write_graph_event(
    project_dir: str | Path | None,
    run_id: str | None,
    event: str,
    *,
    node: str | None = None,
    graph_log_path_value: str | Path | None = None,
    allow_create: bool = True,
    **fields: Any,
) -> Path | None:
    """Append one structured event to the graph run JSONL log."""

    if not project_dir or not run_id:
        return None

    path = Path(graph_log_path_value) if graph_log_path_value else graph_log_path(project_dir, run_id)
    if path is None:
        return None
    project_path = Path(project_dir)
    if not allow_create and not project_path.exists():
        return None

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "run_id": run_id,
        "event": event,
        "node": node,
        "project_dir": str(project_path),
        **fields,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=str, sort_keys=True) + "\n")
    return path
