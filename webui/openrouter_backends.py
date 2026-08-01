import base64
import json
import os
import random
import time
from pathlib import Path

import requests

try:
    from .env_config import load_env_file
except ImportError:
    from env_config import load_env_file

try:
    from .http_utils import request_kwargs
except ImportError:
    from http_utils import request_kwargs

load_env_file()

OPENROUTER_BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
OPENROUTER_SITE_URL = os.environ.get("OPENROUTER_SITE_URL", "")
OPENROUTER_APP_NAME = os.environ.get("OPENROUTER_APP_NAME", "幕库 Muku")
DEFAULT_OPENROUTER_TRANSCRIPTION_MODEL = "google/gemini-2.5-flash"
OPENROUTER_TRANSCRIPTION_MODEL = os.environ.get(
    "OPENROUTER_TRANSCRIPTION_MODEL", DEFAULT_OPENROUTER_TRANSCRIPTION_MODEL
)
OPENROUTER_TRANSCRIPTION_FALLBACK_MODELS = tuple(
    model
    for model in dict.fromkeys(
        part.strip()
        for part in os.environ.get(
            "OPENROUTER_TRANSCRIPTION_FALLBACK_MODELS",
            "google/gemini-2.5-flash,google/gemini-2.5-flash-lite",
        ).split(",")
    )
    if model
)
OPENROUTER_CLEANUP_MODEL = os.environ.get("OPENROUTER_CLEANUP_MODEL", "openai/gpt-4o-mini")
OPENROUTER_ARTICLE_MODEL = os.environ.get("OPENROUTER_ARTICLE_MODEL", "openai/gpt-4o-mini")
OPENROUTER_TIMEOUT_SECONDS = int(os.environ.get("OPENROUTER_TIMEOUT_SECONDS", "600"))
OPENROUTER_CONNECT_TIMEOUT_SECONDS = int(os.environ.get("OPENROUTER_CONNECT_TIMEOUT_SECONDS", "30"))
OPENROUTER_READ_TIMEOUT_SECONDS = int(
    os.environ.get("OPENROUTER_READ_TIMEOUT_SECONDS", str(OPENROUTER_TIMEOUT_SECONDS))
)
OPENROUTER_MAX_RETRIES = int(os.environ.get("OPENROUTER_MAX_RETRIES", "6"))
OPENROUTER_RETRY_BACKOFF_MAX = int(os.environ.get("OPENROUTER_RETRY_BACKOFF_MAX", "60"))
RETRYABLE_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}
AUDIO_INPUT_REFUSAL_MARKERS = (
    "can't listen to audio",
    "cannot listen to audio",
    "can't listen to or transcribe audio",
    "cannot listen to or transcribe audio",
    "can't transcribe audio",
    "cannot transcribe audio",
    "can't process audio",
    "cannot process audio",
    "unable to listen to the audio",
    "unable to transcribe the audio",
    "unable to process audio",
    "provide the text or details from the audio",
    "provide a transcript",
    "无法收听音频",
    "无法直接收听",
    "无法转录音频",
    "无法处理音频",
    "不能转录音频",
    "请提供逐字稿",
)


def _transcription_model_candidates() -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            model
            for model in (OPENROUTER_TRANSCRIPTION_MODEL, *OPENROUTER_TRANSCRIPTION_FALLBACK_MODELS)
            if model
        )
    )


def _response_error_detail(response: requests.Response | None) -> str:
    if response is None:
        return ""

    text = (response.text or "").strip()
    if not text:
        return ""

    try:
        body = response.json()
    except ValueError:
        detail = text
    else:
        error = body.get("error") if isinstance(body, dict) else None
        if isinstance(error, dict):
            message = str(error.get("message") or "").strip()
            code = str(error.get("code") or "").strip()
            detail = message
            if code and code not in detail:
                detail = f"{detail} (code: {code})" if detail else f"code: {code}"
        else:
            detail = text

    if len(detail) > 600:
        detail = detail[:597].rstrip() + "..."
    return detail


def _should_retry(exc: Exception) -> bool:
    if isinstance(exc, (requests.Timeout, requests.ConnectionError)):
        return True

    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    return status_code in RETRYABLE_STATUS_CODES


def _format_request_error(exc: Exception) -> str:
    detail = _response_error_detail(getattr(exc, "response", None))
    if detail:
        return f"{exc} - {detail}"
    return str(exc)


def _safe_header_value(value: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        return ""
    try:
        cleaned.encode("latin-1")
        return cleaned
    except UnicodeEncodeError:
        ascii_only = "".join(ch for ch in cleaned if ord(ch) < 128).strip()
        return " ".join(ascii_only.split())


def _headers() -> dict[str, str]:
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not configured.")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    if OPENROUTER_SITE_URL:
        headers["HTTP-Referer"] = OPENROUTER_SITE_URL
    if OPENROUTER_APP_NAME:
        safe_app_name = _safe_header_value(OPENROUTER_APP_NAME)
        if safe_app_name:
            headers["X-Title"] = safe_app_name
    return headers


def _post_chat(payload: dict) -> dict:
    url = f"{OPENROUTER_BASE_URL.rstrip('/')}/chat/completions"
    last_error: Exception | None = None

    for attempt in range(1, OPENROUTER_MAX_RETRIES + 1):
        try:
            response = requests.post(
                url,
                headers=_headers(),
                json=payload,
                timeout=(OPENROUTER_CONNECT_TIMEOUT_SECONDS, OPENROUTER_READ_TIMEOUT_SECONDS),
                **request_kwargs(),
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt >= OPENROUTER_MAX_RETRIES or not _should_retry(exc):
                break
            base = min(2 ** (attempt - 1), OPENROUTER_RETRY_BACKOFF_MAX)
            time.sleep(base + random.uniform(0, base * 0.2))

    raise RuntimeError(f"OpenRouter request failed: {_format_request_error(last_error)}") from last_error


def _encode_audio(audio_path: Path) -> str:
    return base64.b64encode(audio_path.read_bytes()).decode("utf-8")


def _extract_text(data: dict) -> str:
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("OpenRouter response did not contain choices.")

    message = choices[0].get("message") or {}
    content = message.get("content")

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                text_parts.append(text.strip())
        if text_parts:
            return "\n".join(text_parts).strip()

    raise RuntimeError("Unable to extract transcript text from OpenRouter response.")


def _ensure_response_not_truncated(data: dict, *, operation: str) -> None:
    choices = data.get("choices") or []
    if not choices:
        return

    choice = choices[0] or {}
    finish_reason = str(choice.get("finish_reason") or choice.get("native_finish_reason") or "").strip().lower()
    if finish_reason != "length":
        return

    raise RuntimeError(
        f"OpenRouter {operation} response was truncated before completion. "
        "Try a shorter clip, prefer direct subtitles, or split the audio before retrying."
    )


def _looks_like_audio_input_refusal(text: str) -> bool:
    normalized = " ".join(str(text or "").lower().replace("’", "'").split())
    if not normalized or len(normalized) > 1600:
        return False
    if any(marker in normalized for marker in AUDIO_INPUT_REFUSAL_MARKERS):
        return True

    incapacity_markers = ("can't", "cannot", "unable", "not able", "无法", "不能")
    audio_markers = ("audio", "音频")
    action_markers = ("listen", "transcribe", "process", "收听", "转录", "处理")
    handoff_markers = (
        "provide the text",
        "provide a text",
        "provide a transcript",
        "text form",
        "describe the content",
        "提供文本",
        "提供逐字稿",
        "描述音频",
    )
    return all(
        any(marker in normalized for marker in marker_group)
        for marker_group in (
            incapacity_markers,
            audio_markers,
            action_markers,
            handoff_markers,
        )
    )


def transcribe_audio(audio_path: Path, title: str, source_url: str, language_hint: str) -> dict:
    prompt = (
        "Transcribe this audio faithfully. "
        "Preserve the original language and wording. "
        "Do not summarize. "
        "Return plain text only. "
        "Do not include metadata, titles, source URLs, labels, explanations, or markdown."
    )
    if language_hint and language_hint.lower() != "auto":
        prompt += f" The expected main language is {language_hint}."

    payload = {
        "temperature": 0,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    },
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": _encode_audio(audio_path),
                            "format": audio_path.suffix.lstrip(".").lower() or "mp3",
                        },
                    },
                ],
            }
        ],
    }

    attempted_models: list[str] = []
    last_refusal = ""
    for model in _transcription_model_candidates():
        attempted_models.append(model)
        data = _post_chat({**payload, "model": model})
        _ensure_response_not_truncated(data, operation="transcription")
        transcript_text = _extract_text(data)
        if _looks_like_audio_input_refusal(transcript_text):
            last_refusal = transcript_text
            continue
        return {
            "provider": "openrouter",
            "model": model,
            "text": transcript_text,
            "raw_response": data,
        }

    refusal_preview = " ".join(last_refusal.split())[:240]
    raise RuntimeError(
        "Audio transcription refused audio input with all attempted models "
        f"({', '.join(attempted_models)}). Last response: {refusal_preview}"
    )


def cleanup_markdown(clean_text: str, title: str, source_url: str) -> dict:
    prompt = (
        "Turn the following transcript into clean Markdown.\n"
        "Requirements:\n"
        "- Keep the original language.\n"
        "- Keep the content faithful.\n"
        "- Add a short summary.\n"
        "- Add concise section headings.\n"
        "- Do not invent facts.\n"
        "- Output Markdown only.\n\n"
        f"Title: {title}\n"
        f"Source URL: {source_url}\n\n"
        f"Transcript:\n{clean_text}"
    )

    payload = {
        "model": OPENROUTER_CLEANUP_MODEL,
        "temperature": 0.2,
        "messages": [{"role": "user", "content": prompt}],
    }

    data = _post_chat(payload)
    return {
        "provider": "openrouter",
        "model": OPENROUTER_CLEANUP_MODEL,
        "text": _extract_text(data),
        "raw_response": data,
    }


def generate_article_draft(
    *,
    transcript_text: str,
    system_prompt: str,
    title: str,
    source_url: str,
    platform: str,
    source_author: str | None = None,
) -> dict:
    payload = {
        "model": OPENROUTER_ARTICLE_MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    "请按 System Prompt 生成中文成稿。\n\n"
                    "【元信息】\n"
                    f"- 标题：{title}\n"
                    f"- 作者：{(source_author or '').strip() or '未知作者'}\n"
                    f"- 平台：{platform}\n"
                    f"- 原始链接：{source_url}\n\n"
                    "【逐字稿全文】\n"
                    f"{transcript_text}"
                ),
            },
        ],
    }

    data = _post_chat(payload)
    return {
        "provider": "openrouter",
        "model": OPENROUTER_ARTICLE_MODEL,
        "text": _extract_text(data),
        "raw_response": data,
    }
