# Muku: 1,800+ video extractors, one URL to knowledge

[简体中文](README.md) | English

> **1,800+ video-site extractors.** Turn one URL into a Markdown knowledge base.

[![PyPI](https://img.shields.io/pypi/v/muku?label=PyPI&color=3775A9)](https://pypi.org/project/muku/)
[![Python](https://img.shields.io/pypi/pyversions/muku)](https://pypi.org/project/muku/)
[![CI](https://github.com/qianzhu18/Muku/actions/workflows/ci.yml/badge.svg)](https://github.com/qianzhu18/Muku/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/qianzhu18/Muku)](LICENSE)
[![yt-dlp](https://img.shields.io/badge/yt--dlp-1800%2B_extractors-FF0000)](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

Muku connects [yt-dlp's ecosystem of 1,800+ site extractors](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md) to a local-first Video-to-Markdown pipeline. Bilibili, YouTube, and Douyin are its primary paths, while complete URLs from other yt-dlp-compatible sites can enter the same pipeline. If Muku can obtain subtitles or audio, it can continue through transcription, cleanup, analysis, and knowledge-base generation.

| 1,800+ | 1 URL → 4 knowledge assets | 4 ways to use it |
| --- | --- | --- |
| yt-dlp extractor ecosystem | Transcript, cleaned copy, analysis, knowledge-base Markdown | CLI, Web UI, Docker, AI-agent Skill |

> [!IMPORTANT]
> `1,800+` describes yt-dlp's current extractor surface. It does not mean that Muku has manually verified every site or URL. Site changes, authentication, region, network conditions, and DRM can affect results. The only reliable test is your real URL in your environment.

## Highlights

- Accepts complete URLs through 1,800+ yt-dlp site extractors instead of hard-coding three platforms
- Produces Markdown designed for Obsidian, Git, full-text search, RAG, and agent workflows
- Prefers existing subtitles and uses audio transcription only when needed
- Detects model refusals and tries verified fallback transcription models
- Supports batching, concurrency, checkpoints, resume, JSON, path-only output, and NDJSON progress
- Stores artifacts and settings locally by default
- Tests source and installed wheels on Ubuntu, macOS, and Windows

## Quick start

Requirements:

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/)
- An [OpenRouter](https://openrouter.ai/) API key for transcription and AI processing

On macOS or Linux, install the CLI and AI-agent Skill with one command:

```bash
curl -fsSL https://raw.githubusercontent.com/qianzhu18/Muku/main/scripts/install-muku | bash
muku quickstart
```

On Windows PowerShell:

```powershell
irm https://raw.githubusercontent.com/qianzhu18/Muku/main/scripts/install-muku.ps1 | iex
muku quickstart
```

The installer does not create an API key or copy platform cookies. `muku quickstart` securely prompts for
your OpenRouter key, chooses a local output directory, and starts the local Web UI. If ffmpeg is missing,
it prints the platform-specific install command.

If you only need the CLI, install Muku as an isolated Python tool. No repository checkout or npm installation is required.

```bash
# Choose one
uv tool install muku
pipx install muku

muku --version
muku setup
muku doctor --json
```

If only Python and pip are available:

```bash
python3 -m venv .muku-venv
source .muku-venv/bin/activate
python -m pip install --upgrade pip muku
muku setup
```

Create your first knowledge assets:

```bash
muku capture "https://www.youtube.com/watch?v=..." --knowledge --json
muku audio "/path/to/audio.mp3" --knowledge --json
```

Typical outputs:

| Artifact | Purpose |
| --- | --- |
| `title - 原始逐字稿.txt` | Faithful raw transcript |
| `title - 逐字稿.md` | Cleaned readable transcript |
| `title - 解析稿.md` | Structured article draft |
| `title - 知识库.md` | Knowledge-base-ready Markdown |
| `title - 转写信息.json` | Source, model, route, and error metadata |

## Docker and Web UI

```bash
git clone https://github.com/qianzhu18/Muku.git
cd Muku
cp .env.example .env
docker compose up -d --build
```

Open `http://localhost:5657`, configure your API key and download directory, then prepare platform cookies on the host with `./scripts/refresh-cookies all` before clicking “检查 Cookies” in the UI. Local Python runs can use the one-click browser cookie setup button directly. See the [Docker guide](docs/docker-deployment.md) for details.

The Web UI is intended for personal use, self-hosting, or trusted networks. Do not expose it directly as an unaudited public multi-user service.

## Batch capture

```bash
muku capture \
  --input-file ./urls.txt \
  --knowledge \
  --jobs 0 \
  --resume \
  --result-file ./runs/capture.json \
  --output paths
```

See [docs/cli.md](docs/cli.md) for the full CLI contract.

## AI-agent Skill

The one-command installer above installs both the Muku Python package and the Skill definition. To install
the Skill separately from a checkout:

```bash
git clone https://github.com/qianzhu18/Muku.git
cd Muku
./scripts/install-muku-skill
```

The public Skill is available at [skills/muku-video-to-md/SKILL.md](skills/muku-video-to-md/SKILL.md).

Example request:

> Use muku-video-to-md to turn this video into a transcript, article draft, and knowledge-base Markdown, then return the artifact paths.

## Support across 1,800+ site extractors

| Support level | Platform / input | Recommended authentication | Notes |
| --- | --- | --- | --- |
| ✅ Primary path | Bilibili pages and shared links | `BILIBILI_COOKIES_PATH` | Subtitle-heavy knowledge videos are a primary use case |
| ✅ Primary path | YouTube pages and shared links | `YOUTUBE_COOKIES_PATH` | Some videos require a signed-in session |
| ✅ Primary path | Douyin links and shared text | `DOUYIN_COOKIES_PATH` | Optimized for short-form ideas and source capture |
| 🧩 Baseline compatibility | Other complete URLs in yt-dlp's 1,800+ extractor ecosystem | `COOKIES_PATH` | Actual results depend on yt-dlp, the target site, and your environment |
| 🎧 Local input | MP3, M4A, WAV, and more | None | Enters the transcription pipeline directly |

These extractors are not 1,800+ hard-coded Muku integrations. Muku reuses yt-dlp's maintained site ecosystem, then feeds any available subtitles or audio into its own knowledge pipeline. Free public content is usually easiest; signed-in content may need cookies; VIP, DRM-protected, encrypted in-app video, and access-control bypasses are outside the project's scope.

Platform behavior changes over time. Run `muku doctor --json`, then verify your environment with one real URL.

## Security and limitations

- Never commit `.env`, API keys, cookies, or private generated content
- Report vulnerabilities privately according to [SECURITY.md](SECURITY.md)
- Muku does not bypass platform access controls; follow site terms, copyright rules, and local laws
- External transcription and generation models may incur API charges
- A passing CI build cannot guarantee that every platform URL will remain downloadable

## Still evolving

Muku is a working `v0.x`, not a frozen final product. The current release focuses on making the “video input → subtitles/transcription → Markdown knowledge assets” path reliable. Future iterations can add deeper platform adapters, more models and output templates, better creator/series capture, and lighter desktop, browser, or agent entry points.

Open an [Issue](https://github.com/qianzhu18/Muku/issues) for the workflow you need, or read the [input expansion roadmap](docs/input-expansion-roadmap.md). The framework can keep growing; support for a specific video should always be verified with that real URL.

## Development

```bash
git clone https://github.com/qianzhu18/Muku.git
cd Muku
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt -e . pytest
python -m pytest -q
```

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Participation is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Documentation

- [CLI and automation](docs/cli.md)
- [Docker deployment](docs/docker-deployment.md)
- [Windows guide](docs/windows.md)
- [Batch creator workflow](docs/creator-batch-workflow.md)
- [Skill documentation](skills/README.md)

## License

[MIT](LICENSE) © 2026 qianzhu18
