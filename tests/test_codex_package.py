from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from codex.binary import CodexBinaryResolver
from codex.config import CodexConfig
from codex.project_config import load_project_config
from codex.runner import CodexCliRunner


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
        self.assertIn("model_providers.openrouter.base_url=https://openrouter.ai/api/v1", command)
        self.assertIn("shell_environment_policy.inherit=all", command)
        self.assertEqual(command[-1], "Reply with OK only.")


if __name__ == "__main__":
    unittest.main()
