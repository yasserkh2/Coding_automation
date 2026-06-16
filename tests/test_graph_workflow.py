from __future__ import annotations

import unittest
import tempfile
import subprocess
from pathlib import Path

from graph import create_coding_graph, run_coding_graph
from graph.cli import parse_args


def is_skill_prompt(prompt: str) -> bool:
    return "skill agent for this project" in prompt or "skill ReAct agent for this project" in prompt


def is_compact_conversation_prompt(prompt: str) -> bool:
    return prompt.startswith("Compact conversation for this ")


def compact_conversation_response() -> str:
    return "\n".join(
        [
            "Current focus:",
            "- Need another backend pass.",
            "Important decisions and assumptions:",
            "- Continue the backend ReAct loop.",
            "Relevant files or areas:",
            "- Current_Task.md",
            "Actions already taken:",
            "- Initial skill turn completed.",
            "Verification and results:",
            "- Not verified yet.",
            "Open blockers or questions:",
            "- None.",
            "Remaining next actions:",
            "- Continue with the next focused action.",
            "Latest status:",
            "- SKILL_STATUS: continue",
        ]
    )


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
        if is_compact_conversation_prompt(prompt):
            return compact_conversation_response()
        if prompt.startswith("Classify the prepared task"):
            task = prompt.split("Prepared task:", 1)[-1].lower()
            if any(term in task for term in ("api", "backend", "endpoint", "login")):
                return "backend"
            if any(term in task for term in ("frontend", "ui", "screen", "component")):
                return "frontend"
            return "system_designer"
        if is_skill_prompt(prompt) or prompt.startswith("Continue the "):
            return "\n".join(
                [
                    "Skill work completed.",
                    "Audit checked: README.md, Done_AI_Tasks.md, Current_Task.md, config.yml, .env.example, .env.",
                    "",
                    "SKILL_STATUS: done",
                ]
            )
        if prompt.startswith("Before the ") and "skill can be marked done" in prompt:
            return "\n".join(
                [
                    "Completion audit finished.",
                    "Checked README.md, Done_AI_Tasks.md, Current_Task.md, config.yml, .env.example, and .env.",
                    "",
                    "SKILL_STATUS: done",
                ]
            )
        return f"handled: {prompt}"


class ContinuingSkillSpeaker(FakeSpeaker):
    def __init__(self) -> None:
        super().__init__()
        self.skill_calls = 0

    def speak(
        self,
        prompt: str,
        project_dir: str | Path | None = None,
        full_access: bool = False,
    ) -> str:
        self.calls.append((prompt, project_dir, full_access))
        if is_compact_conversation_prompt(prompt):
            return compact_conversation_response()
        if prompt.startswith("Classify the prepared task"):
            return "backend"
        if is_skill_prompt(prompt) or prompt.startswith("Continue the "):
            self.skill_calls += 1
            if self.skill_calls == 1:
                return "Need another backend pass.\n\nSKILL_STATUS: continue"
            return "Backend pass complete.\n\nSKILL_STATUS: done"
        if prompt.startswith("Before the backend skill can be marked done"):
            return "\n".join(
                [
                    "Completion audit finished.",
                    "Checked README.md, Done_AI_Tasks.md, Current_Task.md, config.yml, .env.example, and .env.",
                    "",
                    "SKILL_STATUS: done",
                ]
            )
        return f"handled: {prompt}"


class AlwaysContinuingSkillSpeaker(FakeSpeaker):
    def __init__(self) -> None:
        super().__init__()
        self.skill_calls = 0

    def speak(
        self,
        prompt: str,
        project_dir: str | Path | None = None,
        full_access: bool = False,
    ) -> str:
        self.calls.append((prompt, project_dir, full_access))
        if is_compact_conversation_prompt(prompt):
            return compact_conversation_response()
        if is_skill_prompt(prompt) or prompt.startswith("Continue the "):
            self.skill_calls += 1
            return f"Still working turn {self.skill_calls}.\n\nSKILL_STATUS: continue"
        return f"handled: {prompt}"


class HumanReviewSkillSpeaker(FakeSpeaker):
    def speak(
        self,
        prompt: str,
        project_dir: str | Path | None = None,
        full_access: bool = False,
    ) -> str:
        self.calls.append((prompt, project_dir, full_access))
        if is_compact_conversation_prompt(prompt):
            return compact_conversation_response()
        if is_skill_prompt(prompt) or prompt.startswith("Continue the "):
            return "\n".join(
                [
                    "I need the product owner to choose the auth policy before implementation.",
                    "",
                    "QUESTION: Should the chatbot API require call-center SSO from day one?",
                    "SKILL_STATUS: human_review",
                ]
            )
        return f"handled: {prompt}"


class CodingGraphTests(unittest.TestCase):
    def test_cli_requires_task_parameter(self) -> None:
        with self.assertRaises(SystemExit):
            parse_args(["--task-status", "enhance"])

    def test_cli_rejects_blank_task_parameter(self) -> None:
        with self.assertRaises(SystemExit):
            parse_args(["--task", "   ", "--task-status", "enhance"])

    def test_cli_accepts_task_parameter(self) -> None:
        args = parse_args(["--task", "# Task\nAdd login", "--task-status", "enhance"])

        self.assertEqual(args.task_md, "# Task\nAdd login")

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
        self.assertTrue((project_dir / ".env.example").exists())
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
        self.assertIn("Keep .env.example filled with required placeholder keys", speaker.calls[0][0])
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
        self.assertIn("You are the backend skill ReAct agent", result["skill_prompt"])
        self.assertIn("Codex chat history:\nNo previous skill/codex chat history.", result["skill_prompt"])
        self.assertIn("Current task:\n# Current Task\n\n# Task\nAdd login", result["skill_prompt"])
        self.assertIn("Before `SKILL_STATUS: done`", result["skill_prompt"])
        self.assertIn("README.md, Done_AI_Tasks.md, Current_Task.md", result["skill_prompt"])
        self.assertIn(".env.example", result["skill_prompt"])
        self.assertIn("Never add real secrets to .env", result["skill_prompt"])
        self.assertEqual(result["skill_turns_completed"], 2)
        self.assertIn("SKILL_STATUS: done", result["skill_response"])
        self.assertEqual(len(speaker.calls), 4)
        self.assertIn("Prepare a concise, task-specific handoff", speaker.calls[0][0])
        self.assertIn("Incoming task:\n# Task\nAdd login", speaker.calls[0][0])
        self.assertIn("Inspect only the project files needed", speaker.calls[0][0])
        self.assertIn("Write Current_Task.md with the exact implementation request", speaker.calls[0][0])
        self.assertIn("If anything is unclear", speaker.calls[0][0])
        self.assertEqual(speaker.calls[0][1:], (str(project_dir), False))
        self.assertIn("Classify the prepared task", speaker.calls[1][0])
        self.assertIn("Allowed routes:\n- backend\n- frontend\n- system_designer", speaker.calls[1][0])
        self.assertIn("one of: backend, frontend, system_designer", speaker.calls[1][0])
        self.assertEqual(speaker.calls[1][1:], (str(project_dir), False))
        self.assertIn("You are the backend skill ReAct agent", speaker.calls[2][0])
        self.assertIn("Project software context:", speaker.calls[2][0])
        self.assertIn("Project structure:", speaker.calls[2][0])
        self.assertIn("- Current_Task.md", speaker.calls[2][0])
        self.assertIn("Git status:", speaker.calls[2][0])
        self.assertIn("Git diff summary:", speaker.calls[2][0])
        self.assertIn("ReAct operating loop:", speaker.calls[2][0])
        self.assertIn("Continue as a ReAct agent", speaker.calls[3][0])
        self.assertIn("Compact conversation: not triggered.", speaker.calls[3][0])
        self.assertIn("Fresh project software context after the previous Codex run:", speaker.calls[3][0])
        self.assertIn("Project structure:", speaker.calls[3][0])
        self.assertIn("Git diff:", speaker.calls[3][0])

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
        self.assertIn("You are the frontend skill ReAct agent", result["skill_prompt"])
        self.assertIn("Codex chat history:\nNo previous skill/codex chat history.", result["skill_prompt"])
        self.assertIn("Current task:\n# Current Task", result["skill_prompt"])
        self.assertEqual(result["skill_turns_completed"], 2)
        self.assertEqual(len(speaker.calls), 3)
        self.assertIn("Continue as a ReAct agent", speaker.calls[2][0])
        self.assertIn("Compact conversation: not triggered.", speaker.calls[2][0])

    def test_ai_orchestrator_prefers_agent_named_in_task_over_classifier(self) -> None:
        speaker = FakeSpeaker()
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        project_dir = Path(temp_dir.name) / "demo"
        project_dir.mkdir()

        result = run_coding_graph(
            "# Task\nUse the frontend agent to review the API health check screen.",
            project_dir=project_dir,
            speaker=speaker,
        )

        self.assertEqual(result["skill_route"], "frontend")
        self.assertEqual(result["response"], "Frontend skill is ready to handle Current_Task.md.")
        self.assertEqual(len(speaker.calls), 3)
        self.assertIn("Continue as a ReAct agent", speaker.calls[2][0])
        self.assertIn("Compact conversation: not triggered.", speaker.calls[2][0])

    def test_ai_orchestrator_can_route_to_system_designer_named_in_task(self) -> None:
        speaker = FakeSpeaker()
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        project_dir = Path(temp_dir.name) / "demo"
        project_dir.mkdir()

        result = run_coding_graph(
            "# Task\nRoute to system designer for the next API architecture plan.",
            project_dir=project_dir,
            speaker=speaker,
        )

        self.assertEqual(result["skill_route"], "system_designer")
        self.assertEqual(result["response"], "System designer skill is ready to handle Current_Task.md.")
        self.assertEqual(len(speaker.calls), 3)
        self.assertIn("Continue as a ReAct agent", speaker.calls[2][0])
        self.assertIn("Compact conversation: not triggered.", speaker.calls[2][0])

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
        self.assertIn("You are the backend skill ReAct agent", result["skill_prompt"])
        self.assertEqual(result["skill_turns_completed"], 2)
        self.assertEqual(len(speaker.calls), 5)
        self.assertIn("Continue as a ReAct agent", speaker.calls[2][0])
        self.assertIn("Compact conversation: not triggered.", speaker.calls[2][0])
        self.assertIn("Continue as a ReAct agent", speaker.calls[4][0])
        self.assertIn("Compact conversation: not triggered.", speaker.calls[4][0])

    def test_skill_node_can_continue_codex_conversation(self) -> None:
        speaker = ContinuingSkillSpeaker()
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        project_dir = Path(temp_dir.name) / "demo"
        project_dir.mkdir()

        result = run_coding_graph(
            "# Task\nAdd backend endpoint",
            project_dir=project_dir,
            requested_skill="backend",
            skill_max_turns=3,
            speaker=speaker,
        )

        self.assertEqual(result["skill_route"], "backend")
        self.assertEqual(result["skill_turns_completed"], 3)
        self.assertIn("SKILL_STATUS: done", result["skill_response"])
        self.assertIn("Checked README.md", result["skill_response"])
        self.assertIn("skill:\nYou are the backend skill ReAct agent", result["skill_transcript"])
        self.assertIn("codex:\nNeed another backend pass.", result["skill_transcript"])
        self.assertIn("skill:\nContinue the backend skill ReAct-agent session", result["skill_transcript"])
        self.assertIn("codex:\nBackend pass complete.", result["skill_transcript"])
        self.assertIn("skill:\nBefore the backend skill can be marked done", result["skill_transcript"])
        self.assertIn("skill:\nYou are the backend skill ReAct agent", result["codex_chat"])
        self.assertIn("codex:\nCompletion audit finished.", result["codex_chat"])
        self.assertIn("Continue the backend skill ReAct-agent session", speaker.calls[2][0])
        self.assertIn("Conversation context:", speaker.calls[2][0])
        self.assertIn("Fresh project software context after the previous Codex run:", speaker.calls[2][0])
        self.assertIn("Project structure:", speaker.calls[2][0])
        self.assertIn("Git diff:", speaker.calls[2][0])
        self.assertIn("Compact conversation: not triggered.", speaker.calls[2][0])
        self.assertIn("Full skill chat history:", speaker.calls[2][0])
        self.assertIn("Need another backend pass.", speaker.calls[2][0])
        self.assertIn("Completion audit:", speaker.calls[2][0])
        self.assertIn("README.md, Done_AI_Tasks.md, Current_Task.md", speaker.calls[2][0])
        self.assertIn("Before the backend skill can be marked done", speaker.calls[3][0])
        self.assertIn("README.md", speaker.calls[3][0])
        self.assertIn(".env.example with required placeholder keys", speaker.calls[3][0])
        self.assertIn(".env placeholders only", speaker.calls[3][0])
        chat_history_dir = project_dir / "Chats_History"
        chat_history_files = list(chat_history_dir.glob("backend_*.md"))
        self.assertEqual(len(chat_history_files), 1)
        chat_history_path = chat_history_files[0]
        self.assertEqual(result["codex_chat_path"], str(chat_history_path))
        self.assertTrue(chat_history_path.exists())
        self.assertIn("codex:\nCompletion audit finished.", chat_history_path.read_text(encoding="utf-8"))

    def test_skill_followup_compacts_conversation_after_token_threshold(self) -> None:
        speaker = ContinuingSkillSpeaker()
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        project_dir = Path(temp_dir.name) / "demo"
        project_dir.mkdir()

        result = run_coding_graph(
            "# Task\nAdd backend endpoint",
            project_dir=project_dir,
            requested_skill="backend",
            skill_max_turns=3,
            compact_conversation_tokens=1,
            speaker=speaker,
        )

        self.assertEqual(result["skill_turns_completed"], 3)
        self.assertIn("Compact conversation for this backend", speaker.calls[2][0])
        self.assertIn("Transcript:", speaker.calls[2][0])
        self.assertIn("Need another backend pass.", speaker.calls[2][0])
        self.assertIn("Continue the backend skill ReAct-agent session", speaker.calls[3][0])
        self.assertIn("Compact conversation: triggered.", speaker.calls[3][0])
        self.assertIn("Current focus:", speaker.calls[3][0])
        self.assertIn("- Need another backend pass.", speaker.calls[3][0])

    def test_skill_max_turns_defaults_to_config_value(self) -> None:
        speaker = AlwaysContinuingSkillSpeaker()
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        project_dir = Path(temp_dir.name) / "demo"
        project_dir.mkdir()

        result = run_coding_graph(
            "# Task\nKeep refining backend",
            project_dir=project_dir,
            requested_skill="backend",
            speaker=speaker,
        )

        self.assertEqual(result["skill_turns_completed"], 3)
        self.assertEqual(speaker.skill_calls, 3)
        chat_history_files = list((project_dir / "Chats_History").glob("backend_*.md"))
        self.assertEqual(len(chat_history_files), 1)
        self.assertIn("Still working turn 3", chat_history_files[0].read_text(encoding="utf-8"))

    def test_skill_chat_history_creates_new_file_each_session(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        project_dir = Path(temp_dir.name) / "demo"
        project_dir.mkdir()

        run_coding_graph(
            "# Task\nAdd backend endpoint",
            project_dir=project_dir,
            requested_skill="backend",
            speaker=FakeSpeaker(),
        )
        run_coding_graph(
            "# Task\nAdd another backend endpoint",
            project_dir=project_dir,
            requested_skill="backend",
            speaker=FakeSpeaker(),
        )

        chat_history_files = list((project_dir / "Chats_History").glob("backend_*.md"))
        self.assertEqual(len(chat_history_files), 2)

    def test_saved_skill_chat_history_includes_uncapped_git_diff(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        project_dir = Path(temp_dir.name) / "demo"
        project_dir.mkdir()
        tracked_file = project_dir / "large.txt"
        tracked_file.write_text("initial\n", encoding="utf-8")
        subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True, text=True)
        subprocess.run(["git", "add", "large.txt"], cwd=project_dir, check=True, capture_output=True, text=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Test User",
                "-c",
                "user.email=test@example.com",
                "commit",
                "-m",
                "initial",
            ],
            cwd=project_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        large_diff_tail = "FULL_DIFF_TAIL_MARKER"
        tracked_file.write_text(
            "\n".join([f"changed line {index}" for index in range(1500)] + [large_diff_tail]),
            encoding="utf-8",
        )

        speaker = FakeSpeaker()
        result = run_coding_graph(
            "# Task\nAdd backend endpoint",
            project_dir=project_dir,
            requested_skill="backend",
            speaker=speaker,
        )

        self.assertIn("... truncated; inspect project files for full diff.", speaker.calls[1][0])
        self.assertNotIn(large_diff_tail, speaker.calls[1][0])
        chat_history_path = Path(result["codex_chat_path"])
        chat_history = chat_history_path.read_text(encoding="utf-8")
        self.assertIn("Full project software context saved for history:", chat_history)
        self.assertIn(large_diff_tail, chat_history)

    def test_skill_max_turns_can_be_configured(self) -> None:
        speaker = AlwaysContinuingSkillSpeaker()
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        project_dir = Path(temp_dir.name) / "demo"
        project_dir.mkdir()
        config_path = Path(temp_dir.name) / "config.yml"
        config_path.write_text("graph:\n  skill_max_turns: 2\n", encoding="utf-8")

        result = run_coding_graph(
            "# Task\nKeep refining backend",
            project_dir=project_dir,
            requested_skill="backend",
            speaker=speaker,
            config_path=config_path,
        )

        self.assertEqual(result["skill_turns_completed"], 2)
        self.assertEqual(speaker.skill_calls, 2)

    def test_skill_node_can_route_to_human_in_the_loop_with_question(self) -> None:
        speaker = HumanReviewSkillSpeaker()
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        project_dir = Path(temp_dir.name) / "demo"
        project_dir.mkdir()

        result = run_coding_graph(
            "# Task\nAdd backend authentication",
            project_dir=project_dir,
            requested_skill="backend",
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
                "human_in_the_loop",
            ],
        )
        self.assertEqual(result["skill_completion_route"], "human_in_the_loop")
        self.assertEqual(
            result["skill_human_question"],
            "Should the chatbot API require call-center SSO from day one?",
        )
        self.assertIn("Question: Should the chatbot API require call-center SSO", result["response"])
        self.assertEqual(result["skill_turns_completed"], 1)
        self.assertEqual(len(speaker.calls), 2)

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
        self.assertIn("You are the system designer skill ReAct agent", result["skill_prompt"])
        self.assertIn("Codex chat history:\nNo previous skill/codex chat history.", result["skill_prompt"])
        self.assertEqual(result["skill_turns_completed"], 2)
        self.assertEqual(len(speaker.calls), 4)
        self.assertIn("Classify the prepared task", speaker.calls[1][0])
        self.assertIn("Allowed routes:\n- backend\n- frontend\n- system_designer", speaker.calls[1][0])
        self.assertIn("Continue as a ReAct agent", speaker.calls[3][0])
        self.assertIn("Compact conversation: not triggered.", speaker.calls[3][0])

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
