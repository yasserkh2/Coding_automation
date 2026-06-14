"""Interactive terminal prompt entry for CodexService."""

from __future__ import annotations

import argparse

from .service import speak_with_codex


class TerminalPromptApp:
    """Collect a prompt from the terminal and send it to Codex."""

    def __init__(self, project_dir: str, full_access: bool, multi_line: bool) -> None:
        self.project_dir = project_dir
        self.full_access = full_access
        self.multi_line = multi_line

    def run(self) -> None:
        """Read a prompt from the terminal and print the Codex response."""

        prompt = self._read_prompt()
        if not prompt:
            print("No prompt entered.")
            return

        result = speak_with_codex(
            prompt,
            project_dir=self.project_dir,
            full_access=self.full_access,
        )
        print(result)

    def _read_prompt(self) -> str:
        if not self.multi_line:
            return input("Prompt> ").strip()

        print("Write your prompt. Finish with Ctrl+D on a new line.")
        print()

        try:
            first_line = input("> ")
        except EOFError:
            return ""

        lines = [first_line]
        while True:
            try:
                lines.append(input())
            except EOFError:
                break

        return "\n".join(lines).strip()


def build_parser() -> argparse.ArgumentParser:
    """Create the parser for the interactive terminal prompt app."""

    parser = argparse.ArgumentParser(description="Send a terminal prompt to Codex CLI.")
    parser.add_argument("--project-dir", default=".", help="Folder Codex should work in.")
    parser.add_argument("--full-access", action="store_true", help="Use danger-full-access mode.")
    parser.add_argument("--multi-line", action="store_true", help="Read prompt until Ctrl+D.")
    return parser


def main() -> None:
    """Parse command-line arguments and run the terminal prompt app."""

    args = build_parser().parse_args()
    TerminalPromptApp(args.project_dir, args.full_access, args.multi_line).run()


if __name__ == "__main__":
    main()
