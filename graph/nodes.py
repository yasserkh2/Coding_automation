"""Node implementations for the LangGraph coding workflow."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from venv import EnvBuilder

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


def project_name_from_state(state: CodingState) -> str:
    """Return the requested new-project folder name when it can be inferred."""

    project_name = state.get("project_name")
    if project_name and project_name.strip():
        return project_name.strip()

    project_dir = state.get("project_dir")
    if project_dir and str(project_dir).strip():
        return Path(project_dir).name

    return "the requested project"


def project_dir_from_state(state: CodingState) -> Path:
    """Return the concrete project directory for setup work."""

    project_dir = state.get("project_dir")
    if project_dir and str(project_dir).strip():
        return Path(project_dir)

    return Path("projects") / project_name_from_state(state)


def append_setup_step(state: CodingState, step: str) -> list[str]:
    """Return project setup history with a new completed step."""

    return [*(state.get("project_setup") or []), step]


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
    """Prepare state for first-task project initialization."""

    def __call__(self, state: CodingState) -> CodingState:
        project_dir = project_dir_from_state(state)
        return {
            "project_name": project_name_from_state(state),
            "project_dir": str(project_dir),
            "project_setup": append_setup_step(state, "new_project"),
        }


@dataclass(frozen=True)
class CreateProjectDirectoryNode:
    """Create the project directory when it does not exist."""

    def __call__(self, state: CodingState) -> CodingState:
        project_dir = project_dir_from_state(state)
        project_dir.mkdir(parents=True, exist_ok=True)
        return {
            "project_dir": str(project_dir),
            "project_setup": append_setup_step(state, "create_project_dir"),
        }


@dataclass(frozen=True)
class CreateProjectDocsNode:
    """Create the task and business requirement documents."""

    def __call__(self, state: CodingState) -> CodingState:
        project_dir = project_dir_from_state(state)
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "task.md").write_text(require_task_md(state) + "\n", encoding="utf-8")
        (project_dir / "business requirements.md").write_text(
            require_business_requirement(state) + "\n",
            encoding="utf-8",
        )
        return {"project_setup": append_setup_step(state, "create_project_docs")}


@dataclass(frozen=True)
class InitializeGitNode:
    """Initialize git in the project directory when needed."""

    def __call__(self, state: CodingState) -> CodingState:
        project_dir = project_dir_from_state(state)
        if not (project_dir / ".git").exists():
            subprocess.run(
                ["git", "init"],
                cwd=project_dir,
                text=True,
                capture_output=True,
                check=True,
            )
        return {"project_setup": append_setup_step(state, "initialize_git")}


@dataclass(frozen=True)
class InitializeVenvNode:
    """Create a Python virtual environment for the new project."""

    def __call__(self, state: CodingState) -> CodingState:
        project_dir = project_dir_from_state(state)
        venv_dir = project_dir / ".venv"
        if not venv_dir.exists():
            EnvBuilder(with_pip=True).create(venv_dir)
        return {"project_setup": append_setup_step(state, "initialize_venv")}


@dataclass(frozen=True)
class CreateEnvironmentFilesNode:
    """Create local environment and config defaults."""

    def __call__(self, state: CodingState) -> CodingState:
        project_dir = project_dir_from_state(state)
        write_text_if_missing(
            project_dir / ".env",
            "# Local secrets and machine-specific settings.\n",
        )
        write_text_if_missing(
            project_dir / "config.yml",
            "project:\n  name: " + project_name_from_state(state) + "\n",
        )
        write_text_if_missing(
            project_dir / "requirements.txt",
            "# Add Python package dependencies here.\n",
        )
        write_text_if_missing(
            project_dir / ".gitignore",
            "\n".join(
                [
                    ".env",
                    ".venv/",
                    "__pycache__/",
                    ".pytest_cache/",
                    "*.pyc",
                    "dist/",
                    "build/",
                    "*.egg-info/",
                    "*.log",
                    ".DS_Store",
                    "",
                ]
            ),
        )
        write_text_if_missing(
            project_dir / "README.md",
            "# " + project_name_from_state(state) + "\n\n## Setup\n\n## Run\n\n## Test\n",
        )
        return {"project_setup": append_setup_step(state, "create_environment_files")}


@dataclass(frozen=True)
class ImplementNewProjectNode:
    """Ask Codex to implement the first task after setup files exist."""

    speaker: CodexSpeaker

    def __call__(self, state: CodingState) -> CodingState:
        task_prompt = build_new_project_prompt(
            require_business_requirement(state),
            require_task_md(state),
            project_name_from_state(state),
            state.get("project_dir"),
            state.get("project_setup") or [],
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


def build_new_project_prompt(
    business_requirement: str,
    task_md: str,
    project_name: str = "the requested project",
    project_dir: str | Path | None = None,
    project_setup: list[str] | None = None,
) -> str:
    """Build the Codex prompt for first-task project initialization."""

    project_location = f"\nProject directory:\n{project_dir}\n" if project_dir else ""
    setup_summary = "\n".join(f"- {step}" for step in (project_setup or []))
    return (
        "This is the first task for a new project. "
        "The graph has already prepared the base project environment. "
        "Inspect it, complete any stack-specific setup that is still missing, "
        "then implement the request.\n\n"
        f"Project name:\n{project_name}\n"
        f"{project_location}\n"
        f"Completed setup steps:\n{setup_summary}\n\n"
        "Implementation requirements:\n"
        "- Keep task.md and business requirements.md aligned with the work.\n"
        "- Preserve .env as placeholders only; do not add real secrets.\n"
        "- Update config.yml with non-secret defaults needed by the app.\n"
        "- Use requirements.txt for Python package dependencies; leave it as a placeholder if no packages are needed.\n"
        "- Update README.md with concrete setup, run, and test commands.\n"
        "- Add focused tests when the stack supports tests.\n"
        "- Keep the setup practical and minimal.\n\n"
        f"Business requirement:\n{business_requirement}\n\n"
        f"task.md:\n{task_md}"
    )


def write_text_if_missing(path: Path, text: str) -> None:
    """Write a text file without overwriting user or previous generated content."""

    if not path.exists():
        path.write_text(text, encoding="utf-8")


def build_enhance_project_prompt(task_md: str) -> str:
    """Build the Codex prompt for enhancing an existing project."""

    return (
        "This is an enhancement to an existing project. "
        "Inspect the current project before changing code and preserve existing behavior.\n\n"
        f"task.md:\n{task_md}"
    )
