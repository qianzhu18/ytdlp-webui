#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run_command(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        encoding="utf-8",
        errors="strict",
        capture_output=True,
        input=input_text,
        timeout=90,
        check=True,
    )


def main() -> int:
    executable = shutil.which("muku")
    if not executable:
        raise RuntimeError("The installed `muku` console entry point was not found on PATH.")

    with tempfile.TemporaryDirectory(prefix="muku-package-smoke-") as temp_dir:
        work_dir = Path(temp_dir)
        config_dir = work_dir / "config"
        output_dir = work_dir / "output"
        env = os.environ.copy()
        env["VIDEO_DOWNLOADE_CONFIG_DIR"] = str(config_dir)
        env["PYTHONPATH"] = ""
        env.pop("OPENROUTER_API_KEY", None)

        run_command([executable, "--version"], cwd=work_dir, env=env)
        run_command([executable, "--help"], cwd=work_dir, env=env)
        run_command([executable, "quickstart", "--help"], cwd=work_dir, env=env)

        if os.name != "nt":
            interactive_env = dict(env)
            interactive_env["VIDEO_DOWNLOADE_CONFIG_DIR"] = str(work_dir / "interactive-config")
            interactive_setup = run_command(
                [executable, "setup", "--download-dir", str(work_dir / "interactive-output")],
                cwd=work_dir,
                env=interactive_env,
                input_text="sk-interactive-package-smoke\n",
            )
            if "sk-interactive-package-smoke" in interactive_setup.stdout:
                raise AssertionError("Interactive setup echoed the complete API key.")
            if "muku doctor --json" not in interactive_setup.stdout:
                raise AssertionError("Interactive setup did not explain the next verification step.")

        setup = run_command(
            [
                executable,
                "setup",
                "--api-key",
                "sk-package-smoke-test",
                "--download-dir",
                str(output_dir),
                "--json",
            ],
            cwd=work_dir,
            env=env,
        )
        if "sk-package-smoke-test" in setup.stdout:
            raise AssertionError("Setup leaked the complete API key to stdout.")
        setup_payload = json.loads(setup.stdout)
        for field in (
            "openrouter_api_key_configured",
            "ai_cleanup_api_key_configured",
            "article_draft_api_key_configured",
            "knowledge_draft_api_key_configured",
        ):
            if setup_payload.get(field) is not True:
                raise AssertionError(f"Setup did not configure {field}.")

        doctor = run_command([executable, "doctor", "--json"], cwd=work_dir, env=env)
        doctor_payload = json.loads(doctor.stdout)
        if doctor_payload.get("yt_dlp_found") is not True:
            raise AssertionError("The wheel cannot import its yt-dlp dependency.")
        for field in (
            "cleanup_prompt_exists",
            "article_prompt_exists",
            "knowledge_prompt_exists",
        ):
            if doctor_payload.get(field) is not True:
                raise AssertionError(f"The wheel is missing the resource checked by {field}.")

        web_smoke = (
            "from webui.app import app; "
            "response = app.test_client().get('/'); "
            "assert response.status_code == 200, response.status_code; "
            "assert '幕库 Muku' in response.get_data(as_text=True)"
        )
        run_command([sys.executable, "-c", web_smoke], cwd=work_dir, env=env)

    print("Installed-package smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
