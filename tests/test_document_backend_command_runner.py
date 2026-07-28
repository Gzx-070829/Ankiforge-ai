import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

from ankiforge_ai.document.errors import DocumentImportError


FAKE_BACKEND = r"""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import time

mode = sys.argv[-2]
source = sys.argv[-1]
if mode == "inspect":
    print(json.dumps({
        "argv_b64": [
            base64.b64encode(value.encode("utf-8")).decode("ascii")
            for value in sys.argv[1:]
        ],
        "cwd_b64": base64.b64encode(os.getcwd().encode("utf-8")).decode("ascii"),
        "environment_keys": sorted(os.environ),
        "temp_values_equal": os.environ.get("TMP") == os.environ.get("TEMP"),
        "temp_matches_cwd": os.environ.get("TMP") == os.getcwd(),
        "source_name": Path(source).name,
    }, sort_keys=True))
elif mode == "stdout":
    sys.stdout.write("x" * 4096)
elif mode == "stderr":
    sys.stderr.write("PRIVATE-SOURCE-TEXT sk-not-a-real-secret-123456789")
    raise SystemExit(7)
elif mode == "sleep":
    time.sleep(10)
    print("late")
elif mode == "invalid-utf8":
    sys.stdout.buffer.write(b"\xff\xfe")
elif mode == "invalid-json":
    print("{}")
elif mode == "absolute-output":
    print("C:\\\\private\\\\source.pdf")
elif mode == "absolute-output-forward-double":
    print("C://private/source.pdf")
elif mode == "unsafe-unc":
    print(r"\\server\share\source.pdf")
elif mode == "unsafe-device-question":
    print(r"\\?\C:\private\source.pdf")
elif mode == "unsafe-device-dot":
    print(r"\\.\C:\private\source.pdf")
elif mode == "unsafe-rooted-windows":
    print(r"\Users\private\source.pdf")
elif mode == "unsafe-posix":
    print("/anything/source.pdf")
elif mode.startswith("unsafe-short-path-"):
    values = {
        "unsafe-short-path-backslash-root": "\\",
        "unsafe-short-path-backslash-name": r"\secret.txt",
        "unsafe-short-path-slash-root": "/",
        "unsafe-short-path-double-slash": "//server/share",
        "unsafe-short-path-dot-name": "/.secret.txt",
        "unsafe-short-path-dash-name": "/-secret.txt",
        "unsafe-short-path-at-name": "/@secret.txt",
        "unsafe-short-path-bracket-name": "/[secret].txt",
        "unsafe-short-path-parenthesis-name": "/(secret).txt",
    }
    print(values[mode])
elif mode == "safe-markdown":
    print(
        "# Safe\n\n[relative](docs/readme.md) input/output ordinary prose "
        "https://example.invalid/cited/path </section>"
    )
elif mode == "safe-html-self-closing":
    print(
        "# Safe\n\nLine one.<br />\n\n<hr/>\n\n"
        "<input disabled/>\n\n<tag attr='x'/>\n\nLine two."
    )
elif mode.startswith("unsafe-html-empty-unquoted-value-"):
    values = {
        "unsafe-html-empty-unquoted-value-tight": "<tag attr=/>",
        "unsafe-html-empty-unquoted-value-spaced": "<tag attr = />",
        "unsafe-html-empty-unquoted-value-before-slash": "<tag attr= />",
        "unsafe-html-empty-unquoted-value-before-equals": "<tag attr =/>",
    }
    print(values[mode])
elif mode.startswith("unsafe-html-path-"):
    values = {
        "unsafe-html-path-standalone": "text /",
        "unsafe-html-path-tag-body": "<tag /etc/passwd>",
        "unsafe-html-path-attribute": "<tag attr='/root/x'>",
    }
    print(values[mode])
elif mode == "artifact-one":
    Path("converted.md").write_text(
        "# Artifact\n\n[relative](docs/readme.md)", encoding="utf-8"
    )
    print("docling progress 100%")
elif mode == "artifact-zero":
    print("docling progress 100%")
elif mode == "artifact-multiple":
    Path("one.md").write_text("# One", encoding="utf-8")
    Path("two.md").write_text("# Two", encoding="utf-8")
elif mode == "artifact-nested":
    Path("nested").mkdir()
    Path("nested/output.md").write_text("# Nested", encoding="utf-8")
elif mode == "artifact-symlink":
    os.symlink(source, "converted.md")
elif mode == "artifact-oversized":
    Path("converted.md").write_text("x" * 4096, encoding="utf-8")
elif mode == "artifact-unsafe":
    Path("converted.md").write_text(
        r"\\server\share\source.pdf", encoding="utf-8"
    )
elif mode == "spawn-immediate-descendant":
    marker = Path(source).with_name(mode + ".marker")
    child = (
        "from pathlib import Path; import sys; "
        "Path(sys.argv[1]).write_text('spawned', encoding='utf-8')"
    )
    subprocess.Popen(
        [sys.executable, "-I", "-c", child, str(marker)],
        stdin=subprocess.DEVNULL,
    )
    time.sleep(10)
elif mode.startswith("spawn-tree-"):
    ready = Path(source).with_name(mode + ".ready")
    survived = Path(source).with_name(mode + ".survived")
    child = r'''
from pathlib import Path
import sys
import time

held = open(Path.cwd() / "held.lock", "w", encoding="utf-8")
Path(sys.argv[1]).write_text("ready", encoding="utf-8")
time.sleep(3)
Path(sys.argv[2]).write_text("survived", encoding="utf-8")
time.sleep(10)
'''
    subprocess.Popen(
        [sys.executable, "-I", "-c", child, str(ready), str(survived)],
        stdin=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + 2
    while not ready.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    time.sleep(10)
else:
    raise SystemExit(8)
"""


class SafeCommandRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.script = self.root / "fake_backend.py"
        self.script.write_text(FAKE_BACKEND, encoding="utf-8")
        self.source = self.root / "source & echo injected.txt"
        self.source.write_text("private source body", encoding="utf-8")
        self.temp_parent = self.root / "runner-temp"
        self.temp_parent.mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def command(
        self,
        mode,
        *,
        output_format="text",
        output_artifact_suffix=None,
    ):
        from ankiforge_ai.document.backends import BackendCommand

        return BackendCommand(
            executable=Path(sys.executable),
            arguments=("-I", str(self.script), mode),
            source_path=self.source,
            output_format=output_format,
            output_artifact_suffix=output_artifact_suffix,
        )

    def runner(self, **overrides):
        from ankiforge_ai.document.backends.command_runner import SafeCommandRunner

        values = {
            "timeout_seconds": 3.0,
            "max_stdout_bytes": 1024,
            "max_stderr_bytes": 128,
            "temp_parent": self.temp_parent,
        }
        values.update(overrides)
        return SafeCommandRunner(**values)

    def test_uses_literal_argv_sanitized_environment_and_controlled_cwd(self):
        with mock.patch.dict(
            os.environ,
            {
                "ANKIFORGE_TEST_SECRET": "must-not-leak",
                "API_KEY": "must-not-leak",
                "PYTHONPATH": "must-not-leak",
            },
            clear=False,
        ):
            result = self.runner().run(self.command("inspect", output_format="json"))

        payload = json.loads(result.stdout)
        import base64

        argv = [
            base64.b64decode(value).decode("utf-8")
            for value in payload["argv_b64"]
        ]
        cwd = base64.b64decode(payload["cwd_b64"]).decode("utf-8")
        self.assertEqual(
            argv,
            ["inspect", str(self.source.resolve())],
        )
        self.assertEqual(payload["source_name"], self.source.name)
        self.assertNotIn("ANKIFORGE_TEST_SECRET", payload["environment_keys"])
        self.assertNotIn("API_KEY", payload["environment_keys"])
        self.assertNotIn("PYTHONPATH", payload["environment_keys"])
        self.assertNotIn("PATH", payload["environment_keys"])
        self.assertTrue(payload["temp_values_equal"])
        self.assertTrue(payload["temp_matches_cwd"])
        self.assertTrue(Path(cwd).is_absolute())
        self.assertFalse((self.root / "echo injected.txt").exists())
        self.assertEqual(list(self.temp_parent.iterdir()), [])

    def test_rejects_relative_executable_url_source_and_user_switches(self):
        from ankiforge_ai.document.backends import BackendCommand

        bad_commands = (
            BackendCommand("python", (), self.source),
            BackendCommand(sys.executable, (), "https://example.invalid/source.pdf"),
            BackendCommand(
                sys.executable,
                (str(self.script), "--filter=untrusted.py"),
                self.source,
            ),
        )
        for command in bad_commands:
            with self.subTest(command=repr(command)):
                with self.assertRaises(DocumentImportError) as caught:
                    self.runner().run(command)
                self.assertIn(
                    caught.exception.code,
                    {"invalid_backend_command", "invalid_local_file"},
                )

    def test_bounds_stdout_and_reports_nonzero_without_output_leakage(self):
        with self.assertRaises(DocumentImportError) as stdout_error:
            self.runner(max_stdout_bytes=64).run(self.command("stdout"))
        self.assertEqual(stdout_error.exception.code, "backend_output_too_large")

        with self.assertRaises(DocumentImportError) as stderr_error:
            self.runner(max_stderr_bytes=16).run(self.command("stderr"))
        self.assertEqual(
            stderr_error.exception.code,
            "backend_output_too_large",
        )

        with self.assertRaises(DocumentImportError) as exit_error:
            self.runner(max_stderr_bytes=128).run(self.command("stderr"))
        self.assertEqual(exit_error.exception.code, "backend_failed")
        diagnostic = repr(exit_error.exception)
        self.assertNotIn("PRIVATE-SOURCE-TEXT", diagnostic)
        self.assertNotIn("sk-not-a-real-secret", diagnostic)
        self.assertNotIn(str(self.source), diagnostic)
        self.assertEqual(list(self.temp_parent.iterdir()), [])

    def test_timeout_and_cancellation_terminate_and_cleanup(self):
        started = time.monotonic()
        with self.assertRaises(DocumentImportError) as timeout_error:
            self.runner(timeout_seconds=0.2).run(self.command("sleep"))
        self.assertEqual(timeout_error.exception.code, "backend_timeout")
        self.assertLess(time.monotonic() - started, 3.0)

        cancelled = threading.Event()
        timer = threading.Timer(0.2, cancelled.set)
        timer.start()
        try:
            with self.assertRaises(DocumentImportError) as cancel_error:
                self.runner().run(self.command("sleep"), cancellation=cancelled)
        finally:
            timer.cancel()
        self.assertEqual(cancel_error.exception.code, "backend_cancelled")
        self.assertEqual(list(self.temp_parent.iterdir()), [])

    def test_rejects_invalid_utf8_json_document_ir_and_absolute_output(self):
        cases = (
            ("invalid-utf8", "text", "backend_invalid_output"),
            ("invalid-json", "json", None),
            ("invalid-json", "document_ir_json", "backend_invalid_output"),
            ("absolute-output", "text", "backend_invalid_output"),
            ("absolute-output-forward-double", "text", "backend_invalid_output"),
            ("unsafe-unc", "text", "backend_invalid_output"),
            ("unsafe-device-question", "text", "backend_invalid_output"),
            ("unsafe-device-dot", "text", "backend_invalid_output"),
            ("unsafe-rooted-windows", "text", "backend_invalid_output"),
            ("unsafe-posix", "text", "backend_invalid_output"),
        )
        for mode, output_format, code in cases:
            with self.subTest(mode=mode, output_format=output_format):
                if code is None:
                    result = self.runner().run(
                        self.command(mode, output_format=output_format)
                    )
                    self.assertEqual(json.loads(result.stdout), {})
                else:
                    with self.assertRaises(DocumentImportError) as caught:
                        self.runner().run(
                            self.command(mode, output_format=output_format)
                        )
                    self.assertEqual(caught.exception.code, code)
        safe = self.runner().run(self.command("safe-markdown"))
        self.assertIn("[relative](docs/readme.md)", safe.stdout)
        self.assertIn("input/output", safe.stdout)
        self.assertIn("https://example.invalid/cited/path", safe.stdout)
        self.assertIn("</section>", safe.stdout)
        self.assertEqual(list(self.temp_parent.iterdir()), [])

    def test_rejects_short_rooted_and_punctuation_leading_absolute_paths(self):
        modes_and_content = (
            ("unsafe-short-path-backslash-root", "\\"),
            ("unsafe-short-path-backslash-name", r"\secret.txt"),
            ("unsafe-short-path-slash-root", "/"),
            ("unsafe-short-path-double-slash", "//server/share"),
            ("unsafe-short-path-dot-name", "/.secret.txt"),
            ("unsafe-short-path-dash-name", "/-secret.txt"),
            ("unsafe-short-path-at-name", "/@secret.txt"),
            ("unsafe-short-path-bracket-name", "/[secret].txt"),
            ("unsafe-short-path-parenthesis-name", "/(secret).txt"),
        )
        for mode, content in modes_and_content:
            with self.subTest(mode=mode):
                with self.assertRaises(DocumentImportError) as caught:
                    self.runner().run(self.command(mode))
                self.assertEqual(caught.exception.code, "backend_invalid_output")
                self.assertNotIn(content, repr(caught.exception))
        self.assertEqual(list(self.temp_parent.iterdir()), [])

    def test_allows_self_closing_html_and_rejects_path_near_misses(self):
        safe = self.runner().run(self.command("safe-html-self-closing"))
        for content in (
            "<br />",
            "<hr/>",
            "<input disabled/>",
            "<tag attr='x'/>",
        ):
            with self.subTest(safe_content=content):
                self.assertIn(content, safe.stdout)

        modes_and_content = (
            ("unsafe-html-empty-unquoted-value-tight", "<tag attr=/>"),
            ("unsafe-html-empty-unquoted-value-spaced", "<tag attr = />"),
            ("unsafe-html-empty-unquoted-value-before-slash", "<tag attr= />"),
            ("unsafe-html-empty-unquoted-value-before-equals", "<tag attr =/>"),
            ("unsafe-html-path-standalone", "text /"),
            ("unsafe-html-path-tag-body", "<tag /etc/passwd>"),
            ("unsafe-html-path-attribute", "<tag attr='/root/x'>"),
        )
        for mode, content in modes_and_content:
            with self.subTest(mode=mode):
                with self.assertRaises(DocumentImportError) as caught:
                    self.runner().run(self.command(mode))
                self.assertEqual(caught.exception.code, "backend_invalid_output")
                self.assertNotIn(content, repr(caught.exception))
        self.assertEqual(list(self.temp_parent.iterdir()), [])

    def test_reads_one_bounded_root_markdown_artifact_before_cleanup(self):
        result = self.runner().run(
            self.command("artifact-one", output_artifact_suffix=".md")
        )
        self.assertEqual(
            result.stdout.replace("\r\n", "\n"),
            "# Artifact\n\n[relative](docs/readme.md)",
        )
        self.assertEqual(list(self.temp_parent.iterdir()), [])

        invalid_modes = (
            "artifact-zero",
            "artifact-multiple",
            "artifact-nested",
            "artifact-oversized",
            "artifact-unsafe",
        )
        for mode in invalid_modes:
            with self.subTest(mode=mode):
                with self.assertRaises(DocumentImportError) as caught:
                    self.runner(max_stdout_bytes=64).run(
                        self.command(mode, output_artifact_suffix=".md")
                    )
                self.assertEqual(caught.exception.code, "backend_invalid_output")
                self.assertNotIn(str(self.root), repr(caught.exception))
                self.assertEqual(list(self.temp_parent.iterdir()), [])

    def test_rejects_symlink_markdown_artifact(self):
        real_is_symlink = Path.is_symlink

        def report_artifact_as_symlink(path):
            return path.name == "converted.md" or real_is_symlink(path)

        with mock.patch.object(Path, "is_symlink", report_artifact_as_symlink):
            with self.assertRaises(DocumentImportError) as caught:
                self.runner().run(
                    self.command("artifact-one", output_artifact_suffix=".md")
                )
        self.assertEqual(caught.exception.code, "backend_invalid_output")
        self.assertNotIn(str(self.root), repr(caught.exception))
        self.assertEqual(list(self.temp_parent.iterdir()), [])

    @unittest.skipUnless(os.name == "nt", "Windows Job Object containment")
    def test_windows_job_assignment_failure_is_fail_closed_and_sanitized(self):
        from ankiforge_ai.document.backends import command_runner

        marker = self.source.with_name("spawn-immediate-descendant.marker")

        def delayed_assignment_failure(process):
            time.sleep(1.0)
            raise OSError(r"C:\private\job-assignment")

        with mock.patch.object(
            command_runner._WindowsJobObject,
            "assign",
            side_effect=delayed_assignment_failure,
        ):
            with self.assertRaises(DocumentImportError) as caught:
                self.runner().run(self.command("spawn-immediate-descendant"))
        self.assertEqual(caught.exception.code, "backend_containment_failed")
        self.assertNotIn("job-assignment", repr(caught.exception))
        self.assertNotIn(str(self.source), repr(caught.exception))
        self.assertFalse(marker.exists())
        self.assertEqual(list(self.temp_parent.iterdir()), [])

    @unittest.skipUnless(os.name == "nt", "Windows suspended process containment")
    def test_windows_runner_does_not_require_sys_executable_as_python(self):
        command = self.command("inspect", output_format="json")
        with mock.patch.object(
            sys,
            "executable",
            str(self.source),
        ):
            result = self.runner().run(command)

        payload = json.loads(result.stdout)
        self.assertEqual(payload["source_name"], self.source.name)
        self.assertEqual(list(self.temp_parent.iterdir()), [])

    @unittest.skipUnless(os.name == "nt", "Windows suspended process containment")
    def test_windows_resume_failure_is_fail_closed_before_target_executes(self):
        from ankiforge_ai.document.backends import command_runner

        marker = self.source.with_name("spawn-immediate-descendant.marker")
        with mock.patch.object(
            command_runner,
            "_resume_suspended_windows_process",
            side_effect=OSError(r"C:\private\resume-failure"),
            create=True,
        ):
            with self.assertRaises(DocumentImportError) as caught:
                self.runner(timeout_seconds=0.5).run(
                    self.command("spawn-immediate-descendant")
                )
        self.assertEqual(caught.exception.code, "backend_containment_failed")
        self.assertNotIn("resume-failure", repr(caught.exception))
        self.assertNotIn(str(self.source), repr(caught.exception))
        self.assertFalse(marker.exists())
        self.assertEqual(list(self.temp_parent.iterdir()), [])

    @unittest.skipUnless(os.name == "nt", "Windows Job Object containment")
    def test_windows_job_kills_descendants_on_timeout_and_cancellation(self):
        cases = ("timeout", "cancel")
        for case in cases:
            with self.subTest(case=case):
                mode = "spawn-tree-" + case
                ready = self.source.with_name(mode + ".ready")
                survived = self.source.with_name(mode + ".survived")
                cancellation = None
                cancellation_thread = None
                if case == "cancel":
                    cancellation = threading.Event()
                    def cancel_when_ready():
                        deadline = time.monotonic() + 4
                        while not ready.exists() and time.monotonic() < deadline:
                            time.sleep(0.01)
                        cancellation.set()

                    cancellation_thread = threading.Thread(
                        target=cancel_when_ready,
                        daemon=True,
                    )
                    cancellation_thread.start()
                try:
                    with self.assertRaises(DocumentImportError) as caught:
                        self.runner(
                            timeout_seconds=2.0 if case == "timeout" else 5.0
                        ).run(
                            self.command(mode),
                            cancellation=cancellation,
                        )
                finally:
                    if cancellation_thread is not None:
                        cancellation_thread.join(timeout=5.0)
                self.assertTrue(ready.exists())
                self.assertEqual(
                    caught.exception.code,
                    "backend_cancelled" if case == "cancel" else "backend_timeout",
                )
                time.sleep(1.2)
                self.assertFalse(survived.exists())
                self.assertEqual(list(self.temp_parent.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
