# Open Source Launch Copy

## One-Line Pitch

**1800+ 视频站解析入口，一条链接变知识库。** `幕库 Muku` 把 yt-dlp 解析器生态接进 Markdown 工作流，生成逐字稿、清洗稿、解析稿和知识库稿，支持 `Web UI + CLI + Docker + Skill` 四种入口。

## X / 推文短版

**1800+ 视频站，一条链接变知识库。**

我把 yt-dlp 的解析器生态接进了自己的 Markdown 知识库：`幕库 Muku`

- 接入 yt-dlp 1800+ 解析器生态
- 支持 `Web UI + CLI + Docker + Skill`
- Bilibili / YouTube / Douyin 是重点适配主链路
- 能直接把视频整理成逐字稿、解析稿、知识库稿
- 适合 AI agent 直接调用，CLI 默认支持 `--json`
- 更适合沉淀知识内容，不只是下载视频

我自己主要拿它做：
1. 把高质量视频收进本地知识库
2. 优先提字幕，失败再回退转写
3. 直接整理成可复用的 Markdown 素材

如果你也在做内容归档、视频笔记、Agent workflow，欢迎试试。

## X / 推文长版

开源了一个我自己一直在用的工具：`幕库 Muku`

它不是单纯的下载器，而是一条完整的视频知识库工作流：

- Web UI：适合直接粘贴链接
- CLI：适合脚本、批量任务和 AI agent
- Docker：适合一键部署
- Skill：适合 Codex / Claude Code / Cursor Agent 直接复用

目前这套链路主打：

- YouTube
- Bilibili
- Douyin
- 其他 yt-dlp 可解析站点的完整 URL

我最在意的点有三个：

1. 不是只下载视频，而是把视频内容收入本地知识库
2. CLI 默认支持 `--json`，方便给 AI 和自动化消费
3. Cookies、平台级登录态、Docker、Skill 都整理成了比较完整的开源形态

`1800+` 指 yt-dlp 当前的解析器范围，不代表逐站逐链接保证。站点改版、登录态、地区、网络和 DRM 仍会影响结果，最可靠的方法是拿真实链接跑一次。

如果你平时会做：

- 视频素材归档
- 课程/访谈整理
- 逐字稿沉淀
- 知识库笔记生产
- Agent workflow

这个项目应该会比较顺手。

## 仓库介绍配文

把 yt-dlp 1800+ 站点的知识视频沉淀为 Markdown：B站 / YouTube / 抖音重点适配，也兼容其他 yt-dlp 可解析链接；支持 `Web UI + CLI + Docker + Skill`，适合个人知识库、内容工作流和 AI agent 调用。
