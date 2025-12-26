import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, send_from_directory

try:
    import yt_dlp
except ImportError as exc:
    raise SystemExit("yt-dlp is not installed. Run: pip install yt-dlp") from exc

APP_TITLE = "Local Video Downloader"
DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", "/downloads")
COOKIES_PATH = os.environ.get("COOKIES_PATH", "")
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))
MAX_LOGS = 600

FORMAT_PRESETS = {
    "Video (Best MP4)": {
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
    },
    "Video (1080p MP4)": {
        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
        "merge_output_format": "mp4",
    },
    "Video (720p MP4)": {
        "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "merge_output_format": "mp4",
    },
    "Audio (MP3)": {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    },
    "Audio (M4A)": {
        "format": "bestaudio[ext=m4a]/bestaudio",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
            }
        ],
    },
}


@dataclass
class Job:
    job_id: str
    url: str
    preset: str
    use_cookies: bool
    created_at: float = field(default_factory=time.time)
    progress: float = 0.0
    status: str = "Queued"
    done: bool = False
    success: bool = False
    error: str | None = None
    logs: list[str] = field(default_factory=list)
    log_offset: int = 0
    last_log_time: float = 0.0
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)


app = Flask(__name__)
jobs: dict[str, Job] = {}
jobs_lock = threading.Lock()


def log_job(job: Job, message: str) -> None:
    with job.lock:
        job.logs.append(message)
        if len(job.logs) > MAX_LOGS:
            removed = len(job.logs) - MAX_LOGS
            job.logs = job.logs[removed:]
            job.log_offset += removed


class JobLogger:
    def __init__(self, job: Job):
        self.job = job

    def debug(self, msg):
        log_job(self.job, str(msg))

    def info(self, msg):
        log_job(self.job, str(msg))

    def warning(self, msg):
        log_job(self.job, f"WARNING: {msg}")

    def error(self, msg):
        log_job(self.job, f"ERROR: {msg}")


def build_options(job: Job) -> dict:
    preset = FORMAT_PRESETS[job.preset]
    options = {
        "format": preset["format"],
        "outtmpl": str(Path(DOWNLOAD_DIR) / "%(title)s.%(ext)s"),
        "logger": JobLogger(job),
        "progress_hooks": [make_progress_hook(job)],
        "postprocessor_hooks": [make_postprocessor_hook(job)],
        "quiet": True,
        "no_warnings": False,
    }
    if preset.get("merge_output_format"):
        options["merge_output_format"] = preset["merge_output_format"]
    if preset.get("postprocessors"):
        options["postprocessors"] = preset["postprocessors"]
    if job.use_cookies and COOKIES_PATH and Path(COOKIES_PATH).is_file():
        options["cookiefile"] = COOKIES_PATH
    return options


def make_progress_hook(job: Job):
    def hook(data):
        status = data.get("status")
        if status == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            downloaded = data.get("downloaded_bytes")
            if total and downloaded:
                with job.lock:
                    job.progress = downloaded / total * 100

            percent = (data.get("_percent_str") or "").strip()
            speed = (data.get("_speed_str") or "").strip()
            eta = (data.get("_eta_str") or "").strip()
            parts = []
            if percent:
                parts.append(percent)
            if speed:
                parts.append(f"at {speed}")
            if eta:
                parts.append(f"ETA {eta}")
            status_line = " ".join(parts)
            if status_line:
                with job.lock:
                    job.status = status_line

            now = time.monotonic()
            should_log = False
            with job.lock:
                if now - job.last_log_time > 1.0:
                    job.last_log_time = now
                    should_log = True
            if should_log and percent:
                log_job(job, f"Downloading: {status_line}")
        elif status == "finished":
            with job.lock:
                job.status = "Processing..."
            log_job(job, "Download finished, processing...")

    return hook


def make_postprocessor_hook(job: Job):
    def hook(data):
        if data.get("status") == "started":
            with job.lock:
                job.status = "Post-processing..."
        elif data.get("status") == "finished":
            with job.lock:
                job.status = "Finalizing..."

    return hook


def get_job(job_id: str) -> Job | None:
    with jobs_lock:
        return jobs.get(job_id)


def download_worker(job_id: str) -> None:
    job = get_job(job_id)
    if not job:
        return

    with job.lock:
        job.status = "Starting..."

    try:
        Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        with job.lock:
            job.done = True
            job.success = False
            job.status = "Failed"
            job.error = str(exc)
        log_job(job, f"ERROR: {exc}")
        return
    log_job(job, f"Preset: {job.preset}")
    log_job(job, f"Saving to: {DOWNLOAD_DIR}")
    if job.use_cookies and not (COOKIES_PATH and Path(COOKIES_PATH).is_file()):
        log_job(job, "WARNING: Cookies enabled but COOKIES_PATH is missing.")

    try:
        options = build_options(job)
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([job.url])
        with job.lock:
            job.progress = 100
            job.status = "Done"
            job.done = True
            job.success = True
        log_job(job, "Download complete.")
    except Exception as exc:
        with job.lock:
            job.done = True
            job.success = False
            job.status = "Failed"
            job.error = str(exc)
        log_job(job, f"ERROR: {exc}")


def list_downloads() -> list[dict]:
    base = Path(DOWNLOAD_DIR)
    if not base.exists():
        return []
    files = []
    for item in base.iterdir():
        if item.is_file():
            stat = item.stat()
            files.append(
                {
                    "name": item.name,
                    "size": stat.st_size,
                    "mtime": stat.st_mtime,
                }
            )
    files.sort(key=lambda x: x["mtime"], reverse=True)
    return files


@app.route("/")
def index():
    config = {
        "presets": list(FORMAT_PRESETS.keys()),
        "defaultPreset": list(FORMAT_PRESETS.keys())[0],
        "downloadDir": DOWNLOAD_DIR,
        "cookiesAvailable": bool(COOKIES_PATH and Path(COOKIES_PATH).is_file()),
        "cookiesPath": COOKIES_PATH,
    }
    return render_template(
        "index.html",
        app_title=APP_TITLE,
        config_json=json.dumps(config),
    )


@app.route("/api/start", methods=["POST"])
def api_start():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    preset = (data.get("preset") or "").strip()
    use_cookies = bool(data.get("use_cookies"))

    if not url:
        return jsonify({"error": "URL is required."}), 400
    if preset not in FORMAT_PRESETS:
        return jsonify({"error": "Invalid preset."}), 400

    job_id = uuid.uuid4().hex
    job = Job(job_id=job_id, url=url, preset=preset, use_cookies=use_cookies)
    with jobs_lock:
        jobs[job_id] = job

    thread = threading.Thread(target=download_worker, args=(job_id,), daemon=True)
    thread.start()
    return jsonify({"job_id": job_id})


@app.route("/api/status/<job_id>")
def api_status(job_id: str):
    job = get_job(job_id)
    if not job:
        abort(404)

    after_raw = request.args.get("after", "0")
    try:
        after = max(0, int(after_raw))
    except ValueError:
        after = 0

    with job.lock:
        start = max(0, after - job.log_offset)
        logs = job.logs[start:]
        next_index = job.log_offset + len(job.logs)
        payload = {
            "job_id": job.job_id,
            "progress": round(job.progress, 2),
            "status": job.status,
            "done": job.done,
            "success": job.success,
            "error": job.error,
            "logs": logs,
            "next": next_index,
        }
    return jsonify(payload)


@app.route("/api/files")
def api_files():
    return jsonify({"files": list_downloads()})


@app.route("/download/<path:filename>")
def download_file(filename: str):
    base = Path(DOWNLOAD_DIR)
    target = base / filename
    if not target.exists() or not target.is_file():
        abort(404)
    return send_from_directory(base, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=False, threaded=True)
