import math
import unittest
from dataclasses import FrozenInstanceError

from ankiforge_ai.document import limits as document_limits
from ankiforge_ai.document import (
    DEFAULT_DOCUMENT_LIMITS,
    DocumentImportError,
    DocumentLimits,
    get_safe_source_label,
)


class DocumentErrorsAndLimitsTests(unittest.TestCase):
    def test_default_limits_match_the_approved_design_exactly(self):
        expected_constants = {
            "MAX_SOURCE_FILE_BYTES": 10 * 1024 * 1024,
            "MAX_TEXT_FILE_BYTES": 5 * 1024 * 1024,
            "MAX_TOTAL_BATCH_BYTES": 25 * 1024 * 1024,
            "MAX_FILES_PER_BATCH": 20,
            "MAX_ARCHIVE_MEMBERS": 2_048,
            "MAX_ARCHIVE_UNCOMPRESSED_BYTES": 64 * 1024 * 1024,
            "MAX_ARCHIVE_COMPRESSION_RATIO": 100.0,
            "MAX_MEMBER_BYTES": 20 * 1024 * 1024,
            "MAX_DOCUMENT_BLOCKS": 20_000,
            "MAX_TABLE_ROWS": 10_000,
            "MAX_TABLE_COLUMNS": 256,
            "MAX_CELL_CHARS": 32_000,
            "MAX_JSON_DEPTH": 64,
            "MAX_XML_DEPTH": 64,
            "MAX_XML_ELEMENTS": 100_000,
            "MAX_TEXT_CHARS": 5_000_000,
            "MAX_NOTEBOOK_OUTPUT_CHARS": 100_000,
            "MAX_CHUNK_CHARS": 12_000,
            "TARGET_CHUNK_CHARS": 6_000,
            "MAX_DOCUMENT_CHUNKS": 48,
            "MAX_AI_CALLS_PER_RUN": 12,
        }
        self.assertEqual(
            {
                name: getattr(document_limits, name)
                for name in expected_constants
            },
            expected_constants,
        )
        self.assertEqual(
            DEFAULT_DOCUMENT_LIMITS,
            DocumentLimits(
                max_source_file_bytes=10 * 1024 * 1024,
                max_text_file_bytes=5 * 1024 * 1024,
                max_total_batch_bytes=25 * 1024 * 1024,
                max_files_per_batch=20,
                max_archive_members=2_048,
                max_archive_uncompressed_bytes=64 * 1024 * 1024,
                max_archive_compression_ratio=100.0,
                max_member_bytes=20 * 1024 * 1024,
                max_document_blocks=20_000,
                max_table_rows=10_000,
                max_table_columns=256,
                max_cell_chars=32_000,
                max_json_depth=64,
                max_xml_depth=64,
                max_xml_elements=100_000,
                max_text_chars=5_000_000,
                max_notebook_output_chars=100_000,
                max_chunk_chars=12_000,
                target_chunk_chars=6_000,
                max_document_chunks=48,
                max_ai_calls_per_run=12,
            ),
        )
        with self.assertRaises(FrozenInstanceError):
            DEFAULT_DOCUMENT_LIMITS.max_files_per_batch = 99

    def test_limits_reject_non_positive_or_internally_inconsistent_values(self):
        values = dict(DEFAULT_DOCUMENT_LIMITS.to_safe_dict())
        values["max_source_file_bytes"] = 0
        with self.assertRaisesRegex(ValueError, "max_source_file_bytes"):
            DocumentLimits(**values)

        values = dict(DEFAULT_DOCUMENT_LIMITS.to_safe_dict())
        values["target_chunk_chars"] = values["max_chunk_chars"] + 1
        with self.assertRaisesRegex(ValueError, "target_chunk_chars"):
            DocumentLimits(**values)

    def test_integer_limits_reject_bool_floats_nan_and_infinity(self):
        for bad_value in (True, 1.5, math.nan, math.inf, -math.inf):
            with self.subTest(value=bad_value):
                values = dict(DEFAULT_DOCUMENT_LIMITS.to_safe_dict())
                values["max_files_per_batch"] = bad_value
                with self.assertRaises((TypeError, ValueError)):
                    DocumentLimits(**values)

    def test_compression_ratio_requires_finite_positive_numeric_value(self):
        for bad_value in (True, 0, -1, math.nan, math.inf, -math.inf):
            with self.subTest(value=bad_value):
                values = dict(DEFAULT_DOCUMENT_LIMITS.to_safe_dict())
                values["max_archive_compression_ratio"] = bad_value
                with self.assertRaises((TypeError, ValueError)):
                    DocumentLimits(**values)

        values = dict(DEFAULT_DOCUMENT_LIMITS.to_safe_dict())
        values["max_archive_compression_ratio"] = 2
        self.assertEqual(
            DocumentLimits(**values).max_archive_compression_ratio,
            2,
        )

    def test_source_labels_are_basenames_bounded_and_control_free(self):
        self.assertEqual(
            get_safe_source_label(r"C:\Users\alice\Private Notes\lesson.txt"),
            "lesson.txt",
        )
        self.assertEqual(get_safe_source_label("/home/alice/lesson.md"), "lesson.md")
        self.assertEqual(get_safe_source_label("  lesson\n\t.md  "), "lesson .md")
        self.assertEqual(len(get_safe_source_label("x" * 200 + ".txt")), 120)
        self.assertEqual(get_safe_source_label(""), "document")
        with self.assertRaisesRegex(ValueError, "invalid Unicode"):
            get_safe_source_label("unsafe\ud800.txt")

    def test_structured_error_has_stable_safe_fields_and_redacted_repr(self):
        error = DocumentImportError(
            code="optional_importer_unavailable",
            message_key="document.error.optional_importer_unavailable",
            action_key="document.action.choose_native_importer",
            severity="error",
            safe_details={"importer_id": "optional_pdf"},
        )

        self.assertEqual(error.code, "optional_importer_unavailable")
        self.assertEqual(
            str(error), "document.error.optional_importer_unavailable"
        )
        self.assertEqual(error.safe_details, {"importer_id": "optional_pdf"})
        diagnostic = repr(error)
        self.assertIn("optional_importer_unavailable", diagnostic)
        self.assertNotIn(r"C:\Users", diagnostic)
        self.assertNotIn("sk-test-not-a-real-key", diagnostic)
        with self.assertRaises(TypeError):
            error.safe_details["path"] = "changed"

    def test_structured_error_rejects_unsafe_detail_shapes(self):
        with self.assertRaises((TypeError, ValueError)):
            DocumentImportError(
                code="bad",
                message_key="document.error.bad",
                action_key="document.action.retry",
                safe_details={"nested": {"path": "/private"}},
            )
        with self.assertRaises((TypeError, ValueError)):
            DocumentImportError(
                code="bad",
                message_key="document.error.bad",
                action_key="document.action.retry",
                safe_details={"path": r"C:\Users\alice\private.txt"},
            )

        with self.assertRaises(ValueError):
            DocumentImportError(
                code=r"C:\Users\alice\private.txt",
                message_key="document.error.bad",
                action_key="document.action.retry",
            )

    def test_metadata_and_error_details_reject_credential_values_safely(self):
        secrets = (
            "sk-test-not-a-real-key-000000",
            "Bearer fake-access-token-1234567890",
        )
        for secret in secrets:
            with self.subTest(kind="metadata", secret_kind=secret.split()[0]):
                with self.assertRaises(ValueError) as raised:
                    from ankiforge_ai.document import BlockKind, DocumentBlock

                    DocumentBlock(
                        block_id="b" * 64,
                        kind=BlockKind.METADATA,
                        text="safe",
                        metadata={"note": secret},
                    )
                self.assertNotIn(secret, str(raised.exception))
                self.assertNotIn(secret, repr(raised.exception))

            with self.subTest(kind="error", secret_kind=secret.split()[0]):
                with self.assertRaises(ValueError) as raised:
                    DocumentImportError(
                        code="bad",
                        message_key="document.error.bad",
                        action_key="document.action.retry",
                        safe_details={"diagnostic": secret},
                    )
                self.assertNotIn(secret, str(raised.exception))
                self.assertNotIn(secret, repr(raised.exception))

        from ankiforge_ai.document import BlockKind, DocumentBlock

        ordinary = DocumentBlock(
            block_id="b" * 64,
            kind=BlockKind.METADATA,
            text="safe",
            metadata={"note": "The API key is not saved by this application."},
        )
        self.assertEqual(
            ordinary.metadata["note"],
            "The API key is not saved by this application.",
        )


if __name__ == "__main__":
    unittest.main()
