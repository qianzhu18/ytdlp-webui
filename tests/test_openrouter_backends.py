import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import requests

from webui import openrouter_backends


class OpenRouterRequestErrorTests(unittest.TestCase):
    def test_402_error_includes_openrouter_message_and_does_not_retry(self) -> None:
        response = requests.Response()
        response.status_code = 402
        response.url = "https://openrouter.ai/api/v1/chat/completions"
        response._content = json.dumps(
            {"error": {"message": "This request requires at least $0.50 in balance for audio", "code": 402}}
        ).encode("utf-8")
        response.headers["Content-Type"] = "application/json"

        with mock.patch.object(openrouter_backends, "OPENROUTER_API_KEY", "sk-test"), mock.patch.object(
            openrouter_backends, "OPENROUTER_MAX_RETRIES", 6
        ), mock.patch.object(
            openrouter_backends.requests, "post", return_value=response
        ) as post, mock.patch.object(
            openrouter_backends.time, "sleep"
        ) as sleep:
            with self.assertRaises(RuntimeError) as cm:
                openrouter_backends._post_chat({"model": "openai/gpt-audio-mini", "messages": []})

        self.assertEqual(post.call_count, 1)
        sleep.assert_not_called()
        self.assertIn("402 Client Error", str(cm.exception))
        self.assertIn("requires at least $0.50 in balance for audio", str(cm.exception))

    def test_429_retries(self) -> None:
        rate_limited = requests.Response()
        rate_limited.status_code = 429
        rate_limited.url = "https://openrouter.ai/api/v1/chat/completions"
        rate_limited._content = b'{"error":{"message":"rate limited","code":429}}'
        rate_limited.headers["Content-Type"] = "application/json"

        ok = mock.Mock()
        ok.raise_for_status.return_value = None
        ok.json.return_value = {"choices": [{"message": {"content": "ok"}}]}

        with mock.patch.object(openrouter_backends, "OPENROUTER_API_KEY", "sk-test"), mock.patch.object(
            openrouter_backends, "OPENROUTER_MAX_RETRIES", 2
        ), mock.patch.object(
            openrouter_backends.requests, "post", side_effect=[rate_limited, ok]
        ) as post, mock.patch.object(
            openrouter_backends.time, "sleep"
        ) as sleep:
            data = openrouter_backends._post_chat({"model": "openai/gpt-audio-mini", "messages": []})

        self.assertEqual(data["choices"][0]["message"]["content"], "ok")
        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once()


class OpenRouterTranscriptionTests(unittest.TestCase):
    @staticmethod
    def response_with_text(text: str) -> dict:
        return {"choices": [{"message": {"content": text}}]}

    def test_default_transcription_model_matches_openrouter_audio_reference(self) -> None:
        self.assertEqual(
            openrouter_backends.DEFAULT_OPENROUTER_TRANSCRIPTION_MODEL,
            "google/gemini-2.5-flash",
        )

    def test_model_candidates_are_recomputed_after_runtime_primary_change(self) -> None:
        with mock.patch.object(
            openrouter_backends,
            "OPENROUTER_TRANSCRIPTION_MODEL",
            "openai/gpt-audio-mini",
        ), mock.patch.object(
            openrouter_backends,
            "OPENROUTER_TRANSCRIPTION_FALLBACK_MODELS",
            ("google/gemini-2.5-flash", "google/gemini-2.5-flash-lite"),
        ):
            self.assertEqual(
                openrouter_backends._transcription_model_candidates(),
                (
                    "openai/gpt-audio-mini",
                    "google/gemini-2.5-flash",
                    "google/gemini-2.5-flash-lite",
                ),
            )

    def test_audio_refusal_detection_rejects_cannot_process_audio_wording(self) -> None:
        refusal = (
            "I'm sorry, but I currently can't process audio directly. "
            "If you can provide a text version, I'd be happy to help."
        )

        self.assertTrue(openrouter_backends._looks_like_audio_input_refusal(refusal))

    def test_audio_refusal_detection_handles_words_inserted_between_markers(self) -> None:
        refusal = (
            "I'm sorry, but I can't actually listen to or transcribe audio directly. "
            "If you can provide the audio content in text form, I'd be happy to help."
        )

        self.assertTrue(openrouter_backends._looks_like_audio_input_refusal(refusal))

    def test_transcription_falls_back_when_primary_model_refuses_audio(self) -> None:
        refusal = (
            "I'm sorry, but I can't listen to or transcribe audio directly. "
            "Please provide the text instead."
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "sample.mp3"
            audio_path.write_bytes(b"audio")

            with mock.patch.object(
                openrouter_backends,
                "OPENROUTER_TRANSCRIPTION_MODEL",
                "openai/gpt-audio-mini",
            ), mock.patch.object(
                openrouter_backends,
                "OPENROUTER_TRANSCRIPTION_FALLBACK_MODELS",
                ("google/gemini-2.5-flash",),
                create=True,
            ), mock.patch.object(
                openrouter_backends,
                "_post_chat",
                side_effect=[
                    self.response_with_text(refusal),
                    self.response_with_text("这是有效的音频逐字稿。"),
                ],
            ) as post:
                result = openrouter_backends.transcribe_audio(
                    audio_path,
                    title="Sample",
                    source_url="https://example.com/audio",
                    language_hint="zh",
                )

        self.assertEqual(result["text"], "这是有效的音频逐字稿。")
        self.assertEqual(result["model"], "google/gemini-2.5-flash")
        self.assertEqual(
            [call.args[0]["model"] for call in post.call_args_list],
            ["openai/gpt-audio-mini", "google/gemini-2.5-flash"],
        )

    def test_transcription_fails_when_every_model_refuses_audio(self) -> None:
        refusals = [
            "I can't listen to audio. Please provide a transcript.",
            "I cannot transcribe audio directly. Please provide the text.",
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "sample.mp3"
            audio_path.write_bytes(b"audio")

            with mock.patch.object(
                openrouter_backends,
                "OPENROUTER_TRANSCRIPTION_MODEL",
                "primary/audio",
            ), mock.patch.object(
                openrouter_backends,
                "OPENROUTER_TRANSCRIPTION_FALLBACK_MODELS",
                ("fallback/audio",),
                create=True,
            ), mock.patch.object(
                openrouter_backends,
                "_post_chat",
                side_effect=[self.response_with_text(text) for text in refusals],
            ):
                with self.assertRaisesRegex(RuntimeError, "refused audio input"):
                    openrouter_backends.transcribe_audio(
                        audio_path,
                        title="Sample",
                        source_url="https://example.com/audio",
                        language_hint="zh",
                    )


if __name__ == "__main__":
    unittest.main()
