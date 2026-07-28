import unittest
import tempfile
from dataclasses import replace
from pathlib import Path

from ankiforge_ai.document import (
    DEFAULT_DOCUMENT_LIMITS,
    BlockKind,
    DocumentImportError,
)
from ankiforge_ai.document.importers.html import HtmlImporter, _SafeHTMLParser
from ankiforge_ai.document.importers.markdown import MarkdownImporter
from ankiforge_ai.document.importers.text import TextImporter, TextMarkupImporter


FIXTURES = Path(__file__).parent / "fixtures" / "documents"


class DocumentTextMarkupImporterTests(unittest.TestCase):
    def test_document_ids_are_stable_content_derived_and_do_not_use_full_paths(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_path = Path(first) / "same.txt"
            second_path = Path(second) / "same.txt"
            first_path.write_text("first", encoding="utf-8")
            second_path.write_text("second", encoding="utf-8")
            importer = TextImporter()
            first_document = importer.import_document(first_path)
            repeated = importer.import_document(first_path)
            second_document = importer.import_document(second_path)
        self.assertEqual(first_document.document_id, repeated.document_id)
        self.assertNotEqual(first_document.document_id, second_document.document_id)
        self.assertNotIn(first, repr(first_document))
        self.assertNotIn(second, repr(second_document))

    def test_plain_text_paragraphs_have_exact_line_locations_and_safe_label(self):
        document = TextImporter().import_document(FIXTURES / "plain.txt")
        blocks = document.sections[0].blocks
        self.assertEqual(document.source_label, "plain.txt")
        self.assertEqual([block.kind for block in blocks], [BlockKind.PARAGRAPH] * 2)
        self.assertEqual([block.text for block in blocks], ["Alpha paragraph.\ncontinued", "Beta paragraph."])
        self.assertEqual(
            [(block.location.line_start, block.location.line_end) for block in blocks],
            [(1, 2), (4, 4)],
        )
        self.assertIsInstance(document.sections, tuple)

    def test_markdown_preserves_heading_paths_lists_code_tables_and_frontmatter(self):
        document = MarkdownImporter().import_document(FIXTURES / "structured.md")
        self.assertEqual(document.title, "Safe Lesson")
        self.assertEqual(
            [section.heading_path for section in document.sections],
            [("Topic",), ("Topic", "Details")],
        )
        self.assertEqual(
            [block.kind for section in document.sections for block in section.blocks],
            [
                BlockKind.HEADING,
                BlockKind.PARAGRAPH,
                BlockKind.HEADING,
                BlockKind.LIST,
                BlockKind.CODE,
                BlockKind.TABLE,
            ],
        )
        self.assertEqual(document.sections[1].blocks[0].location.line_start, 8)
        self.assertIn("print('not executed')", document.sections[1].blocks[2].text)

    def test_html_drops_active_content_and_never_opens_remote_resources(self):
        document = HtmlImporter().import_document(FIXTURES / "safe.html")
        text = "\n".join(
            block.text for section in document.sections for block in section.blocks
        )
        self.assertEqual(document.title, "HTML Lesson")
        self.assertIn("Useful diagram", text)
        self.assertIn("never_run()", text)
        self.assertNotIn("FETCHED_SCRIPT", text)
        self.assertNotIn("SECRET_STYLE", text)
        self.assertNotIn("REMOTE_FRAME", text)
        self.assertNotIn("example.invalid", text)
        self.assertEqual(
            [block.kind for section in document.sections for block in section.blocks],
            [
                BlockKind.HEADING,
                BlockKind.PARAGRAPH,
                BlockKind.LIST,
                BlockKind.TABLE,
                BlockKind.CAPTION,
                BlockKind.QUOTE,
                BlockKind.CODE,
            ],
        )

    def test_native_text_markup_formats_preserve_include_directives_without_reading(self):
        cases = {
            "notes.yaml": "include: never-read.txt",
            "notes.rst": ".. include:: never-read.txt",
            "notes.org": '#+INCLUDE: "never-read.txt"',
            "notes.tex": "\\input{never-read.txt}",
            "events.log": "WARNING stopped",
        }
        for filename, literal in cases.items():
            with self.subTest(filename=filename):
                document = TextMarkupImporter.for_path(FIXTURES / filename).import_document(
                    FIXTURES / filename
                )
                text = "\n".join(
                    block.text
                    for section in document.sections
                    for block in section.blocks
                )
                self.assertIn(literal, text)
                if filename != "events.log":
                    self.assertEqual(
                        document.sections[0].blocks[0].kind,
                        BlockKind.HEADING,
                    )

    def test_html_and_markdown_tables_enforce_row_column_and_cell_limits(self):
        cases = (
            (
                HtmlImporter(),
                "table.html",
                "<html><body><table><tr><td>A</td><td>B</td></tr>"
                "<tr><td>too long</td><td>D</td></tr></table></body></html>",
            ),
            (
                MarkdownImporter(),
                "table.md",
                "| A | B |\n|---|---|\n| too long | D |\n",
            ),
        )
        limits = (
            replace(DEFAULT_DOCUMENT_LIMITS, max_table_rows=1),
            replace(DEFAULT_DOCUMENT_LIMITS, max_table_columns=1),
            replace(DEFAULT_DOCUMENT_LIMITS, max_cell_chars=1),
        )
        for importer, filename, payload in cases:
            for selected_limits in limits:
                with self.subTest(
                    filename=filename,
                    limits=selected_limits,
                ):
                    with tempfile.TemporaryDirectory() as directory:
                        path = Path(directory) / filename
                        path.write_text(payload, encoding="utf-8")
                        with self.assertRaises(DocumentImportError) as raised:
                            importer.import_document(path, selected_limits)
                    self.assertEqual(
                        raised.exception.code,
                        "table_too_large",
                    )

    def test_html_colspan_cannot_bypass_column_limit(self):
        limits = replace(DEFAULT_DOCUMENT_LIMITS, max_table_columns=1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "merged.html"
            path.write_text(
                "<html><body><table><tr><td colspan='2'>A</td>"
                "</tr></table></body></html>",
                encoding="utf-8",
            )
            with self.assertRaises(DocumentImportError) as raised:
                HtmlImporter().import_document(path, limits)
        self.assertEqual(raised.exception.code, "table_too_large")

    def test_html_counts_empty_and_whitespace_table_rows_incrementally(self):
        limits = replace(DEFAULT_DOCUMENT_LIMITS, max_table_rows=2)
        payloads = (
            "<table><tr></tr><tr></tr><tr></tr></table>",
            "<table><tr> </tr><tr>\n\t</tr><tr> </tr></table>",
            "<table><tr><td>outer<table><tr></tr><tr></tr><tr></tr>"
            "</table></td></tr></table>",
        )
        for payload in payloads:
            with self.subTest(payload=payload):
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "empty-rows.html"
                    path.write_text(payload, encoding="utf-8")
                    with self.assertRaises(DocumentImportError) as raised:
                        HtmlImporter().import_document(path, limits)
                self.assertEqual(
                    raised.exception.code, "table_too_large"
                )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "row-boundary.html"
            path.write_text(
                "<table><tr></tr><tr> </tr></table>",
                encoding="utf-8",
            )
            HtmlImporter().import_document(path, limits)

    def test_html_cell_fragment_accounting_is_linear_and_exactly_bounded(self):
        class CountingFragments(list):
            def __init__(self):
                super().__init__()
                self.iterations = 0

            def __iter__(self):
                self.iterations += 1
                return super().__iter__()

        limits = replace(DEFAULT_DOCUMENT_LIMITS, max_cell_chars=64)
        parser = _SafeHTMLParser(limits)
        parser.feed("<table><tr><td>")
        fragments = CountingFragments()
        parser._cell_parts = fragments

        for _ in range(64):
            parser.handle_data("x")

        self.assertEqual(fragments.iterations, 0)
        self.assertEqual(parser._cell_chars, 64)
        self.assertEqual(len(fragments), 64)
        with self.assertRaises(DocumentImportError) as raised:
            parser.handle_data("x")
        self.assertEqual(raised.exception.code, "table_too_large")

    def test_html_nested_tables_are_depth_bounded_and_not_reinjected(self):
        class TrackingFragments(list):
            def __init__(self, values):
                super().__init__(values)
                self.append_calls = 0

            def append(self, value):
                self.append_calls += 1
                super().append(value)

        limits = replace(DEFAULT_DOCUMENT_LIMITS, max_xml_depth=3)
        parser = _SafeHTMLParser(limits)
        parser.feed("<table><tr><td>level-1 ")
        parent_fragments = TrackingFragments(parser._cell_parts)
        parser._cell_parts = parent_fragments
        parser.feed(
            "<table><tr><td>level-2 "
            "<table><tr><td>level-3</td></tr></table>"
            "</td></tr></table>"
        )
        self.assertEqual(parent_fragments.append_calls, 0)
        parser.feed("</td></tr></table>")
        parser.close()

        table_texts = [
            value
            for kind, value, _, _ in parser.items
            if kind is BlockKind.TABLE
        ]
        self.assertEqual(
            table_texts,
            ["level-3", "level-2", "level-1"],
        )
        self.assertEqual(
            parser._table_output_chars,
            sum(len(value) for value in table_texts),
        )
        self.assertEqual(
            sum(value.count("level-3") for value in table_texts),
            1,
        )
        self.assertEqual(parser._table_stack, [])

        too_deep = _SafeHTMLParser(limits)
        payload = (
            "<table><tr><td>" * 4
            + "leaf"
            + "</td></tr></table>" * 4
        )
        with self.assertRaises(DocumentImportError) as raised:
            too_deep.feed(payload)
        self.assertEqual(
            raised.exception.code, "document_too_complex"
        )
        self.assertEqual(len(too_deep._table_stack), 2)

    def test_html_table_output_budget_is_global_and_exact(self):
        limits = replace(DEFAULT_DOCUMENT_LIMITS, max_text_chars=6)
        exact = _SafeHTMLParser(limits)
        exact.feed(
            "<table><tr><td>abc</td></tr></table>"
            "<table><tr><td>def</td></tr></table>"
        )
        exact.close()
        self.assertEqual(exact._table_output_chars, 6)
        self.assertEqual(
            [value for kind, value, _, _ in exact.items],
            ["abc", "def"],
        )

        overflow = _SafeHTMLParser(limits)
        with self.assertRaises(DocumentImportError) as raised:
            overflow.feed(
                "<table><tr><td>abc</td></tr></table>"
                "<table><tr><td>defg</td></tr></table>"
            )
        self.assertEqual(
            raised.exception.code, "document_too_complex"
        )
        self.assertLessEqual(
            overflow._table_output_chars, limits.max_text_chars
        )


if __name__ == "__main__":
    unittest.main()
