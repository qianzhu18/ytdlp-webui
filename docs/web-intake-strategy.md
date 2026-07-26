# Web Intake Strategy

幕库以前更像 `video-to-md`：给一个视频 URL 或本地音频，产出逐字稿、解析稿和知识库稿。
吸收 `web-to-fim` 的关键不是照搬飞书或 IMA，而是把入口从“只有视频”扩展为“所有高价值网页资料都先转成结构化 Markdown”。

## Decision

当前建议的联网优先级：

1. Kimi WebBridge first：视觉、动态、登录态、需要滚动/展开/截图的网页。
2. web-access fallback：普通搜索、静态正文、来源核实、Kimi 不可用时的浏览器/CDP fallback。
3. Jina / curl：静态文章、官方文档、结构简单页面的低成本抽取。
4. Scrapling later：字段稳定后再做可重复的大批量结构化采集。
5. Muku CLI：视频 URL 和本地音频的稳定产物生成。

所以不要把 `web-access` 固定为第一优先级。它很好，但更适合作为通用 fallback 和静态/批量侧能力；qianzhu 的默认策略应该由 `a2w-skill` 先判断，Kimi 负责真实浏览器观察。

## Intake Contract

网页采集 agent 输出 Markdown 时，至少保留：

```yaml
source_url: "<original url>"
title: "<page title>"
captured_at: "YYYY-MM-DDTHH:mm:ssZ"
capture_tool: "kimi-webbridge | web-access | jina | curl | other"
```

如果页面是转载、飞书 wiki 聚合页或带有“原文链接”的内容，优先抓取原文链接，并同时保留中转页 URL。

## Routing

| 输入 | 第一选择 | 后续 |
| --- | --- | --- |
| Bilibili / YouTube / Douyin / 其他 yt-dlp 视频 | `muku capture --knowledge` | 产出逐字稿、解析稿、知识库稿 |
| 本地音频 | `muku audio --knowledge` | 产出逐字稿、解析稿、知识库稿 |
| 普通网页 / 官方文档 / 博客 | A2W 选择 Kimi 或 web-access | 转 Markdown 后入 Obsidian / RAG / 下游知识库 |
| X/Twitter / 公众号 / 小红书 / 微博 / 飞书 wiki | A2W 选择真实浏览器或专用抓取路径 | 保证正文完整度和原文链接 |
| 创作者主页 / 系列页 / 合集页 | Kimi/Web-access 提取视频 URL 列表 | 再交给 Muku 批量 `capture --knowledge` |

## What We Borrow From Web-to-FIM

- 多信源入口：网页、社交长文、飞书 wiki、本地文件都能进入同一个 Markdown intake。
- 路由优先于工具执念：按来源和正文完整度选择工具，而不是默认一种工具。
- 原文链接优先：聚合页不是最终事实源，能拿原文就拿原文。
- 元信息必留：URL、标题、抓取时间、抓取工具是后续去重、追溯和 RAG 的基本字段。
- 存储层解耦：Markdown 是中间资产，至于落到 Obsidian、飞书、IMA、RAG，可以按场景选择。

## Current Boundary

幕库当前不内置 `markitdown`、飞书 API、IMA API 或 X/Twitter 专用抓取器。这样做是刻意的：
先把 agent 路由和 Markdown 契约稳定下来，再决定是否把网页转 Markdown 做成 CLI 的一等命令。

下一步如果要产品化，可以新增一个独立命令，例如：

```bash
muku ingest-web URL --output ./runs/web-intake --json
```

但在实现前，agent 侧先按本文件执行即可。
