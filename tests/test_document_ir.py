import json
import unittest
from dataclasses import FrozenInstanceError

from ankiforge_ai.document import (
    BlockKind,
    DocumentBlock,
    DocumentIR,
    DocumentSection,
    DocumentWarning,
    SourceLocation,
    count_blocks_by_kind,
    document_from_safe_json,
    document_summary,
    document_to_plain_text,
    document_to_safe_json,
    document_to_safe_markdown,
    validate_document_ir,
)


DOCUMENT_ID = "a" * 64
SECTION_ONE_ID = "b" * 64
SECTION_TWO_ID = "c" * 64
HEADING_BLOCK_ID = "d" * 64
PARAGRAPH_BLOCK_ID = "e" * 64
CODE_BLOCK_ID = "f" * 64


def make_document(document_metadata=None, paragraph_metadata=None):
    paragraph_metadata = (
        {"importance": 2, "reviewed": False}
        if paragraph_metadata is None
        else paragraph_metadata
    )
    first_blocks = [
        DocumentBlock(
            block_id=HEADING_BLOCK_ID,
            kind=BlockKind.HEADING,
            text="Safety",
            location=SourceLocation(file_label="lesson.md", line_start=1, line_end=1),
        ),
        DocumentBlock(
            block_id=PARAGRAPH_BLOCK_ID,
            kind=BlockKind.PARAGRAPH,
            text="Never execute imported content.",
            location=SourceLocation(file_label="lesson.md", line_start=3, line_end=3),
            metadata=paragraph_metadata,
        ),
    ]
    sections = [
        DocumentSection(
            section_id=SECTION_ONE_ID,
            heading="Safety",
            heading_path=["Guide", "Safety"],
            location=SourceLocation(file_label="lesson.md", section="Safety"),
            blocks=first_blocks,
        ),
        DocumentSection(
            section_id=SECTION_TWO_ID,
            heading="Example",
            heading_path=["Guide", "Example"],
            location=SourceLocation(file_label="lesson.md", section="Example"),
            blocks=[
                DocumentBlock(
                    block_id=CODE_BLOCK_ID,
                    kind=BlockKind.CODE,
                    text="print('not executed')",
                    location=SourceLocation(
                        file_label="lesson.md", line_start=7, line_end=7
                    ),
                    metadata={"language": "python"},
                )
            ],
        ),
    ]
    warnings = [
        DocumentWarning(
            code="images_skipped",
            severity="warning",
            message_key="document.warning.images_skipped",
            action_key="document.action.review_source",
            location=SourceLocation(file_label="lesson.md", section="Example"),
        )
    ]
    document = DocumentIR(
        schema_version=1,
        document_id=DOCUMENT_ID,
        title="Import safety guide",
        language_hint="en",
        source_type="markdown",
        source_label="lesson.md",
        metadata=(
            {"course": "Security"}
            if document_metadata is None
            else document_metadata
        ),
        sections=sections,
        warnings=warnings,
        original_char_count=59,
        extracted_char_count=59,
    )
    return document, sections, first_blocks, warnings


class DocumentIRTests(unittest.TestCase):
    def test_document_and_nested_inputs_are_immutable_snapshots(self):
        document_metadata = {"course": "Security"}
        paragraph_metadata = {"importance": 2, "reviewed": False}
        document, sections, first_blocks, warnings = make_document(
            document_metadata, paragraph_metadata
        )

        document_metadata["course"] = "Changed"
        paragraph_metadata["importance"] = 99
        sections.clear()
        first_blocks.clear()
        warnings.clear()

        self.assertEqual(document.metadata["course"], "Security")
        self.assertEqual(document.sections[0].blocks[1].metadata["importance"], 2)
        self.assertEqual(len(document.sections), 2)
        self.assertEqual(len(document.sections[0].blocks), 2)
        self.assertEqual(len(document.warnings), 1)
        with self.assertRaises(TypeError):
            document.metadata["course"] = "Changed"
        with self.assertRaises(FrozenInstanceError):
            document.title = "Changed"

    def test_safe_dictionary_is_literal_json_compatible_copy(self):
        document, *_ = make_document()
        expected = {
            "schema_version": 1,
            "document_id": DOCUMENT_ID,
            "title": "Import safety guide",
            "language_hint": "en",
            "source_type": "markdown",
            "source_label": "lesson.md",
            "metadata": {"course": "Security"},
            "sections": [
                {
                    "section_id": SECTION_ONE_ID,
                    "heading": "Safety",
                    "heading_path": ["Guide", "Safety"],
                    "location": {
                        "file_label": "lesson.md",
                        "page": None,
                        "slide": None,
                        "sheet": None,
                        "row_start": None,
                        "row_end": None,
                        "cell_range": None,
                        "section": "Safety",
                        "timestamp_start": None,
                        "timestamp_end": None,
                        "notebook_cell": None,
                        "line_start": None,
                        "line_end": None,
                    },
                    "blocks": [
                        {
                            "block_id": HEADING_BLOCK_ID,
                            "kind": "heading",
                            "text": "Safety",
                            "location": {
                                "file_label": "lesson.md",
                                "page": None,
                                "slide": None,
                                "sheet": None,
                                "row_start": None,
                                "row_end": None,
                                "cell_range": None,
                                "section": None,
                                "timestamp_start": None,
                                "timestamp_end": None,
                                "notebook_cell": None,
                                "line_start": 1,
                                "line_end": 1,
                            },
                            "metadata": {},
                        },
                        {
                            "block_id": PARAGRAPH_BLOCK_ID,
                            "kind": "paragraph",
                            "text": "Never execute imported content.",
                            "location": {
                                "file_label": "lesson.md",
                                "page": None,
                                "slide": None,
                                "sheet": None,
                                "row_start": None,
                                "row_end": None,
                                "cell_range": None,
                                "section": None,
                                "timestamp_start": None,
                                "timestamp_end": None,
                                "notebook_cell": None,
                                "line_start": 3,
                                "line_end": 3,
                            },
                            "metadata": {"importance": 2, "reviewed": False},
                        },
                    ],
                },
                {
                    "section_id": SECTION_TWO_ID,
                    "heading": "Example",
                    "heading_path": ["Guide", "Example"],
                    "location": {
                        "file_label": "lesson.md",
                        "page": None,
                        "slide": None,
                        "sheet": None,
                        "row_start": None,
                        "row_end": None,
                        "cell_range": None,
                        "section": "Example",
                        "timestamp_start": None,
                        "timestamp_end": None,
                        "notebook_cell": None,
                        "line_start": None,
                        "line_end": None,
                    },
                    "blocks": [
                        {
                            "block_id": CODE_BLOCK_ID,
                            "kind": "code",
                            "text": "print('not executed')",
                            "location": {
                                "file_label": "lesson.md",
                                "page": None,
                                "slide": None,
                                "sheet": None,
                                "row_start": None,
                                "row_end": None,
                                "cell_range": None,
                                "section": None,
                                "timestamp_start": None,
                                "timestamp_end": None,
                                "notebook_cell": None,
                                "line_start": 7,
                                "line_end": 7,
                            },
                            "metadata": {"language": "python"},
                        }
                    ],
                },
            ],
            "warnings": [
                {
                    "code": "images_skipped",
                    "severity": "warning",
                    "message_key": "document.warning.images_skipped",
                    "action_key": "document.action.review_source",
                    "location": {
                        "file_label": "lesson.md",
                        "page": None,
                        "slide": None,
                        "sheet": None,
                        "row_start": None,
                        "row_end": None,
                        "cell_range": None,
                        "section": "Example",
                        "timestamp_start": None,
                        "timestamp_end": None,
                        "notebook_cell": None,
                        "line_start": None,
                        "line_end": None,
                    },
                }
            ],
            "original_char_count": 59,
            "extracted_char_count": 59,
        }

        first = document.to_safe_dict()
        self.assertEqual(first, expected)
        json.dumps(first)
        first["metadata"]["course"] = "Changed"
        first["sections"][0]["blocks"][1]["text"] = "Changed"
        self.assertEqual(document.to_safe_dict(), expected)

    def test_repr_excludes_source_content_paths_and_credentials(self):
        secret_body = (
            r"C:\Users\alice\private\lesson.md "
            "Never execute imported content. "
            "sk-test-not-a-real-key-000000"
        )
        block = DocumentBlock(
            block_id=PARAGRAPH_BLOCK_ID,
            kind=BlockKind.PARAGRAPH,
            text=secret_body,
            location=SourceLocation(file_label="lesson.md"),
        )
        document = DocumentIR(
            schema_version=1,
            document_id=DOCUMENT_ID,
            title="Lesson",
            language_hint=None,
            source_type="text",
            source_label="lesson.md",
            sections=(
                DocumentSection(
                    section_id=SECTION_ONE_ID,
                    heading=None,
                    blocks=(block,),
                ),
            ),
            original_char_count=len(secret_body),
            extracted_char_count=len(secret_body),
        )

        diagnostic = repr(document) + repr(block)
        self.assertNotIn(r"C:\Users\alice", diagnostic)
        self.assertNotIn("Never execute imported content.", diagnostic)
        self.assertNotIn("sk-test-not-a-real-key", diagnostic)
        self.assertIn(DOCUMENT_ID, repr(document))
        self.assertIn("blocks=1", repr(document))

    def test_renderers_counts_summary_and_json_round_trip_are_deterministic(self):
        document, *_ = make_document()

        self.assertEqual(
            document_to_plain_text(document),
            "Safety\nNever execute imported content.\n\nprint('not executed')",
        )
        self.assertEqual(
            document_to_safe_markdown(document),
            "## Safety\n\nNever execute imported content.\n\n"
            "## Example\n\n```python\nprint('not executed')\n```",
        )
        self.assertEqual(
            count_blocks_by_kind(document),
            {"code": 1, "heading": 1, "paragraph": 1},
        )
        self.assertEqual(
            document_summary(document),
            {
                "document_id": DOCUMENT_ID,
                "title": "Import safety guide",
                "source_type": "markdown",
                "source_label": "lesson.md",
                "section_count": 2,
                "block_count": 3,
                "warning_count": 1,
                "original_char_count": 59,
                "extracted_char_count": 59,
                "blocks_by_kind": {"code": 1, "heading": 1, "paragraph": 1},
            },
        )
        payload = document_to_safe_json(document)
        self.assertEqual(payload, document_to_safe_json(document))
        self.assertEqual(document_from_safe_json(payload), document)

    def test_invalid_ids_duplicate_ids_and_unknown_kinds_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "block_id"):
            DocumentBlock(
                block_id="../private",
                kind=BlockKind.PARAGRAPH,
                text="text",
            )
        with self.assertRaisesRegex(ValueError, "kind"):
            DocumentBlock(
                block_id=PARAGRAPH_BLOCK_ID,
                kind="unknown",
                text="text",
            )

        duplicate = DocumentBlock(
            block_id=PARAGRAPH_BLOCK_ID,
            kind=BlockKind.PARAGRAPH,
            text="text",
        )
        with self.assertRaisesRegex(ValueError, "duplicate block_id"):
            DocumentIR(
                schema_version=1,
                document_id=DOCUMENT_ID,
                title="Duplicate",
                language_hint=None,
                source_type="text",
                source_label="duplicate.txt",
                sections=(
                    DocumentSection(
                        section_id=SECTION_ONE_ID,
                        heading=None,
                        blocks=(duplicate,),
                    ),
                    DocumentSection(
                        section_id=SECTION_TWO_ID,
                        heading=None,
                        blocks=(duplicate,),
                    ),
                ),
                original_char_count=4,
                extracted_char_count=4,
            )

    def test_unsafe_metadata_absolute_labels_and_invalid_ranges_are_rejected(self):
        for metadata in (
            {"nested": ["not", "a", "scalar"]},
            {"x" * 121: "value"},
            {"value": "x" * 2001},
            {1: "non-string-key"},
        ):
            with self.subTest(metadata=repr(metadata)[:40]):
                with self.assertRaises((TypeError, ValueError)):
                    DocumentBlock(
                        block_id=PARAGRAPH_BLOCK_ID,
                        kind=BlockKind.PARAGRAPH,
                        text="text",
                        metadata=metadata,
                    )

        for label in (r"C:\private\lesson.txt", "/private/lesson.txt", "../lesson.txt"):
            with self.subTest(label=label):
                with self.assertRaisesRegex(ValueError, "file_label|source_label"):
                    SourceLocation(file_label=label)

        with self.assertRaisesRegex(ValueError, "line"):
            SourceLocation(file_label="lesson.txt", line_start=5, line_end=4)

    def test_validation_enforces_text_and_block_limits(self):
        document, *_ = make_document()
        validate_document_ir(document)

        overlong = DocumentIR(
            schema_version=1,
            document_id=DOCUMENT_ID,
            title="Large",
            language_hint=None,
            source_type="text",
            source_label="large.txt",
            sections=(
                DocumentSection(
                    section_id=SECTION_ONE_ID,
                    heading=None,
                    blocks=(
                        DocumentBlock(
                            block_id=PARAGRAPH_BLOCK_ID,
                            kind=BlockKind.PARAGRAPH,
                            text="12345",
                        ),
                    ),
                ),
            ),
            original_char_count=5,
            extracted_char_count=5,
        )
        with self.assertRaisesRegex(ValueError, "MAX_TEXT_CHARS"):
            validate_document_ir(overlong, max_text_chars=4)
        with self.assertRaisesRegex(ValueError, "MAX_DOCUMENT_BLOCKS"):
            validate_document_ir(overlong, max_document_blocks=0)

    def test_validation_counts_metadata_and_rejects_invalid_location_objects(self):
        document = DocumentIR(
            schema_version=1,
            document_id=DOCUMENT_ID,
            title="T",
            language_hint=None,
            source_type="text",
            source_label="safe.txt",
            metadata={"description": "1234567890"},
            sections=(),
            original_char_count=0,
            extracted_char_count=0,
        )
        with self.assertRaisesRegex(ValueError, "MAX_TEXT_CHARS"):
            validate_document_ir(document, max_text_chars=5)

        with self.assertRaisesRegex(TypeError, "location"):
            DocumentBlock(
                block_id=PARAGRAPH_BLOCK_ID,
                kind=BlockKind.PARAGRAPH,
                text="text",
                location="not-a-location",
            )

        with self.assertRaisesRegex(ValueError, "sheet"):
            SourceLocation(file_label="safe.xlsx", sheet=r"C:\private\sheet")

    def test_safe_json_rejects_nesting_beyond_the_design_limit(self):
        payload = '{"x":' + "[" * 65 + "0" + "]" * 65 + "}"
        with self.assertRaisesRegex(ValueError, "MAX_JSON_DEPTH"):
            document_from_safe_json(payload)

    def test_safe_json_rejects_duplicate_object_keys(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            document_from_safe_json('{"sections":[],"sections":[]}')

    def test_safe_json_rejects_unknown_keys_at_every_schema_level(self):
        document, *_ = make_document()
        safe = document.to_safe_dict()
        mutations = (
            lambda value: value.__setitem__("unknown_root", "value"),
            lambda value: value["sections"][0].__setitem__("unknown_section", 1),
            lambda value: value["sections"][0]["blocks"][0].__setitem__(
                "unknown_block", 1
            ),
            lambda value: value["warnings"][0].__setitem__("unknown_warning", 1),
            lambda value: value["sections"][0]["location"].__setitem__(
                "unknown_location", 1
            ),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(level=index):
                candidate = json.loads(json.dumps(safe))
                mutate(candidate)
                with self.assertRaisesRegex(ValueError, "unexpected keys"):
                    document_from_safe_json(json.dumps(candidate))

    def test_safe_json_rejects_huge_unknown_padding_before_normalization(self):
        payload = '{"padding":"' + "x" * 5_000_001 + '"}'
        with self.assertRaisesRegex(ValueError, "MAX_TEXT_CHARS"):
            document_from_safe_json(payload)

    def test_all_document_numeric_fields_are_serialization_safe_and_bounded(self):
        with self.assertRaisesRegex(ValueError, "original_char_count"):
            DocumentIR(
                schema_version=1,
                document_id=DOCUMENT_ID,
                title="Large",
                language_hint=None,
                source_type="text",
                source_label="large.txt",
                original_char_count=10**10_000,
                extracted_char_count=0,
            )
        with self.assertRaisesRegex(ValueError, "line_start"):
            SourceLocation(file_label="large.txt", line_start=10**10_000)

    def test_surrogate_code_points_are_rejected_from_serialized_model_strings(self):
        surrogate = "\ud800"
        constructors = (
            lambda: DocumentBlock(
                block_id=PARAGRAPH_BLOCK_ID,
                kind=BlockKind.PARAGRAPH,
                text=f"unsafe{surrogate}body",
            ),
            lambda: DocumentBlock(
                block_id=PARAGRAPH_BLOCK_ID,
                kind=BlockKind.METADATA,
                text="safe",
                metadata={"note": f"unsafe{surrogate}value"},
            ),
            lambda: DocumentBlock(
                block_id=PARAGRAPH_BLOCK_ID,
                kind=BlockKind.METADATA,
                text="safe",
                metadata={f"unsafe{surrogate}key": "value"},
            ),
            lambda: SourceLocation(file_label=f"unsafe{surrogate}.txt"),
            lambda: SourceLocation(file_label="safe.xlsx", sheet=f"unsafe{surrogate}"),
            lambda: DocumentSection(
                section_id=SECTION_ONE_ID,
                heading=f"unsafe{surrogate}",
            ),
            lambda: DocumentIR(
                schema_version=1,
                document_id=DOCUMENT_ID,
                title=f"unsafe{surrogate}",
                language_hint=None,
                source_type="text",
                source_label="safe.txt",
            ),
        )
        for index, construct in enumerate(constructors):
            with self.subTest(case=index):
                with self.assertRaisesRegex(ValueError, "invalid Unicode") as raised:
                    construct()
                self.assertNotIn(surrogate, str(raised.exception))
                self.assertNotIn(surrogate, repr(raised.exception))

    def test_safe_json_input_wraps_surrogate_encoding_failure(self):
        payload = '{"unsafe":"\ud800"}'
        with self.assertRaisesRegex(ValueError, "invalid Unicode") as raised:
            document_from_safe_json(payload)
        self.assertNotIsInstance(raised.exception, UnicodeEncodeError)
        self.assertNotIn("\ud800", str(raised.exception))

    def test_astral_unicode_remains_round_trip_safe(self):
        document, *_ = make_document()
        safe = document.to_safe_dict()
        safe["title"] = "Astronomy 🚀"
        restored = document_from_safe_json(
            json.dumps(safe, ensure_ascii=False, separators=(",", ":"))
        )
        self.assertEqual(restored.title, "Astronomy 🚀")


if __name__ == "__main__":
    unittest.main()
