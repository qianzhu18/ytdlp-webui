---
name: muku-video-to-md
description: >
  Use this skill when an AI agent needs to turn knowledge-heavy video URLs, local audio,
  or already-extracted web page Markdown into transcript and knowledge-base assets.
  Pair it with qianzhu a2w / Kimi WebBridge for webpage intake and dynamic source
  discovery, then use the Muku CLI for stable local artifact generation.
---

# Muku Video to MD

幕库的目标是把知识视频和高价值网页资料收入本地 Markdown 知识库，而不是做一个通用下载器。

对于视频 URL 和本地音频，优先使用这个仓库的 CLI，不要默认去驱动网页。对于普通网页、社交链接、
飞书 wiki、公众号文章等网页资料，先用 qianzhu `a2w-skill` 选择网页采集路径，再把得到的
Markdown / 正文交给幕库的知识库整理链路或下游知识库。

## Best use cases

- 用户给的是知识型视频 URL，希望直接得到逐字稿、解析稿和知识库稿
- 用户给的是一组视频列表，希望批量沉淀为 Markdown 知识库
- 用户已经有本地音频，希望补做转写和知识库整理
- 用户给的是普通网页、公众号、X/Twitter、飞书 wiki、小红书、微博、GitHub 文档等资料，希望先转成结构化 Markdown 再入库
- 用户想让 agent 返回 JSON 或路径，继续衔接后续 AI 工作流

## Fast path

```bash
muku doctor --json
muku config --json
muku capture "https://www.youtube.com/watch?v=..." --knowledge --json
muku capture "https://www.bilibili.com/video/BVxxxx" --knowledge --json
muku audio "/path/to/file.mp3" --knowledge --json
muku artifacts "/path/to/file.mp3" --json
muku knowledge "/path/to/file.mp3" --json
```

## Routing rules

- 目标是从视频 URL 直接得到 Markdown 资产：优先用 `capture --knowledge`
- 只在用户明确要求“下载文件本身”时才用 `download`
- 已经有本地音频：用 `audio`；若还要知识库稿，用 `audio --knowledge`
- 已经拿到 sidecar 或音频路径：用 `artifacts`
- 已经有逐字稿资产，只想补生成知识库稿：用 `knowledge`
- 输入是普通网页或动态网页：先用 `a2w-skill` 路由。默认 Kimi WebBridge first；静态正文、批量校验或 Kimi 不可用时再用 `web-access` / Jina / curl 等 fallback
- 已经从网页提取出 Markdown：保留原始 URL、标题、抓取日期和工具来源，然后交给知识库整理提示词处理；不要把网页链接强塞进 `capture`
- 不确定依赖、模型、Cookies、提示词是否就绪：先跑 `doctor`

## Web page intake

吸收 `web-to-fim` 的思路：入口不只应该是视频，还应该覆盖网页、社交长文、公众号、飞书 wiki
和本地文件；第一步统一变成结构化 Markdown，第二步再决定落到本地知识库、飞书、IMA 或其他系统。
幕库当前只承诺本地 Markdown / CLI 产物，不默认同步飞书或 IMA。

推荐路由：

| 输入 | 第一选择 | 说明 |
| --- | --- | --- |
| 视觉/交互网页、登录态页面、复杂动态页面 | Kimi WebBridge | 使用真实浏览器观察页面、滚动、展开、截图和读取 DOM |
| 普通文章、官方文档、静态网页 | web-access / Jina / curl | 低成本抽正文；需要核实时访问一手来源 |
| X/Twitter、公众号、小红书、微博、飞书 wiki | a2w-skill 决策 | 根据平台反爬、登录态和正文完整度选择 Kimi 或 web-access |
| 视频平台 URL | Muku CLI `capture --knowledge` | 字幕优先，失败回退音频转写 |
| 本地音频 | Muku CLI `audio --knowledge` | 直接进入转写和知识库整理 |

网页转 Markdown 时必须保留元信息：

- `source_url`
- `title`
- `captured_at`
- `capture_tool`
- 若存在原文链接，优先保留并抓取原文链接

如果用户说“联网搜索策略”“网页资料入库”“web-to-fim”“三处存放”或类似意图，先加载
`a2w-skill` 判断工具优先级；不要把 `web-access` 固定为第一优先级。

## Output strategy

- 默认优先 `--json`
- 只需要路径时，用 `--output paths`
- 批量任务建议加 `--result-file`
- 长批量任务默认搭配 `--resume`
- 批量输入优先 `--input-file` 或 `--stdin`

## Batch ingestion

```bash
muku capture \
  --input-file ./urls.txt \
  --knowledge \
  --jobs 0 \
  --resume \
  --result-file ./runs/creator-series/capture.json \
  --output paths
```

批量场景约定：

- `--jobs 0`：自动并发
- `--result-file`：每个条目完成即写 checkpoint
- `--resume`：优先复用 checkpoint 和已有 sidecar，避免重复下载、重复转写

## Auth handling

优先使用平台级登录态：

```bash
muku capture URL \
  --youtube-cookies-from-browser chrome \
  --bilibili-cookies-path ./cookies/bilibili.cookies.txt \
  --douyin-cookies-from-browser chrome \
  --json
```

推荐流程：

1. 先执行 `muku doctor --json`
2. 检查 `youtube_auth_configured`、`bilibili_auth_configured`、`douyin_auth_configured`
3. 优先用 `*_COOKIES_FROM_BROWSER`
4. 浏览器方案不稳定时，再回退到 `*_COOKIES_PATH`

如果 macOS 上 `--bilibili-cookies-from-browser chrome` 长时间无输出，而
`web-access` 已连接到一个已登录的 Chrome，可以从当前 CDP 会话导出只包含 B 站域名的
Netscape cookie 文件：

```bash
node ./scripts/export-cdp-cookies.mjs \
  --domain bilibili.com \
  --output ./cookies/bilibili.cdp.cookies.txt

muku capture URL \
  --bilibili-cookies-path ./cookies/bilibili.cdp.cookies.txt \
  --knowledge --json
```

导出文件包含登录凭据，必须保持在 `cookies/` 或其他 gitignored 目录，不要回显内容、
提交到 Git，也不要复制进任务产物目录。

如果任务开始前需要先把默认下载目录、模型或服务地址写好，优先执行：

```bash
muku config \
  --download-dir "/Users/you/Downloads/muku" \
  --transcription-model openai/gpt-audio-mini \
  --cleanup-base-url https://openrouter.ai/api/v1 \
  --cleanup-model stepfun/step-3.7-flash \
  --article-base-url https://openrouter.ai/api/v1 \
  --article-model stepfun/step-3.7-flash \
  --knowledge-base-url https://openrouter.ai/api/v1 \
  --knowledge-model stepfun/step-3.7-flash \
  --json
```

Docker 场景下，把 `--download-dir` 改成容器内路径，例如 `/downloads/default`。

## Pairing with browsing agents

如果任务是“先从博主主页、频道页、系列页、合集页采链接，再批量收入知识库”，推荐先用
qianzhu `a2w-skill` 判断路径。默认策略是 Kimi WebBridge first，`web-access` 作为通用 fallback：

1. 让浏览器型 agent 把目标视频 URL 提取成 `./urls.txt`
2. 再调用上面的批量 `capture --knowledge` 命令

## Useful runtime overrides

```bash
muku capture URL --language zh --json
muku capture URL --transcription-model openai/gpt-audio-mini --json
muku capture URL --knowledge-model stepfun/step-3.7-flash --json
muku capture URL --knowledge-prompt-file ./知识库提示词.md --json
muku audio FILE --no-article --knowledge --json
```

## Local text backend

本机清洗稿、解析稿、知识库稿默认都走 OpenRouter：

```bash
AI_CLEANUP_BASE_URL=https://openrouter.ai/api/v1
AI_CLEANUP_MODEL=stepfun/step-3.7-flash
ARTICLE_DRAFT_BASE_URL=https://openrouter.ai/api/v1
ARTICLE_DRAFT_MODEL=stepfun/step-3.7-flash
KNOWLEDGE_DRAFT_BASE_URL=https://openrouter.ai/api/v1
KNOWLEDGE_DRAFT_MODEL=stepfun/step-3.7-flash
```

转写也使用 `OPENROUTER_API_KEY`；不要回显真实 key。

## Expected artifacts

- `xxx - 原始逐字稿.txt`
  原始逐字稿，仅保留原始文本
- `xxx - 逐字稿.md`
  清洗后的逐字稿正文，不重复附带原始稿、解析稿或额外说明
- `xxx - 解析稿.md`
  仅保留解析成稿正文，严格遵循 `解析提示词.md`
- `xxx - 知识库.md`
- `xxx - 转写信息.json`

## Operational notes

- 不要在命令输出中回显真实密钥或 Cookies 内容
- 若入口报 `ModuleNotFoundError: No module named 'webui'`，先用
  `python -m pip show muku` 检查 `Editable project location`。若它指向已迁移或
  不存在的旧仓库，进入当前 Muku 仓库运行 `./scripts/install-muku-cli`；安装脚本会使用
  非 editable 安装，避免仓库改名或移动后入口再次失效
- `.env` 中指向仓库内部的 cookie / prompt 路径如果仍是旧绝对路径，应改为当前路径，
  或在命令中传入当前 `--*-cookies-path`；不要用 `--skip-cookie-check` 掩盖已过期 cookie
- YouTube 下载失败时，优先检查 `doctor --json` 里的 `youtube_auth_configured`
- Bilibili、YouTube、Douyin 建议分开配置 Cookies，避免串用
- 如果用户说“网页端已经配好了”，仍然建议先跑 `muku config --json`，确认 CLI 与网页看到的是同一份默认配置
- 转写前预处理音频默认写入系统临时目录，不会在下载目录里额外留下第二个可见 MP3
- `逐字稿.md` 默认只写清洗后的正文；原始内容单独放在 `原始逐字稿.txt`
- `解析稿.md` 默认只写最终成稿，不添加“解析稿”“成稿如下”等外层包装
- 默认解析规则来自仓库根目录的 `解析提示词.md`；批量回写或重生成时也要遵守同一规范
- 知识库整理默认显式使用 `KNOWLEDGE_DRAFT_*`，本机与 `ARTICLE_DRAFT_*` 同样走 OpenRouter StepFun
