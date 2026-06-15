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
        self.assertTrue((project_dir / "Current_Task.md").exists())
        self.assertTrue((project_dir / "Done_AI_Tasks.md").exists())
        self.assertFalse((project_dir / "task.md").exists())
        self.assertFalse((project_dir / "Ai_Task.md").exists())
        self.assertTrue((project_dir / "business requirements.md").exists())
        self.assertTrue((project_dir / ".git").exists())
        self.assertTrue((project_dir / ".venv").exists())
        self.assertTrue((project_dir / ".env").exists())
        self.assertTrue((project_dir / "config.yml").exists())
        self.assertTrue((project_dir / "requirements.txt").exists())
        self.assertTrue((project_dir / ".gitignore").exists())
        self.assertTrue((project_dir / "README.md").exists())
        self.assertEqual(
            (project_dir / "Current_Task.md").read_text(encoding="utf-8"),
            "# Current Task\n\n# Task\nCreate a file\n",
        )
        self.assertIn("## Graph Setup Summary", (project_dir / "Done_AI_Tasks.md").read_text(encoding="utf-8"))
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
        self.assertIn("If Current_Task.md only asks to initialize the environment", speaker.calls[0][0])
        self.assertIn("Use Current_Task.md as the active task handoff file", speaker.calls[0][0])
        self.assertIn("Before finishing, update Done_AI_Tasks.md in this same Codex session", speaker.calls[0][0])
        self.assertIn("Use requirements.txt for Python package dependencies", speaker.calls[0][0])
        self.assertIn("Business requirement:", speaker.calls[0][0])
        self.assertIn("Build the first version", speaker.calls[0][0])
        self.assertIn("Current_Task.md:", speaker.calls[0][0])
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
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        project_dir = Path(temp_dir.name) / "demo"
        project_dir.mkdir()
        (project_dir / "Ai_Task.md").write_text(
            "# AI Task\n\nImplemented the initial login screen.\n",
            encoding="utf-8",
        )

        result = run_coding_graph(
            "# Task\nAdd login",
            project_dir=project_dir,
            speaker=speaker,
        )

        self.assertEqual(result["task_type"], "enhance_project")
        self.assertEqual(
            result["project_setup"],
            [
                "enhance_project",
                "create_enhance_project_docs",
                "agent_status",
                "ai_orchestrator",
                "backend",
            ],
        )
        self.assertEqual(result["agent_route"], "ai_orchestrator")
        self.assertEqual(result["skill_route"], "backend")
        self.assertIn("Next route: ai_orchestrator", result["agent_status"])
        expected_done_ai_tasks = "# AI Task\n\nImplemented the initial login screen.\n"
        expected_current_task = "# Current Task\n\n# Task\nAdd login\n"
        self.assertEqual(
            (project_dir / "Done_AI_Tasks.md").read_text(encoding="utf-8"),
            expected_done_ai_tasks,
        )
        self.assertEqual(
            (project_dir / "Current_Task.md").read_text(encoding="utf-8"),
            expected_current_task,
        )
        self.assertEqual(result["task_md"], expected_current_task.strip())
        self.assertEqual(
            (project_dir / "Ai_Task.md").read_text(encoding="utf-8"),
            "# AI Task\n\nImplemented the initial login screen.\n",
        )
        self.assertEqual(result["response"], "Backend skill is ready to handle Current_Task.md.")
        self.assertEqual(len(speaker.calls), 1)
        self.assertIn("Prepare the enhancement handoff", speaker.calls[0][0])
        self.assertIn("Incoming task:\n# Task\nAdd login", speaker.calls[0][0])
        self.assertIn("Read Done_AI_Tasks.md", speaker.calls[0][0])
        self.assertIn("Write the current implementation request to Current_Task.md", speaker.calls[0][0])
        self.assertEqual(speaker.calls[0][1:], (str(project_dir), False))

    def test_ai_orchestrator_can_route_to_requested_frontend_skill(self) -> None:
        speaker = FakeSpeaker()
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        project_dir = Path(temp_dir.name) / "demo"
        project_dir.mkdir()

        result = run_coding_graph(
            "# Task\nAdd API health check",
            project_dir=project_dir,
            requested_skill="frontend",
            speaker=speaker,
        )

        self.assertEqual(result["skill_route"], "frontend")
        self.assertTrue((project_dir / "Done_AI_Tasks.md").exists())
        self.assertTrue((project_dir / "Current_Task.md").exists())
        self.assertFalse((project_dir / "Ai_Task.md").exists())
        self.assertEqual(
            result["project_setup"],
            [
                "enhance_project",
                "create_enhance_project_docs",
                "agent_status",
                "ai_orchestrator",
                "frontend",
            ],
        )
        self.assertEqual(result["response"], "Frontend skill is ready to handle Current_Task.md.")
        self.assertEqual(len(speaker.calls), 1)

    def test_skill_node_can_loop_once_back_to_agent_status(self) -> None:
        speaker = FakeSpeaker()
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        project_dir = Path(temp_dir.name) / "demo"
        project_dir.mkdir()

        result = run_coding_graph(
            "# Task\nAdd backend endpoint",
            project_dir=project_dir,
            requested_skill="backend",
            react_to_agent_status=True,
            speaker=speaker,
        )

        self.assertEqual(
            result["project_setup"],
            [
                "enhance_project",
                "create_enhance_project_docs",
                "agent_status",
                "ai_orchestrator",
                "backend",
                "agent_status",
                "ai_orchestrator",
                "backend",
            ],
        )
        self.assertEqual(result["skill_completion_route"], "end")
        self.assertTrue(result["skill_rechecked_agent_status"])
        self.assertEqual(result["response"], "Backend skill is ready to handle Current_Task.md.")
        self.assertEqual(len(speaker.calls), 1)

    def test_ai_orchestrator_defaults_unclear_tasks_to_system_designer(self) -> None:
        speaker = FakeSpeaker()
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        project_dir = Path(temp_dir.name) / "demo"
        project_dir.mkdir()

        result = run_coding_graph(
            "# Task\nThink through the next milestone",
            project_dir=project_dir,
            speaker=speaker,
        )

        self.assertEqual(result["skill_route"], "system_designer")
        self.assertEqual(result["response"], "System designer skill is ready to handle Current_Task.md.")
        self.assertEqual(len(speaker.calls), 1)

    def test_enhance_project_can_route_to_human_in_the_loop(self) -> None:
        speaker = FakeSpeaker()
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        project_dir = Path(temp_dir.name) / "demo"
        project_dir.mkdir()

        result = run_coding_graph(
            "# Task\nReview risky migration",
            project_dir=project_dir,
            needs_human_review=True,
            speaker=speaker,
        )

        self.assertEqual(result["agent_route"], "human_in_the_loop")
        self.assertEqual(
            result["project_setup"],
            [
                "enhance_project",
                "create_enhance_project_docs",
                "agent_status",
                "human_in_the_loop",
            ],
        )
        self.assertIn("Next route: human_in_the_loop", result["agent_status"])
        self.assertEqual(result["response"], "Human review is required before AI orchestration.")
        self.assertEqual(len(speaker.calls), 1)

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
        self.assertIn("create_enhance_project_docs", node_names)
        self.assertIn("agent_status", node_names)
        self.assertIn("ai_orchestrator", node_names)
        self.assertIn("human_in_the_loop", node_names)
        self.assertIn("backend", node_names)
        self.assertIn("frontend", node_names)
        self.assertIn("system_designer", node_names)

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
