---
name: muku-video-to-md
description: >
  Use this skill when the user wants to turn knowledge-heavy video URLs, local audio,
  or already-extracted web page Markdown into transcript and knowledge-base assets.
  Pair it with qianzhu a2w / Kimi WebBridge for webpage intake and dynamic source
  discovery, then use the Muku CLI for stable local artifact generation.
---

# Muku Video to MD

幕库的目标是把知识视频和高价值网页资料收入本地 Markdown 知识库，而不是做一个通用下载器。

对于视频 URL 和本地音频，优先使用这个仓库的 CLI，不要默认去驱动网页。对于普通网页、社交链接、
飞书 wiki、公众号文章等网页资料，先用 qianzhu `a2w-skill` 选择网页采集路径，再把得到的
Markdown / 正文交给幕库的知识库整理链路或下游知识库。

## Fast path

```bash
muku doctor --json
muku config --json
muku capture "https://www.bilibili.com/video/BVxxxx" --knowledge --json
muku capture "https://www.youtube.com/watch?v=..." --knowledge --json
muku audio "/path/to/file.mp3" --knowledge --json
muku artifacts "/path/to/file.mp3" --json
muku knowledge "/path/to/file.mp3" --json
```

## Command selection

- 用户给的是视频 URL，且目标是知识库产物：优先用 `capture --knowledge`
- 用户给的是普通网页或动态网页：先用 `a2w-skill` 路由。默认 Kimi WebBridge first；静态正文、批量校验或 Kimi 不可用时再用 `web-access` / Jina / curl 等 fallback
- 已经从网页提取出 Markdown：保留原始 URL、标题、抓取日期和工具来源，然后交给知识库整理提示词处理；不要把网页链接强塞进 `capture`
- 用户只想下载文件本身：用 `download`
- 用户已经有本地音频：用 `audio`；若还要知识库稿，用 `audio --knowledge`
- 用户已经拿到某个 sidecar，想定位整组文件或 metadata：用 `artifacts`
- 用户只想补生成知识库稿：用 `knowledge`
- 先确认配置、依赖、密钥状态：用 `doctor`

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

- 默认优先 `--json`，给 AI 最稳定
- 只需要路径时，用 `--output paths`
- 需要保存机器可读结果时，加 `--result-file`
- 长批量任务默认搭配 `--resume`
- 批量输入优先 `--input-file` 或 `--stdin`

## Batch workflow

```bash
muku capture \
  --input-file ./urls.txt \
  --knowledge \
  --jobs 0 \
  --resume \
  --result-file ./capture.json \
  --output paths
```

- `--jobs 0`：自动并发
- `--result-file`：每个条目完成就会写 checkpoint
- `--resume`：优先复用 checkpoint 和已有逐字稿 sidecar

## Useful runtime overrides

```bash
muku config --download-dir "/Users/you/Downloads/muku" --json
muku capture URL --language zh --json
muku capture URL --transcription-model openai/gpt-audio-mini --json
muku capture URL --youtube-cookies-path ./cookies/youtube.cookies.txt --json
muku capture URL --bilibili-cookies-path ./cookies/bilibili.cookies.txt --json
muku capture URL --douyin-cookies-from-browser chrome --json
muku capture URL --knowledge-model stepfun/step-3.7-flash --json
muku capture URL --knowledge-prompt-file ./知识库提示词.md --json
muku audio FILE --cleanup-prompt-file ./角色提示词.md --article-prompt-file ./解析提示词.md --json
```

## Browser-cookie fallback

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

转写仍使用 `OPENROUTER_API_KEY` 和 `openai/gpt-audio-mini`。不要回显真实 key。

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

- 默认配置从仓库根目录 `.env` 读取，不要在命令里回显密钥
- 若入口报 `ModuleNotFoundError: No module named 'webui'`，先用
  `python -m pip show muku` 检查 `Editable project location`。若它指向已迁移或
  不存在的旧仓库，进入当前 Muku 仓库运行 `./scripts/install-muku-cli`；安装脚本会使用
  非 editable 安装，避免仓库改名或移动后入口再次失效
- `.env` 中指向仓库内部的 cookie / prompt 路径如果仍是旧绝对路径，应改为当前路径，
  或在命令中传入当前 `--*-cookies-path`；不要用 `--skip-cookie-check` 掩盖已过期 cookie
- 如果用户说“网页里已经配过默认目录和模型”，先跑 `muku config --json`，确认 CLI 侧也已经读到同一份配置
- 先跑 `doctor --json`，检查 `youtube_auth_configured`、`bilibili_auth_configured`、`douyin_auth_configured`
- YouTube、B 站、抖音受限内容抓取失败时，优先尝试平台级参数：`--youtube-cookies-*` / `--bilibili-cookies-*` / `--douyin-cookies-*`
- `artifacts` 默认只返回摘要 metadata；排障时再加 `--full-metadata`
- 若仅需下载，不要额外开启逐字稿，以节省成本和时间
- 转写前预处理音频默认写入系统临时目录，不会在下载目录里额外留下第二个可见 MP3
- `逐字稿.md` 默认只写清洗后的正文；原始内容单独放在 `原始逐字稿.txt`
- `解析稿.md` 默认只写最终成稿，不添加“解析稿”“成稿如下”等外层包装
- 默认解析规则来自仓库根目录的 `解析提示词.md`；批量回写或重生成时也要遵守同一规范
- 知识库整理默认显式使用 `KNOWLEDGE_DRAFT_*`，本机与 `ARTICLE_DRAFT_*` 同样走 OpenRouter StepFun
- 如果要先从创作者主页 / 系列页提取链接，推荐先用 qianzhu `a2w-skill` 判断路径。默认策略是 Kimi WebBridge first，`web-access` 作为通用 fallback：先生成 `urls.txt`，再调上面的批量命令
