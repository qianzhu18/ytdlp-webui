import os
import queue
import shutil
import subprocess
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

try:
    import yt_dlp
except ImportError as exc:
    raise SystemExit("yt-dlp is not installed. Run: pip3 install yt-dlp") from exc

APP_TITLE = "Mac YouTube Downloader"
DEFAULT_PRESET = "Video (Best MP4)"

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


class QueueLogger:
    def __init__(self, log_queue):
        self.log_queue = log_queue

    def debug(self, msg):
        self._log(msg)

    def info(self, msg):
        self._log(msg)

    def warning(self, msg):
        self._log(f"WARNING: {msg}")

    def error(self, msg):
        self._log(f"ERROR: {msg}")

    def _log(self, msg):
        self.log_queue.put(("log", str(msg)))


def build_ui():
    root = tk.Tk()
    root.title(APP_TITLE)
    root.minsize(760, 560)

    main = ttk.Frame(root, padding=12)
    main.grid(row=0, column=0, sticky="nsew")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    main.columnconfigure(0, weight=1)

    url_var = tk.StringVar()
    preset_var = tk.StringVar(value=DEFAULT_PRESET)
    download_dir_var = tk.StringVar(value=os.path.expanduser("~/Downloads"))
    cookie_var = tk.BooleanVar(value=True)

    ttk.Label(main, text="Video URL").grid(row=0, column=0, sticky="w")
    url_entry = ttk.Entry(main, textvariable=url_var)
    url_entry.grid(row=1, column=0, sticky="ew")
    paste_button = ttk.Button(main, text="Paste")
    paste_button.grid(row=1, column=1, padx=(8, 0))
    clear_url_button = ttk.Button(main, text="Clear")
    clear_url_button.grid(row=1, column=2, padx=(8, 0))

    type_frame = ttk.Frame(main)
    type_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(10, 0))
    type_frame.columnconfigure(1, weight=1)
    ttk.Label(type_frame, text="Download type").grid(row=0, column=0, sticky="w")
    preset_combo = ttk.Combobox(
        type_frame,
        textvariable=preset_var,
        values=list(FORMAT_PRESETS.keys()),
        state="readonly",
    )
    preset_combo.grid(row=0, column=1, sticky="ew", padx=(8, 0))

    folder_frame = ttk.Frame(main)
    folder_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(10, 0))
    folder_frame.columnconfigure(1, weight=1)
    ttk.Label(folder_frame, text="Save to").grid(row=0, column=0, sticky="w")
    dir_entry = ttk.Entry(folder_frame, textvariable=download_dir_var)
    dir_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0))
    browse_button = ttk.Button(folder_frame, text="Browse")
    browse_button.grid(row=0, column=2, padx=(8, 0))
    open_button = ttk.Button(folder_frame, text="Open")
    open_button.grid(row=0, column=3, padx=(8, 0))

    cookie_check = ttk.Checkbutton(
        main,
        text="Read Chrome Cookies (avoid 403/limits)",
        variable=cookie_var,
    )
    cookie_check.grid(row=4, column=0, columnspan=3, sticky="w", pady=(8, 0))

    button_frame = ttk.Frame(main)
    button_frame.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(10, 0))
    button_frame.columnconfigure(0, weight=1)
    start_button = ttk.Button(button_frame, text="Start Download")
    start_button.grid(row=0, column=0, sticky="ew")
    clear_log_button = ttk.Button(button_frame, text="Clear Log")
    clear_log_button.grid(row=0, column=1, padx=(8, 0))

    progress_var = tk.DoubleVar(value=0.0)
    status_var = tk.StringVar(value="Idle")
    progress_bar = ttk.Progressbar(main, variable=progress_var, maximum=100)
    progress_bar.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(4, 0))
    status_label = ttk.Label(main, textvariable=status_var)
    status_label.grid(row=7, column=0, columnspan=3, sticky="w")

    log_box = ScrolledText(main, height=14, wrap="word")
    log_box.grid(row=8, column=0, columnspan=3, sticky="nsew", pady=(8, 0))
    main.rowconfigure(8, weight=1)

    url_entry.focus()

    return {
        "root": root,
        "url_var": url_var,
        "preset_var": preset_var,
        "download_dir_var": download_dir_var,
        "cookie_var": cookie_var,
        "url_entry": url_entry,
        "paste_button": paste_button,
        "clear_url_button": clear_url_button,
        "preset_combo": preset_combo,
        "dir_entry": dir_entry,
        "browse_button": browse_button,
        "open_button": open_button,
        "cookie_check": cookie_check,
        "start_button": start_button,
        "clear_log_button": clear_log_button,
        "progress_var": progress_var,
        "status_var": status_var,
        "log_box": log_box,
    }


def main():
    ui = build_ui()
    root = ui["root"]
    url_var = ui["url_var"]
    preset_var = ui["preset_var"]
    download_dir_var = ui["download_dir_var"]
    cookie_var = ui["cookie_var"]
    url_entry = ui["url_entry"]
    paste_button = ui["paste_button"]
    clear_url_button = ui["clear_url_button"]
    preset_combo = ui["preset_combo"]
    dir_entry = ui["dir_entry"]
    browse_button = ui["browse_button"]
    open_button = ui["open_button"]
    cookie_check = ui["cookie_check"]
    start_button = ui["start_button"]
    clear_log_button = ui["clear_log_button"]
    progress_var = ui["progress_var"]
    status_var = ui["status_var"]
    log_box = ui["log_box"]

    log_queue = queue.Queue()
    logger = QueueLogger(log_queue)
    progress_state = {"last_log": 0.0}

    def append_log(message):
        log_box.insert(tk.END, message + "\n")
        log_box.see(tk.END)

    def poll_log_queue():
        try:
            while True:
                kind, payload = log_queue.get_nowait()
                if kind == "log":
                    append_log(payload)
                elif kind == "progress":
                    progress_var.set(payload)
                elif kind == "status":
                    status_var.set(payload)
        except queue.Empty:
            pass
        root.after(100, poll_log_queue)

    def set_ui_state(downloading):
        if downloading:
            start_button.config(state=tk.DISABLED, text="Downloading...")
            url_entry.config(state=tk.DISABLED)
            paste_button.config(state=tk.DISABLED)
            clear_url_button.config(state=tk.DISABLED)
            preset_combo.config(state=tk.DISABLED)
            dir_entry.config(state=tk.DISABLED)
            browse_button.config(state=tk.DISABLED)
            open_button.config(state=tk.DISABLED)
            cookie_check.config(state=tk.DISABLED)
        else:
            start_button.config(state=tk.NORMAL, text="Start Download")
            url_entry.config(state=tk.NORMAL)
            paste_button.config(state=tk.NORMAL)
            clear_url_button.config(state=tk.NORMAL)
            preset_combo.config(state="readonly")
            dir_entry.config(state=tk.NORMAL)
            browse_button.config(state=tk.NORMAL)
            open_button.config(state=tk.NORMAL)
            cookie_check.config(state=tk.NORMAL)

    def check_dependencies():
        if not shutil.which("ffmpeg"):
            log_queue.put(
                ("log", "WARNING: ffmpeg not found. Merging/conversion may fail.")
            )
        if not any(shutil.which(rt) for rt in ("deno", "node", "bun")):
            log_queue.put(
                (
                    "log",
                    "WARNING: No JS runtime found. Install deno or node if needed.",
                )
            )

    def progress_hook(data):
        status = data.get("status")
        if status == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            downloaded = data.get("downloaded_bytes")
            if total and downloaded:
                log_queue.put(("progress", downloaded / total * 100))

            percent = (data.get("_percent_str") or "").strip()
            speed = (data.get("_speed_str") or "").strip()
            eta = (data.get("_eta_str") or "").strip()
            if percent or speed or eta:
                parts = []
                if percent:
                    parts.append(percent)
                if speed:
                    parts.append(f"at {speed}")
                if eta:
                    parts.append(f"ETA {eta}")
                log_queue.put(("status", " ".join(parts)))

            now = time.monotonic()
            if now - progress_state["last_log"] > 1.0:
                if percent:
                    logger.info(f"Downloading: {percent} at {speed}, ETA {eta}".strip())
                progress_state["last_log"] = now
        elif status == "finished":
            log_queue.put(("status", "Processing..."))
            logger.info("Download finished, processing...")

    def postprocessor_hook(data):
        if data.get("status") == "started":
            log_queue.put(("status", "Processing..."))
        elif data.get("status") == "finished":
            log_queue.put(("status", "Post-processing complete"))

    def build_options(download_dir, preset_name, use_cookies):
        preset = FORMAT_PRESETS.get(preset_name, FORMAT_PRESETS[DEFAULT_PRESET])
        options = {
            "format": preset["format"],
            "outtmpl": os.path.join(download_dir, "%(title)s.%(ext)s"),
            "logger": logger,
            "progress_hooks": [progress_hook],
            "postprocessor_hooks": [postprocessor_hook],
            "quiet": True,
            "no_warnings": True,
        }
        if preset.get("merge_output_format"):
            options["merge_output_format"] = preset["merge_output_format"]
        if preset.get("postprocessors"):
            options["postprocessors"] = preset["postprocessors"]
        if use_cookies:
            options["cookiesfrombrowser"] = ("chrome",)
        return options

    def on_download_complete(success, detail):
        set_ui_state(False)
        if success:
            status_var.set("Done")
            messagebox.showinfo("Download complete", detail)
        else:
            status_var.set("Failed")
            messagebox.showerror("Download failed", detail)

    def download_worker(url, use_cookies, preset_name, download_dir):
        try:
            os.makedirs(download_dir, exist_ok=True)
        except OSError as exc:
            root.after(0, lambda: on_download_complete(False, str(exc)))
            return

        options = build_options(download_dir, preset_name, use_cookies)

        try:
            logger.info(f"Preset: {preset_name}")
            logger.info(f"Saving to: {download_dir}")
            with yt_dlp.YoutubeDL(options) as ydl:
                ydl.download([url])
            log_queue.put(("progress", 100))
            root.after(
                0,
                lambda: on_download_complete(True, f"Saved to {download_dir}"),
            )
        except Exception as exc:
            logger.error(str(exc))
            root.after(0, lambda: on_download_complete(False, str(exc)))

    def start_download():
        url = url_var.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Please paste a video URL.")
            return

        download_dir = download_dir_var.get().strip()
        if not download_dir:
            messagebox.showwarning("Missing folder", "Please choose a download folder.")
            return

        progress_var.set(0)
        status_var.set("Starting...")
        log_queue.put(("log", "Starting download..."))
        set_ui_state(True)

        thread = threading.Thread(
            target=download_worker,
            args=(url, cookie_var.get(), preset_var.get(), download_dir),
            daemon=True,
        )
        thread.start()

    def paste_url():
        try:
            clipboard = root.clipboard_get().strip()
        except tk.TclError:
            return
        if clipboard:
            url_var.set(clipboard)

    def clear_url():
        url_var.set("")

    def browse_download_dir():
        selected = filedialog.askdirectory(
            initialdir=download_dir_var.get() or os.path.expanduser("~")
        )
        if selected:
            download_dir_var.set(selected)

    def open_download_dir():
        target = download_dir_var.get().strip()
        if not target:
            return
        try:
            subprocess.run(["open", target], check=False)
        except OSError as exc:
            messagebox.showerror("Open failed", str(exc))

    def clear_log():
        log_box.delete("1.0", tk.END)

    start_button.config(command=start_download)
    paste_button.config(command=paste_url)
    clear_url_button.config(command=clear_url)
    browse_button.config(command=browse_download_dir)
    open_button.config(command=open_download_dir)
    clear_log_button.config(command=clear_log)

    root.bind("<Return>", lambda event: start_download())
    root.after(100, poll_log_queue)
    check_dependencies()
    root.mainloop()


if __name__ == "__main__":
    main()
