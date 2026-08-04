# Muku Skills

这个目录存放幕库对外公开的 agent / AI skill。视频和音频目标不是让 agent 去点网页，而是直接复用稳定的 CLI 契约，把 Bilibili、YouTube、Douyin 等平台上的知识视频沉淀为 Markdown 知识库。普通网页、社交长文、公众号、飞书 wiki 等资料则先由 A2W/Kimi/Web-access 提取成 Markdown，再进入知识库整理。

## 当前提供

- [muku-video-to-md](muku-video-to-md/SKILL.md)

这个 skill 适合：

- 单条 URL 直接生成逐字稿、解析稿和知识库稿
- 本地音频补做转写和知识库整理
- 从 `urls.txt` 批量把一组视频收入本地知识库
- 把已经由网页采集 agent 提取好的 Markdown / 正文继续整理为本地知识资产
- 让 AI agent 复用稳定 JSON 输出，不必驱动 Web UI

推荐使用顺序：

1. 先跑 `muku doctor --json`
2. 再跑 `muku config --json`，确认默认下载目录和模型配置
3. 按平台补 `--youtube-cookies-*` / `--bilibili-cookies-*` / `--douyin-cookies-*`
4. 最后让 agent 调 `capture --knowledge`、`audio --knowledge`、`artifacts` 等命令

推荐的批量入库命令：

```bash
muku capture \
  --input-file ./urls.txt \
  --knowledge \
  --jobs 0 \
  --resume \
  --result-file ./runs/creator-series/capture.json \
  --output paths
```

如果你要先从创作者主页、系列页、合集页采链接，再批量生成 Markdown 知识库，推荐先用 qianzhu `a2w-skill` 判断浏览路径：Kimi WebBridge first，`web-access` 作为通用 fallback。浏览器侧负责采集 URL，幕库负责把视频 URL 批量入库。

如果你要吸收普通网页资料，参考 `web-to-fim` 的抽象：先把 URL / 文件转成结构化 Markdown，并保留 `source_url`、标题、抓取时间和抓取工具，再写入 Obsidian、RAG 或其他知识库。幕库当前不默认同步飞书或 IMA。

## 快速安装到 Codex

如果用户还没有安装 Muku，推荐一条命令同时安装 CLI 和 Skill：

```bash
curl -fsSL https://raw.githubusercontent.com/qianzhu18/Muku/main/scripts/install-muku | bash
muku quickstart
```

Windows PowerShell：

```powershell
irm https://raw.githubusercontent.com/qianzhu18/Muku/main/scripts/install-muku.ps1 | iex
muku quickstart
```

如果 CLI 已经安装，只需要安装 Skill：

```bash
./scripts/install-muku-skill
```

如果你还在沿用旧脚本名，`./scripts/install-video-downloade-skill` 也可以继续使用。

如果你想手动安装：

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R ./skills/muku-video-to-md "${CODEX_HOME:-$HOME/.codex}/skills/muku-video-to-md"
```

## 目录约定

- `.codex/skills/`：仓库内当前直接使用的本地 skill
- `skills/`：适合开源发布、给其他 agent 工具复用的版本

后续如果要兼容更多 agent 平台，可以继续在这里补不同格式的 skill 模板。核心原则是：视频处理优先复用 CLI；网页处理优先复用 A2W 路由和真实浏览器能力，再把结果交给知识库整理。
