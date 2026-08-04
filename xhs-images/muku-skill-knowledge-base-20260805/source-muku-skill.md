# Muku Skill 内容事实

幕库 Muku 是一个本地优先的 Video-to-Markdown 工具和 AI-agent Skill。

核心链路：

- Bilibili、YouTube、Douyin 等知识视频 URL → 逐字稿、解析稿、知识库 Markdown
- 本地 MP3、M4A、WAV 等音频 → 同样的知识资产
- 字幕优先，字幕不可用时回退到音频转写
- CLI 支持 JSON、路径输出、批量任务、断点续跑
- `muku quickstart` 负责首次配置 API Key、默认目录和本地 Web UI
- macOS / Linux 可用 `scripts/install-muku` 一次安装 CLI 和 Skill
- Windows PowerShell 可用 `scripts/install-muku.ps1`
- API Key 和 Cookies 由用户自己配置，不应在项目或帖子中共享
- 转写和 AI 整理会调用用户选择的 AI 服务，不是纯离线工具
- 小红书等普通网页资料目前需要先由浏览器型 agent 提取 Markdown，再交给 Muku 整理

公开入口：https://github.com/qianzhu18/Muku
