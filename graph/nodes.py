"""Node implementations for the LangGraph coding workflow."""

from __future__ import annotations

from dataclasses import dataclass, field

from codex.ports import CodexSpeaker

from .state import CodingState, TaskStatus, TaskType


def require_task_md(state: CodingState) -> str:
    """Return normalized task markdown or raise a clear validation error."""

    task_md = state.get("task_md") or ""
    if not task_md.strip():
        raise ValueError("CodingState.task_md is required.")
    return task_md.strip()


def require_task_status(state: CodingState) -> TaskStatus:
    """Return a valid task status from graph state."""

    task_status = state.get("task_status")
    if task_status not in ("new", "enhance"):
        raise ValueError("CodingState.task_status must be 'new' or 'enhance'.")
    return task_status


def require_business_requirement(state: CodingState) -> str:
    """Return normalized business requirements for first-task work."""

    business_requirement = state.get("business_requirement")
    if not business_requirement or not business_requirement.strip():
        raise ValueError("CodingState.business_requirement is required for new tasks.")
    return business_requirement.strip()


DEFAULT_ROUTES: dict[TaskStatus, TaskType] = {
    "new": "new_project",
    "enhance": "enhance_project",
}
DEFAULT_REQUIRED_INPUTS: dict[TaskStatus, list[str]] = {
    "new": ["task_status", "business_requirement", "task_md"],
    "enhance": ["task_status", "task_md"],
}


def task_type_for_status(
    task_status: TaskStatus,
    routes: dict[TaskStatus, TaskType] | None = None,
) -> TaskType:
    """Map public task status input to internal graph node names."""

    return (routes or DEFAULT_ROUTES)[task_status]


@dataclass(frozen=True)
class ProjectRouterNode:
    """Validate router inputs and choose the next project-work node."""

    routes: dict[TaskStatus, TaskType] = field(default_factory=lambda: DEFAULT_ROUTES.copy())
    required_inputs: dict[TaskStatus, list[str]] = field(
        default_factory=lambda: {key: value.copy() for key, value in DEFAULT_REQUIRED_INPUTS.items()}
    )

    def __call__(self, state: CodingState) -> CodingState:
        task_status = require_task_status(state)
        self._validate_required_inputs(task_status, state)
        task_md = require_task_md(state)

        return {
            "task_md": task_md,
            "task_type": task_type_for_status(task_status, self.routes),
        }

    def _validate_required_inputs(self, task_status: TaskStatus, state: CodingState) -> None:
        """Validate inputs configured for the selected task status."""

        for field_name in self.required_inputs.get(task_status, []):
            if field_name == "task_status":
                require_task_status(state)
            elif field_name == "task_md":
                require_task_md(state)
            elif field_name == "business_requirement":
                require_business_requirement(state)
            elif not state.get(field_name):
                raise ValueError(f"CodingState.{field_name} is required.")


@dataclass(frozen=True)
class NewProjectNode:
    """Run the first implementation task for a new project."""

    speaker: CodexSpeaker

    def __call__(self, state: CodingState) -> CodingState:
        task_prompt = build_new_project_prompt(
            require_business_requirement(state),
            require_task_md(state),
        )
        response = self.speaker.speak(
            task_prompt,
            project_dir=state.get("project_dir"),
            full_access=state.get("full_access", False),
        )
        return {"response": response}


@dataclass(frozen=True)
class EnhanceProjectNode:
    """Run an enhancement task against an existing project."""

    speaker: CodexSpeaker

    def __call__(self, state: CodingState) -> CodingState:
        task_prompt = build_enhance_project_prompt(require_task_md(state))
        response = self.speaker.speak(
            task_prompt,
            project_dir=state.get("project_dir"),
            full_access=state.get("full_access", False),
        )
        return {"response": response}


def build_new_project_prompt(business_requirement: str, task_md: str) -> str:
    """Build the Codex prompt for first-task project initialization."""

    return (
        "This is the first task for a new project. "
        "Create the initial project structure before implementing the request.\n\n"
        f"Business requirement:\n{business_requirement}\n\n"
        f"task.md:\n{task_md}"
    )


def build_enhance_project_prompt(task_md: str) -> str:
    """Build the Codex prompt for enhancing an existing project."""

    return (
        "This is an enhancement to an existing project. "
        "Inspect the current project before changing code and preserve existing behavior.\n\n"
        f"task.md:\n{task_md}"
    )
