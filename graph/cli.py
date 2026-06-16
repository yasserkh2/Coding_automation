"""Command-line entry point for running the LangGraph coding workflow."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .workflow import run_coding_graph


def non_empty_task(value: str) -> str:
    """Return a stripped task string or fail argparse validation."""

    task = value.strip()
    if not task:
        raise argparse.ArgumentTypeError("task is required and cannot be empty.")
    return task


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for graph execution."""

    parser = argparse.ArgumentParser(description="Run the LangGraph coding workflow.")
    parser.add_argument(
        "--task",
        dest="task_md",
        required=True,
        type=non_empty_task,
        help="Required task markdown/instructions to send through the graph.",
    )
    parser.add_argument("--project-dir", default=".", help="Directory Codex should edit.")
    parser.add_argument("--full-access", action="store_true", help="Use danger-full-access mode.")
    parser.add_argument(
        "--task-status",
        choices=["new", "enhance"],
        default="enhance",
        help="Route as a new project or an enhancement.",
    )
    parser.add_argument(
        "--business-requirement",
        help="Business requirement text. Required when --task-status new.",
    )
    parser.add_argument(
        "--project-name",
        help="Folder name to create or verify when --task-status new.",
    )
    parser.add_argument(
        "--requested-skill",
        choices=["backend", "frontend", "system_designer"],
        help="Force the AI orchestrator to route to a specific skill node.",
    )
    parser.add_argument(
        "--react-to-agent-status",
        action="store_true",
        help="After a skill node runs, loop once back to agent_status before ending.",
    )
    parser.add_argument(
        "--skill-max-turns",
        type=int,
        help="Maximum Codex turns for the selected skill agent. Defaults to graph.skill_max_turns in config.yml.",
    )
    parser.add_argument(
        "--compact-conversation-tokens",
        type=int,
        help=(
            "Approximate skill chat token threshold before using compact conversation. "
            "Defaults to graph.compact_conversation_tokens in config.yml."
        ),
    )
    parser.add_argument("--config", type=Path, help="Path to an alternate config.yml file.")
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI args and require an explicit task input."""

    return build_parser().parse_args(argv)


def main() -> None:
    """Parse command-line arguments and run the graph once."""

    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    result = run_coding_graph(
        args.task_md,
        args.project_dir,
        args.full_access,
        args.task_status,
        args.business_requirement,
        args.project_name,
        args.requested_skill,
        args.react_to_agent_status,
        args.skill_max_turns,
        args.compact_conversation_tokens,
        config_path=args.config,
    )
    print(result.get("response", ""))


if __name__ == "__main__":
    main()
