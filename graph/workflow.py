"""Factories and entry points for the LangGraph coding workflow."""

from __future__ import annotations

from pathlib import Path

from langgraph.graph import END, StateGraph

from codex.paths import ROOT
from codex.project_config import load_project_config, resolve_config_path
from codex.ports import CodexSpeaker
from codex.service import CodexService

from .nodes import (
    CreateEnvironmentFilesNode,
    CreateProjectDirectoryNode,
    CreateProjectDocsNode,
    EnhanceProjectNode,
    FinalizeNewProjectNode,
    ImplementNewProjectNode,
    InitializeGitNode,
    InitializeVenvNode,
    NewProjectNode,
    ProjectRouterNode,
)
from .state import CodingState, TaskStatus, TaskType


DEFAULT_PROJECT_ROUTER = "project_router"
DEFAULT_NEW_PROJECT = "new_project"
DEFAULT_CREATE_PROJECT_DIR = "create_project_dir"
DEFAULT_CREATE_PROJECT_DOCS = "create_project_docs"
DEFAULT_INITIALIZE_GIT = "initialize_git"
DEFAULT_INITIALIZE_VENV = "initialize_venv"
DEFAULT_CREATE_ENVIRONMENT_FILES = "create_environment_files"
DEFAULT_IMPLEMENT_NEW_PROJECT = "implement_new_project"
DEFAULT_FINALIZE_NEW_PROJECT = "finalize_new_project"
DEFAULT_ENHANCE_PROJECT = "enhance_project"


def route_project_task(state: CodingState) -> TaskType:
    """Return the route selected by ``ProjectRouterNode``."""

    return state.get("task_type", "enhance_project")


def create_coding_graph(speaker: CodexSpeaker | None = None, config_path: Path | None = None):
    """Compile the coding workflow.

    The workflow is intentionally small for now:

    ``project_router`` validates input and routes to either ``new_project`` or
    ``enhance_project``. The new-project route runs deterministic setup nodes
    before handing the first implementation task to Codex.
    """

    project_config = load_project_config(config_path)
    graph_config = project_config["graph"]
    routes = {
        "new": str(graph_config["routes"]["new"]),
        "enhance": str(graph_config["routes"]["enhance"]),
    }
    required_inputs = {
        "new": list(graph_config["required_inputs"]["new"]),
        "enhance": list(graph_config["required_inputs"]["enhance"]),
    }
    project_router = str(graph_config.get("entrypoint", DEFAULT_PROJECT_ROUTER))
    new_project = routes["new"]
    enhance_project = routes["enhance"]

    codex_speaker = speaker or CodexService()
    graph = StateGraph(CodingState)
    graph.add_node(project_router, ProjectRouterNode(routes, required_inputs))
    graph.add_node(new_project, NewProjectNode())
    graph.add_node(DEFAULT_CREATE_PROJECT_DIR, CreateProjectDirectoryNode())
    graph.add_node(DEFAULT_CREATE_PROJECT_DOCS, CreateProjectDocsNode())
    graph.add_node(DEFAULT_INITIALIZE_GIT, InitializeGitNode())
    graph.add_node(DEFAULT_INITIALIZE_VENV, InitializeVenvNode())
    graph.add_node(DEFAULT_CREATE_ENVIRONMENT_FILES, CreateEnvironmentFilesNode())
    graph.add_node(DEFAULT_IMPLEMENT_NEW_PROJECT, ImplementNewProjectNode(codex_speaker))
    graph.add_node(DEFAULT_FINALIZE_NEW_PROJECT, FinalizeNewProjectNode())
    graph.add_node(enhance_project, EnhanceProjectNode(codex_speaker))
    graph.set_entry_point(project_router)
    graph.add_conditional_edges(
        project_router,
        route_project_task,
        {
            new_project: new_project,
            enhance_project: enhance_project,
        },
    )
    graph.add_edge(new_project, DEFAULT_CREATE_PROJECT_DIR)
    graph.add_edge(DEFAULT_CREATE_PROJECT_DIR, DEFAULT_CREATE_PROJECT_DOCS)
    graph.add_edge(DEFAULT_CREATE_PROJECT_DOCS, DEFAULT_INITIALIZE_GIT)
    graph.add_edge(DEFAULT_INITIALIZE_GIT, DEFAULT_INITIALIZE_VENV)
    graph.add_edge(DEFAULT_INITIALIZE_VENV, DEFAULT_CREATE_ENVIRONMENT_FILES)
    graph.add_edge(DEFAULT_CREATE_ENVIRONMENT_FILES, DEFAULT_IMPLEMENT_NEW_PROJECT)
    graph.add_edge(DEFAULT_IMPLEMENT_NEW_PROJECT, DEFAULT_FINALIZE_NEW_PROJECT)
    graph.add_edge(DEFAULT_FINALIZE_NEW_PROJECT, END)
    graph.add_edge(enhance_project, END)
    return graph.compile()


def run_coding_graph(
    task_md: str,
    project_dir: str | Path | None = None,
    full_access: bool = False,
    task_status: TaskStatus = "enhance",
    business_requirement: str | None = None,
    project_name: str | None = None,
    speaker: CodexSpeaker | None = None,
    config_path: Path | None = None,
) -> CodingState:
    """Run one task through the coding workflow.

    Args:
        task_md: Markdown instructions for the current task.
        project_dir: Directory Codex should inspect or edit.
        full_access: Whether Codex may run with broader local access.
        task_status: ``"new"`` for first-task initialization, otherwise
            ``"enhance"`` for existing project work.
        business_requirement: Required when ``task_status`` is ``"new"``.
        project_name: Optional folder name for first-task project setup.
        speaker: Optional Codex speaker implementation, mostly for tests.
    """

    project_config = load_project_config(config_path)
    if project_dir is None:
        config_root = config_path.parent if config_path else ROOT
        project_dir = resolve_config_path(str(project_config["project"]["projects_dir"]), config_root)

    app = create_coding_graph(speaker, config_path)
    return app.invoke(
        {
            "task_status": task_status,
            "business_requirement": business_requirement,
            "task_md": task_md,
            "project_name": project_name,
            "project_dir": str(project_dir) if project_dir is not None else None,
            "full_access": full_access,
        }
    )
