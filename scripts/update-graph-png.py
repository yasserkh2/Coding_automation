#!/usr/bin/env python3
"""Regenerate graph.png from the current LangGraph workflow."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from graph import create_coding_graph  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    """Create the parser for graph image regeneration."""

    parser = argparse.ArgumentParser(description="Regenerate the LangGraph workflow PNG.")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "graph.png",
        help="PNG path to write. Defaults to ./graph.png.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Optional config.yml path for custom graph route names.",
    )
    return parser


def main() -> None:
    """Regenerate the workflow PNG at the requested output path."""

    args = build_parser().parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output

    graph = create_coding_graph(config_path=args.config).get_graph()
    try:
        png = graph.draw_png()
    except ImportError:
        png = graph.draw_mermaid_png()

    output.write_bytes(png)
    print(f"Updated {output}")


if __name__ == "__main__":
    main()
