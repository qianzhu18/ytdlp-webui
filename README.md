# 幕库 Muku

[English](https://github.com/qianzhu18/Muku/blob/main/README_EN.md) | 简体中文

> 把 Bilibili、YouTube、Douyin 等知识视频和本地音频，转换成可检索、可连接、可被 AI 持续使用的 Markdown 知识库。

[![PyPI](https://img.shields.io/pypi/v/muku?label=PyPI&color=3775A9)](https://pypi.org/project/muku/)
[![Python](https://img.shields.io/pypi/pyversions/muku)](https://pypi.org/project/muku/)
[![CI](https://github.com/qianzhu18/Muku/actions/workflows/ci.yml/badge.svg)](https://github.com/qianzhu18/Muku/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/qianzhu18/Muku)](https://github.com/qianzhu18/Muku/blob/main/LICENSE)

幕库不是“把视频下载下来就结束”的通用下载器。它关注的是从链接或音频到知识资产的完整链路：优先提取平台字幕，必要时回退音频转写，然后生成逐字稿、解析稿、知识库稿和可追踪的元数据。

项目提供四种入口：`CLI`、`Web UI`、`Docker` 和可供 Codex 等 AI agent 使用的 `Skill`。

## 为什么用幕库

- **Video-to-Markdown**：最终产物是适合 Obsidian、Git、全文检索、RAG 和 agent 工作流的 Markdown
- **字幕优先，转写兜底**：能拿平台字幕时避免重复转写；模型拒绝音频时自动回退，不制造假成功
- **本地优先**：文件、配置和知识资产保存在自己的电脑或自托管环境
- **批量与断点续跑**：支持 URL 文件、标准输入、并发、checkpoint、`--resume` 和 NDJSON 进度
- **面向自动化**：CLI 支持稳定 JSON 和纯路径输出，Skill 不需要驱动网页表单
- **跨平台交付**：PyPI wheel 在 Ubuntu、macOS、Windows 上持续验证

## 60 秒开始

### 准备条件

- Python `3.10+`
- [ffmpeg](https://ffmpeg.org/)：用于音视频处理
- 一把 [OpenRouter](https://openrouter.ai/) API Key：用于音频转写和 AI 整理

安装 ffmpeg：

```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt install ffmpeg
```

Windows 用户可以先看 [Windows 安装指南](https://github.com/qianzhu18/Muku/blob/main/docs/windows.md)。

### 安装 CLI

macOS / Linux 用户可以直接用一条命令安装 CLI 和 AI-agent Skill：

```bash
curl -fsSL https://raw.githubusercontent.com/qianzhu18/Muku/main/scripts/install-muku | bash
muku quickstart
```

Windows PowerShell：

```powershell
irm https://raw.githubusercontent.com/qianzhu18/Muku/main/scripts/install-muku.ps1 | iex
muku quickstart
```

安装器不会替用户创建 API Key，也不会自动读取或上传 Cookies。`muku quickstart` 会安全地提示输入
自己的 OpenRouter Key，配置默认目录并启动本地 Web UI；如果缺少 ffmpeg，会显示对应系统的安装命令。

如果只想安装 CLI，也可以使用隔离式 Python 工具安装，不依赖仓库，也不需要 npm：

```bash
# 二选一
uv tool install muku
pipx install muku

muku --version
muku setup
muku doctor --json
```

如果电脑上只有 Python 和 pip：

```bash
python3 -m venv .muku-venv
source .muku-venv/bin/activate
python -m pip install --upgrade pip muku
muku setup
```

`muku setup` 只需输入一把 OpenRouter Key，会同时配置转写、清洗、解析和知识库阶段；完整 Key 不会回显到终端。

### 生成第一份 Markdown

```bash
# 视频 URL -> 逐字稿 + 解析稿 + 知识库稿
muku capture "https://www.bilibili.com/video/BVxxxx" --knowledge --json

# 本地音频 -> 逐字稿 + 解析稿 + 知识库稿
muku audio "/path/to/audio.mp3" --knowledge --json
```

常见产物：

| 文件 | 内容 |
| --- | --- |
| `标题 - 原始逐字稿.txt` | 未经改写的转录文本 |
| `标题 - 逐字稿.md` | 清洗后的可读逐字稿 |
| `标题 - 解析稿.md` | 按提示词整理的结构化文章 |
| `标题 - 知识库.md` | 适合继续入库和检索的知识稿 |
| `标题 - 转写信息.json` | 来源、模型、处理路径和错误信息 |

## Web UI 与 Docker

想使用图形界面时，克隆仓库后启动 Docker Compose：

```bash
git clone https://github.com/qianzhu18/Muku.git
cd Muku
cp .env.example .env
docker compose up -d --build
```

Windows PowerShell：

```powershell
git clone https://github.com/qianzhu18/Muku.git
Set-Location Muku
Copy-Item .env.example .env
docker compose up -d --build
```

访问 `http://localhost:5657`，在右上角设置中填写 Key、下载目录和平台 Cookies。下载产物默认保存在 `./docker-data/downloads`，配置保存在 `./docker-data/config`。

更完整的容器说明见 [Docker 部署指南](https://github.com/qianzhu18/Muku/blob/main/docs/docker-deployment.md)。Web 面板适合个人、本地或可信网络，不建议直接暴露为公网多人服务。

## 工作原理

```mermaid
flowchart LR
    A[视频 URL / 本地音频] --> B{可获得平台字幕?}
    B -->|是| C[提取并规范化字幕]
    B -->|否| D[压缩音频并转写]
    D --> E{模型拒绝音频?}
    E -->|是| F[切换回退模型]
    E -->|否| G[得到原始逐字稿]
    F --> G
    C --> G
    G --> H[清洗逐字稿]
    H --> I[生成解析稿 / 知识库稿]
    I --> J[本地 Markdown + metadata]
```

## 平台支持

| 平台 | 输入 | 推荐认证 | 说明 |
| --- | --- | --- | --- |
| Bilibili | 视频页、分享链接 | `BILIBILI_COOKIES_PATH` | 字幕与高知识密度内容是主要场景 |
| YouTube | 视频页、分享链接 | `YOUTUBE_COOKIES_PATH` | 字幕优先；部分视频需要登录态 |
| Douyin | 分享链接、分享文案 | `DOUYIN_COOKIES_PATH` | 适合短视频观点和素材沉淀 |
| 其他 yt-dlp 平台 | 完整 URL | `COOKIES_PATH` | 能力取决于 yt-dlp 对目标站点的支持 |
| 本地音频 | MP3、M4A、WAV 等 | 不需要平台 Cookies | 直接进入音频转写链路 |

平台策略会随站点规则变化。请先运行 `muku doctor --json`，再用一条真实链接验证自己的登录态和网络环境。

## 批量任务

```bash
muku capture \
  --input-file ./urls.txt \
  --knowledge \
  --jobs 0 \
  --resume \
  --result-file ./runs/capture.json \
  --output paths
```

- `--jobs 0`：自动选择并发数
- `--resume`：复用 checkpoint 和已有产物
- `--result-file`：每个任务结束后增量写入结果
- `--stream`：输出 NDJSON 进度，适合 `tail -f`、监控和 agent 消费

完整命令见 [CLI 文档](https://github.com/qianzhu18/Muku/blob/main/docs/cli.md)。

## 安装 AI Skill

Skill 负责告诉 agent 何时以及如何调用 Muku CLI；上面的一键安装器会同时安装两者。
如果只安装了 Python 包，也可以单独安装 Skill：

```bash
git clone https://github.com/qianzhu18/Muku.git
cd Muku
./scripts/install-muku-skill
```

安装后可直接向支持 Skill 的 agent 提出：

> 使用 muku-video-to-md，把这个 B 站视频整理成逐字稿、解析稿和知识库 Markdown，并返回产物路径。

公开 Skill 位于 [skills/muku-video-to-md](https://github.com/qianzhu18/Muku/blob/main/skills/muku-video-to-md/SKILL.md)，更多说明见 [Skill 文档](https://github.com/qianzhu18/Muku/blob/main/skills/README.md)。

## 配置与安全

- 不要提交 `.env`、API Key、Cookies 或生成的私密内容
- Docker 优先使用平台专用 `cookies.txt`；本地调试也可以使用 `*_COOKIES_FROM_BROWSER`
- 默认转写模型为 `google/gemini-2.5-flash`，拒绝音频输入时会尝试回退模型
- `muku doctor --json` 会区分“已配置”和“已验证”，配置存在不等于目标平台一定可用
- 发现安全问题请按 [SECURITY.md](https://github.com/qianzhu18/Muku/blob/main/SECURITY.md) 私下报告，不要先公开 Issue

## 验证范围

| 环境 | 验证方式 |
| --- | --- |
| Ubuntu + Python 3.10 / 3.12 | 单元测试、CLI、自检、wheel 安装 |
| macOS + Python 3.12 | 单元测试、CLI、自检、wheel 安装 |
| Windows + Python 3.12 | 单元测试、CLI、自检、wheel 安装 |
| Docker Compose | 配置解析与本地部署 |
| PyPI | Trusted Publishing、独立安装烟测 |

“CI 通过”不代表所有平台链接永远可下载。视频站点的风控、Cookies、地区和网络状态仍会影响真实任务。

## 开发

```bash
git clone https://github.com/qianzhu18/Muku.git
cd Muku
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt -e . pytest
python -m pytest -q
```

提交改动前请阅读 [CONTRIBUTING.md](https://github.com/qianzhu18/Muku/blob/main/CONTRIBUTING.md) 和 [CODE_OF_CONDUCT.md](https://github.com/qianzhu18/Muku/blob/main/CODE_OF_CONDUCT.md)。Bug、功能建议和文档改进都欢迎提交 Issue 或 Pull Request。

## 文档

- [CLI 与自动化](https://github.com/qianzhu18/Muku/blob/main/docs/cli.md)
- [Docker 部署](https://github.com/qianzhu18/Muku/blob/main/docs/docker-deployment.md)
- [Windows 指南](https://github.com/qianzhu18/Muku/blob/main/docs/windows.md)
- [批量采集工作流](https://github.com/qianzhu18/Muku/blob/main/docs/creator-batch-workflow.md)
- [平台集成评估](https://github.com/qianzhu18/Muku/blob/main/docs/platform-integration-evaluation.md)
- [Skill 使用说明](https://github.com/qianzhu18/Muku/blob/main/skills/README.md)
- [安全策略](https://github.com/qianzhu18/Muku/blob/main/SECURITY.md)
- [贡献指南](https://github.com/qianzhu18/Muku/blob/main/CONTRIBUTING.md)

## 项目边界

- 当前定位是个人、本地、自托管和可信小团队工作流
- 普通网页应先由网页采集工具提取为 Markdown，不要直接塞进视频 `capture` 命令
- 项目不会绕过平台访问控制；请遵守目标站点条款、版权规则和所在地法律
- 转写与整理会产生第三方 API 成本，使用前请查看所选模型价格和 Key 限额

## License

[MIT](https://github.com/qianzhu18/Muku/blob/main/LICENSE) © 2026 qianzhu18
