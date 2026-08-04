import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from webui import cli as web_cli
from webui.cli import main


REPO_ROOT = Path(__file__).resolve().parents[1]


class PackageCliTests(unittest.TestCase):
    def test_cli_exposes_distribution_version(self) -> None:
        result = CliRunner().invoke(main, ["--version"])

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertRegex(result.output.strip(), r"^muku, version \d+\.\d+\.\d+$")

    def test_doctor_uses_bundled_yt_dlp_module_not_global_path(self) -> None:
        with mock.patch.object(web_cli.shutil, "which", return_value=None):
            report = web_cli._doctor_report()

        self.assertTrue(report["yt_dlp_found"])
        self.assertFalse(report["transcript_capture_ready"])
        self.assertFalse(report["knowledge_capture_ready"])

    def test_module_help_uses_utf8_when_parent_encoding_cannot_render_chinese(self) -> None:
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "cp1252"

        result = subprocess.run(
            [sys.executable, "-m", "webui.cli", "--help"],
            cwd=REPO_ROOT,
            env=environment,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
        self.assertIn("幕库 Muku".encode(), result.stdout)

    def test_doctor_next_steps_use_the_muku_command_name(self) -> None:
        report = web_cli._doctor_report()
        report["openrouter_key_configured"] = False

        steps = web_cli._doctor_next_steps(report)

        self.assertTrue(any("muku doctor --json" in step for step in steps))
        self.assertFalse(any("video-downloade" in step for step in steps))


class InstallerPolicyTests(unittest.TestCase):
    def test_installer_uses_python_tool_installers(self) -> None:
        script = (REPO_ROOT / "scripts" / "install-muku-cli").read_text(encoding="utf-8")

        self.assertIn("uv tool install", script)
        self.assertIn("pipx install", script)

    def test_installer_does_not_mutate_a_live_venv_or_homebrew_bin(self) -> None:
        script = (REPO_ROOT / "scripts" / "install-muku-cli").read_text(encoding="utf-8")

        self.assertNotIn("--force-reinstall", script)
        self.assertNotIn("/opt/homebrew/bin", script)

    def test_unified_installer_installs_cli_and_skill_from_local_or_remote_source(self) -> None:
        script = (REPO_ROOT / "scripts" / "install-muku").read_text(encoding="utf-8")

        self.assertIn("install-muku-cli", script)
        self.assertIn("install-muku-skill", script)
        self.assertIn("MUKU_REPO_BRANCH", script)
        self.assertIn("archive/refs/heads", script)

    def test_windows_installer_has_the_same_cli_and_skill_contract(self) -> None:
        script = (REPO_ROOT / "scripts" / "install-muku.ps1").read_text(encoding="utf-8")

        self.assertIn("pip install", script)
        self.assertIn("muku-video-to-md", script)
        self.assertIn("MUKU_REPO_BRANCH", script)


class QuickstartTests(unittest.TestCase):
    def _ready_report(self, *, ffmpeg_found: bool = True, yt_dlp_found: bool = True) -> dict[str, object]:
        return {
            "settings_path": "/tmp/muku-settings.json",
            "download_dir": "/tmp/muku-output",
            "ffmpeg_found": ffmpeg_found,
            "yt_dlp_found": yt_dlp_found,
            "transcript_capture_ready": ffmpeg_found and yt_dlp_found,
            "knowledge_capture_ready": ffmpeg_found and yt_dlp_found,
        }

    def _patch_quickstart_runtime(self):
        patches = [
            mock.patch.object(web_cli, "_port_is_available", return_value=True),
            mock.patch.object(web_cli.web_app, "initialize_web_jobs"),
            mock.patch.object(web_cli.web_app.app, "run"),
            mock.patch.object(web_cli.web_app, "masked_runtime_settings", return_value={
                "settings_path": "/tmp/muku-settings.json",
                "download_dir": "/tmp/muku-output",
            }),
            mock.patch.object(web_cli, "_doctor_report", return_value=self._ready_report()),
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_quickstart_reuses_saved_key_and_starts_loopback_server(self) -> None:
        self._patch_quickstart_runtime()
        current_settings = {
            "openrouter_api_key": "sk-existing-secret",
            "openrouter_base_url": "https://openrouter.ai/api/v1",
            "download_dir": "/tmp/muku-output",
        }
        with (
            mock.patch.object(web_cli.web_app, "current_runtime_settings", return_value=current_settings),
            mock.patch.object(web_cli.web_app, "load_settings", return_value={"download_dir": "/tmp/muku-output"}),
            mock.patch.object(web_cli.web_app, "persist_runtime_settings") as persist_settings,
        ):
            # Keep Click's command decorators and runner intact; only ensure a reused key never prompts.
            with mock.patch.object(
                web_cli.click,
                "prompt",
                side_effect=AssertionError("quickstart prompted for an existing key"),
            ):
                result = CliRunner().invoke(main, ["quickstart", "--no-browser", "--port", "5678"])

        self.assertEqual(result.exit_code, 0, result.output)
        payload = persist_settings.call_args.args[0]
        self.assertEqual(payload["openrouter_api_key"], "sk-existing-secret")
        self.assertEqual(payload["download_dir"], "/tmp/muku-output")
        self.assertNotIn("sk-existing-secret", result.output)
        web_cli.web_app.app.run.assert_called_once_with(host="127.0.0.1", port=5678, threaded=True)

    def test_quickstart_prompts_once_and_uses_muku_download_directory(self) -> None:
        self._patch_quickstart_runtime()
        with (
            mock.patch.object(web_cli.web_app, "current_runtime_settings", return_value={
                "openrouter_api_key": "",
                "openrouter_base_url": "",
                "download_dir": str(Path.home() / "Downloads"),
            }),
            mock.patch.object(web_cli.web_app, "load_settings", return_value={}),
            mock.patch.object(web_cli.web_app, "persist_runtime_settings") as persist_settings,
        ):
            result = CliRunner().invoke(
                main,
                ["quickstart", "--no-browser", "--port", "5678"],
                input="sk-prompted-secret\n",
            )

        self.assertEqual(result.exit_code, 0, result.output)
        payload = persist_settings.call_args.args[0]
        self.assertEqual(payload["openrouter_api_key"], "sk-prompted-secret")
        self.assertTrue(str(payload["download_dir"]).endswith("Downloads/Muku"))
        self.assertNotIn("sk-prompted-secret", result.output)

    def test_quickstart_saves_configuration_but_stops_when_ffmpeg_is_missing(self) -> None:
        self._patch_quickstart_runtime()
        web_cli._doctor_report.return_value = self._ready_report(ffmpeg_found=False)
        with (
            mock.patch.object(web_cli.web_app, "current_runtime_settings", return_value={
                "openrouter_api_key": "",
                "openrouter_base_url": "",
                "download_dir": "",
            }),
            mock.patch.object(web_cli.web_app, "persist_runtime_settings") as persist_settings,
            mock.patch.object(web_cli.sys, "platform", "darwin"),
        ):
            result = CliRunner().invoke(
                main,
                ["quickstart", "--api-key", "sk-missing-ffmpeg", "--no-browser"],
            )

        self.assertNotEqual(result.exit_code, 0)
        self.assertTrue(persist_settings.called)
        self.assertIn("brew install ffmpeg", result.output)
        web_cli.web_app.app.run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
