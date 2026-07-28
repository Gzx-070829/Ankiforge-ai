import tempfile
import unittest
import zipfile
from dataclasses import replace
from pathlib import Path
from unittest import mock

import ankiforge_ai.document as document_package
import ankiforge_ai.importers.source_import as source_import_module
from ankiforge_ai.document import DEFAULT_DOCUMENT_LIMITS, DocumentImportError
from ankiforge_ai.document.importers.registry import (
    create_native_importer_registry,
    import_documents,
)
from ankiforge_ai.importers.source_import import (
    ImportedSource,
    SourceImportError,
    import_docx_file,
    import_source_file,
    merge_imported_source_text,
)


class SourceImportTests(unittest.TestCase):
    def test_document_package_exports_multi_file_native_import(self):
        self.assertIs(document_package.import_documents, import_documents)

    def test_native_registry_registers_every_core_format_without_optional_dependencies(self):
        registry = create_native_importer_registry()
        extensions = {
            extension
            for capability in registry.capabilities()
            for extension in capability.supported_extensions
        }
        self.assertTrue(
            {
                ".txt",
                ".md",
                ".docx",
                ".pptx",
                ".xlsx",
                ".csv",
                ".tsv",
                ".html",
                ".json",
                ".jsonl",
                ".xml",
                ".ipynb",
                ".epub",
                ".srt",
                ".vtt",
                ".yaml",
                ".rst",
                ".org",
                ".tex",
                ".py",
                ".js",
                ".ts",
                ".java",
                ".c",
                ".cpp",
                ".rs",
                ".go",
                ".sql",
                ".sh",
                ".ps1",
            }.issubset(extensions)
        )
        self.assertTrue(all(not item.external_dependencies for item in registry.capabilities()))

    def test_import_documents_preserves_explicit_order_and_enforces_batch_bounds(self):
        fixtures = Path(__file__).parent / "fixtures" / "documents"
        documents = import_documents(
            (fixtures / "plain.txt", fixtures / "structured.md")
        )
        self.assertEqual(
            [document.source_label for document in documents],
            ["plain.txt", "structured.md"],
        )
        self.assertIsInstance(documents, tuple)

        limits = replace(DEFAULT_DOCUMENT_LIMITS, max_files_per_batch=1)
        with self.assertRaises(DocumentImportError) as raised:
            import_documents(
                (fixtures / "plain.txt", fixtures / "structured.md"), limits
            )
        self.assertEqual(raised.exception.code, "too_many_files")

        limits = replace(DEFAULT_DOCUMENT_LIMITS, max_total_batch_bytes=1)
        with self.assertRaises(DocumentImportError) as raised:
            import_documents((fixtures / "plain.txt",), limits)
        self.assertEqual(raised.exception.code, "batch_too_large")

    def test_txt_utf8_is_read_without_changing_structure(self):
        with self.temporary_file("notes.txt", "第一段\n\n第二段") as path:
            imported = import_source_file(path)

        self.assertEqual(imported.filename, "notes.txt")
        self.assertEqual(imported.suffix, ".txt")
        self.assertEqual(imported.text, "第一段\n\n第二段")
        self.assertEqual(imported.char_count, len(imported.text))
        self.assertEqual(imported.warnings, ())

    def test_utf8_bom_is_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bom.txt"
            path.write_bytes(b"\xef\xbb\xbfhello")
            imported = import_source_file(path)

        self.assertEqual(imported.text, "hello")

    def test_system_encoding_fallback_has_warning(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.txt"
            path.write_bytes(b"caf\xe9")
            with mock.patch(
                "ankiforge_ai.importers.source_import.locale.getpreferredencoding",
                return_value="cp1252",
            ):
                imported = import_source_file(path)

        self.assertEqual(imported.text, "café")
        self.assertEqual(imported.warnings, ("system_encoding_fallback",))

    def test_legacy_text_preserves_crlf_cr_and_lf_bytes_exactly(self):
        payload = b"first\r\nsecond\rthird\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "line-endings.txt"
            path.write_bytes(payload)
            imported = import_source_file(path)

        self.assertEqual(imported.text.encode("utf-8"), payload)
        combined, appended = merge_imported_source_text("existing\r\n", imported)
        self.assertTrue(appended)
        self.assertTrue(combined.endswith(payload.decode("utf-8")))

    def test_empty_text_file_has_safe_error(self):
        with self.temporary_file("empty.txt", "") as path:
            with self.assertRaises(SourceImportError) as raised:
                import_source_file(path)

        self.assertEqual(raised.exception.code, "empty_file")

    def test_markdown_preserves_markdown(self):
        markdown = "# 标题\n\n- 项目一\n- **项目二**\n"
        for filename in ("notes.md", "notes.markdown"):
            with self.subTest(filename=filename):
                with self.temporary_file(filename, markdown) as path:
                    imported = import_source_file(path)
                self.assertEqual(imported.text, markdown)

    def test_unsupported_suffix_and_legacy_doc_have_distinct_errors(self):
        for filename, expected_code in (
            ("notes.csv", "unsupported_type"),
            ("notes.doc", "legacy_doc"),
        ):
            with self.subTest(filename=filename):
                with self.temporary_file(filename, "content") as path:
                    with self.assertRaises(SourceImportError) as raised:
                        import_source_file(path)
                self.assertEqual(raised.exception.code, expected_code)

    def test_text_size_limit_is_checked_before_reading(self):
        with self.temporary_file("large.txt", "12345") as path:
            with mock.patch(
                "ankiforge_ai.importers.source_import.TEXT_FILE_SIZE_LIMIT",
                4,
            ):
                with self.assertRaises(SourceImportError) as raised:
                    import_source_file(path)

        self.assertEqual(raised.exception.code, "file_too_large")

    def test_minimal_docx_extracts_paragraphs_and_table_cells(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>第一段</w:t></w:r></w:p>
    <w:p><w:r><w:t>Second paragraph</w:t></w:r></w:p>
    <w:tbl><w:tr>
      <w:tc><w:p><w:r><w:t>Cell A</w:t></w:r></w:p></w:tc>
      <w:tc><w:p><w:r><w:t>Cell B</w:t></w:r></w:p></w:tc>
    </w:tr></w:tbl>
  </w:body>
</w:document>"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lesson.docx"
            with zipfile.ZipFile(path, mode="w") as archive:
                archive.writestr("word/document.xml", xml)
            imported = import_docx_file(path)

        self.assertEqual(
            imported.text,
            "第一段\nSecond paragraph\nCell A\tCell B",
        )
        self.assertEqual(imported.warnings, ("docx_text_only",))

    def test_public_docx_path_rejects_all_member_archive_security_failures(self):
        xml = (
            "<w:document xmlns:w='w'><w:body><w:p><w:r>"
            "<w:t>safe</w:t></w:r></w:p></w:body></w:document>"
        )
        cases = (
            ("macro", None),
            ("traversal", None),
            ("symlink", None),
            ("duplicate", None),
            ("encrypted", None),
            (
                "ratio",
                replace(
                    DEFAULT_DOCUMENT_LIMITS,
                    max_archive_compression_ratio=1.0,
                ),
            ),
            (
                "member",
                replace(DEFAULT_DOCUMENT_LIMITS, max_member_bytes=8),
            ),
            (
                "aggregate",
                replace(
                    DEFAULT_DOCUMENT_LIMITS,
                    max_archive_uncompressed_bytes=32,
                ),
            ),
        )
        for attack, limits in cases:
            with self.subTest(attack=attack):
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / f"{attack}.docx"
                    compression = (
                        zipfile.ZIP_DEFLATED
                        if attack == "ratio"
                        else zipfile.ZIP_STORED
                    )
                    with zipfile.ZipFile(
                        path, "w", compression=compression
                    ) as archive:
                        archive.writestr("word/document.xml", xml)
                        if attack == "macro":
                            archive.writestr("word/vbaProject.bin", b"macro")
                        elif attack == "traversal":
                            archive.writestr("../outside.txt", b"unsafe")
                        elif attack == "symlink":
                            info = zipfile.ZipInfo("word/link")
                            info.create_system = 3
                            info.external_attr = 0o120777 << 16
                            archive.writestr(info, b"target")
                        elif attack == "duplicate":
                            archive.writestr("WORD/DOCUMENT.XML", xml)
                        elif attack == "encrypted":
                            archive.writestr("word/secret.bin", b"secret")
                        elif attack == "ratio":
                            archive.writestr("word/padding.bin", b"0" * 1000)
                    if attack == "encrypted":
                        payload = bytearray(path.read_bytes())
                        local_offsets = []
                        offset = 0
                        while True:
                            offset = payload.find(b"PK\x03\x04", offset)
                            if offset < 0:
                                break
                            local_offsets.append(offset)
                            offset += 4
                        central_offsets = []
                        offset = 0
                        while True:
                            offset = payload.find(b"PK\x01\x02", offset)
                            if offset < 0:
                                break
                            central_offsets.append(offset)
                            offset += 4
                        local = local_offsets[-1]
                        central = central_offsets[-1]
                        payload[local + 6 : local + 8] = (
                            int.from_bytes(
                                payload[local + 6 : local + 8], "little"
                            )
                            | 1
                        ).to_bytes(2, "little")
                        payload[central + 8 : central + 10] = (
                            int.from_bytes(
                                payload[central + 8 : central + 10], "little"
                            )
                            | 1
                        ).to_bytes(2, "little")
                        path.write_bytes(payload)
                    limits_context = (
                        mock.patch.object(
                            source_import_module,
                            "DEFAULT_DOCUMENT_LIMITS",
                            limits,
                            create=True,
                        )
                        if limits is not None
                        else mock.patch.object(
                            source_import_module,
                            "DEFAULT_DOCUMENT_LIMITS",
                            DEFAULT_DOCUMENT_LIMITS,
                            create=True,
                        )
                    )
                    with limits_context:
                        with self.assertRaises(SourceImportError) as raised:
                            import_source_file(path)
                self.assertEqual(raised.exception.code, "docx_invalid")
                self.assertFalse(
                    (Path(directory) / "outside.txt").exists()
                    if Path(directory).exists()
                    else False
                )

    def test_public_docx_never_uses_legacy_fallback_for_malformed_xml(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "malformed.docx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("[Content_Types].xml", "<Types />")
                archive.writestr(
                    "word/document.xml",
                    "<document><broken></document>",
                )
            with mock.patch.object(
                source_import_module,
                "import_docx_file",
                side_effect=AssertionError("legacy fallback must not run"),
            ):
                with self.assertRaises(SourceImportError) as raised:
                    import_source_file(path)
        self.assertEqual(raised.exception.code, "docx_invalid")

    def test_corrupt_or_incomplete_docx_has_safe_error(self):
        with tempfile.TemporaryDirectory() as directory:
            corrupt = Path(directory) / "corrupt.docx"
            corrupt.write_bytes(b"not a zip")
            with self.assertRaises(SourceImportError) as raised:
                import_source_file(corrupt)
            self.assertEqual(raised.exception.code, "docx_invalid")

            incomplete = Path(directory) / "incomplete.docx"
            with zipfile.ZipFile(incomplete, mode="w") as archive:
                archive.writestr("[Content_Types].xml", "<Types />")
            with self.assertRaises(SourceImportError) as raised:
                import_source_file(incomplete)
            self.assertEqual(raised.exception.code, "docx_missing_document")

    def test_docx_rejects_document_type_declarations(self):
        xml = b'<!DOCTYPE document [<!ENTITY x "unsafe">]><document />'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unsafe.docx"
            with zipfile.ZipFile(path, mode="w") as archive:
                archive.writestr("word/document.xml", xml)
            with self.assertRaises(SourceImportError) as raised:
                import_source_file(path)

        self.assertEqual(raised.exception.code, "docx_invalid")

    def test_docx_rejects_utf16_entity_declarations(self):
        xml = (
            '<?xml version="1.0" encoding="utf-16"?>'
            '<!DOCTYPE document [<!ENTITY x "expanded">]>'
            '<document><body><p>&x;</p></body></document>'
        ).encode("utf-16")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unsafe-utf16.docx"
            with zipfile.ZipFile(path, mode="w") as archive:
                archive.writestr("word/document.xml", xml)
            with self.assertRaises(SourceImportError) as raised:
                import_source_file(path)

        self.assertEqual(raised.exception.code, "docx_invalid")

    def test_docx_invalid_xml_encoding_has_safe_error(self):
        for encoding in ("no-such-encoding", "utf-32"):
            with self.subTest(encoding=encoding):
                xml = (
                    f'<?xml version="1.0" encoding="{encoding}"?><document />'
                ).encode("ascii")
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "invalid-encoding.docx"
                    with zipfile.ZipFile(path, mode="w") as archive:
                        archive.writestr("word/document.xml", xml)
                    with self.assertRaises(SourceImportError) as raised:
                        import_source_file(path)

                self.assertEqual(raised.exception.code, "docx_invalid")

    def test_docx_element_limit_has_safe_size_error(self):
        xml = b"<document><body><p><r><t>text</t></r></p></body></document>"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "too-complex.docx"
            with zipfile.ZipFile(path, mode="w") as archive:
                archive.writestr("word/document.xml", xml)
            with mock.patch(
                "ankiforge_ai.importers.source_import.DOCX_ELEMENT_LIMIT",
                3,
            ):
                with self.assertRaises(SourceImportError) as raised:
                    import_source_file(path)

        self.assertEqual(raised.exception.code, "file_too_large")

    def test_pdf_without_optional_reader_falls_back_safely(self):
        with self.temporary_file("lesson.pdf", "%PDF-1.4") as path:
            with self.assertRaises(SourceImportError) as raised:
                import_source_file(path)

        self.assertEqual(raised.exception.code, "pdf_unavailable")

    def test_pdf_size_limit_runs_before_fallback(self):
        with self.temporary_file("large.pdf", "%PDF-1.4") as path:
            with mock.patch(
                "ankiforge_ai.importers.source_import.DOCUMENT_FILE_SIZE_LIMIT",
                4,
            ):
                with self.assertRaises(SourceImportError) as raised:
                    import_source_file(path)

        self.assertEqual(raised.exception.code, "file_too_large")

    def test_existing_material_is_appended_with_a_visible_file_separator(self):
        imported = ImportedSource(
            filename="lesson.md",
            suffix=".md",
            text="# New lesson",
            char_count=12,
            warnings=(),
            source_label="lesson.md",
        )

        combined, appended = merge_imported_source_text("Existing notes", imported)
        replacement, replaced = merge_imported_source_text("", imported)

        self.assertTrue(appended)
        self.assertIn("Existing notes", combined)
        self.assertIn("--- lesson.md ---", combined)
        self.assertTrue(combined.endswith("# New lesson"))
        self.assertFalse(replaced)
        self.assertEqual(replacement, "# New lesson")

    def test_append_preserves_existing_trailing_whitespace(self):
        imported = ImportedSource(
            filename="lesson.txt",
            suffix=".txt",
            text="new",
            char_count=3,
            warnings=(),
            source_label="lesson.txt",
        )
        existing = "Existing notes\n\n  "

        combined, appended = merge_imported_source_text(existing, imported)

        self.assertTrue(appended)
        self.assertTrue(combined.startswith(existing))

    @staticmethod
    def temporary_file(filename, content):
        class TemporaryFileContext:
            def __enter__(self):
                self.directory = tempfile.TemporaryDirectory()
                self.path = Path(self.directory.name) / filename
                self.path.write_bytes(content.encode("utf-8"))
                return self.path

            def __exit__(self, *_args):
                self.directory.cleanup()

        return TemporaryFileContext()


if __name__ == "__main__":
    unittest.main()
