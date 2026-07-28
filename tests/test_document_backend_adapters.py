from dataclasses import replace
import os
from pathlib import Path
import tempfile
import unittest

from ankiforge_ai.document import BlockKind, DEFAULT_DOCUMENT_LIMITS
from ankiforge_ai.document.errors import DocumentImportError


MARKDOWN = """# Intro

Local paragraph.

- first
- second

| Name | Value |
| --- | --- |
| alpha | 1 |
"""


class LiteralRunner:
    def __init__(self, output, *, returncode=0):
        from ankiforge_ai.document.backends import BackendResult

        self.result = BackendResult(
            returncode=returncode,
            stdout=output,
            stderr_summary="",
        )
        self.commands = []

    def run(self, command, *, cancellation=None):
        self.commands.append(command)
        return self.result


class DocumentBackendAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.pdf = self.root / "lesson.pdf"
        self.pdf.write_bytes(b"%PDF-1.4\nlocal fixture\n")
        self.markdown = self.root / "lesson.md"
        self.markdown.write_text("# Source\n\nbody", encoding="utf-8")
        self.pandoc = self.root / ("pandoc.exe" if os.name == "nt" else "pandoc")
        self.pandoc.write_bytes(b"local test executable placeholder")
        if os.name != "nt":
            self.pandoc.chmod(0o700)

    def tearDown(self):
        self.temporary.cleanup()

    def test_markitdown_maps_literal_markdown_to_validated_document_ir(self):
        from ankiforge_ai.document.backends import MarkItDownBackend

        runner = LiteralRunner(MARKDOWN)
        document = MarkItDownBackend(runner=runner).convert_local_file(self.pdf)

        self.assertEqual(document.source_type, "markitdown")
        self.assertEqual(document.source_label, "lesson.pdf")
        self.assertEqual(document.title, "Intro")
        self.assertEqual(
            [block.kind for section in document.sections for block in section.blocks],
            [
                BlockKind.HEADING,
                BlockKind.PARAGRAPH,
                BlockKind.LIST,
                BlockKind.TABLE,
            ],
        )
        self.assertEqual(
            runner.commands[0].arguments,
            ("-I", "-m", "markitdown"),
        )
        self.assertEqual(runner.commands[0].source_path, self.pdf.resolve())

    def test_docling_uses_bounded_markdown_artifact_with_all_risky_features_off(self):
        from ankiforge_ai.document.backends import DoclingBackend
        from ankiforge_ai.document.importers.optional_backends import (
            parse_docling_output,
        )

        markdown_outputs = (
            "{literal Markdown, not guessed JSON}\n\n"
            "# Structured\n\nLayout paragraph.",
            "[relative](docs/readme.md)\n\n"
            "# Structured\n\nLayout paragraph.",
        )
        for markdown in markdown_outputs:
            with self.subTest(first_character=markdown[0]):
                markdown_runner = LiteralRunner(markdown)
                document = DoclingBackend(
                    runner=markdown_runner
                ).convert_local_file(self.pdf)
                self.assertEqual(document.source_type, "docling")
                self.assertEqual(document.title, "Structured")

        capability = DoclingBackend(runner=markdown_runner).capabilities()

        self.assertFalse(capability.ocr_enabled)
        self.assertFalse(capability.remote_enabled)
        self.assertFalse(capability.downloads_enabled)
        self.assertFalse(capability.plugins_enabled)
        self.assertEqual(
            markdown_runner.commands[0].arguments,
            (
                "-I",
                "-m",
                "docling",
                "--to",
                "md",
                "--output",
                ".",
                "--no-ocr",
            ),
        )
        self.assertEqual(
            markdown_runner.commands[0].output_artifact_suffix,
            ".md",
        )
        json_document = parse_docling_output(
            self.pdf,
            '{"markdown":"# JSON\\n\\nTrusted schema.","title":"Course"}',
            DEFAULT_DOCUMENT_LIMITS,
            schema="docling_json_v1",
        )
        self.assertEqual(json_document.title, "Course")

    def test_pandoc_uses_only_fixed_sandboxed_allowlisted_arguments(self):
        from ankiforge_ai.document.backends import PandocBackend

        runner = LiteralRunner("# Pandoc\n\nConverted body.")
        backend = PandocBackend(executable=self.pandoc, runner=runner)
        document = backend.convert_local_file(self.markdown)

        self.assertEqual(document.source_type, "pandoc")
        self.assertEqual(
            runner.commands[0].arguments,
            ("--sandbox", "--from", "gfm", "--to", "gfm"),
        )
        flattened = " ".join(runner.commands[0].arguments)
        for forbidden in (
            "--filter",
            "--lua-filter",
            "--include",
            "--template",
            "--pdf-engine",
            "--resource-path",
        ):
            self.assertNotIn(forbidden, flattened)

        unsupported = self.root / "lesson.pdf"
        with self.assertRaises(DocumentImportError) as caught:
            backend.convert_local_file(unsupported)
        self.assertEqual(caught.exception.code, "backend_format_unsupported")

    def test_adapters_reject_remote_paths_malformed_output_and_limit_overflow(self):
        from ankiforge_ai.document.backends import MarkItDownBackend

        with self.assertRaises(DocumentImportError) as remote:
            MarkItDownBackend(runner=LiteralRunner(MARKDOWN)).convert_local_file(
                "https://example.invalid/private.pdf"
            )
        self.assertEqual(remote.exception.code, "invalid_local_file")

        cases = (
            ("", DEFAULT_DOCUMENT_LIMITS),
            ("C:\\private\\source.pdf", DEFAULT_DOCUMENT_LIMITS),
            ("C://private/source.pdf", DEFAULT_DOCUMENT_LIMITS),
            (r"\\server\share\source.pdf", DEFAULT_DOCUMENT_LIMITS),
            (r"\\?\C:\private\source.pdf", DEFAULT_DOCUMENT_LIMITS),
            (r"\\.\C:\private\source.pdf", DEFAULT_DOCUMENT_LIMITS),
            (r"\Users\private\source.pdf", DEFAULT_DOCUMENT_LIMITS),
            ("\\", DEFAULT_DOCUMENT_LIMITS),
            (r"\secret.txt", DEFAULT_DOCUMENT_LIMITS),
            ("/", DEFAULT_DOCUMENT_LIMITS),
            ("//server/share", DEFAULT_DOCUMENT_LIMITS),
            ("/.secret.txt", DEFAULT_DOCUMENT_LIMITS),
            ("/-secret.txt", DEFAULT_DOCUMENT_LIMITS),
            ("/@secret.txt", DEFAULT_DOCUMENT_LIMITS),
            ("/[secret].txt", DEFAULT_DOCUMENT_LIMITS),
            ("/(secret).txt", DEFAULT_DOCUMENT_LIMITS),
            ("/root/source.pdf", DEFAULT_DOCUMENT_LIMITS),
            ("/opt/source.pdf", DEFAULT_DOCUMENT_LIMITS),
            ("/private/source.pdf", DEFAULT_DOCUMENT_LIMITS),
            ("/anything/source.pdf", DEFAULT_DOCUMENT_LIMITS),
            ("text /", DEFAULT_DOCUMENT_LIMITS),
            ("<tag attr=/>", DEFAULT_DOCUMENT_LIMITS),
            ("<tag attr = />", DEFAULT_DOCUMENT_LIMITS),
            ("<tag attr= />", DEFAULT_DOCUMENT_LIMITS),
            ("<tag attr =/>", DEFAULT_DOCUMENT_LIMITS),
            ("<tag /etc/passwd>", DEFAULT_DOCUMENT_LIMITS),
            ("<tag attr='/root/x'>", DEFAULT_DOCUMENT_LIMITS),
            (
                "x" * 65,
                replace(DEFAULT_DOCUMENT_LIMITS, max_text_chars=64),
            ),
        )
        for output, limits in cases:
            with self.subTest(output_length=len(output)):
                with self.assertRaises(DocumentImportError) as caught:
                    MarkItDownBackend(
                        runner=LiteralRunner(output)
                    ).convert_local_file(self.pdf, limits)
                self.assertEqual(caught.exception.code, "backend_invalid_output")
                self.assertNotIn(str(self.pdf), repr(caught.exception))
                if output:
                    self.assertNotIn(output, repr(caught.exception))

        safe = MarkItDownBackend(
            runner=LiteralRunner(
                "# Safe\n\n[relative](docs/readme.md) input/output ordinary prose "
                "https://example.invalid/cited/path </section> <br /> <hr/> "
                "<input disabled/> <tag attr='x'/>"
            )
        ).convert_local_file(self.pdf)
        self.assertEqual(safe.title, "Safe")

    def test_optional_importers_are_not_created_or_registered_by_default(self):
        from ankiforge_ai.document.importers.optional_backends import (
            create_optional_backend_importers,
        )
        from ankiforge_ai.document.importers.registry import (
            create_native_importer_registry,
        )

        self.assertEqual(create_optional_backend_importers(), ())
        registry = create_native_importer_registry()
        importer_ids = {
            capability.importer_id for capability in registry.capabilities()
        }
        self.assertNotIn("docling", importer_ids)
        self.assertNotIn("markitdown", importer_ids)
        self.assertNotIn("pandoc", importer_ids)


if __name__ == "__main__":
    unittest.main()
