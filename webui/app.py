import json
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

try:
    import yt_dlp
except ImportError as exc:
    raise SystemExit("yt-dlp is not installed.") from exc

APP_TITLE = "Zen Downloader"
DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", "/downloads")
COOKIES_PATH = os.environ.get("COOKIES_PATH", "")
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "2"))
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))

FORMAT_PRESETS = {
    "Best Video (MP4)": {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
    },
    "Best Audio (MP3)": {
        "format": "bestaudio/best",
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}],
    },
    "4K / High Res": {
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
    },
}


@dataclass
class Job:
    job_id: str
    url: str
    preset: str
    use_cookies: bool
    created_at: float = field(default_factory=time.time)
    title: str = "Fetching info..."
    status: str = "Queued"
    progress: float = 0.0
    done: bool = False
    error: str | None = None
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)


app = Flask(__name__)
jobs: dict[str, Job] = {}
jobs_lock = threading.Lock()
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)


def progress_hook(job):
    def hook(data):
        if data["status"] == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            downloaded = data.get("downloaded_bytes")
            with job.lock:
                if total:
                    job.progress = (downloaded / total) * 100
                job.status = data.get("_percent_str", "0%").strip() + " " + data.get(
                    "_speed_str", ""
                ).strip()
                if data.get("info_dict"):
                    job.title = data["info_dict"].get("title", job.title)
        elif data["status"] == "finished":
            with job.lock:
                job.progress = 100
                job.status = "Processing..."

    return hook


def worker(job_id):
    job = jobs.get(job_id)
    if not job:
        return

    with job.lock:
        job.status = "Starting..."

    preset_conf = FORMAT_PRESETS[job.preset]
    options = {
        "format": preset_conf["format"],
        "outtmpl": str(Path(DOWNLOAD_DIR) / "%(title)s.%(ext)s"),
        "progress_hooks": [progress_hook(job)],
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
    }

    if "merge_output_format" in preset_conf:
        options["merge_output_format"] = preset_conf["merge_output_format"]
    if "postprocessors" in preset_conf:
        options["postprocessors"] = preset_conf["postprocessors"]
    if job.use_cookies and COOKIES_PATH:
        options["cookiefile"] = COOKIES_PATH

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            try:
                info = ydl.extract_info(job.url, download=False)
                with job.lock:
                    job.title = info.get("title", job.url)
            except Exception:
                pass

            ydl.download([job.url])

        with job.lock:
            job.done = True
            job.status = "Done"
            job.progress = 100
    except Exception as exc:
        with job.lock:
            job.done = True
            job.status = "Failed"
            job.error = str(exc)


@app.route("/")
def index():
    config = {
        "presets": list(FORMAT_PRESETS.keys()),
        "defaultPreset": "Best Video (MP4)",
    }
    return render_template("index.html", app_title=APP_TITLE, config_json=json.dumps(config))


@app.route("/api/start", methods=["POST"])
def start():
    data = request.json or {}
    urls = [u.strip() for u in data.get("url", "").splitlines() if u.strip()]
    if not urls:
        return jsonify({"error": "No URL"}), 400

    added = 0
    with jobs_lock:
        for url in urls:
            job_id = uuid.uuid4().hex
            job = Job(job_id, url, data.get("preset"), data.get("use_cookies"))
            jobs[job_id] = job
            executor.submit(worker, job_id)
            added += 1
    return jsonify({"count": added})


@app.route("/api/tasks")
def tasks():
    with jobs_lock:
        tasks_list = []
        for job in sorted(jobs.values(), key=lambda x: x.created_at, reverse=True)[:20]:
            tasks_list.append(
                {
                    "id": job.job_id,
                    "title": job.title,
                    "status": job.status,
                    "progress": round(job.progress),
                    "done": job.done,
                    "error": job.error,
                }
            )
    return jsonify({"tasks": tasks_list})


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, threaded=True)
