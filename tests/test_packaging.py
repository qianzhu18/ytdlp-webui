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


class InstallerPolicyTests(unittest.TestCase):
    def test_installer_uses_python_tool_installers(self) -> None:
        script = (REPO_ROOT / "scripts" / "install-muku-cli").read_text(encoding="utf-8")

        self.assertIn("uv tool install", script)
        self.assertIn("pipx install", script)

    def test_installer_does_not_mutate_a_live_venv_or_homebrew_bin(self) -> None:
        script = (REPO_ROOT / "scripts" / "install-muku-cli").read_text(encoding="utf-8")

        self.assertNotIn("--force-reinstall", script)
        self.assertNotIn("/opt/homebrew/bin", script)


if __name__ == "__main__":
    unittest.main()
