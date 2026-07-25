import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from ankiforge_ai.document import (
    DEFAULT_DOCUMENT_LIMITS,
    BlockKind,
    DocumentImportError,
)
from ankiforge_ai.document.importers.json_data import JsonDataImporter
from ankiforge_ai.document.importers.notebook import NotebookImporter
from ankiforge_ai.document.importers.registry import create_native_importer_registry
from ankiforge_ai.document.importers.tabular import TabularImporter
from ankiforge_ai.document.importers.xml_data import XmlDataImporter


FIXTURES = Path(__file__).parent / "fixtures" / "documents"


class DocumentDataNotebookImporterTests(unittest.TestCase):
    def test_csv_and_tsv_repeat_headers_and_preserve_row_locations(self):
        for filename, source_type in (("table.csv", "csv"), ("table.tsv", "tsv")):
            with self.subTest(filename=filename):
                document = TabularImporter.for_path(FIXTURES / filename).import_document(
                    FIXTURES / filename
                )
                block = document.sections[0].blocks[0]
                self.assertEqual(document.source_type, source_type)
                self.assertEqual(block.kind, BlockKind.TABLE)
                self.assertEqual(block.text, "Name\tScore\nAda\t10\nLin\t9")
                self.assertEqual(
                    (block.location.row_start, block.location.row_end), (2, 3)
                )
                self.assertEqual(block.metadata, {"column_count": 2})

    def test_tabular_row_and_column_limits_fail_closed(self):
        limits = replace(
            DEFAULT_DOCUMENT_LIMITS, max_table_rows=1, max_table_columns=1
        )
        with self.assertRaises(DocumentImportError) as raised:
            TabularImporter.for_path(FIXTURES / "table.csv").import_document(
                FIXTURES / "table.csv", limits
            )
        self.assertEqual(raised.exception.code, "table_too_large")

    def test_long_valid_csv_header_is_not_duplicated_into_block_metadata(self):
        header = "H" * 2001
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "long-header.csv"
            path.write_text(f"{header}\nvalue\n", encoding="utf-8")
            document = create_native_importer_registry().import_document(path)
        table = document.sections[0].blocks[0]
        self.assertEqual(table.text, f"{header}\nvalue")
        self.assertEqual(table.metadata, {"column_count": 1})

    def test_json_and_jsonl_emit_bounded_path_value_blocks_in_input_order(self):
        document = JsonDataImporter.for_path(FIXTURES / "data.json").import_document(
            FIXTURES / "data.json"
        )
        self.assertEqual(
            [block.text for block in document.sections[0].blocks],
            ["$.topic.facts[0] = one", "$.topic.facts[1] = two", "$.topic.count = 2"],
        )
        records = JsonDataImporter.for_path(
            FIXTURES / "records.jsonl"
        ).import_document(FIXTURES / "records.jsonl")
        self.assertEqual(
            [section.heading for section in records.sections], ["Record 1", "Record 2"]
        )
        self.assertEqual(records.sections[1].location.line_start, 2)

    def test_json_depth_is_bounded_without_recursive_importer_walk(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "deep.json"
            path.write_text('{"a":{"b":{"c":1}}}', encoding="utf-8")
            limits = replace(DEFAULT_DOCUMENT_LIMITS, max_json_depth=2)
            with self.assertRaises(DocumentImportError) as raised:
                JsonDataImporter().import_document(path, limits)
        self.assertEqual(raised.exception.code, "document_too_complex")

    def test_safe_xml_has_tag_paths_and_locations(self):
        document = XmlDataImporter().import_document(FIXTURES / "safe.xml")
        blocks = document.sections[0].blocks
        self.assertEqual(blocks[0].kind, BlockKind.METADATA)
        self.assertEqual(blocks[0].text, "/catalog/item/@id = 1")
        self.assertEqual(blocks[1].text, "/catalog/item/name = Alpha")
        self.assertEqual(blocks[0].location.section, "catalog/item")

    def test_notebook_cells_keep_locations_skip_images_and_never_execute(self):
        document = NotebookImporter().import_document(FIXTURES / "lesson.ipynb")
        blocks = [block for section in document.sections for block in section.blocks]
        self.assertEqual(
            [(block.kind, block.location.notebook_cell) for block in blocks],
            [
                (BlockKind.PARAGRAPH, 1),
                (BlockKind.CODE, 2),
                (BlockKind.TRANSCRIPT, 2),
            ],
        )
        combined = "\n".join(block.text for block in blocks)
        self.assertIn("raise RuntimeError('never executed')", combined)
        self.assertIn("safe output", combined)
        self.assertNotIn("aGVsbG8", combined)
        self.assertEqual(
            [item.code for item in document.warnings], ["notebook_binary_output_skipped"]
        )

    def test_notebook_text_output_limit_skips_output_with_warning(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "large-output.ipynb"
            path.write_text(
                '{"cells":[{"cell_type":"code","source":["x"],"outputs":'
                '[{"output_type":"stream","text":["12345"]}]}],'
                '"metadata":{},"nbformat":4,"nbformat_minor":5}',
                encoding="utf-8",
            )
            limits = replace(DEFAULT_DOCUMENT_LIMITS, max_notebook_output_chars=4)
            document = NotebookImporter().import_document(path, limits)
        self.assertEqual(
            [item.code for item in document.warnings],
            ["notebook_output_too_large"],
        )
        self.assertEqual(
            [block.kind for block in document.sections[0].blocks],
            [BlockKind.CODE],
        )


if __name__ == "__main__":
    unittest.main()
