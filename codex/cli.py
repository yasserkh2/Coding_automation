"""Command-line entry point for one-shot Codex CLI execution."""

from __future__ import annotations

import argparse

from .service import run_codex_cli


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Codex CLI through OpenRouter.")
    parser.add_argument("prompt", help="Task prompt to send to Codex.")
    parser.add_argument("--project-dir", default=".", help="Directory Codex should edit.")
    parser.add_argument(
        "--sandbox",
        default="workspace-write",
        choices=["read-only", "workspace-write", "danger-full-access"],
        help="Codex sandbox mode.",
    )
    parser.add_argument(
        "--full-env",
        action="store_true",
        help="Allow Codex CLI to inherit the full shell environment.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    print(run_codex_cli(args.prompt, args.project_dir, args.sandbox, args.full_env))


if __name__ == "__main__":
    main()
