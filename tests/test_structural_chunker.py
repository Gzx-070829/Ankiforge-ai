import unittest

from ankiforge_ai.document import (
    BlockKind,
    DocumentBlock,
    DocumentIR,
    DocumentSection,
    SourceLocation,
)
from ankiforge_ai.intelligence.chunking import DocumentChunk, chunk_document
from ankiforge_ai.intelligence.chunking.table_chunker import _iter_lines
from ankiforge_ai.intelligence.chunking.token_budget import split_text_to_budget


class _SliceCountingText(str):
    slice_count = 0
    max_slices = 49

    def __getitem__(self, key):
        if isinstance(key, slice):
            type(self).slice_count += 1
            if type(self).slice_count > type(self).max_slices:
                raise AssertionError("splitter materialized beyond cap+1")
        return super().__getitem__(key)


class _LazyTableText(str):
    row_slice_count = 0
    splitlines_count = 0

    def splitlines(self, *args, **kwargs):
        type(self).splitlines_count += 1
        raise AssertionError("table splitter must not materialize all lines")

    def __getitem__(self, key):
        result = super().__getitem__(key)
        if isinstance(key, slice) and result == "r":
            type(self).row_slice_count += 1
            if type(self).row_slice_count > 49:
                raise AssertionError("table splitter read beyond cap+1 rows")
        return result


class _LinearTableText(str):
    index_visits = 0
    separator_search_span = 0

    def find(self, sub, start=0, end=None):
        resolved_end = len(self) if end is None else end
        type(self).separator_search_span += max(0, resolved_end - start)
        if end is None:
            return super().find(sub, start)
        return super().find(sub, start, end)

    def __getitem__(self, key):
        if isinstance(key, int):
            type(self).index_visits += 1
        return super().__getitem__(key)


def _document(*sections, document_id="doc-chunks", source_label="notes.md"):
    char_count = sum(
        len(block.text) for section in sections for block in section.blocks
    )
    return DocumentIR(
        schema_version=1,
        document_id=document_id,
        title="Chunk fixture",
        language_hint="en",
        source_type="markdown",
        source_label=source_label,
        sections=tuple(sections),
        original_char_count=char_count,
        extracted_char_count=char_count,
    )


class StructuralChunkerTests(unittest.TestCase):
    def test_merges_adjacent_peers_under_heading_and_keeps_list_intact(self):
        location = SourceLocation(
            file_label="notes.md", page=2, section="Cell cycle"
        )
        document = _document(
            DocumentSection(
                section_id="cell-cycle",
                heading="Cell cycle",
                heading_path=("Biology", "Cell cycle"),
                location=location,
                blocks=(
                    DocumentBlock(
                        "overview",
                        BlockKind.PARAGRAPH,
                        "The cell cycle coordinates growth and division.",
                        location,
                    ),
                    DocumentBlock(
                        "stages",
                        BlockKind.LIST,
                        "- G1 growth\n- S replication\n- M division",
                        location,
                    ),
                ),
            )
        )

        chunks = chunk_document(document, target_chars=180, max_chars=240)

        self.assertEqual(len(chunks), 1)
        self.assertTrue(chunks[0].text.startswith("# Biology > Cell cycle\n\n"))
        self.assertIn("- G1 growth\n- S replication\n- M division", chunks[0].text)
        self.assertEqual(chunks[0].block_ids, ("overview", "stages"))
        self.assertEqual(chunks[0].source_locations, (location,))
        self.assertEqual(chunks[0].section_id, "cell-cycle")

    def test_table_splits_by_rows_and_repeats_header_without_exceeding_max(self):
        rows = ["Name | Value"] + [
            f"item-{index:02d} | {'x' * 18}" for index in range(12)
        ]
        location = SourceLocation(
            file_label="table.csv",
            sheet="Data",
            row_start=1,
            row_end=13,
        )
        document = _document(
            DocumentSection(
                section_id="data",
                heading="Data",
                heading_path=("Data",),
                location=location,
                blocks=(
                    DocumentBlock(
                        "table",
                        BlockKind.TABLE,
                        "\n".join(rows),
                        location,
                    ),
                ),
            ),
            source_label="table.csv",
        )

        chunks = chunk_document(document, target_chars=100, max_chars=140)

        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(chunk.char_count, 140)
            self.assertEqual(chunk.text.count("Name | Value"), 1)
            self.assertEqual(chunk.block_ids, ("table",))
            self.assertEqual(chunk.source_locations, (location,))
        rendered_rows = [
            line
            for chunk in chunks
            for line in chunk.text.splitlines()
            if line.startswith("item-")
        ]
        self.assertEqual(rendered_rows, rows[1:])

    def test_code_and_formula_stay_with_neighboring_explanations(self):
        document = _document(
            DocumentSection(
                section_id="code-formula",
                heading="Examples",
                heading_path=("Examples",),
                blocks=(
                    DocumentBlock(
                        "code-explanation",
                        BlockKind.PARAGRAPH,
                        "The function returns the square of its input.",
                    ),
                    DocumentBlock(
                        "code",
                        BlockKind.CODE,
                        "def square(value):\n    return value * value",
                    ),
                    DocumentBlock(
                        "formula-explanation",
                        BlockKind.PARAGRAPH,
                        "Kinetic energy depends on mass and squared velocity.",
                    ),
                    DocumentBlock(
                        "formula",
                        BlockKind.FORMULA,
                        "E = 1/2 * m * v^2",
                    ),
                ),
            )
        )

        chunks = chunk_document(document, target_chars=115, max_chars=180)

        code_chunk = next(chunk for chunk in chunks if "def square" in chunk.text)
        formula_chunk = next(chunk for chunk in chunks if "E = 1/2" in chunk.text)
        self.assertIn("function returns the square", code_chunk.text)
        self.assertIn("Kinetic energy depends", formula_chunk.text)
        self.assertEqual(
            code_chunk.block_ids, ("code-explanation", "code")
        )
        self.assertEqual(
            formula_chunk.block_ids, ("formula-explanation", "formula")
        )

    def test_retains_slide_sheet_chapter_and_timestamp_provenance(self):
        locations = (
            SourceLocation(file_label="deck.pptx", slide=1),
            SourceLocation(file_label="deck.pptx", slide=2),
            SourceLocation(file_label="book.epub", section="Chapter 3"),
            SourceLocation(
                file_label="talk.vtt",
                timestamp_start=12.5,
                timestamp_end=18.0,
            ),
            SourceLocation(file_label="book.xlsx", sheet="Sheet B", cell_range="A2"),
        )
        sections = tuple(
            DocumentSection(
                section_id=f"boundary-{index}",
                heading=f"Boundary {index}",
                heading_path=(f"Boundary {index}",),
                location=location,
                blocks=(
                    DocumentBlock(
                        f"boundary-block-{index}",
                        (
                            BlockKind.TRANSCRIPT
                            if location.timestamp_start is not None
                            else BlockKind.PARAGRAPH
                        ),
                        f"Evidence for boundary {index}.",
                        location,
                    ),
                ),
            )
            for index, location in enumerate(locations)
        )

        chunks = chunk_document(_document(*sections), target_chars=600)

        self.assertEqual(len(chunks), 5)
        self.assertEqual(
            tuple(chunk.source_locations[0] for chunk in chunks), locations
        )
        self.assertEqual(
            tuple(chunk.section_id for chunk in chunks),
            tuple(f"boundary-{index}" for index in range(5)),
        )

    def test_every_source_location_field_is_a_same_section_boundary(self):
        base = {
            "file_label": "one.md",
            "page": 1,
            "slide": 1,
            "sheet": "Sheet A",
            "row_start": 1,
            "row_end": 2,
            "cell_range": "A1",
            "section": "Chapter",
            "timestamp_start": 1.0,
            "timestamp_end": 2.0,
            "notebook_cell": 1,
            "line_start": 1,
            "line_end": 2,
        }
        changes = {
            "file_label": "two.md",
            "page": 2,
            "slide": 2,
            "sheet": "Sheet B",
            "row_start": 2,
            "row_end": 3,
            "cell_range": "B1",
            "section": "Appendix",
            "timestamp_start": 1.5,
            "timestamp_end": 3.0,
            "notebook_cell": 2,
            "line_start": 2,
            "line_end": 3,
        }

        for field, changed_value in changes.items():
            with self.subTest(field=field):
                first = SourceLocation(**base)
                second_values = dict(base)
                second_values[field] = changed_value
                second = SourceLocation(**second_values)
                document = _document(
                    DocumentSection(
                        section_id="same-section",
                        heading="Boundaries",
                        blocks=(
                            DocumentBlock(
                                "boundary-one",
                                BlockKind.PARAGRAPH,
                                "First bounded fact.",
                                first,
                            ),
                            DocumentBlock(
                                "boundary-two",
                                BlockKind.PARAGRAPH,
                                "Second bounded fact.",
                                second,
                            ),
                        ),
                    )
                )

                chunks = chunk_document(document, target_chars=1_000)

                self.assertEqual(len(chunks), 2)
                self.assertEqual(
                    tuple(chunk.source_locations for chunk in chunks),
                    ((first,), (second,)),
                )

    def test_long_unbroken_unicode_is_split_without_overlap_or_omission(self):
        body = "界" * 300
        document = _document(
            DocumentSection(
                section_id="unicode",
                heading="Unicode",
                heading_path=("Unicode",),
                blocks=(DocumentBlock("long", BlockKind.PARAGRAPH, body),),
            )
        )

        chunks = chunk_document(document, target_chars=60, max_chars=100)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(chunk.char_count <= 100 for chunk in chunks))
        reconstructed = "".join(
            chunk.text.removeprefix("# Unicode\n\n") for chunk in chunks
        )
        self.assertEqual(reconstructed, body)
        self.assertEqual(
            tuple(chunk.chunk_id for chunk in chunks),
            tuple(
                chunk.chunk_id
                for chunk in chunk_document(
                    document, target_chars=60, max_chars=100
                )
            ),
        )

    def test_separator_at_hard_boundary_cannot_overflow_chunk_budget(self):
        body = "a" * 91 + ". " + "b" * 20
        document = _document(
            DocumentSection(
                section_id="edge",
                heading="Edge",
                heading_path=("Edge",),
                blocks=(DocumentBlock("edge-body", BlockKind.PARAGRAPH, body),),
            )
        )

        chunks = chunk_document(document, target_chars=100, max_chars=100)

        self.assertTrue(all(chunk.char_count <= 100 for chunk in chunks))
        self.assertEqual(
            "".join(chunk.text.removeprefix("# Edge\n\n") for chunk in chunks),
            body,
        )

    def test_oversized_code_repeats_bounded_explanation_context(self):
        explanation = "This function doubles each supplied value."
        code = "\n".join(
            f"result_{index} = value_{index} * 2" for index in range(12)
        )
        document = _document(
            DocumentSection(
                section_id="large-code",
                heading="Large code",
                heading_path=("Large code",),
                blocks=(
                    DocumentBlock(
                        "large-code-explanation",
                        BlockKind.PARAGRAPH,
                        explanation,
                    ),
                    DocumentBlock("large-code-body", BlockKind.CODE, code),
                ),
            )
        )

        chunks = chunk_document(document, target_chars=90, max_chars=120)
        code_chunks = tuple(
            chunk for chunk in chunks if "result_" in chunk.text
        )

        self.assertGreater(len(code_chunks), 1)
        self.assertTrue(all(explanation in chunk.text for chunk in code_chunks))
        self.assertTrue(all(chunk.char_count <= 120 for chunk in code_chunks))

    def test_more_than_48_structural_chunks_fails_without_source_leakage(self):
        secret_body = "private source evidence"
        sections = tuple(
            DocumentSection(
                section_id=f"section-{index}",
                heading=f"Section {index}",
                blocks=(
                    DocumentBlock(
                        f"block-{index}",
                        BlockKind.PARAGRAPH,
                        secret_body,
                    ),
                ),
            )
            for index in range(49)
        )

        with self.assertRaisesRegex(ValueError, "MAX_DOCUMENT_CHUNKS") as raised:
            chunk_document(_document(*sections, source_label="safe.md"))

        rendered = str(raised.exception)
        self.assertNotIn(secret_body, rendered)
        self.assertNotIn("C:\\Users\\", rendered)

    def test_huge_unbroken_text_stops_slicing_at_chunk_cap_plus_one(self):
        _SliceCountingText.slice_count = 0
        body = _SliceCountingText("x" * 4_999_000)
        document = _document(
            DocumentSection(
                section_id="huge",
                heading=None,
                blocks=(DocumentBlock("huge-body", BlockKind.PARAGRAPH, body),),
            )
        )

        with self.assertRaisesRegex(ValueError, "MAX_DOCUMENT_CHUNKS"):
            chunk_document(document, target_chars=1, max_chars=1)

        self.assertEqual(_SliceCountingText.slice_count, 49)

    def test_tuple_split_helper_is_also_capped_before_materialization(self):
        _SliceCountingText.slice_count = 0
        body = _SliceCountingText("x" * 100_000)

        with self.assertRaisesRegex(ValueError, "MAX_DOCUMENT_CHUNKS"):
            split_text_to_budget(body, target_chars=1, max_chars=1)

        self.assertEqual(_SliceCountingText.slice_count, 49)

    def test_table_header_at_or_over_hard_budget_fails_before_generic_split(self):
        for header in ("h" * 20, "h" * 21):
            with self.subTest(header_length=len(header)):
                document = _document(
                    DocumentSection(
                        section_id="header",
                        heading=None,
                        blocks=(
                            DocumentBlock(
                                "header-table",
                                BlockKind.TABLE,
                                header + "\nrow",
                            ),
                        ),
                    )
                )

                with self.assertRaisesRegex(ValueError, "table header"):
                    chunk_document(document, target_chars=20, max_chars=20)

        header_only = _document(
            DocumentSection(
                section_id="header-only",
                heading=None,
                blocks=(
                    DocumentBlock(
                        "header-only-table",
                        BlockKind.TABLE,
                        "h" * 21,
                    ),
                ),
            )
        )
        with self.assertRaisesRegex(ValueError, "table header"):
            chunk_document(header_only, target_chars=20, max_chars=20)

    def test_near_limit_table_scans_only_chunk_cap_plus_one_rows(self):
        _LazyTableText.row_slice_count = 0
        _LazyTableText.splitlines_count = 0
        body = _LazyTableText("H\n" + "r\n" * 2_499_000)
        document = _document(
            DocumentSection(
                section_id="huge-table",
                heading=None,
                blocks=(DocumentBlock("huge-table-body", BlockKind.TABLE, body),),
            )
        )

        with self.assertRaisesRegex(ValueError, "MAX_DOCUMENT_CHUNKS"):
            chunk_document(document, target_chars=3, max_chars=3)

        self.assertEqual(_LazyTableText.splitlines_count, 0)
        self.assertEqual(_LazyTableText.row_slice_count, 49)

    def test_table_line_scanner_supports_lf_crlf_and_cr(self):
        for separator in ("\n", "\r\n", "\r"):
            with self.subTest(separator=repr(separator)):
                document = _document(
                    DocumentSection(
                        section_id="newlines",
                        heading=None,
                        blocks=(
                            DocumentBlock(
                                "newline-table",
                                BlockKind.TABLE,
                                separator.join(("H", "A", "B")),
                            ),
                        ),
                    )
                )

                chunks = chunk_document(
                    document,
                    target_chars=3,
                    max_chars=3,
                )

                self.assertEqual(
                    tuple(chunk.text for chunk in chunks),
                    ("H\nA", "H\nB"),
                )

    def test_default_budget_many_short_rows_use_linear_separator_work(self):
        _LinearTableText.index_visits = 0
        _LinearTableText.separator_search_span = 0
        body = _LinearTableText("H\n" + "r\n" * 8_000)
        document = _document(
            DocumentSection(
                section_id="linear-table",
                heading=None,
                blocks=(DocumentBlock("linear-table-body", BlockKind.TABLE, body),),
            )
        )

        chunks = chunk_document(document)

        rendered_rows = sum(
            line == "r"
            for chunk in chunks
            for line in chunk.text.splitlines()
        )
        scan_work = (
            _LinearTableText.index_visits
            + _LinearTableText.separator_search_span
        )
        self.assertEqual(rendered_rows, 8_000)
        self.assertLessEqual(scan_work, len(body) * 2)

    def test_lazy_line_scanner_matches_splitlines_terminal_behavior(self):
        cases = (
            "",
            "H",
            "H\n",
            "H\r",
            "H\r\n",
            "\n",
            "\r",
            "\r\n",
            "H\n\n",
            "H\r\r",
            "H\r\n\r\n",
            "H\nA\n",
            "H\rA\r",
            "H\r\nA\r\n",
            "H\n\rA",
        )

        for text in cases:
            with self.subTest(text=repr(text)):
                self.assertEqual(tuple(_iter_lines(text)), tuple(text.splitlines()))

    def test_document_chunk_constructor_enforces_approved_safe_bounds(self):
        location = SourceLocation(file_label="safe.md", line_start=1)
        valid = DocumentChunk(
            chunk_id="chunk-0123456789abcdef",
            document_id="doc-safe",
            sequence=0,
            section_id="section-safe",
            heading_path=["Safe"],
            text="evidence",
            block_ids=["block-safe"],
            block_kinds=[BlockKind.PARAGRAPH],
            source_locations=[location],
        )

        self.assertIsInstance(valid.heading_path, tuple)
        self.assertIsInstance(valid.block_ids, tuple)
        self.assertIsInstance(valid.block_kinds, tuple)
        self.assertIsInstance(valid.source_locations, tuple)
        invalid_changes = (
            {"document_id": "C:\\Users\\private"},
            {"section_id": "../section"},
            {"heading_path": ("C:\\Users\\private",)},
            {"block_ids": ("../block",)},
            {"block_kinds": ()},
            {"text": "x" * 12_001},
        )
        for changes in invalid_changes:
            with self.subTest(changes=tuple(changes)):
                values = {
                    "chunk_id": valid.chunk_id,
                    "document_id": valid.document_id,
                    "sequence": valid.sequence,
                    "section_id": valid.section_id,
                    "heading_path": valid.heading_path,
                    "text": valid.text,
                    "block_ids": valid.block_ids,
                    "block_kinds": valid.block_kinds,
                    "source_locations": valid.source_locations,
                }
                values.update(changes)
                with self.assertRaises((TypeError, ValueError)):
                    DocumentChunk(**values)

    def test_chunk_repr_reports_identity_and_counts_not_body(self):
        body = "source body that must stay out of diagnostics"
        document = _document(
            DocumentSection(
                section_id="safe",
                heading="Safe",
                blocks=(DocumentBlock("safe-body", BlockKind.PARAGRAPH, body),),
            )
        )

        rendered = repr(chunk_document(document)[0])

        self.assertIn("document_id='doc-chunks'", rendered)
        self.assertIn("blocks=1", rendered)
        self.assertNotIn(body, rendered)


if __name__ == "__main__":
    unittest.main()
