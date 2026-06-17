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
SkillRoute = Literal[
    "backend",
    "frontend",
    "system_designer",
    "data_analysis",
    "ml_data_preparation",
    "model_training",
    "model_evaluation",
]
SkillCompletionRoute = Literal["human_in_the_loop", "end"]


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
    graph_run_id: str
    graph_log_path: str
    project_setup: list[str]
    codex_chat: str
    full_access: bool
    task_type: TaskType
    requested_skill: SkillRoute
    skill_route: SkillRoute
    skill_prompt: str
    skill_agent_response: str
    skill_agent_transcript: str
    skill_agent_session_id: str
    skill_response: str
    codex_instruction: str
    codex_response: str
    skill_transcript: str
    skill_turns_completed: int
    skill_max_turns: int
    compact_conversation_tokens: int
    codex_session_id: str
    skill_session_ids: dict[str, str]
    codex_chat_path: str
    codex_executor_chat_path: str
    skill_agent_chat_path: str
    skill_human_question: str
    skill_completion_route: SkillCompletionRoute
    response: str
