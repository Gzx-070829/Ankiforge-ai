import unittest
import tempfile
import importlib
from concurrent.futures import Future
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest import mock

from ankiforge_ai.document import (
    BlockKind,
    DocumentBlock,
    DocumentImportError,
    DocumentIR,
    DocumentSection,
)
from ankiforge_ai.document.importers.base import DocumentImporter, ImportInspection
from ankiforge_ai.ui.document_import_queue import (
    DocumentImportRequestSnapshot,
    DocumentImportWorkerResult,
    PrivatePathToken,
)
from ankiforge_ai.ui.document_import_task_controller import (
    DocumentImportTaskController,
    build_bounded_import_material,
    build_bounded_import_material_preview,
    import_document_path_token,
)


def _document(label="notes.txt"):
    return DocumentIR(
        schema_version=1,
        document_id="doc-notes",
        title="Notes",
        language_hint="en",
        source_type="text",
        source_label=label,
    )


def _request(request_id, item_id="item-1"):
    return DocumentImportRequestSnapshot(
        request_id=request_id,
        item_id=item_id,
        path_token=PrivatePathToken.from_path(
            "C:/Users/private/Documents/notes.txt",
            byte_size=10,
        ),
    )


class FakeTaskman:
    def __init__(self):
        self.submissions = []

    def run_in_background(self, background, on_done, *, uses_collection):
        self.submissions.append((background, on_done, uses_collection))

    def complete(self, index=0):
        background, on_done, _uses_collection = self.submissions[index]
        future = Future()
        try:
            future.set_result(background())
        except Exception as exc:
            future.set_exception(exc)
        on_done(future)


class RaisingTaskman:
    def run_in_background(self, _background, _on_done, *, uses_collection):
        self.uses_collection = uses_collection
        raise RuntimeError("taskman unavailable")


class DocumentImportTaskControllerTests(unittest.TestCase):
    def test_native_worker_builds_bounded_analysis_chunks_and_all_level_estimates(self):
        fixture = (
            __import__("pathlib").Path(__file__).parent
            / "fixtures"
            / "documents"
            / "structured.md"
        )
        token = PrivatePathToken.from_path(
            fixture,
            byte_size=fixture.stat().st_size,
        )

        result = import_document_path_token(token)

        self.assertEqual(result.document.source_label, "structured.md")
        self.assertEqual(result.analysis.document_id, result.document.document_id)
        self.assertTrue(result.chunks)
        self.assertEqual(
            tuple(estimate.level.value for estimate in result.estimates),
            ("fast", "standard", "deep"),
        )
        rendered = repr(result)
        self.assertNotIn(str(fixture.parent), rendered)
        self.assertNotIn(result.document.sections[0].blocks[0].text, rendered)

    def test_material_builder_keeps_every_successful_file_in_order_and_caps_output(self):
        first = DocumentImportWorkerResult(
            document=_document("first.txt"),
            file_type="text",
            importer_name="TXT",
        )
        second_document = DocumentIR(
            schema_version=1,
            document_id="doc-second",
            title="Second",
            language_hint="en",
            source_type="text",
            source_label="second.txt",
        )
        second = DocumentImportWorkerResult(
            document=second_document,
            file_type="text",
            importer_name="TXT",
        )

        material = build_bounded_import_material((first, second), max_chars=80)

        self.assertIn("first.txt", material)
        self.assertIn("second.txt", material)
        self.assertLessEqual(len(material), 80)

    def test_material_preview_explicitly_reports_truncation(self):
        result = DocumentImportWorkerResult(
            document=DocumentIR(
                schema_version=1,
                document_id="doc-preview",
                title="Preview",
                language_hint="en",
                source_type="text",
                source_label="preview.txt",
                sections=(
                    DocumentSection(
                        section_id="section-preview",
                        heading=None,
                        blocks=(
                            DocumentBlock(
                                "block-preview",
                                BlockKind.PARAGRAPH,
                                "preview body " * 20,
                            ),
                        ),
                    ),
                ),
            ),
            file_type="text",
            importer_name="TXT",
        )

        preview = build_bounded_import_material_preview(
            (result,),
            max_chars=40,
        )

        self.assertTrue(preview.truncated)
        self.assertEqual(len(preview.text), 40)
        self.assertGreater(preview.original_char_count, len(preview.text))

    def test_pdf_backend_is_default_off_and_only_used_after_explicit_selection(self):
        class FakeDoclingImporter(DocumentImporter):
            importer_id = "docling"
            supported_extensions = (".pdf",)

            def availability(self):
                return True

            def inspect(self, path, limits):
                return ImportInspection(
                    importer_id=self.importer_id,
                    source_label=Path(path).name,
                    detected_file_type="pdf",
                )

            def import_document(self, path, limits):
                return DocumentIR(
                    schema_version=1,
                    document_id="doc-pdf",
                    title="PDF",
                    language_hint="en",
                    source_type="docling",
                    source_label=Path(path).name,
                    sections=(
                        DocumentSection(
                            section_id="section-pdf",
                            heading="PDF",
                            blocks=(
                                DocumentBlock(
                                    "block-pdf",
                                    BlockKind.PARAGRAPH,
                                    "Locally extracted PDF text.",
                                ),
                            ),
                        ),
                    ),
                    original_char_count=27,
                    extracted_char_count=27,
                )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lesson.pdf"
            path.write_bytes(b"%PDF-1.4\nlocal fixture")
            token = PrivatePathToken.from_path(
                path,
                byte_size=path.stat().st_size,
            )
            with self.assertRaises(DocumentImportError) as raised:
                import_document_path_token(token)
            optional_backends = importlib.import_module(
                "ankiforge_ai.document.importers.optional_backends"
            )
            with mock.patch.object(
                optional_backends,
                "create_optional_backend_importers",
                return_value=(FakeDoclingImporter(),),
            ):
                result = import_document_path_token(
                    token,
                    enabled_backend_ids=("docling",),
                )

        self.assertEqual(raised.exception.code, "optional_backend_missing")
        self.assertEqual(result.importer_name, "DOCLING")
        self.assertEqual(result.document.source_type, "docling")

    def test_optional_backend_probe_failure_becomes_actionable_missing_error(self):
        class BrokenBackendImporter(DocumentImporter):
            importer_id = "docling"
            supported_extensions = (".pdf",)

            def availability(self):
                raise RuntimeError("private backend probe detail")

            def inspect(self, path, limits):
                raise AssertionError("not reached")

            def import_document(self, path, limits):
                raise AssertionError("not reached")

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lesson.pdf"
            path.write_bytes(b"%PDF-1.4\nlocal fixture")
            token = PrivatePathToken.from_path(path, byte_size=path.stat().st_size)
            optional_backends = importlib.import_module(
                "ankiforge_ai.document.importers.optional_backends"
            )
            with mock.patch.object(
                optional_backends,
                "create_optional_backend_importers",
                return_value=(BrokenBackendImporter(),),
            ):
                with self.assertRaises(DocumentImportError) as raised:
                    import_document_path_token(
                        token,
                        enabled_backend_ids=("docling",),
                    )

        self.assertEqual(raised.exception.code, "optional_backend_missing")
        self.assertNotIn("private", repr(raised.exception).casefold())

    def test_submit_uses_collection_false_and_captures_an_immutable_snapshot(self):
        taskman = FakeTaskman()
        controller = DocumentImportTaskController(taskman)
        request = _request(1)
        completions = []

        request_id = controller.submit(
            request=request,
            importer_callback=lambda _token: DocumentImportWorkerResult(
                document=_document(),
                file_type="text",
                importer_name="TXT",
            ),
            on_complete=completions.append,
        )

        self.assertEqual(request_id, 1)
        self.assertEqual(len(taskman.submissions), 1)
        self.assertFalse(taskman.submissions[0][2])
        with self.assertRaises(FrozenInstanceError):
            request.request_id = 2
        taskman.complete()
        self.assertEqual(completions[0].request_id, 1)
        self.assertIsInstance(completions[0].result.document, DocumentIR)

    def test_new_request_supersedes_old_completion_and_only_current_callback_runs(self):
        taskman = FakeTaskman()
        controller = DocumentImportTaskController(taskman)
        received = []
        importer = lambda _token: DocumentImportWorkerResult(
            document=_document(),
            file_type="text",
            importer_name="TXT",
        )

        controller.submit(
            request=_request(1),
            importer_callback=importer,
            on_complete=lambda result: received.append(("old", result.request_id)),
        )
        controller.submit(
            request=_request(2, "item-2"),
            importer_callback=importer,
            on_complete=lambda result: received.append(("new", result.request_id)),
        )
        taskman.complete(0)
        taskman.complete(1)

        self.assertEqual(received, [("new", 2)])
        self.assertFalse(controller.running)

    def test_invalidate_discards_late_completion_and_close_is_a_permanent_no_op(self):
        taskman = FakeTaskman()
        controller = DocumentImportTaskController(taskman)
        received = []
        importer = lambda _token: DocumentImportWorkerResult(
            document=_document(),
            file_type="text",
            importer_name="TXT",
        )
        controller.submit(
            request=_request(1),
            importer_callback=importer,
            on_complete=received.append,
        )
        controller.invalidate()
        taskman.complete()
        controller.close()

        result = controller.submit(
            request=_request(2),
            importer_callback=importer,
            on_complete=received.append,
        )

        self.assertIsNone(result)
        self.assertEqual(received, [])
        self.assertFalse(controller.alive)

    def test_worker_and_submission_exceptions_become_safe_completion_codes(self):
        taskman = FakeTaskman()
        controller = DocumentImportTaskController(taskman)
        received = []
        controller.submit(
            request=_request(1),
            importer_callback=lambda _token: (_ for _ in ()).throw(
                RuntimeError("C:/Users/private/secret.txt")
            ),
            on_complete=received.append,
        )
        taskman.complete()

        self.assertEqual(received[0].error_code, "document_import_failed")
        self.assertNotIn("private", repr(received[0]).casefold())

        submit_received = []
        raising_taskman = RaisingTaskman()
        second = DocumentImportTaskController(raising_taskman)
        second.submit(
            request=_request(1),
            importer_callback=lambda _token: None,
            on_complete=submit_received.append,
        )
        self.assertFalse(raising_taskman.uses_collection)
        self.assertEqual(
            submit_received[0].error_code,
            "document_import_submit_failed",
        )

    def test_callback_exceptions_do_not_escape_completion(self):
        taskman = FakeTaskman()
        controller = DocumentImportTaskController(taskman)
        controller.submit(
            request=_request(1),
            importer_callback=lambda _token: DocumentImportWorkerResult(
                document=_document(),
                file_type="text",
                importer_name="TXT",
            ),
            on_complete=lambda _completion: (_ for _ in ()).throw(
                RuntimeError("deleted Qt wrapper")
            ),
        )

        taskman.complete()

        self.assertFalse(controller.running)

    def test_controller_rejects_invalid_requests_and_callbacks(self):
        controller = DocumentImportTaskController(FakeTaskman())

        with self.assertRaisesRegex(TypeError, "request"):
            controller.submit(
                request={},
                importer_callback=lambda _token: None,
                on_complete=lambda _completion: None,
            )
        with self.assertRaisesRegex(TypeError, "importer_callback"):
            controller.submit(
                request=_request(1),
                importer_callback=None,
                on_complete=lambda _completion: None,
            )
        with self.assertRaisesRegex(TypeError, "on_complete"):
            controller.submit(
                request=_request(1),
                importer_callback=lambda _token: None,
                on_complete=None,
            )


if __name__ == "__main__":
    unittest.main()
