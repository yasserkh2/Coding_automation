"""Node implementations for the LangGraph coding workflow."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from venv import EnvBuilder

from codex.ports import CodexSpeaker

from .prompt_catalog import render_prompt
from .state import CodingState, TaskStatus, TaskType


logger = logging.getLogger(__name__)


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
        logger.info("project_router: validating task inputs")
        task_status = require_task_status(state)
        self._validate_required_inputs(task_status, state)
        task_md = require_task_md(state)
        task_type = task_type_for_status(task_status, self.routes)
        logger.info("project_router: routed task_status=%s to %s", task_status, task_type)

        return {
            "task_md": task_md,
            "task_type": task_type,
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
        logger.info("new_project: preparing project_dir=%s", project_dir)
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
        logger.info("create_project_dir: ensuring project directory exists at %s", project_dir)
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
        logger.info("create_project_docs: writing initial markdown files in %s", project_dir)
        project_dir.mkdir(parents=True, exist_ok=True)
        current_task = build_current_task_document(require_task_md(state))
        (project_dir / "Current_Task.md").write_text(current_task, encoding="utf-8")
        (project_dir / "Done_AI_Tasks.md").write_text(
            render_prompt("new_project.done_ai_tasks_initial"),
            encoding="utf-8",
        )
        (project_dir / "business requirements.md").write_text(
            require_business_requirement(state) + "\n",
            encoding="utf-8",
        )
        return {
            "task_md": current_task.strip(),
            "project_setup": append_setup_step(state, "create_project_docs"),
        }


@dataclass(frozen=True)
class InitializeGitNode:
    """Initialize git in the project directory when needed."""

    def __call__(self, state: CodingState) -> CodingState:
        project_dir = project_dir_from_state(state)
        if not (project_dir / ".git").exists():
            logger.info("initialize_git: running git init in %s", project_dir)
            subprocess.run(
                ["git", "init"],
                cwd=project_dir,
                text=True,
                capture_output=True,
                check=True,
            )
        else:
            logger.info("initialize_git: existing git repository found in %s", project_dir)
        return {"project_setup": append_setup_step(state, "initialize_git")}


@dataclass(frozen=True)
class InitializeVenvNode:
    """Create a Python virtual environment for the new project."""

    def __call__(self, state: CodingState) -> CodingState:
        project_dir = project_dir_from_state(state)
        venv_dir = project_dir / ".venv"
        if not venv_dir.exists():
            logger.info("initialize_venv: creating virtual environment at %s", venv_dir)
            EnvBuilder(with_pip=True).create(venv_dir)
        else:
            logger.info("initialize_venv: existing virtual environment found at %s", venv_dir)
        return {"project_setup": append_setup_step(state, "initialize_venv")}


@dataclass(frozen=True)
class CreateEnvironmentFilesNode:
    """Create local environment and config defaults."""

    def __call__(self, state: CodingState) -> CodingState:
        project_dir = project_dir_from_state(state)
        logger.info("create_environment_files: ensuring environment files in %s", project_dir)
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
        logger.info("implement_new_project: sending prepared task to Codex")
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
        logger.info("implement_new_project: Codex response received")
        return {"response": response}


@dataclass(frozen=True)
class EnhanceProjectNode:
    """Prepare state for enhancing an existing project."""

    def __call__(self, state: CodingState) -> CodingState:
        project_dir = require_project_dir(state)
        logger.info("enhance_project: preparing existing project_dir=%s", project_dir)
        return {
            "project_name": project_name_from_state(state),
            "project_dir": str(project_dir),
            "project_setup": append_setup_step(state, "enhance_project"),
        }


@dataclass(frozen=True)
class CreateEnhanceProjectDocsNode:
    """Ask Codex to prepare the markdown handoff for an enhancement task."""

    speaker: CodexSpeaker

    def __call__(self, state: CodingState) -> CodingState:
        project_dir = require_project_dir(state)
        logger.info("create_enhance_project_docs: preparing enhancement docs in %s", project_dir)
        if not project_dir.exists():
            raise ValueError(f"Enhance project directory does not exist: {project_dir}")
        if not project_dir.is_dir():
            raise ValueError(f"Enhance project path is not a directory: {project_dir}")

        done_ai_tasks_path = project_dir / "Done_AI_Tasks.md"
        current_task_path = project_dir / "Current_Task.md"
        legacy_ai_task_path = project_dir / "Ai_Task.md"
        done_work_summary = read_done_work_summary(done_ai_tasks_path, legacy_ai_task_path)
        raw_task = require_task_md(state)

        write_text_if_missing(done_ai_tasks_path, done_work_summary.rstrip() + "\n")
        logger.info("create_enhance_project_docs: asking Codex to inspect project and write Current_Task.md")
        self.speaker.speak(
            build_enhance_project_docs_prompt(raw_task),
            project_dir=str(project_dir),
            full_access=state.get("full_access", False),
        )
        logger.info("create_enhance_project_docs: Codex doc preparation returned")
        current_task = (
            current_task_path.read_text(encoding="utf-8")
            if current_task_path.exists()
            else build_current_task_document(raw_task)
        )
        current_task_path.write_text(current_task, encoding="utf-8")
        return {
            "task_md": current_task.strip(),
            "project_setup": append_setup_step(state, "create_enhance_project_docs"),
        }


@dataclass(frozen=True)
class AgentStatusNode:
    """Record current workflow status and choose the next agent route."""

    def __call__(self, state: CodingState) -> CodingState:
        agent_route = agent_route_from_state(state)
        logger.info("agent_status: next route is %s", agent_route)
        return {
            "agent_status": build_agent_status(state, agent_route),
            "agent_route": agent_route,
            "project_setup": append_setup_step(state, "agent_status"),
        }


@dataclass(frozen=True)
class AiOrchestratorNode:
    """Choose the skill lane that should handle the prepared task."""

    def __call__(self, state: CodingState) -> CodingState:
        skill_route = skill_route_from_state(state)
        logger.info("ai_orchestrator: selected skill route %s", skill_route)
        return {
            "project_setup": append_setup_step(state, "ai_orchestrator"),
            "skill_route": skill_route,
            "response": render_prompt("responses.ai_orchestrator_routed", skill_route=skill_route),
        }


@dataclass(frozen=True)
class BackendSkillNode:
    """Placeholder node for backend implementation work."""

    def __call__(self, state: CodingState) -> CodingState:
        logger.info("backend: ready to handle Current_Task.md")
        return {
            "project_setup": append_setup_step(state, "backend"),
            "response": render_prompt("responses.backend_ready"),
        }


@dataclass(frozen=True)
class FrontendSkillNode:
    """Placeholder node for frontend implementation work."""

    def __call__(self, state: CodingState) -> CodingState:
        logger.info("frontend: ready to handle Current_Task.md")
        return {
            "project_setup": append_setup_step(state, "frontend"),
            "response": render_prompt("responses.frontend_ready"),
        }


@dataclass(frozen=True)
class SystemDesignerSkillNode:
    """Placeholder node for architecture and system design work."""

    def __call__(self, state: CodingState) -> CodingState:
        logger.info("system_designer: ready to handle Current_Task.md")
        return {
            "project_setup": append_setup_step(state, "system_designer"),
            "response": render_prompt("responses.system_designer_ready"),
        }


@dataclass(frozen=True)
class HumanInTheLoopNode:
    """Placeholder node for pausing enhancement work for human review."""

    def __call__(self, state: CodingState) -> CodingState:
        logger.info("human_in_the_loop: pausing for human review")
        return {
            "project_setup": append_setup_step(state, "human_in_the_loop"),
            "response": render_prompt("responses.human_review_required"),
        }


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
    return render_prompt(
        "new_project.implementation_prompt",
        project_name=project_name,
        project_location=project_location,
        setup_summary=setup_summary,
        business_requirement=business_requirement,
        task_md=task_md,
    )


@dataclass(frozen=True)
class FinalizeNewProjectNode:
    """Record the graph-level new-project setup summary in Done_AI_Tasks.md."""

    def __call__(self, state: CodingState) -> CodingState:
        project_dir = project_dir_from_state(state)
        logger.info("finalize_new_project: recording setup summary in %s", project_dir / "Done_AI_Tasks.md")
        done_ai_tasks_path = project_dir / "Done_AI_Tasks.md"
        existing = done_ai_tasks_path.read_text(encoding="utf-8") if done_ai_tasks_path.exists() else ""
        marker = "## Graph Setup Summary"
        if marker not in existing:
            setup_steps = "\n".join(
                f"- {step}" for step in [*(state.get("project_setup") or []), "finalize_new_project"]
            )
            summary = render_prompt("new_project.graph_setup_summary", setup_steps=setup_steps)
            done_ai_tasks_path.write_text(existing.rstrip() + summary, encoding="utf-8")

        return {"project_setup": append_setup_step(state, "finalize_new_project")}


def write_text_if_missing(path: Path, text: str) -> None:
    """Write a text file without overwriting user or previous generated content."""

    if not path.exists():
        path.write_text(text, encoding="utf-8")


def require_project_dir(state: CodingState) -> Path:
    """Return a normalized project directory or raise a validation error."""

    project_dir = state.get("project_dir")
    if not project_dir or not str(project_dir).strip():
        raise ValueError("CodingState.project_dir is required for enhance tasks.")
    return Path(project_dir)


def read_done_work_summary(done_ai_tasks_path: Path, legacy_ai_task_path: Path | None = None) -> str:
    """Return previous AI handoff content to summarize completed work."""

    for path in (done_ai_tasks_path, legacy_ai_task_path):
        if not path or not path.exists():
            continue
        existing = path.read_text(encoding="utf-8").strip()
        if existing:
            return existing
    return render_prompt("enhance_project.missing_done_work_summary")


def build_enhance_task_document(done_work_summary: str, task_description: str) -> str:
    """Build task.md content for an enhancement handoff."""

    return render_prompt(
        "enhance_project.task_document",
        done_work_summary=done_work_summary.strip(),
        task_description=task_description.strip(),
    )


def build_enhance_project_docs_prompt(task_description: str) -> str:
    """Build the Codex prompt for preparing enhancement handoff docs."""

    return render_prompt(
        "enhance_project.docs_prompt",
        task_description=task_description.strip(),
    )


def build_current_task_document(task_description: str) -> str:
    """Build Current_Task.md content for the active enhancement request."""

    return render_prompt(
        "enhance_project.current_task_document",
        task_description=task_description.strip(),
    )


def agent_route_from_state(state: CodingState) -> str:
    """Return the next route after the agent status check."""

    return "human_in_the_loop" if state.get("needs_human_review", False) else "ai_orchestrator"


def build_agent_status(state: CodingState, agent_route: str) -> str:
    """Build a short status report for the current graph position."""

    completed_steps = "\n".join(f"- {step}" for step in state.get("project_setup", []))
    return render_prompt(
        "agent_status.status_report",
        task_type=state.get("task_type", "unknown"),
        project_name=state.get("project_name", "unknown"),
        project_dir=state.get("project_dir", "unknown"),
        completed_steps=completed_steps or "- None",
        agent_route=agent_route,
    )


def skill_route_from_state(state: CodingState) -> str:
    """Choose a skill route from explicit input or task keywords."""

    requested_skill = state.get("requested_skill")
    if requested_skill in ("backend", "frontend", "system_designer"):
        return requested_skill

    task_md = new_task_description_from_task_md(state.get("task_md", "")).lower()
    backend_terms = ("api", "database", "backend", "server", "endpoint", "auth", "login", "model", "migration")
    frontend_terms = ("frontend", "ui", "css", "html", "component", "page", "screen", "button", "form")
    design_terms = ("architecture", "design", "system", "plan", "schema", "workflow")

    if any(term in task_md for term in backend_terms):
        return "backend"
    if any(term in task_md for term in frontend_terms):
        return "frontend"
    if any(term in task_md for term in design_terms):
        return "system_designer"
    return "system_designer"


def new_task_description_from_task_md(task_md: str) -> str:
    """Return only the new task section from a prepared enhancement document."""

    marker = "## New Task Description"
    if marker not in task_md:
        return task_md
    return task_md.split(marker, 1)[1]


def build_enhance_project_prompt(task_md: str) -> str:
    """Build the Codex prompt for enhancing an existing project."""

    return render_prompt("enhance_project.implementation_prompt", task_md=task_md)
