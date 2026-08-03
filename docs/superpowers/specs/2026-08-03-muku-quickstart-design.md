# Muku Quickstart Design

## Goal

Add a human-first `muku quickstart` command that turns an installed Muku package into a ready local Web UI with the minimum required user input. Keep `muku setup` stable for scripts and existing users.

The intended first-run path is:

```bash
uv tool install muku
muku quickstart
```

Success means a beginner can enter one OpenRouter API key, receive actionable dependency guidance, get a sensible local output directory, pass Muku readiness checks, and arrive at the local Web UI without editing environment variables or configuration files.

## Non-goals

- Do not change the behavior or output contract of `muku setup`.
- Do not build a native macOS or Windows installer.
- Do not automatically run `sudo`, Homebrew, apt, winget, or other system package managers.
- Do not create OpenRouter accounts, API keys, or platform Cookies for the user.
- Do not make platform Cookies a prerequisite for the first local-audio or public-video workflow.
- Do not expose the Web UI on a public network interface.

## CLI Contract

Add the command:

```text
muku quickstart [--api-key KEY] [--download-dir DIR] [--port PORT] [--no-browser]
```

Options:

- `--api-key`: optional OpenRouter key for non-interactive or assisted setup. If absent and no saved key exists, prompt with hidden input.
- `--download-dir`: optional output directory. If absent, reuse the current non-empty saved directory; otherwise use `~/Downloads/Muku`.
- `--port`: local Web UI port, default `5657`.
- `--no-browser`: start the server without opening the system browser.

`quickstart` is intentionally human-facing. Existing `muku setup --json` remains the machine-facing configuration command.

## First-run Flow

1. Inspect the current masked runtime settings and dependency report.
2. Resolve the API key:
   - Use `--api-key` when supplied.
   - Reuse an already configured OpenRouter key without prompting.
   - Otherwise prompt once using hidden input.
3. Resolve the output directory:
   - Use `--download-dir` when supplied.
   - Otherwise reuse a non-empty saved directory.
   - Otherwise create and use `~/Downloads/Muku`.
4. Persist one shared key and base URL for transcription, cleanup, article, and knowledge stages by reusing the same settings payload as `muku setup`.
5. Run the complete doctor report after persistence.
6. If required dependencies and AI stages are ready, bind the Web UI to `127.0.0.1:<port>`.
7. Open `http://127.0.0.1:<port>` in the default browser unless `--no-browser` is set.
8. Print a concise success summary before the blocking Web server starts.

Re-running `muku quickstart` must reuse valid saved configuration and avoid asking for the key again. Supplying `--api-key` or `--download-dir` explicitly replaces the corresponding saved value.

## Dependency Handling

`yt-dlp` ships with the Python package and should normally be ready after installation. `ffmpeg` is a system dependency and needs platform-specific handling.

When ffmpeg is missing:

- Save valid Muku configuration first so the user does not lose completed work.
- Do not start the Web UI.
- Exit with a Click error that names the missing dependency and prints an exact command:
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - Windows: direct the user to the existing Windows guide and mention `winget install Gyan.FFmpeg` when winget is available as the documented path.
- Tell the user to rerun `muku quickstart` after installation.

When yt-dlp is unexpectedly missing, report that the Muku installation is incomplete and recommend reinstalling or upgrading the package. Do not attempt a nested package installation from the running command.

## Browser and Server Behavior

- Use Python's `webbrowser` module; no browser automation dependency is required.
- Schedule browser opening only after configuration, dependency, and port checks pass.
- Start the existing Flask application through the same server path as `muku serve`.
- Always use host `127.0.0.1`; `quickstart` does not expose a host option.
- If opening the browser fails, print the local URL and continue serving.
- If the selected port is unavailable, fail before launching the browser and suggest another `--port` value.
- `--no-browser` skips browser opening but still starts the server.

Because Flask's development server call blocks, the command should preflight the port, print the URL, schedule a short delayed browser-open callback on a daemon timer, and then call the existing blocking server path on the main thread. Do not move Flask itself to a background thread; keeping it on the main thread preserves normal shutdown and signal behavior.

## User Guidance

The terminal output should describe state, not implementation details:

- Configuration saved or existing configuration reused
- Download directory
- Dependency readiness
- Local Web UI URL
- Cookies are optional for the first run and can be added later for restricted platform content
- The next beginner action: try a local audio file or a public video URL

Update these public entry points:

- Chinese and English README quick-start sections
- `muku quickstart --help`
- `docs/cli.md`
- `skills/muku-video-to-md/SKILL.md`

The Python package and Skill must both recommend `muku quickstart` for a human's first local run, while automation examples continue to use `muku setup --json` and `muku doctor --json`.

## Internal Design

Keep responsibilities separated:

- A shared configuration helper builds and persists the one-key setup payload. Both `setup` and `quickstart` call it so model and provider defaults cannot drift.
- A quickstart dependency helper converts a doctor report plus detected operating system into a user-facing blocking error or a ready result.
- A browser helper schedules and opens the local URL and is independently mockable.
- A server helper delegates to the existing Flask run path.

Do not put OS detection, settings persistence, browser launch, and Flask startup into one untestable command body.

## Error and Secret Safety

- Never print, log, or include the full API key in exceptions.
- Empty `--api-key` values fail before settings are written.
- Invalid output paths surface the existing settings validation error.
- Configuration is saved before reporting a missing ffmpeg dependency.
- Browser launch errors do not terminate a successfully started server.
- Server bind errors must not be reported as successful setup.
- Cookies and authentication warnings remain non-blocking during quickstart.

## Tests

Use test-first development for each behavior:

- Fresh run prompts once, writes all four AI stages, and selects `~/Downloads/Muku`.
- Existing configured key is reused without prompting.
- Explicit key and download directory override saved values.
- Full secrets never appear in output.
- Missing ffmpeg saves configuration, prints the correct OS command, does not open a browser, and does not start Flask.
- Missing yt-dlp gives an installation repair message.
- Ready state opens the expected local URL and starts the existing app on `127.0.0.1` with the chosen port.
- `--no-browser` starts the app without calling `webbrowser.open`.
- Browser-open failure still starts the app and leaves the URL visible.
- Port conflict fails before browser launch.
- Existing `setup` tests remain unchanged and green.

Release verification includes the complete test suite, Python 3.10 compatibility, wheel/sdist build, twine check, isolated wheel smoke test, and a clean-directory `muku quickstart` run with browser and server calls safely stubbed.

## Delivery

- Ship as the next patch version after `0.2.2`.
- Create a feature branch and pull request.
- Wait for Ubuntu, macOS, Windows, and installed-wheel CI checks.
- Merge only after checks pass.
- Create a GitHub Release to trigger Trusted Publishing to PyPI.
- Verify the public PyPI package exposes `muku quickstart --help` and completes the non-interactive quickstart smoke path.
