"""Typed state shared by the LangGraph coding workflow.

The graph starts with a router node. That router needs three business-level
inputs:

- ``task_status`` decides whether this is the first task or an enhancement.
- ``business_requirement`` captures the project goal for first-task work.
- ``task_md`` contains the concrete task instructions.
- ``project_name`` names the folder to create for first-task work.
"""

from __future__ import annotations

from typing import Literal, TypeAlias, TypedDict


TaskStatus = Literal["new", "enhance"]
TaskType: TypeAlias = str


class CodingState(TypedDict, total=False):
    """Mutable dictionary passed between graph nodes.

    LangGraph merges partial dictionaries returned by each node into this
    state. Fields are optional because each node owns only the keys it needs.
    """

    task_status: TaskStatus
    business_requirement: str | None
    task_md: str
    project_name: str | None
    project_dir: str | None
    project_setup: list[str]
    full_access: bool
    task_type: TaskType
    response: str
