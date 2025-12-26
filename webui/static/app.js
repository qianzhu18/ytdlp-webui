const config = window.APP_CONFIG || {};

const form = document.getElementById("download-form");
const urlInput = document.getElementById("url");
const presetSelect = document.getElementById("preset");
const downloadDirEl = document.getElementById("download-dir");
const useCookiesInput = document.getElementById("use-cookies");
const cookieHint = document.getElementById("cookie-hint");
const startButton = document.getElementById("start-btn");
const clearButton = document.getElementById("clear-btn");
const statusText = document.getElementById("status-text");
const progressBar = document.getElementById("progress-bar");
const logBox = document.getElementById("log-box");
const clearLogButton = document.getElementById("clear-log");
const filesList = document.getElementById("files-list");
const refreshFilesButton = document.getElementById("refresh-files");

let activeJobId = null;
let logIndex = 0;
let pollTimer = null;

function initForm() {
  const presets = config.presets || [];
  presets.forEach((preset) => {
    const option = document.createElement("option");
    option.value = preset;
    option.textContent = preset;
    presetSelect.appendChild(option);
  });
  if (config.defaultPreset) {
    presetSelect.value = config.defaultPreset;
  }
  downloadDirEl.textContent = config.downloadDir || "/downloads";

  if (!config.cookiesAvailable) {
    useCookiesInput.checked = false;
    useCookiesInput.disabled = true;
    cookieHint.textContent = "未挂载 cookies.txt，可通过 COOKIES_PATH 启用。";
  } else {
    cookieHint.textContent = `使用 Cookies: ${config.cookiesPath}`;
  }
}

function setStatus(text) {
  statusText.textContent = text || "空闲";
}

function setProgress(percent) {
  const safeValue = Math.max(0, Math.min(100, percent || 0));
  progressBar.style.width = `${safeValue}%`;
}

function appendLogs(lines) {
  if (!lines || lines.length === 0) {
    return;
  }
  const content = lines.join("\n") + "\n";
  logBox.textContent += content;
  logBox.scrollTop = logBox.scrollHeight;
}

function resetLogs() {
  logBox.textContent = "";
}

function setRunningState(running) {
  startButton.disabled = running;
  startButton.classList.toggle("is-loading", running);
  urlInput.disabled = running;
  presetSelect.disabled = running;
  useCookiesInput.disabled = running || !config.cookiesAvailable;
}

async function startDownload(payload) {
  const response = await fetch("/api/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Failed to start download.");
  }
  return data.job_id;
}

async function pollStatus() {
  if (!activeJobId) return;
  const response = await fetch(`/api/status/${activeJobId}?after=${logIndex}`);
  if (!response.ok) {
    setStatus("获取状态失败");
    stopPolling();
    return;
  }
  const data = await response.json();
  setStatus(data.status);
  setProgress(data.progress);
  appendLogs(data.logs || []);
  logIndex = data.next || logIndex;

  if (data.done) {
    stopPolling();
    setRunningState(false);
    if (data.success) {
      setStatus("完成");
      refreshFiles();
    } else {
      setStatus("失败");
      if (data.error) {
        appendLogs([`ERROR: ${data.error}`]);
      }
    }
  }
}

function startPolling(jobId) {
  activeJobId = jobId;
  logIndex = 0;
  setRunningState(true);
  pollStatus();
  pollTimer = setInterval(pollStatus, 1000);
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
  activeJobId = null;
}

function formatBytes(bytes) {
  if (!bytes && bytes !== 0) return "-";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(1)} ${units[unit]}`;
}

function formatDate(timestamp) {
  if (!timestamp) return "-";
  const date = new Date(timestamp * 1000);
  return date.toLocaleString();
}

function renderFiles(files) {
  if (!files || files.length === 0) {
    filesList.innerHTML =
      '<div class="file-item"><div class="file-meta">暂无文件</div></div>';
    return;
  }
  filesList.innerHTML = "";
  files.forEach((file) => {
    const item = document.createElement("div");
    item.className = "file-item";
    const meta = document.createElement("div");
    meta.className = "file-meta";
    const name = document.createElement("div");
    name.className = "file-name";
    name.textContent = file.name;
    const details = document.createElement("div");
    details.className = "file-details";
    details.textContent = `${formatBytes(file.size)} · ${formatDate(
      file.mtime
    )}`;
    meta.appendChild(name);
    meta.appendChild(details);

    const link = document.createElement("a");
    link.href = `/download/${encodeURIComponent(file.name)}`;
    link.textContent = "下载";
    link.setAttribute("download", file.name);

    item.appendChild(meta);
    item.appendChild(link);
    filesList.appendChild(item);
  });
}

async function refreshFiles() {
  const response = await fetch("/api/files");
  if (!response.ok) {
    return;
  }
  const data = await response.json();
  renderFiles(data.files || []);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (activeJobId) return;
  const url = urlInput.value.trim();
  if (!url) {
    setStatus("请输入链接");
    return;
  }
  resetLogs();
  setProgress(0);
  setStatus("准备开始...");
  try {
    const jobId = await startDownload({
      url,
      preset: presetSelect.value,
      use_cookies: useCookiesInput.checked,
    });
    startPolling(jobId);
  } catch (error) {
    setStatus(error.message || "启动失败");
  }
});

clearButton.addEventListener("click", () => {
  urlInput.value = "";
  urlInput.focus();
});

clearLogButton.addEventListener("click", () => {
  resetLogs();
});

refreshFilesButton.addEventListener("click", () => {
  refreshFiles();
});

initForm();
refreshFiles();
