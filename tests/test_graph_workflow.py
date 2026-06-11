from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

from graph import create_coding_graph, run_coding_graph


class FakeSpeaker:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | Path | None, bool]] = []

    def speak(
        self,
        prompt: str,
        project_dir: str | Path | None = None,
        full_access: bool = False,
    ) -> str:
        self.calls.append((prompt, project_dir, full_access))
        return f"handled: {prompt}"


class CodingGraphTests(unittest.TestCase):
    def test_graph_routes_new_project_task(self) -> None:
        speaker = FakeSpeaker()
        result = run_coding_graph(
            "# Task\nCreate a file",
            project_dir="projects/demo",
            full_access=True,
            task_status="new",
            business_requirement="Build the first version of the demo app.",
            speaker=speaker,
        )

        self.assertEqual(result["task_type"], "new_project")
        self.assertEqual(result["response"], f"handled: {speaker.calls[0][0]}")
        self.assertIn("first task for a new project", speaker.calls[0][0])
        self.assertIn("Business requirement:", speaker.calls[0][0])
        self.assertIn("Build the first version", speaker.calls[0][0])
        self.assertIn("task.md:", speaker.calls[0][0])
        self.assertIn("Create a file", speaker.calls[0][0])
        self.assertEqual(speaker.calls[0][1:], ("projects/demo", True))

    def test_graph_routes_existing_project_task_by_default(self) -> None:
        speaker = FakeSpeaker()
        result = run_coding_graph(
            "# Task\nAdd login",
            project_dir="projects/demo",
            speaker=speaker,
        )

        self.assertEqual(result["task_type"], "enhance_project")
        self.assertIn("enhancement to an existing project", speaker.calls[0][0])
        self.assertIn("task.md:", speaker.calls[0][0])
        self.assertIn("Add login", speaker.calls[0][0])
        self.assertEqual(speaker.calls[0][1:], ("projects/demo", False))

    def test_graph_requires_task_md(self) -> None:
        graph = create_coding_graph(FakeSpeaker())

        with self.assertRaises(ValueError):
            graph.invoke({"task_status": "enhance", "task_md": "   "})

    def test_new_project_requires_business_requirement(self) -> None:
        graph = create_coding_graph(FakeSpeaker())

        with self.assertRaises(ValueError):
            graph.invoke({"task_status": "new", "task_md": "# Task\nCreate app"})

    def test_graph_uses_route_names_from_config_yml(self) -> None:
        with self.subTest("custom route names"):
            speaker = FakeSpeaker()
            config_path = Path(self.create_temp_config())
            graph = create_coding_graph(speaker, config_path=config_path)
            node_names = set(graph.get_graph().nodes)

        self.assertIn("initialize_project", node_names)
        self.assertIn("improve_project", node_names)

    def create_temp_config(self) -> str:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        config_path = Path(temp_dir.name) / "config.yml"
        config_path.write_text(
            "\n".join(
                [
                    "graph:",
                    "  entrypoint: project_router",
                    "  routes:",
                    "    new: initialize_project",
                    "    enhance: improve_project",
                ]
            ),
            encoding="utf-8",
        )
        return str(config_path)


if __name__ == "__main__":
    unittest.main()
