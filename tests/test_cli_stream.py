import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from webui import cli as web_cli


class StreamEventTests(unittest.TestCase):
    def test_success_result_mapped_to_task_done(self) -> None:
        result = {"source_url": "https://example.com", "status": "Done · transcript ready", "artifact_dir": "/tmp/x"}
        event = web_cli._to_stream_event(result)
        self.assertEqual(event["event"], "task_done")
        self.assertEqual(event["source_url"], "https://example.com")

    def test_failed_result_mapped_to_task_failed(self) -> None:
        result = {"source_url": "https://example.com", "status": "Failed", "error": "boom"}
        event = web_cli._to_stream_event(result)
        self.assertEqual(event["event"], "task_failed")
        self.assertEqual(event["error"], "boom")

    def test_none_values_dropped(self) -> None:
        result = {"status": "ok", "download_path": None, "title": "t"}
        event = web_cli._to_stream_event(result)
        self.assertNotIn("download_path", event)
        self.assertIn("title", event)


class ResolveOutputModeTests(unittest.TestCase):
    def test_stream_takes_priority(self) -> None:
        self.assertEqual(web_cli._resolve_output_mode("text", as_json=True, stream=True), "stream")

    def test_json_when_as_json_and_no_stream(self) -> None:
        self.assertEqual(web_cli._resolve_output_mode("text", as_json=True, stream=False), "json")

    def test_passthrough_text(self) -> None:
        self.assertEqual(web_cli._resolve_output_mode("text", as_json=False, stream=False), "text")


class CollectUrlInputsTests(unittest.TestCase):
    def test_input_file_preserves_supported_and_generic_urls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "urls.txt"
            input_file.write_text(
                "https://www.youtube.com/watch?v=abcdefghijk\n"
                "https://www.ted.com/talks/example\n",
                encoding="utf-8",
            )

            urls = web_cli._collect_url_inputs(
                values=(),
                input_file=input_file,
                stdin_enabled=False,
            )

        self.assertEqual(
            urls,
            (
                "https://www.youtube.com/watch?v=abcdefghijk",
                "https://www.ted.com/talks/example",
            ),
        )

    def test_multiple_positional_values_are_normalized_independently(self) -> None:
        urls = web_cli._collect_url_inputs(
            values=(
                "https://www.bilibili.com/video/BV1111111111/",
                "https://vimeo.com/123456789",
            ),
            input_file=None,
            stdin_enabled=False,
        )

        self.assertEqual(
            urls,
            (
                "https://www.bilibili.com/video/BV1111111111/",
                "https://vimeo.com/123456789",
            ),
        )


class FinalizeOutputTests(unittest.TestCase):
    def test_stream_mode_emits_batch_complete_only(self) -> None:
        results = [{"status": "ok"}, {"status": "Failed", "error": "x"}]
        buf = io.StringIO()
        with redirect_stdout(buf):
            web_cli._finalize_output(results, "stream")
        lines = [line for line in buf.getvalue().splitlines() if line.strip()]
        self.assertEqual(len(lines), 1)
        event = json.loads(lines[0])
        self.assertEqual(event["event"], "batch_complete")
        self.assertEqual(event["total"], 2)
        self.assertEqual(event["succeeded"], 1)
        self.assertEqual(event["failed"], 1)

    def test_non_stream_mode_delegates_to_emit_results(self) -> None:
        with mock.patch.object(web_cli, "_emit_results") as mock_emit:
            web_cli._finalize_output([], "json")
        mock_emit.assert_called_once_with([], "json")


class ParallelMapStreamTests(unittest.TestCase):
    def test_emitter_invoked_per_result(self) -> None:
        captured: list[dict] = []

        def fake_emitter(event: dict) -> None:
            captured.append(event)

        web_cli._set_stream_emitter(fake_emitter)
        try:
            items = [{"source_url": f"u{i}", "status": "ok"} for i in range(3)]
            results = web_cli._run_parallel_map(items, jobs=1, worker=lambda x: x)
        finally:
            web_cli._set_stream_emitter(None)

        self.assertEqual(len(results), 3)
        self.assertEqual(len(captured), 3)
        self.assertTrue(all(e["event"] == "task_done" for e in captured))

    def test_no_emitter_no_output(self) -> None:
        web_cli._set_stream_emitter(None)
        buf = io.StringIO()
        with redirect_stdout(buf):
            items = [{"status": "ok"}]
            web_cli._run_parallel_map(items, jobs=1, worker=lambda x: x)
        self.assertEqual(buf.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
