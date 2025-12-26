📺 Local Video Downloader 2.0 升级设计文档1. 设计理念与审美重构 (The "Qianzhu" Aesthetic)核心目标：从当前的“科技/游戏风”转变为“现代禅意/极简主义”风格。关键词：Clean (干净), Typography (排版优先), Nature (自然色调), Focus (聚焦内容)。1.1 配色方案 (Color Palette)放弃原有的橙/绿高对比度和大面积渐变背景，采用“纸张”质感与自然色系。变量名原始颜色 (旧)新版颜色 (千竹风格)说明--bg-body暖色渐变 (#fff6e5...)#FAFAF9 (Warm Paper)仿纸张的暖灰白色背景，护眼且高级。--bg-card半透明毛玻璃#FFFFFF (Pure White)实心白卡片，去除模糊滤镜，强调层级。--text-primary#14130f#2C2C2C (Ink Grey)接近纯黑的墨色，比纯黑更柔和。--text-secondary#5c5a52#666666 (Stone Grey)次级信息颜色。--accent#e4572e (亮橙)#3A5F45 (Bamboo Green)核心主色。深竹青色，稳重且优雅。--accent-hoverN/A#2A4533 (Deep Green)悬停状态的深色。--border浅色透明#E5E5E5极细的、几乎不可见的分割线。1.2 排版系统 (Typography)标题 (Headings): 引入衬线字体 (Serif) 如 Noto Serif SC 或系统自带的宋体/明体，增加文学感。正文 (Body): 使用干净的无衬线字体 (Sans-serif) 如 Inter, -apple-system, PingFang SC，确保功能性文字（如进度、日志）的易读性。1.3 界面布局 (Layout)去噪 (De-noise): 移除 .ambient, .glow, .grid 等背景装饰元素，回归纯净背景。容器 (Container): 缩小最大宽度 (e.g., 720px 或 800px)，增加垂直间距，让视线更聚焦。卡片 (Cards): 移除厚重的阴影 (box-shadow)，改用极淡的阴影或仅用边框 (1px solid #eee) 来区分区块。输入框与按钮: 从“圆角胶囊”改为“微圆角矩形” (Radius: 6px - 8px)，显得更严谨、商务。2. 功能与代码升级方案虽然重点是 UI，但在重构时建议同步优化以下代码逻辑：2.1 templates/index.html (结构语义化)引入 Google Fonts (可选) 或定义更好的 font-family 栈。简化 DOM 结构，去除用于装饰的空 div。增加 <meta name="theme-color" content="#fafaf9"> 以适配浏览器标题栏颜色。2.2 static/style.css (完全重写)使用 CSS Variables 定义新的设计系统。引入 ::selection 伪类，定制文字选中颜色（如淡绿色背景，墨色文字）。优化移动端适配，确保在手机上输入框和按钮不会过小。2.3 static/app.js (交互微调)Loading 状态: 按钮点击后变灰并显示 Loading Spinner，而不是简单的文字变化。进度条动画: 使用 CSS transition 让进度条变化更丝滑。3. 实现指南 (Implementation Guide)以下是根据新风格生成的关键代码片段。你可以直接替换原有文件内容。3.1 升级版 style.css (千竹风格)CSS:root {
  /* 调色板 - Qianzhu Inspired */
  --bg-body: #fafaf9;        /* 暖调纸白 */
  --bg-card: #ffffff;        /* 纯白 */
  --ink-primary: #333333;    /* 墨黑 */
  --ink-secondary: #666666;  /* 石灰 */
  --ink-tertiary: #999999;   /* 浅灰 */
  
  --accent: #2f5c3e;         /* 竹青 */
  --accent-light: #e8f5e9;   /* 极淡绿背景 */
  --accent-hover: #1e3b28;   /* 深竹青 */
  
  --border: #ebebeb;         /* 极淡边框 */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.03);
  
  --radius: 8px;             /* 微圆角 */
  --font-serif: "Noto Serif SC", "Songti SC", serif;
  --font-sans: "Inter", -apple-system, BlinkMacSystemFont, "PingFang SC", "Segoe UI", sans-serif;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  font-family: var(--font-sans);
  color: var(--ink-primary);
  background-color: var(--bg-body);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

/* 页面容器 */
.shell {
  max-width: 680px; /* 更窄，更聚焦 */
  margin: 0 auto;
  padding: 60px 20px 100px;
  display: flex;
  flex-direction: column;
  gap: 40px;
}

/* 头部设计 */
.header {
  text-align: center;
  margin-bottom: 20px;
}

.header h1 {
  font-family: var(--font-serif);
  font-weight: 700;
  font-size: 2.2rem;
  margin: 0 0 10px;
  color: var(--ink-primary);
  letter-spacing: -0.02em;
}

.eyebrow {
  font-size: 0.85rem;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-weight: 600;
  margin-bottom: 8px;
  display: block;
}

.header-meta {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 16px;
}

.badge {
  font-size: 12px;
  padding: 4px 10px;
  background: var(--border);
  color: var(--ink-secondary);
  border-radius: 999px;
}

/* 卡片通用样式 */
.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 32px;
  box-shadow: var(--shadow-sm);
  transition: box-shadow 0.3s ease;
}

.card:hover {
  box-shadow: var(--shadow-md);
}

.card-title h2 {
  font-family: var(--font-serif);
  font-size: 1.25rem;
  margin: 0 0 8px;
  color: var(--ink-primary);
}

.card-title p {
  font-size: 0.9rem;
  color: var(--ink-secondary);
  margin: 0;
}

/* 表单元素 */
form {
  margin-top: 24px;
  display: grid;
  gap: 20px;
}

.field {
  display: grid;
  gap: 8px;
}

.field span {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--ink-secondary);
}

input[type="text"],
input[type="url"],
select {
  width: 100%;
  padding: 12px;
  font-size: 1rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: #fff;
  color: var(--ink-primary);
  transition: border-color 0.2s, box-shadow 0.2s;
  font-family: var(--font-sans);
}

input:focus,
select:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-light);
}

/* 按钮 */
.actions {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}

button {
  padding: 12px 24px;
  font-size: 0.95rem;
  font-weight: 500;
  border-radius: var(--radius);
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: var(--font-sans);
}

button[type="submit"] {
  background-color: var(--accent);
  color: white;
  border: 1px solid var(--accent);
}

button[type="submit"]:hover {
  background-color: var(--accent-hover);
  border-color: var(--accent-hover);
}

button[type="submit"]:disabled {
  background-color: var(--ink-tertiary);
  border-color: var(--ink-tertiary);
  cursor: not-allowed;
}

button.ghost {
  background: transparent;
  color: var(--ink-secondary);
  border: 1px solid var(--border);
}

button.ghost:hover {
  border-color: var(--ink-secondary);
  color: var(--ink-primary);
}

/* 状态与日志 */
.progress-wrap {
  height: 6px; /* 更细 */
  background: var(--border);
  border-radius: 999px;
  overflow: hidden;
  margin-top: 8px;
}

.progress-bar {
  height: 100%;
  background: var(--accent);
  width: 0%;
  transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.logs {
  background: #fcfcfc;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px;
  font-family: "JetBrains Mono", "Menlo", monospace;
  font-size: 0.8rem;
  color: var(--ink-secondary);
}

pre {
  margin: 0;
  white-space: pre-wrap;
  max-height: 200px;
  overflow-y: auto;
}

/* 文件列表 */
.files-list {
  display: grid;
  gap: 1px; /* 细线分隔风格 */
  background: var(--border); /* 用于生成分割线 */
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
}

.file-item {
  background: white;
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.file-name {
  font-weight: 500;
  color: var(--ink-primary);
  margin-bottom: 4px;
}

.file-details {
  font-size: 0.8rem;
  color: var(--ink-tertiary);
}

.file-item a {
  color: var(--accent);
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 500;
  padding: 6px 12px;
  background: var(--accent-light);
  border-radius: 4px;
  transition: background 0.2s;
}

.file-item a:hover {
  background: #dceddd; /* 稍深一点的绿 */
}

/* 移动端适配 */
@media (max-width: 600px) {
  .shell { padding: 40px 16px; }
  .card { padding: 24px; }
}
3.2 升级版 index.html (精简结构)需要移除 .ambient, .glow 等 div，并使用更语义化的标签。HTML<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
    <meta name="theme-color" content="#fafaf9">
    <title>{{ app_title }}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}" />
  </head>
  <body>
    <main class="shell">
      <header class="header">
        <span class="eyebrow">Video Downloader</span>
        <h1>{{ app_title }}</h1>
        <div class="header-meta">
          <div class="badge">v2.0</div>
          <div class="badge">Docker Ready</div>
        </div>
      </header>

      <section class="card">
        <div class="card-title">
          <h2>新建任务</h2>
          <p>输入视频链接，选择格式后开始下载。</p>
        </div>
        <form id="download-form">
          <div class="field">
            <span>视频链接 (URL)</span>
            <input
              type="url"
              name="url"
              id="url"
              placeholder="例如: https://www.youtube.com/watch?v=..."
              required
              autocomplete="off"
            />
          </div>

          <div class="field">
            <span>格式选择</span>
            <select name="preset" id="preset"></select>
          </div>
          
          <div class="field">
             <label class="checkbox" style="display:flex; gap:8px; align-items:center; font-size:0.9rem; color:var(--ink-secondary);">
              <input type="checkbox" id="use-cookies" />
              <span>使用 Cookies (防止 403 错误)</span>
            </label>
             <span id="cookie-hint" style="font-size:0.8rem; color:var(--ink-tertiary); margin-left: 24px;"></span>
          </div>

          <div class="actions">
            <button type="submit" id="start-btn">开始下载</button>
            <button type="button" class="ghost" id="clear-btn">清空</button>
          </div>
        </form>
      </section>

      <section class="card status-card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
          <div class="card-title" style="margin:0;">
            <h2>任务状态</h2>
          </div>
          <span id="status-text" style="color:var(--accent); font-weight:500; font-size:0.9rem;">空闲</span>
        </div>
        
        <div class="progress-wrap">
          <div class="progress-bar" id="progress-bar"></div>
        </div>
        
        <div style="margin-top:20px;">
           <div style="display:flex; justify-content:space-between; margin-bottom:8px; font-size:0.8rem; color:var(--ink-tertiary);">
             <span>运行日志</span>
             <span id="clear-log" style="cursor:pointer; color:var(--ink-secondary);">清除</span>
           </div>
           <div class="logs">
             <pre id="log-box"></pre>
           </div>
        </div>
      </section>

      <section class="card">
        <div class="card-title" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
          <h2>已下载文件</h2>
          <button type="button" class="ghost" id="refresh-files" style="padding:6px 12px; font-size:0.8rem;">刷新列表</button>
        </div>
        <div id="files-list" class="files-list"></div>
      </section>
    </main>

    <script>
      window.APP_CONFIG = {{ config_json | safe }};
    </script>
    <script src="{{ url_for('static', filename='app.js') }}"></script>
  </body>
</html>
这个升级方案完全改变了工具的气质，从“极客工具”变成了“优雅的产品”，非常符合千竹博客那种注重内容与阅读体验的风格。CSS Grid for UI Layouts这个视频介绍了现代 CSS Grid 布局，虽然本方案主要用了 Flexbox 和简单的 Grid，但了解 Grid 对于构建这种极简、对齐精确的卡片式布局非常有帮助，能帮你进一步微调间距和结构。