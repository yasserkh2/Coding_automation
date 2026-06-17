from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from codex.binary import CodexBinaryResolver
from codex.config import CodexConfig
from codex.ports import CodexSessionResult
from codex.project_config import load_project_config
from codex.runner import CodexCliRunner, extract_last_agent_message, extract_thread_id, parse_codex_jsonl
from codex.service import CodexService


class CodexBinaryResolverTests(unittest.TestCase):
    def test_prefers_configured_binary(self) -> None:
        with patch.dict(os.environ, {"CODEX_BIN": "/custom/codex"}):
            self.assertEqual(CodexBinaryResolver().resolve(), "/custom/codex")

    def test_avoids_snap_when_vscode_binary_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir)
            bundled = home / ".vscode/extensions/openai.chatgpt-test/bin/linux-x86_64/codex"
            bundled.parent.mkdir(parents=True)
            bundled.touch()

            with patch.dict(os.environ, {}, clear=True), patch("shutil.which", return_value="/snap/bin/codex"):
                self.assertEqual(CodexBinaryResolver(home=home).resolve(), str(bundled))


class CodexCliRunnerTests(unittest.TestCase):
    def test_loads_project_config_defaults_from_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"
            config_path.write_text(
                "\n".join(
                    [
                        "codex:",
                        "  model: custom/model",
                        "  timeout_seconds: 99",
                    ]
                ),
                encoding="utf-8",
            )

            config = load_project_config(config_path)

        self.assertEqual(config["codex"]["model"], "custom/model")
        self.assertEqual(config["codex"]["timeout_seconds"], 99)
        self.assertEqual(config["codex"]["model_provider"], "openrouter")

    def test_codex_config_reflects_project_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "config.yml"
            config_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  root: .",
                        "codex:",
                        "  model_provider: test-provider",
                        "  model: test/model",
                        "  provider_name: Test Provider",
                        "  base_url: https://example.test/api",
                        "  env_key: TEST_API_KEY",
                        "  timeout_seconds: 12",
                        "  reasoning_effort: high",
                    ]
                ),
                encoding="utf-8",
            )

            config = CodexConfig.from_project_config(config_path)

        self.assertEqual(config.root, root)
        self.assertEqual(config.model_provider, "test-provider")
        self.assertEqual(config.model, "test/model")
        self.assertEqual(config.provider_name, "Test Provider")
        self.assertEqual(config.base_url, "https://example.test/api")
        self.assertEqual(config.env_key, "TEST_API_KEY")
        self.assertEqual(config.timeout_seconds, 12)
        self.assertEqual(config.reasoning_effort, "high")

    def test_codex_config_can_use_node_specific_model_settings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "config.yml"
            config_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  root: .",
                        "codex:",
                        "  model_provider: global-provider",
                        "  model: global/model",
                        "  provider_name: Global Provider",
                        "  base_url: https://global.example/api",
                        "  env_key: GLOBAL_API_KEY",
                        "  timeout_seconds: 12",
                        "  reasoning_effort: medium",
                        "  nodes:",
                        "    backend:",
                        "      model: backend/model",
                        "      timeout_seconds: 34",
                        "      reasoning_effort: high",
                    ]
                ),
                encoding="utf-8",
            )

            backend_config = CodexConfig.from_project_config(config_path, "backend")
            frontend_config = CodexConfig.from_project_config(config_path, "frontend")

        self.assertEqual(backend_config.model, "backend/model")
        self.assertEqual(backend_config.timeout_seconds, 34)
        self.assertEqual(backend_config.model_provider, "global-provider")
        self.assertEqual(backend_config.base_url, "https://global.example/api")
        self.assertEqual(backend_config.reasoning_effort, "high")
        self.assertEqual(frontend_config.model, "global/model")
        self.assertEqual(frontend_config.timeout_seconds, 12)
        self.assertEqual(frontend_config.reasoning_effort, "medium")

    def test_builds_openrouter_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = CodexConfig(root=root, env_file=root / ".env", codex_home=root / ".codex-home")
            runner = CodexCliRunner(config=config, binary_resolver=CodexBinaryResolver())

            with patch.object(runner.binary_resolver, "resolve", return_value="/bin/codex"):
                command = runner._build_command(  # pylint: disable=protected-access
                    "Reply with OK only.",
                    root,
                    "danger-full-access",
                    True,
                )

        self.assertEqual(command[0], "/bin/codex")
        self.assertIn("model_provider=openrouter", command)
        self.assertIn("reasoning_effort=medium", command)
        self.assertIn("model_providers.openrouter.base_url=https://openrouter.ai/api/v1", command)
        self.assertIn("shell_environment_policy.inherit=all", command)
        self.assertEqual(command[-1], "Reply with OK only.")

    def test_builds_json_session_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = CodexConfig(root=root, env_file=root / ".env", codex_home=root / ".codex-home")
            runner = CodexCliRunner(config=config, binary_resolver=CodexBinaryResolver())

            with patch.object(runner.binary_resolver, "resolve", return_value="/bin/codex"):
                command = runner._build_command(  # pylint: disable=protected-access
                    "Start a skill session.",
                    root,
                    "workspace-write",
                    False,
                    json_output=True,
                )

        self.assertIn("--json", command)
        self.assertLess(command.index("--json"), len(command) - 1)
        self.assertEqual(command[-1], "Start a skill session.")

    def test_builds_resume_session_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = CodexConfig(root=root, env_file=root / ".env", codex_home=root / ".codex-home")
            runner = CodexCliRunner(config=config, binary_resolver=CodexBinaryResolver())

            with patch.object(runner.binary_resolver, "resolve", return_value="/bin/codex"):
                command = runner._build_resume_command(  # pylint: disable=protected-access
                    "Continue the same skill session.",
                    "session-123",
                    True,
                )

        self.assertEqual(command[:3], ["/bin/codex", "exec", "resume"])
        self.assertIn("--skip-git-repo-check", command)
        self.assertIn("shell_environment_policy.inherit=all", command)
        self.assertIn("--json", command)
        self.assertEqual(command[-2:], ["session-123", "Continue the same skill session."])

    def test_parses_codex_json_session_output(self) -> None:
        events = parse_codex_jsonl(
            "\n".join(
                [
                    "not json",
                    '{"type":"thread.started","thread_id":"session-123"}',
                    '{"type":"item.completed","item":{"type":"agent_message","text":"Done."}}',
                ]
            )
        )

        self.assertEqual(extract_thread_id(events), "session-123")
        self.assertEqual(extract_last_agent_message(events), "Done.")

    def test_codex_service_passes_node_name_to_runner(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "config.yml"
            config_path.write_text(
                "\n".join(
                    [
                        "project:",
                        "  root: .",
                    ]
                ),
                encoding="utf-8",
            )

            service = CodexService(config_path=config_path, node_name="backend")

        self.assertEqual(service.node_name, "backend")
        self.assertEqual(service.runner.node_name, "backend")

    def test_codex_service_can_speak_in_session(self) -> None:
        class FakeRunner:
            node_name = "backend"

            def run_in_session(self, prompt, project_dir, sandbox, full_env, session_id):
                return CodexSessionResult(
                    response=f"handled: {prompt}",
                    session_id=session_id or "new-session",
                )

        service = CodexService(runner=FakeRunner(), node_name="backend")

        result = service.speak_in_session(
            "Continue",
            project_dir=".",
            full_access=True,
            session_id="existing-session",
        )

        self.assertEqual(result.response, "handled: Continue")
        self.assertEqual(result.session_id, "existing-session")


if __name__ == "__main__":
    unittest.main()
