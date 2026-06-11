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
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        project_dir = Path(temp_dir.name) / "demo"
        result = run_coding_graph(
            "# Task\nCreate a file",
            project_dir=project_dir,
            full_access=True,
            task_status="new",
            business_requirement="Build the first version of the demo app.",
            project_name="demo",
            speaker=speaker,
        )

        self.assertEqual(result["task_type"], "new_project")
        self.assertEqual(
            result["project_setup"],
            [
                "new_project",
                "create_project_dir",
                "create_project_docs",
                "initialize_git",
                "initialize_venv",
                "create_environment_files",
                "finalize_new_project",
            ],
        )
        self.assertTrue(project_dir.exists())
        self.assertTrue((project_dir / "task.md").exists())
        self.assertTrue((project_dir / "Ai_Task.md").exists())
        self.assertTrue((project_dir / "business requirements.md").exists())
        self.assertTrue((project_dir / ".git").exists())
        self.assertTrue((project_dir / ".venv").exists())
        self.assertTrue((project_dir / ".env").exists())
        self.assertTrue((project_dir / "config.yml").exists())
        self.assertTrue((project_dir / "requirements.txt").exists())
        self.assertTrue((project_dir / ".gitignore").exists())
        self.assertTrue((project_dir / "README.md").exists())
        self.assertIn("## Graph Setup Summary", (project_dir / "Ai_Task.md").read_text(encoding="utf-8"))
        self.assertIn("finalize_new_project", result["project_setup"])
        self.assertEqual(len(speaker.calls), 1)
        self.assertEqual(result["response"], f"handled: {speaker.calls[0][0]}")
        self.assertIn("first task for a new project", speaker.calls[0][0])
        self.assertIn("already prepared the base project environment", speaker.calls[0][0])
        self.assertIn("Project name:\ndemo", speaker.calls[0][0])
        self.assertIn(f"Project directory:\n{project_dir}", speaker.calls[0][0])
        self.assertIn("- create_project_dir", speaker.calls[0][0])
        self.assertIn("- create_project_docs", speaker.calls[0][0])
        self.assertIn("- initialize_git", speaker.calls[0][0])
        self.assertIn("- initialize_venv", speaker.calls[0][0])
        self.assertIn("- create_environment_files", speaker.calls[0][0])
        self.assertIn("Do not create extra directories", speaker.calls[0][0])
        self.assertIn("If task.md only asks to initialize the environment", speaker.calls[0][0])
        self.assertIn("Use Ai_Task.md as the AI handoff file", speaker.calls[0][0])
        self.assertIn("Before finishing, update Ai_Task.md in this same Codex session", speaker.calls[0][0])
        self.assertIn("Use requirements.txt for Python package dependencies", speaker.calls[0][0])
        self.assertIn("Business requirement:", speaker.calls[0][0])
        self.assertIn("Build the first version", speaker.calls[0][0])
        self.assertIn("task.md:", speaker.calls[0][0])
        self.assertIn("Create a file", speaker.calls[0][0])
        self.assertEqual(speaker.calls[0][1:], (str(project_dir), True))

    def test_graph_derives_new_project_name_from_project_dir(self) -> None:
        speaker = FakeSpeaker()
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        project_dir = Path(temp_dir.name) / "derived-demo"
        run_coding_graph(
            "# Task\nCreate a file",
            project_dir=project_dir,
            task_status="new",
            business_requirement="Build a derived-name app.",
            speaker=speaker,
        )

        self.assertIn("Project name:\nderived-demo", speaker.calls[0][0])

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
        self.assertIn("create_project_dir", node_names)
        self.assertIn("implement_new_project", node_names)
        self.assertIn("finalize_new_project", node_names)

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
