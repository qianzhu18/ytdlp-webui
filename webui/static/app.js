const config = window.APP_CONFIG || {};

const form = document.getElementById("download-form");
const urlInput = document.getElementById("url");
const presetSelect = document.getElementById("preset");
const startButton = document.getElementById("start-btn");
const clearButton = document.getElementById("clear-btn");
const taskListEl = document.getElementById("task-list");
const filesListEl = document.getElementById("files-list");
const refreshFilesBtn = document.getElementById("refresh-files");

let pollTimer = null;

function init() {
  const presets = config.presets || [];
  presets.forEach((preset) => {
    const option = document.createElement("option");
    option.value = preset;
    option.textContent = preset;
    presetSelect.appendChild(option);
  });
  if (config.defaultPreset) presetSelect.value = config.defaultPreset;

  startPolling();
  refreshFiles();
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const rawUrls = urlInput.value.trim();
  if (!rawUrls) return;

  const originalText = startButton.textContent;
  startButton.disabled = true;
  startButton.textContent = "提交中...";

  try {
    const res = await fetch("/api/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: rawUrls,
        preset: presetSelect.value,
        use_cookies: document.getElementById("use-cookies")?.checked || false,
      }),
    });

    if (res.ok) {
      urlInput.value = "";
      pollTasks();
    } else {
      alert("提交失败，请检查网络或输入");
    }
  } catch (error) {
    console.error(error);
    alert("网络错误");
  } finally {
    startButton.disabled = false;
    startButton.textContent = originalText;
  }
});

async function pollTasks() {
  try {
    const res = await fetch("/api/tasks");
    if (!res.ok) return;
    const data = await res.json();
    renderTasks(data.tasks || []);
  } catch (error) {
    console.warn("Poll failed", error);
  }
}

function renderTasks(tasks) {
  if (tasks.length === 0) {
    taskListEl.innerHTML =
      '<div style="text-align:center; color:#999; padding:20px; font-size:0.9rem;">暂无活动任务</div>';
    return;
  }

  taskListEl.innerHTML = tasks
    .map((task) => {
      const isError = task.status === "Failed";
      const isDone = task.done && task.success;

      let statusColor = "var(--accent)";
      if (isError) statusColor = "#d32f2f";
      if (isDone) statusColor = "#999";

      const progressStyle = `
      width: ${task.progress}%; 
      background-color: ${isError ? "#ef5350" : "var(--accent)"};
      opacity: ${isDone ? "0.5" : "1"};
    `;

      return `
      <li class="task-item" style="padding: 12px; border-bottom: 1px solid var(--border); position: relative;">
        <div style="display:flex; justify-content:space-between; margin-bottom: 6px;">
          <div style="font-weight:500; font-size:0.9rem; max-width:70%; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${
            task.title || task.url
          }">
            ${task.title || task.url}
          </div>
          <div style="font-size:0.8rem; color:${statusColor}; font-family:monospace;">
            ${task.status}
          </div>
        </div>
        <div style="height:4px; background:#f0f0f0; border-radius:2px; overflow:hidden;">
          <div style="height:100%; transition: width 0.3s; ${progressStyle}"></div>
        </div>
        ${
          isError
            ? `<div style="font-size:0.75rem; color:#d32f2f; margin-top:4px;">${task.error}</div>`
            : ""
        }
      </li>
    `;
    })
    .join("");
}

function startPolling() {
  pollTasks();
  pollTimer = setInterval(pollTasks, 2000);
}

function formatBytes(bytes) {
  if (bytes === 0) return "0 B";
  const unitBase = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const index = Math.floor(Math.log(bytes) / Math.log(unitBase));
  return (
    parseFloat((bytes / Math.pow(unitBase, index)).toFixed(2)) +
    " " +
    sizes[index]
  );
}

async function refreshFiles() {
  try {
    const res = await fetch("/api/files");
    const data = await res.json();
    renderFiles(data.files || []);
  } catch (error) {
    console.error(error);
  }
}

function renderFiles(files) {
  if (files.length === 0) {
    filesListEl.innerHTML =
      '<div style="padding:16px; text-align:center; color:#999; font-size:0.9rem;">下载目录为空</div>';
    return;
  }
  filesListEl.innerHTML = files
    .map(
      (file) => `
    <div class="file-item" style="padding:12px; background:var(--bg-page); border-radius:6px; display:flex; justify-content:space-between; align-items:center;">
      <div style="overflow:hidden;">
        <div style="font-weight:500; font-size:0.9rem; margin-bottom:2px;">${file.name}</div>
        <div style="font-size:0.75rem; color:#999;">${formatBytes(file.size)}</div>
      </div>
      <a href="/download/${encodeURIComponent(
        file.name
      )}" download style="color:var(--accent); text-decoration:none; font-size:0.85rem; padding:4px 8px; border:1px solid var(--border); border-radius:4px;">下载</a>
    </div>
  `
    )
    .join("");
}

if (refreshFilesBtn) refreshFilesBtn.addEventListener("click", refreshFiles);
if (clearButton) {
  clearButton.addEventListener("click", () => {
    urlInput.value = "";
    urlInput.focus();
  });
}

init();
