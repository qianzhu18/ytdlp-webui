import json
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
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
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "2"))
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))

FORMAT_PRESETS = {
    "Video (Best MP4)": {
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
    },
    "Video (4K/High Res)": {
        "format": "bestvideo[height>1080]+bestaudio/best",
        "merge_output_format": "mp4",
    },
    "Video (1080p MP4)": {
        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
        "merge_output_format": "mp4",
    },
    "Audio (MP3 Best)": {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
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
    title: str | None = None
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)


app = Flask(__name__)
jobs: dict[str, Job] = {}
jobs_lock = threading.Lock()
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)


class JobLogger:
    def __init__(self, job: Job):
        self.job = job

    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(f"[{self.job.job_id}] Error: {msg}")


def make_progress_hook(job: Job):
    def hook(data):
        if data["status"] == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            downloaded = data.get("downloaded_bytes")

            with job.lock:
                if total and downloaded:
                    job.progress = (downloaded / total) * 100

                if not job.title and data.get("info_dict"):
                    job.title = data["info_dict"].get("title")

                percent = data.get("_percent_str", "").strip()
                speed = data.get("_speed_str", "").strip()
                job.status = f"Downloading {percent} ({speed})"

        elif data["status"] == "finished":
            with job.lock:
                job.progress = 100
                job.status = "Processing..."

    return hook


def download_task(job_id: str):
    job = jobs.get(job_id)
    if not job:
        return

    with job.lock:
        job.status = "Starting..."

    preset_conf = FORMAT_PRESETS.get(job.preset, FORMAT_PRESETS["Video (Best MP4)"])
    options = {
        "format": preset_conf["format"],
        "outtmpl": str(Path(DOWNLOAD_DIR) / "%(title)s.%(ext)s"),
        "logger": JobLogger(job),
        "progress_hooks": [make_progress_hook(job)],
        "ignoreerrors": True,
        "no_warnings": True,
    }

    if preset_conf.get("merge_output_format"):
        options["merge_output_format"] = preset_conf["merge_output_format"]
    if preset_conf.get("postprocessors"):
        options["postprocessors"] = preset_conf["postprocessors"]

    if job.use_cookies and COOKIES_PATH and Path(COOKIES_PATH).is_file():
        options["cookiefile"] = COOKIES_PATH

    try:
        Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)
        with yt_dlp.YoutubeDL(options) as ydl:
            try:
                info = ydl.extract_info(job.url, download=False)
                with job.lock:
                    job.title = info.get("title", "Unknown Title")
            except Exception:
                pass

            ydl.download([job.url])

        with job.lock:
            job.status = "Completed"
            job.done = True
            job.success = True
            job.progress = 100
    except Exception as exc:
        with job.lock:
            job.status = "Failed"
            job.done = True
            job.success = False
            job.error = str(exc)


@app.route("/")
def index():
    config = {
        "presets": list(FORMAT_PRESETS.keys()),
        "defaultPreset": list(FORMAT_PRESETS.keys())[0],
    }
    return render_template("index.html", app_title=APP_TITLE, config_json=json.dumps(config))


@app.route("/api/start", methods=["POST"])
def api_start():
    data = request.get_json(silent=True) or {}
    raw_urls = data.get("url", "")
    preset = data.get("preset", "")
    use_cookies = bool(data.get("use_cookies"))

    url_list = [line.strip() for line in raw_urls.splitlines() if line.strip()]

    if not url_list:
        return jsonify({"error": "No URL provided"}), 400

    created_ids = []
    with jobs_lock:
        for url in url_list:
            job_id = uuid.uuid4().hex
            job = Job(job_id=job_id, url=url, preset=preset, use_cookies=use_cookies)
            jobs[job_id] = job
            executor.submit(download_task, job_id)
            created_ids.append(job_id)

    return jsonify({"message": "Tasks started", "count": len(created_ids)})


@app.route("/api/tasks")
def api_tasks():
    with jobs_lock:
        all_jobs = sorted(jobs.values(), key=lambda x: x.created_at, reverse=True)[:50]

        task_list = []
        for job in all_jobs:
            task_list.append(
                {
                    "id": job.job_id,
                    "url": job.url,
                    "title": job.title or job.url,
                    "status": job.status,
                    "progress": round(job.progress, 1),
                    "done": job.done,
                    "success": job.success,
                    "error": job.error,
                }
            )

    return jsonify({"tasks": task_list})


@app.route("/api/files")
def api_files():
    base = Path(DOWNLOAD_DIR)
    if not base.exists():
        return jsonify({"files": []})

    files = []
    for item in base.iterdir():
        if item.is_file() and not item.name.startswith("."):
            stat = item.stat()
            files.append({"name": item.name, "size": stat.st_size, "mtime": stat.st_mtime})
    files.sort(key=lambda x: x["mtime"], reverse=True)
    return jsonify({"files": files})


@app.route("/download/<path:filename>")
def download_file(filename):
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, threaded=True)
