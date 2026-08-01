# CLI 与 AI 集成

这个仓库的命令行已经是第一公民，不只是 Web UI 的附属工具。

如果你的目标是：

- 让 AI 代理稳定调用这个项目
- 批量处理 URL 或本地音频
- 从视频直接整理出知识库笔记
- 在 Docker 容器里复用同一套能力

优先走 CLI，而不是驱动浏览器。

## 安装

日常使用推荐安装成独立工具。它拥有自己的 Python 环境，可以在任意项目目录调用：

```bash
uv tool install muku
# 或者
pipx install muku
```

没有 `uv` / `pipx` 时，可在独立虚拟环境中使用标准 pip：

```bash
python3 -m venv ~/.local/share/muku/venv
~/.local/share/muku/venv/bin/python -m pip install muku
~/.local/share/muku/venv/bin/muku --version
```

克隆仓库后也可以运行自动安装器：

```bash
./scripts/install-muku-cli
```

只有参与开发时才使用 editable 安装：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Muku 是 Python 应用，不需要 npm。npm 只适用于用 Node.js 发布和运行的 CLI；为本项目再套一层 npm
只会多出一套版本、缓存和 PATH 管理。

首次安装后运行一次向导：

```bash
muku setup
muku doctor --json
```

`muku setup` 会隐藏输入的 OpenRouter API Key，并把它复用于转写、清洗、解析和知识库四个阶段。
如果是脚本或 agent，使用纯 JSON 模式：

```bash
muku setup --api-key "$OPENROUTER_API_KEY" --download-dir "$PWD/muku-output" --json
```

建议第一次接入前先跑：

```bash
muku doctor --json
muku config --json
```

Python 安装会自动带上 `yt-dlp` 模块，但媒体转换依赖系统级 `ffmpeg`。macOS 可运行
`brew install ffmpeg`，Ubuntu/Debian 可运行 `sudo apt install ffmpeg`；缺失时 `doctor` 会把
`transcript_capture_ready` 和 `knowledge_capture_ready` 标记为 `false`。

## 最推荐的工作流

### URL -> 逐字稿 + 解析稿 + 知识库稿

```bash
muku capture "https://www.bilibili.com/video/BVxxxx" \
  --knowledge \
  --json
```

### 本地音频 -> 逐字稿 + 知识库稿

```bash
muku audio "/path/to/file.mp3" \
  --knowledge \
  --json
```

### 已有 sidecar -> 单独补知识库稿

```bash
muku knowledge "/path/to/file.mp3" --json
```

### 批量 URL

```bash
muku capture \
  --input-file ./urls.txt \
  --knowledge \
  --jobs 0 \
  --resume \
  --result-file ./capture.json \
  --json
cat ./urls.txt | muku capture --stdin --output paths
```

## 命令选择

- URL 输入，目标是逐字稿或知识库产物：`capture`
- 只想下载视频或 MP3：`download`
- 已经有本地音频：`audio`
- 已经有 sidecar 路径，想定位整组产物：`artifacts`
- 已经有逐字稿资产，只想补生成知识库稿：`knowledge`
- 想查看或保存默认下载目录、模型、提示词和服务地址：`config`
- 想先检查依赖、模型、Cookies、提示词：`doctor`

## 配置命令

`config` 用来查看或写入默认运行配置，适合给 Codex、Claude Code 或容器内脚本做首轮初始化。

```bash
# 查看当前生效配置
muku config --json

# 设置默认下载目录和模型
muku config \
  --download-dir "/Users/you/Downloads/muku" \
  --transcription-model google/gemini-2.5-flash \
  --cleanup-base-url https://openrouter.ai/api/v1 \
  --cleanup-model stepfun/step-3.7-flash \
  --article-base-url https://openrouter.ai/api/v1 \
  --article-model stepfun/step-3.7-flash \
  --knowledge-base-url https://openrouter.ai/api/v1 \
  --knowledge-model stepfun/step-3.7-flash \
  --json

# Docker 容器里建议写容器内路径
muku config \
  --download-dir /downloads/default \
  --json
```

注意两点：

- macOS / Windows 本地运行时，`--download-dir` 建议使用绝对路径
- Docker 场景下，`--download-dir` 必须位于 `/downloads` 之内；真正落到宿主机哪个目录，由 `DOCKER_DOWNLOADS_DIR` 决定

## 多平台建议

| 平台 | 最稳命令习惯 | 推荐认证方式 |
| --- | --- | --- |
| YouTube | `capture --knowledge --youtube-cookies-from-browser chrome --json` | 浏览器登录态优先 |
| Bilibili | `capture --knowledge --bilibili-cookies-from-browser chrome --json` | 平台专用 cookies 优先 |
| Douyin | `download` 或 `capture` 配合 `--douyin-cookies-*` | 浏览器登录态或专用 `cookies.txt` |

## AI 友好的输出约定

- 默认推荐 `--json`
- 只需要路径时用 `--output paths`
- 需要把结果落盘时用 `--result-file`
- 长批量任务建议始终带上 `--resume`
- `artifacts` 默认只返回 metadata 摘要；排障时再加 `--full-metadata`

如果你在写 agent workflow，推荐顺序是：

1. `muku doctor --json`
2. `capture --knowledge --json` 或 `audio --knowledge --json`
3. 必要时再用 `artifacts --json` 反查 sidecar

## 常用覆盖项

```bash
muku capture URL --language zh --json
muku capture URL --output-dir "/Users/you/Downloads/muku/bilibili" --json
muku capture URL --transcription-model google/gemini-2.5-flash --json
muku capture URL --cleanup-model stepfun/step-3.7-flash --article-model stepfun/step-3.7-flash --json
muku capture URL --knowledge-model stepfun/step-3.7-flash --json
muku capture URL --knowledge-prompt-file ./知识库提示词.md --json
muku audio FILE --no-article --knowledge --json
```

默认音频模型是 `google/gemini-2.5-flash`。模型明确拒绝音频输入时，Muku 会自动尝试 `OPENROUTER_TRANSCRIPTION_FALLBACK_MODELS` 中的候选模型；全部拒绝时任务会失败，不会生成内容错误的逐字稿。使用 `muku doctor --json` 可以查看当前生效的主模型和回退列表。

## 断点恢复与高并发

`capture`、`download`、`audio`、`knowledge` 现在都支持：

```bash
--jobs 0
--resume
--result-file ./capture.json
```

推荐理解方式：

- `--jobs 0`：自动并发；URL 批量会走更积极的自动并发档位，本地音频和知识库整理维持更稳的并发上限
- `--result-file`：每个条目完成就会增量写入 JSON checkpoint，不需要等整批跑完
- `--resume`：先复用 checkpoint；对于 `capture` / `download --transcript` / `audio`，还会额外复用下载目录里已经存在的逐字稿 sidecar

这意味着如果一批任务在第 7 条时中断，再跑同一条命令时：

- 已经完成知识库的条目会直接跳过
- 已经生成逐字稿、但知识库还没完成的条目会直接从知识库阶段继续
- 本地已经存在 sidecar 的 URL / 音频，也不会重复下载或重复转写

一个更稳的批量模板：

```bash
muku capture \
  --input-file ./urls.txt \
  --knowledge \
  --jobs 0 \
  --resume \
  --result-file ./runs/creator-series/capture.json \
  --output paths
```

## Cookies 与平台登录态

推荐按平台分开配置登录态，而不是所有平台共用一份全局 cookies：

```bash
muku capture URL \
  --youtube-cookies-from-browser chrome \
  --bilibili-cookies-path ./cookies/bilibili.cookies.txt \
  --douyin-cookies-from-browser chrome \
  --json
```

也可以写进 `.env`：

```bash
YOUTUBE_COOKIES_FROM_BROWSER=chrome
YOUTUBE_COOKIES_PATH=/absolute/path/to/youtube.cookies.txt
BILIBILI_COOKIES_PATH=/absolute/path/to/bilibili.cookies.txt
DOUYIN_COOKIES_PATH=/absolute/path/to/douyin.cookies.txt
```

推荐检查顺序：

1. 目标平台先在浏览器中登录。
2. 优先尝试 `*_COOKIES_FROM_BROWSER=chrome`。
3. 执行 `muku doctor --json`。
4. 确认 `youtube_auth_configured`、`bilibili_auth_configured`、`douyin_auth_configured` 等字段。
5. 只有浏览器方案不稳定时，再回退到 `*_COOKIES_PATH`。

## 产物说明

- 下载目录默认只保留最终视频或最终 MP3，以及 sidecar 文稿。
- 转写前预处理音频会写到系统临时目录，不再在产物目录里额外留下第二个可见 MP3。
- 只有当你显式设置 `KEEP_TRANSCRIPTION_INPUT=true` 时，才建议保留这类调试输入。
- `capture` / `download` 的 `--output-dir` 只覆盖当前命令；想改长期默认值，用 `muku config --download-dir ...`

## 容器里调用 CLI

如果你已经用 Docker 启动服务，也不需要额外装第二套工具：

```bash
docker compose exec ytdl-webui muku doctor --json
docker compose exec ytdl-webui muku config --json
docker compose exec ytdl-webui muku capture URL --knowledge --json
```

## Skill 封装

公开 skill 已经整理在：

- [../skills/muku-video-to-md/SKILL.md](../skills/muku-video-to-md/SKILL.md)

安装到 Codex：

```bash
./scripts/install-muku-skill
```

如果你想手动复制：

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R ./skills/muku-video-to-md "${CODEX_HOME:-$HOME/.codex}/skills/muku-video-to-md"
```

## 搭配 A2W / Kimi / Web-access

如果你的需求不是“已经有视频链接”，而是“先去某个博主主页、合集页、系列页把链接采下来”，推荐先用 qianzhu `a2w-skill` 判断采集路径：

- Kimi WebBridge first：适合创作者主页、动态页面、视觉判断和需要浏览器登录态的站点
- `web-access` fallback：适合普通搜索、静态正文、来源核实和 Kimi 不可用时的浏览器/CDP 路径
- 本仓库 CLI 负责把 `urls.txt` 批量变成逐字稿、解析稿和知识库 Markdown

推荐 prompt：

```text
请打开这个创作者主页，只提取「XXX 系列」的视频链接。
要求：
1. 每行一个 URL
2. 不要输出解释
3. 保存为 ./urls.txt
```

然后直接执行：

```bash
muku capture \
  --input-file ./urls.txt \
  --knowledge \
  --jobs 0 \
  --resume \
  --result-file ./runs/creator-series/capture.json \
  --output paths
```

仓库里还附了一个可直接试跑的 demo 链接文件，见 [creator-batch-workflow.md](./creator-batch-workflow.md)。
