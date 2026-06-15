"""Node implementations for the LangGraph coding workflow."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from venv import EnvBuilder

from codex.ports import CodexSpeaker

from .prompt_catalog import render_prompt
from .state import CodingState, TaskStatus, TaskType


logger = logging.getLogger(__name__)


class SkillClassifier(Protocol):
    """Classify a prepared task into one skill route."""

    def classify(
        self,
        task_md: str,
        project_dir: str | Path | None = None,
        full_access: bool = False,
    ) -> str | None:
        """Return backend, frontend, system_designer, or None."""


@dataclass(frozen=True)
class CodexSkillClassifier:
    """LLM-backed skill classifier used by the AI orchestrator route helper."""

    speaker: CodexSpeaker
    skill_routes: tuple[str, ...]

    def classify(
        self,
        task_md: str,
        project_dir: str | Path | None = None,
        full_access: bool = False,
    ) -> str | None:
        response = self.speaker.speak(
            build_skill_classifier_prompt(task_md, self.skill_routes),
            project_dir=project_dir,
            full_access=full_access,
        )
        return parse_skill_classifier_response(response, self.skill_routes)


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


def append_codex_chat(state: CodingState, skill_message: str, codex_response: str) -> str:
    """Return role-style Codex chat history with a skill/codex turn appended."""

    existing = (state.get("codex_chat") or "").strip()
    turn = f"skill:\n{skill_message.strip()}\n\ncodex:\n{codex_response.strip()}"
    return "\n\n".join(part for part in (existing, turn) if part)


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
        logger.info("project_router: running")
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
        logger.info("new_project: running")
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
        logger.info("create_project_dir: running")
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
        logger.info("create_project_docs: running")
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
        logger.info("initialize_git: running")
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
        logger.info("initialize_venv: running")
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
        logger.info("create_environment_files: running")
        project_dir = project_dir_from_state(state)
        logger.info("create_environment_files: ensuring environment files in %s", project_dir)
        write_text_if_missing(
            project_dir / ".env",
            "# Local secrets and machine-specific settings.\n",
        )
        write_text_if_missing(
            project_dir / ".env.example",
            "# Copy this file to .env and fill local values.\n",
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
        logger.info("implement_new_project: running")
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
        logger.info("enhance_project: running")
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
        logger.info("create_enhance_project_docs: running")
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
        logger.info("agent_status: running")
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

    classifier: SkillClassifier | None = None

    def __call__(self, state: CodingState) -> CodingState:
        logger.info("ai_orchestrator: running")
        skill_route = skill_route_from_state(state, self.classifier)
        logger.info("ai_orchestrator: selected skill route %s", skill_route)
        return {
            "project_setup": append_setup_step(state, "ai_orchestrator"),
            "skill_route": skill_route,
            "response": render_prompt("responses.ai_orchestrator_routed", skill_route=skill_route),
        }


@dataclass(frozen=True)
class BackendSkillNode:
    """Run the backend skill agent."""

    speaker: CodexSpeaker

    def __call__(self, state: CodingState) -> CodingState:
        logger.info("backend: running")
        logger.info("backend: speaking with Codex")
        skill_prompt = build_backend_skill_prompt(state.get("task_md", ""), state.get("codex_chat", ""))
        conversation = run_skill_conversation("backend", skill_prompt, state, self.speaker)
        return {
            **conversation,
            **skill_completion_state(state, conversation),
            "project_setup": append_setup_step(state, "backend"),
            "response": render_prompt("responses.backend_ready"),
        }


@dataclass(frozen=True)
class FrontendSkillNode:
    """Run the frontend skill agent."""

    speaker: CodexSpeaker

    def __call__(self, state: CodingState) -> CodingState:
        logger.info("frontend: running")
        logger.info("frontend: speaking with Codex")
        skill_prompt = build_frontend_skill_prompt(state.get("task_md", ""), state.get("codex_chat", ""))
        conversation = run_skill_conversation("frontend", skill_prompt, state, self.speaker)
        return {
            **conversation,
            **skill_completion_state(state, conversation),
            "project_setup": append_setup_step(state, "frontend"),
            "response": render_prompt("responses.frontend_ready"),
        }


@dataclass(frozen=True)
class SystemDesignerSkillNode:
    """Run the system designer skill agent."""

    speaker: CodexSpeaker

    def __call__(self, state: CodingState) -> CodingState:
        logger.info("system_designer: running")
        logger.info("system_designer: speaking with Codex")
        skill_prompt = build_system_designer_skill_prompt(state.get("task_md", ""), state.get("codex_chat", ""))
        conversation = run_skill_conversation("system_designer", skill_prompt, state, self.speaker)
        return {
            **conversation,
            **skill_completion_state(state, conversation),
            "project_setup": append_setup_step(state, "system_designer"),
            "response": render_prompt("responses.system_designer_ready"),
        }


@dataclass(frozen=True)
class HumanInTheLoopNode:
    """Placeholder node for pausing enhancement work for human review."""

    def __call__(self, state: CodingState) -> CodingState:
        logger.info("human_in_the_loop: running")
        logger.info("human_in_the_loop: pausing for human review")
        human_question = state.get("skill_human_question", "").strip()
        response = (
            render_prompt("responses.human_review_question", question=human_question)
            if human_question
            else render_prompt("responses.human_review_required")
        )
        return {
            "project_setup": append_setup_step(state, "human_in_the_loop"),
            "response": response,
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
        logger.info("finalize_new_project: running")
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


def build_backend_skill_prompt(task_md: str, codex_chat: str = "") -> str:
    """Build the backend skill agent prompt."""

    return render_prompt(
        "skills.backend_prompt",
        task_md=task_md.strip(),
        codex_chat=codex_chat.strip() or "No previous skill/codex chat history.",
        completion_audit=render_prompt("skills.completion_audit"),
    )


def build_frontend_skill_prompt(task_md: str, codex_chat: str = "") -> str:
    """Build the frontend skill agent prompt."""

    return render_prompt(
        "skills.frontend_prompt",
        task_md=task_md.strip(),
        codex_chat=codex_chat.strip() or "No previous skill/codex chat history.",
        completion_audit=render_prompt("skills.completion_audit"),
    )


def build_system_designer_skill_prompt(task_md: str, codex_chat: str = "") -> str:
    """Build the system designer skill agent prompt."""

    return render_prompt(
        "skills.system_designer_prompt",
        task_md=task_md.strip(),
        codex_chat=codex_chat.strip() or "No previous skill/codex chat history.",
        completion_audit=render_prompt("skills.completion_audit"),
    )


def build_skill_followup_prompt(skill_route: str, transcript: str) -> str:
    """Build a follow-up prompt for a multi-turn skill conversation."""

    return render_prompt(
        "skills.followup_prompt",
        skill_route=skill_route,
        transcript=transcript.strip(),
        completion_audit=render_prompt("skills.completion_audit"),
    )


def build_skill_audit_prompt(skill_route: str) -> str:
    """Build a focused final audit prompt before accepting skill completion."""

    return render_prompt(
        "skills.audit_prompt",
        skill_route=skill_route,
    )


def run_skill_conversation(
    skill_route: str,
    skill_prompt: str,
    state: CodingState,
    speaker: CodexSpeaker,
) -> CodingState:
    """Run a bounded multi-turn skill conversation through Codex."""

    max_turns = max(1, int(state.get("skill_max_turns", 3)))
    project_dir = state.get("project_dir")
    full_access = state.get("full_access", False)
    turns: list[tuple[str, str]] = []
    prompt = skill_prompt

    for turn_index in range(max_turns):
        logger.info("%s: Codex conversation turn %s/%s", skill_route, turn_index + 1, max_turns)
        response = speaker.speak(prompt, project_dir=project_dir, full_access=full_access)
        turns.append((prompt, response))
        if skill_response_is_done(response):
            if skill_response_has_completion_audit(response):
                break
            if turn_index + 1 >= max_turns:
                logger.info("%s: done response did not confirm completion audit", skill_route)
                break
            prompt = build_skill_audit_prompt(skill_route)
            continue
        if skill_response_needs_human_review(response):
            break
        if not skill_response_should_continue(response):
            break
        prompt = build_skill_followup_prompt(skill_route, render_skill_followup_context(turns))

    codex_chat = state.get("codex_chat") or ""
    for skill_message, codex_response in turns:
        codex_chat = append_codex_chat({"codex_chat": codex_chat}, skill_message, codex_response)
    codex_chat_path = save_codex_chat_history(project_dir, skill_route, codex_chat)

    return {
        "codex_chat": codex_chat,
        "codex_chat_path": str(codex_chat_path) if codex_chat_path else "",
        "skill_prompt": skill_prompt,
        "skill_response": turns[-1][1] if turns else "",
        "skill_transcript": render_skill_transcript(turns),
        "skill_turns_completed": len(turns),
    }


def save_codex_chat_history(project_dir: str | Path | None, skill_route: str, codex_chat: str) -> Path | None:
    """Persist the skill/Codex chat transcript in the project for review."""

    if not project_dir:
        return None
    history_dir = Path(project_dir) / "Chats_History"
    history_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    safe_skill_route = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in skill_route)
    path = history_dir / f"{safe_skill_route}_{timestamp}.md"
    path.write_text("# Codex Chat History\n\n" + codex_chat.strip() + "\n", encoding="utf-8")
    logger.info("skill_conversation: saved Codex chat history to %s", path)
    return path


def render_skill_transcript(turns: list[tuple[str, str]]) -> str:
    """Render skill conversation turns into a prompt-friendly transcript."""

    sections: list[str] = []
    for prompt, response in turns:
        sections.append(f"skill:\n{prompt.strip()}\n\ncodex:\n{response.strip()}")
    return "\n\n".join(sections)


def render_skill_followup_context(turns: list[tuple[str, str]], max_turns: int = 2) -> str:
    """Render compact prior Codex responses for low-cost follow-up prompts."""

    recent_turns = turns[-max_turns:]
    sections: list[str] = []
    first_turn_number = len(turns) - len(recent_turns) + 1
    for offset, (_, response) in enumerate(recent_turns):
        sections.append(f"Turn {first_turn_number + offset} Codex response:\n{response.strip()}")
    return "\n\n".join(sections)


def skill_response_is_done(response: str) -> bool:
    """Return whether a skill response says the skill work is complete."""

    return "skill_status: done" in response.lower()


def skill_response_has_completion_audit(response: str) -> bool:
    """Return whether a done response confirms the required file audit."""

    normalized = response.lower().replace("-", "_").replace(" ", "_")
    required_markers = (
        "readme",
        "done_ai_tasks",
        "current_task",
        ".env.example",
        ".env",
        "config",
    )
    return all(marker in normalized for marker in required_markers)


def skill_response_needs_human_review(response: str) -> bool:
    """Return whether a skill response asks to pause for human input."""

    return "skill_status: human_review" in response.lower()


def skill_response_should_continue(response: str) -> bool:
    """Return whether a skill response asks for another Codex turn."""

    return "skill_status: continue" in response.lower()


def extract_skill_human_question(response: str) -> str:
    """Extract the human-review question from a skill response."""

    for line in response.splitlines():
        if line.lower().startswith("question:"):
            return line.split(":", 1)[1].strip()
    return "The selected skill agent needs human input before continuing."


def agent_route_from_state(state: CodingState) -> str:
    """Return the next route after the agent status check."""

    return "ai_orchestrator"


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


def skill_route_from_state(state: CodingState, classifier: SkillClassifier | None = None) -> str:
    """Choose a skill route from explicit input, LLM classifier, or local inference."""

    requested_skill = state.get("requested_skill")
    if requested_skill in ("backend", "frontend", "system_designer"):
        return requested_skill

    task_md = new_task_description_from_task_md(state.get("task_md", "")).lower()
    requested_agent = explicit_skill_route_from_task(task_md)
    if requested_agent:
        return requested_agent

    if not classifier:
        logger.info("ai_orchestrator: no classifier available, defaulting to system_designer")
        return "system_designer"

    classified_route = classifier.classify(
        state.get("task_md", ""),
        project_dir=state.get("project_dir"),
        full_access=state.get("full_access", False),
    )
    if classified_route:
        return classified_route
    logger.info("ai_orchestrator: classifier returned invalid route, defaulting to system_designer")
    return "system_designer"


def build_skill_classifier_prompt(task_md: str, skill_routes: tuple[str, ...]) -> str:
    """Build the LLM prompt for skill-route classification."""

    route_labels = ", ".join(skill_routes)
    allowed_routes = "\n".join(f"- {route}" for route in skill_routes)
    return render_prompt(
        "ai_orchestrator.skill_classifier_prompt",
        allowed_routes=allowed_routes,
        route_labels=route_labels,
        task_md=task_md.strip(),
    )


def parse_skill_classifier_response(response: str, skill_routes: tuple[str, ...]) -> str | None:
    """Parse the skill classifier response into a supported route."""

    first_line = response.strip().splitlines()[0] if response.strip() else ""
    normalized = first_line.strip(" .:`").lower().replace("-", "_").replace(" ", "_")
    for route in skill_routes:
        if normalized == route:
            return route
    return None


def explicit_skill_route_from_task(task_md: str) -> str | None:
    """Return a named skill route when the task explicitly asks for an agent."""

    explicit_routes = (
        ("backend", ("backend agent", "backend skill", "use backend", "route to backend")),
        ("frontend", ("frontend agent", "frontend skill", "use frontend", "route to frontend")),
        (
            "system_designer",
            (
                "system designer agent",
                "system designer skill",
                "system_designer agent",
                "system_designer skill",
                "use system designer",
                "route to system designer",
                "route to system_designer",
            ),
        ),
    )
    for route, phrases in explicit_routes:
        if any(phrase in task_md for phrase in phrases):
            return route
    return None


def skill_completion_route_from_state(state: CodingState, conversation: CodingState | None = None) -> str:
    """Return whether a skill node should end or return to agent status."""

    skill_response = (conversation or {}).get("skill_response", "")
    if skill_response_needs_human_review(skill_response):
        return "human_in_the_loop"
    if state.get("react_to_agent_status", False) and not state.get("skill_rechecked_agent_status", False):
        return "agent_status"
    return "end"


def skill_completion_state(state: CodingState, conversation: CodingState | None = None) -> CodingState:
    """Build state returned by skill nodes for post-skill routing."""

    completion_route = skill_completion_route_from_state(state, conversation)
    logger.info("skill_completion: selected route %s", completion_route)
    completion_state: CodingState = {
        "skill_completion_route": completion_route,
        "skill_rechecked_agent_status": state.get("skill_rechecked_agent_status", False)
        or completion_route == "agent_status",
    }
    skill_response = (conversation or {}).get("skill_response", "")
    if completion_route == "human_in_the_loop":
        completion_state["skill_human_question"] = extract_skill_human_question(skill_response)
    return completion_state


def new_task_description_from_task_md(task_md: str) -> str:
    """Return only the new task section from a prepared enhancement document."""

    marker = "## New Task Description"
    if marker not in task_md:
        return task_md
    return task_md.split(marker, 1)[1]


def build_enhance_project_prompt(task_md: str) -> str:
    """Build the Codex prompt for enhancing an existing project."""

    return render_prompt("enhance_project.implementation_prompt", task_md=task_md)
