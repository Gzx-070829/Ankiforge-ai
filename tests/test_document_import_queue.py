import unittest
from dataclasses import FrozenInstanceError, replace

from ankiforge_ai.document import (
    BlockKind,
    DocumentBlock,
    DocumentIR,
    DocumentSection,
)
from ankiforge_ai.ui.document_import_queue import (
    DocumentImportStatus,
    DocumentImportTaskCompletion,
    DocumentImportWorkerResult,
    PrivatePathToken,
    add_import_paths,
    apply_import_completion,
    begin_import,
    create_import_queue,
    move_import_item,
    remove_import_item,
    retry_failed_imports,
)


def _token(name, size=100):
    return PrivatePathToken.from_path(
        f"C:/Users/private/Documents/{name}",
        byte_size=size,
    )


def _document(label, *, warning_codes=()):
    block = DocumentBlock(
        block_id=f"block-{label.replace('.', '-')}",
        kind=BlockKind.PARAGRAPH,
        text="Private extracted source text must not appear in queue rows.",
    )
    return DocumentIR(
        schema_version=1,
        document_id=f"doc-{label.replace('.', '-')}",
        title=label,
        language_hint="en",
        source_type="text",
        source_label=label,
        sections=(
            DocumentSection(
                section_id=f"section-{label.replace('.', '-')}",
                heading="Overview",
                blocks=(block,),
            ),
        ),
        original_char_count=len(block.text),
        extracted_char_count=len(block.text),
        warnings=tuple(warning_codes),
    )


class DocumentImportQueueTests(unittest.TestCase):
    def test_queue_preserves_twenty_selected_files_and_rejects_the_twenty_first(self):
        tokens = tuple(_token(f"{index:02}.txt") for index in range(20))

        queue = create_import_queue(tokens)

        self.assertEqual(
            tuple(row.filename for row in queue.safe_rows),
            tuple(f"{index:02}.txt" for index in range(20)),
        )
        self.assertEqual(queue.total_bytes, 2_000)
        with self.assertRaisesRegex(ValueError, "too_many_files"):
            add_import_paths(queue, (_token("overflow.txt"),))

    def test_batch_byte_limit_is_enforced_before_any_item_is_added(self):
        below_limit = 25 * 1024 * 1024 - 1
        queue = create_import_queue((_token("large.docx", below_limit),))

        with self.assertRaisesRegex(ValueError, "batch_too_large"):
            add_import_paths(queue, (_token("one-byte-too-many.txt", 2),))

        self.assertEqual(
            tuple(row.filename for row in queue.safe_rows),
            ("large.docx",),
        )

    def test_add_remove_and_reorder_return_new_queues_without_mutating_input(self):
        original = create_import_queue((_token("a.txt"), _token("b.md")))
        added = add_import_paths(original, (_token("c.docx"),))
        moved = move_import_item(added, 2, 0)
        removed = remove_import_item(moved, 1)

        self.assertEqual(
            tuple(row.filename for row in original.safe_rows),
            ("a.txt", "b.md"),
        )
        self.assertEqual(
            tuple(row.filename for row in added.safe_rows),
            ("a.txt", "b.md", "c.docx"),
        )
        self.assertEqual(
            tuple(row.filename for row in moved.safe_rows),
            ("c.docx", "a.txt", "b.md"),
        )
        self.assertEqual(
            tuple(row.filename for row in removed.safe_rows),
            ("c.docx", "b.md"),
        )

    def test_private_paths_and_document_text_are_absent_from_repr_and_safe_dicts(self):
        token = _token("secret-notes.txt")
        queue = create_import_queue((token,))
        importing, request = begin_import(queue, 0)
        document = _document("secret-notes.txt")
        completion = DocumentImportTaskCompletion(
            request_id=request.request_id,
            item_id=request.item_id,
            result=DocumentImportWorkerResult(
                document=document,
                file_type="text",
                importer_name="TXT",
            ),
        )
        completed = apply_import_completion(importing, completion)

        rendered = (
            repr(token)
            + repr(queue)
            + repr(importing)
            + repr(request)
            + repr(completion)
            + repr(completed)
            + str(token.to_safe_dict())
            + str(completed.to_safe_dict())
        )
        self.assertNotIn("C:/Users/private", rendered)
        self.assertNotIn("Private extracted source text", rendered)
        self.assertNotIn("path", str(token.to_safe_dict()).casefold())
        self.assertEqual(
            set(completed.safe_rows[0].to_safe_dict()),
            {
                "filename",
                "file_type",
                "importer",
                "status",
                "section_count",
                "block_count",
                "char_count",
                "warnings",
            },
        )

    def test_success_warning_and_failure_are_applied_independently(self):
        queue = create_import_queue(
            (_token("ok.txt"), _token("warning.md"), _token("bad.pdf"))
        )
        requests = []
        for index in range(3):
            queue, request = begin_import(queue, index)
            requests.append(request)

        queue = apply_import_completion(
            queue,
            DocumentImportTaskCompletion(
                request_id=requests[0].request_id,
                item_id=requests[0].item_id,
                result=DocumentImportWorkerResult(
                    document=_document("ok.txt"),
                    file_type="text",
                    importer_name="TXT",
                ),
            ),
        )
        queue = apply_import_completion(
            queue,
            DocumentImportTaskCompletion(
                request_id=requests[1].request_id,
                item_id=requests[1].item_id,
                result=DocumentImportWorkerResult(
                    document=_document("warning.md"),
                    file_type="markdown",
                    importer_name="Markdown",
                    warning_codes=("structure_simplified",),
                ),
            ),
        )
        queue = apply_import_completion(
            queue,
            DocumentImportTaskCompletion(
                request_id=requests[2].request_id,
                item_id=requests[2].item_id,
                error_code="optional_backend_missing",
            ),
        )

        self.assertEqual(
            tuple(row.status for row in queue.safe_rows),
            (
                DocumentImportStatus.SUCCESS,
                DocumentImportStatus.WARNING,
                DocumentImportStatus.FAILURE,
            ),
        )
        self.assertEqual(queue.successful_documents, (_document("ok.txt"), _document("warning.md")))
        self.assertEqual(queue.safe_rows[1].warnings, ("structure_simplified",))
        self.assertEqual(
            queue.safe_rows[2].warnings,
            ("optional_backend_missing",),
        )

    def test_stale_completion_is_ignored_after_a_new_request_for_same_item(self):
        queue = create_import_queue((_token("retry.txt"),))
        first_queue, first = begin_import(queue, 0)
        failed = apply_import_completion(
            first_queue,
            DocumentImportTaskCompletion(
                request_id=first.request_id,
                item_id=first.item_id,
                error_code="document_empty",
            ),
        )
        retrying, retry_requests = retry_failed_imports(failed)
        second = retry_requests[0]

        stale = apply_import_completion(
            retrying,
            DocumentImportTaskCompletion(
                request_id=first.request_id,
                item_id=first.item_id,
                result=DocumentImportWorkerResult(
                    document=_document("retry.txt"),
                    file_type="text",
                    importer_name="TXT",
                ),
            ),
        )

        self.assertIs(stale, retrying)
        self.assertEqual(stale.safe_rows[0].status, DocumentImportStatus.IMPORTING)
        self.assertGreater(second.request_id, first.request_id)

    def test_failed_only_retry_requires_explicit_transition_and_preserves_success(self):
        queue = create_import_queue((_token("ok.txt"), _token("bad.txt")))
        queue, ok_request = begin_import(queue, 0)
        queue, bad_request = begin_import(queue, 1)
        queue = apply_import_completion(
            queue,
            DocumentImportTaskCompletion(
                request_id=ok_request.request_id,
                item_id=ok_request.item_id,
                result=DocumentImportWorkerResult(
                    document=_document("ok.txt"),
                    file_type="text",
                    importer_name="TXT",
                ),
            ),
        )
        failed = apply_import_completion(
            queue,
            DocumentImportTaskCompletion(
                request_id=bad_request.request_id,
                item_id=bad_request.item_id,
                error_code="document_empty",
            ),
        )

        self.assertEqual(failed.safe_rows[1].status, DocumentImportStatus.FAILURE)
        retrying, requests = retry_failed_imports(failed)

        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].item_id, bad_request.item_id)
        self.assertEqual(
            tuple(row.status for row in retrying.safe_rows),
            (DocumentImportStatus.SUCCESS, DocumentImportStatus.IMPORTING),
        )
        self.assertEqual(retrying.successful_documents, (_document("ok.txt"),))

    def test_serial_multi_file_queue_stays_pending_until_every_import_finishes(self):
        queue = create_import_queue((_token("first.txt"), _token("second.txt")))
        queue, first = begin_import(queue, 0)
        queue, second = begin_import(queue, 1)

        queue = apply_import_completion(
            queue,
            DocumentImportTaskCompletion(
                request_id=first.request_id,
                item_id=first.item_id,
                result=DocumentImportWorkerResult(
                    document=_document("first.txt"),
                    file_type="text",
                    importer_name="TXT",
                ),
            ),
        )

        self.assertTrue(queue.imports_pending)
        self.assertEqual(
            tuple(row.status for row in queue.safe_rows),
            (DocumentImportStatus.SUCCESS, DocumentImportStatus.IMPORTING),
        )

        queue = apply_import_completion(
            queue,
            DocumentImportTaskCompletion(
                request_id=second.request_id,
                item_id=second.item_id,
                result=DocumentImportWorkerResult(
                    document=_document("second.txt"),
                    file_type="text",
                    importer_name="TXT",
                ),
            ),
        )

        self.assertFalse(queue.imports_pending)

    def test_models_are_frozen_and_request_identity_cannot_be_rewritten(self):
        queue = create_import_queue((_token("immutable.txt"),))
        _queue, request = begin_import(queue, 0)

        with self.assertRaises(FrozenInstanceError):
            request.request_id = 99
        with self.assertRaisesRegex(ValueError, "request_id"):
            replace(request, request_id=0)


if __name__ == "__main__":
    unittest.main()
