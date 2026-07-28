import tempfile
import unittest
import zipfile
from dataclasses import replace
from pathlib import Path
from unittest import mock

from ankiforge_ai.document import (
    DEFAULT_DOCUMENT_LIMITS,
    BlockKind,
    DocumentImportError,
)
from ankiforge_ai.document.importers.epub import EpubImporter
from ankiforge_ai.document.importers import epub, office_open_xml
from ankiforge_ai.document.importers.office_open_xml import (
    DocxImporter,
    PptxImporter,
    XlsxImporter,
)
from ankiforge_ai.document.importers.registry import create_native_importer_registry


FIXTURES = Path(__file__).parent / "fixtures" / "documents"
CONTENT_TYPES = "http://schemas.openxmlformats.org/package/2006/content-types"
RELATIONSHIPS = (
    "http://schemas.openxmlformats.org/package/2006/relationships"
)
OFFICE_RELATIONSHIPS = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
)
OFFICE_DOCUMENT_RELATIONSHIP = f"{OFFICE_RELATIONSHIPS}/officeDocument"
SLIDE_RELATIONSHIP = f"{OFFICE_RELATIONSHIPS}/slide"
WORKSHEET_RELATIONSHIP = f"{OFFICE_RELATIONSHIPS}/worksheet"
WORD_NAMESPACE = (
    "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
)
PRESENTATION_NAMESPACE = (
    "http://schemas.openxmlformats.org/presentationml/2006/main"
)
SPREADSHEET_NAMESPACE = (
    "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
)
WORD_MAIN = (
    "application/vnd.openxmlformats-officedocument."
    "wordprocessingml.document.main+xml"
)
PRESENTATION_MAIN = (
    "application/vnd.openxmlformats-officedocument."
    "presentationml.presentation.main+xml"
)
WORKBOOK_MAIN = (
    "application/vnd.openxmlformats-officedocument."
    "spreadsheetml.sheet.main+xml"
)
SLIDE_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument."
    "presentationml.slide+xml"
)
WORKSHEET_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument."
    "spreadsheetml.worksheet+xml"
)


def content_types(part, media_type, *additional):
    overrides = "".join(
        f"<Override PartName='/{name}' ContentType='{kind}'/>"
        for name, kind in ((part, media_type), *additional)
    )
    return (
        f"<Types xmlns='{CONTENT_TYPES}'>"
        "<Default Extension='xml' ContentType='application/xml'/>"
        f"{overrides}"
        "</Types>"
    )


def relationships(target, relation_type, *, namespace=RELATIONSHIPS):
    return (
        f"<Relationships xmlns='{namespace}'>"
        f"<Relationship Id='rId1' Target='{target}' "
        f"Type='{relation_type}'/></Relationships>"
    )


def changed_member(members, member_name, payload):
    return [
        (name, payload if name == member_name else value)
        for name, value in members
    ]


class DocumentOfficeEpubImporterTests(unittest.TestCase):
    def test_docx_preserves_heading_list_table_order_and_ignores_external_relation(self):
        document = DocxImporter().import_document(FIXTURES / "lesson.docx")
        blocks = [block for section in document.sections for block in section.blocks]
        self.assertEqual(
            [block.kind for block in blocks],
            [BlockKind.HEADING, BlockKind.LIST, BlockKind.TABLE],
        )
        self.assertEqual([block.text for block in blocks], ["DOCX Topic", "List item", "A\tB"])
        self.assertTrue(all(block.location.section == "word/document.xml" for block in blocks))
        self.assertNotIn("example.invalid", "\n".join(block.text for block in blocks))

    def test_pptx_follows_relationship_slide_order_with_slide_locations(self):
        document = PptxImporter().import_document(FIXTURES / "slides.pptx")
        self.assertEqual([section.heading for section in document.sections], ["First Slide", "Second Slide"])
        self.assertEqual(
            [section.location.slide for section in document.sections], [1, 2]
        )
        self.assertEqual(document.sections[0].blocks[1].kind, BlockKind.LIST)
        self.assertEqual(document.sections[0].blocks[1].text, "Bullet one")

    def test_xlsx_skips_hidden_sheet_and_preserves_formula_text_and_cached_value(self):
        document = XlsxImporter().import_document(FIXTURES / "workbook.xlsx")
        self.assertEqual([section.heading for section in document.sections], ["Visible"])
        blocks = document.sections[0].blocks
        self.assertEqual([block.kind for block in blocks], [BlockKind.TABLE, BlockKind.FORMULA])
        self.assertIn("Name\tScore", blocks[0].text)
        self.assertEqual(blocks[1].text, "=1+1 (cached: 2)")
        self.assertEqual(blocks[1].location.cell_range, "B2")
        self.assertNotIn("SECRET", "\n".join(block.text for block in blocks))
        self.assertEqual([item.code for item in document.warnings], ["hidden_sheet_skipped"])

    def test_epub_uses_opf_spine_order_and_only_local_validated_chapters(self):
        document = EpubImporter().import_document(FIXTURES / "book.epub")
        self.assertEqual(document.title, "Safe Book")
        self.assertEqual([section.heading for section in document.sections], ["Second", "First"])
        self.assertEqual(
            [section.location.section for section in document.sections],
            ["OPS/chapter2.xhtml", "OPS/chapter1.xhtml"],
        )
        combined = "\n".join(
            block.text for section in document.sections for block in section.blocks
        )
        self.assertEqual(combined, "Second\nChapter two.\nFirst\nChapter one.")
        self.assertNotIn("example.invalid", combined)

    def test_epub_and_office_stop_building_blocks_at_the_shared_limit(self):
        limits = replace(DEFAULT_DOCUMENT_LIMITS, max_document_blocks=2)
        with mock.patch.object(
            epub,
            "block",
            wraps=epub.block,
        ) as epub_block:
            with self.assertRaises(DocumentImportError) as raised:
                EpubImporter().import_document(FIXTURES / "book.epub", limits)
        self.assertEqual(raised.exception.code, "document_too_complex")
        self.assertLessEqual(epub_block.call_count, 3)

        limits = replace(DEFAULT_DOCUMENT_LIMITS, max_document_blocks=1)
        with mock.patch.object(
            office_open_xml,
            "block",
            wraps=office_open_xml.block,
        ) as office_block:
            with self.assertRaises(DocumentImportError) as raised:
                DocxImporter().import_document(FIXTURES / "lesson.docx", limits)
        self.assertEqual(raised.exception.code, "document_too_complex")
        self.assertLessEqual(office_block.call_count, 2)

    def test_fake_office_archive_and_malformed_epub_fail_with_safe_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake = root / "fake.docx"
            with zipfile.ZipFile(fake, "w") as archive:
                archive.writestr("[Content_Types].xml", "<Types />")
            with self.assertRaises(DocumentImportError) as raised:
                DocxImporter().import_document(fake)
            self.assertEqual(raised.exception.code, "invalid_office_archive")

            epub = root / "bad.epub"
            with zipfile.ZipFile(epub, "w") as archive:
                archive.writestr("mimetype", "application/epub+zip")
                archive.writestr("META-INF/container.xml", "<container />")
            with self.assertRaises(DocumentImportError) as raised:
                EpubImporter().import_document(epub)
            self.assertEqual(raised.exception.code, "malformed_file")
            self.assertNotIn(str(root), repr(raised.exception))

    def test_epub_xhtml_spine_chapters_require_strict_safe_xml(self):
        chapters = (
            ("<html><body><img></body></html>", "malformed_file"),
            (
                "<!DOCTYPE html [<!ENTITY x 'unsafe'>]>"
                "<html><body>&x;</body></html>",
                "xml_not_safe",
            ),
        )
        for chapter, code in chapters:
            with self.subTest(code=code):
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "strict.epub"
                    with zipfile.ZipFile(path, "w") as archive:
                        archive.writestr("mimetype", "application/epub+zip")
                        archive.writestr(
                            "META-INF/container.xml",
                            "<container><rootfiles><rootfile "
                            "full-path='OPS/book.opf'/></rootfiles></container>",
                        )
                        archive.writestr(
                            "OPS/book.opf",
                            "<package><manifest><item id='c1' "
                            "href='chapter.xhtml' "
                            "media-type='application/xhtml+xml'/></manifest>"
                            "<spine><itemref idref='c1'/></spine></package>",
                        )
                        archive.writestr("OPS/chapter.xhtml", chapter)
                    with self.assertRaises(DocumentImportError) as raised:
                        EpubImporter().import_document(path)
                self.assertEqual(raised.exception.code, code)

    def test_ooxml_validates_declared_main_types_and_internal_relationship_targets(self):
        cases = (
            (
                "fake.docx",
                DocxImporter(),
                [
                    (
                        "[Content_Types].xml",
                        content_types("word/document.xml", WORKBOOK_MAIN),
                    ),
                    (
                        "word/document.xml",
                        f"<w:document xmlns:w='{WORD_NAMESPACE}'><w:body><w:p>"
                        "<w:r><w:t>text</w:t></w:r></w:p></w:body></w:document>",
                    ),
                ],
            ),
            (
                "missing-slide.pptx",
                PptxImporter(),
                [
                    (
                        "[Content_Types].xml",
                        content_types("ppt/presentation.xml", PRESENTATION_MAIN),
                    ),
                    (
                        "_rels/.rels",
                        relationships(
                            "ppt/presentation.xml",
                            OFFICE_DOCUMENT_RELATIONSHIP,
                        ),
                    ),
                    (
                        "ppt/presentation.xml",
                        f"<p:presentation xmlns:p='{PRESENTATION_NAMESPACE}' "
                        f"xmlns:r='{OFFICE_RELATIONSHIPS}'>"
                        "<p:sldIdLst><p:sldId r:id='rId1'/></p:sldIdLst>"
                        "</p:presentation>",
                    ),
                    (
                        "ppt/_rels/presentation.xml.rels",
                        relationships(
                            "slides/missing.xml", SLIDE_RELATIONSHIP
                        ),
                    ),
                ],
            ),
            (
                "missing-sheet.xlsx",
                XlsxImporter(),
                [
                    (
                        "[Content_Types].xml",
                        content_types("xl/workbook.xml", WORKBOOK_MAIN),
                    ),
                    (
                        "_rels/.rels",
                        relationships(
                            "xl/workbook.xml",
                            OFFICE_DOCUMENT_RELATIONSHIP,
                        ),
                    ),
                    (
                        "xl/workbook.xml",
                        f"<workbook xmlns='{SPREADSHEET_NAMESPACE}' "
                        f"xmlns:r='{OFFICE_RELATIONSHIPS}'>"
                        "<sheets><sheet name='Sheet' r:id='rId1'/></sheets>"
                        "</workbook>",
                    ),
                    (
                        "xl/_rels/workbook.xml.rels",
                        relationships(
                            "worksheets/missing.xml",
                            WORKSHEET_RELATIONSHIP,
                        ),
                    ),
                ],
            ),
        )
        for filename, importer, members in cases:
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / filename
                    with zipfile.ZipFile(path, "w") as archive:
                        for name, payload in members:
                            archive.writestr(name, payload)
                    with self.assertRaises(DocumentImportError) as raised:
                        importer.import_document(path)
                self.assertEqual(
                    raised.exception.code, "invalid_office_archive"
                )

    def test_ooxml_rejects_namespace_and_package_identity_lookalikes(self):
        docx = [
            (
                "[Content_Types].xml",
                content_types("word/document.xml", WORD_MAIN),
            ),
            (
                "_rels/.rels",
                relationships(
                    "word/document.xml", OFFICE_DOCUMENT_RELATIONSHIP
                ),
            ),
            (
                "word/document.xml",
                f"<w:document xmlns:w='{WORD_NAMESPACE}'><w:body>"
                "<w:p><w:r><w:t>text</w:t></w:r></w:p>"
                "</w:body></w:document>",
            ),
        ]
        pptx = [
            (
                "[Content_Types].xml",
                content_types(
                    "ppt/presentation.xml",
                    PRESENTATION_MAIN,
                    ("ppt/slides/slide1.xml", SLIDE_CONTENT_TYPE),
                ),
            ),
            (
                "_rels/.rels",
                relationships(
                    "ppt/presentation.xml",
                    OFFICE_DOCUMENT_RELATIONSHIP,
                ),
            ),
            (
                "ppt/presentation.xml",
                f"<p:presentation xmlns:p='{PRESENTATION_NAMESPACE}' "
                f"xmlns:r='{OFFICE_RELATIONSHIPS}'>"
                "<p:sldIdLst><p:sldId r:id='rId1'/></p:sldIdLst>"
                "</p:presentation>",
            ),
            (
                "ppt/_rels/presentation.xml.rels",
                relationships("slides/slide1.xml", SLIDE_RELATIONSHIP),
            ),
            (
                "ppt/slides/slide1.xml",
                f"<p:sld xmlns:p='{PRESENTATION_NAMESPACE}'/>",
            ),
        ]
        xlsx = [
            (
                "[Content_Types].xml",
                content_types(
                    "xl/workbook.xml",
                    WORKBOOK_MAIN,
                    (
                        "xl/worksheets/sheet1.xml",
                        WORKSHEET_CONTENT_TYPE,
                    ),
                ),
            ),
            (
                "_rels/.rels",
                relationships(
                    "xl/workbook.xml", OFFICE_DOCUMENT_RELATIONSHIP
                ),
            ),
            (
                "xl/workbook.xml",
                f"<workbook xmlns='{SPREADSHEET_NAMESPACE}' "
                f"xmlns:r='{OFFICE_RELATIONSHIPS}'>"
                "<sheets><sheet name='Sheet' r:id='rId1'/></sheets>"
                "</workbook>",
            ),
            (
                "xl/_rels/workbook.xml.rels",
                relationships(
                    "worksheets/sheet1.xml", WORKSHEET_RELATIONSHIP
                ),
            ),
            (
                "xl/worksheets/sheet1.xml",
                f"<worksheet xmlns='{SPREADSHEET_NAMESPACE}'>"
                "<sheetData/></worksheet>",
            ),
        ]
        fake_content_types_root = content_types(
            "word/document.xml", WORD_MAIN
        ).replace(CONTENT_TYPES, "urn:fake:content-types")
        fake_content_types_child = (
            f"<Types xmlns='{CONTENT_TYPES}' "
            "xmlns:x='urn:fake:content-types'>"
            "<x:Override PartName='/word/document.xml' "
            f"ContentType='{WORD_MAIN}'/></Types>"
        )
        fake_relationship_child = (
            f"<Relationships xmlns='{RELATIONSHIPS}' "
            "xmlns:x='urn:fake:relationships'>"
            "<x:Relationship Id='rId1' Target='slides/slide1.xml' "
            f"Type='{SLIDE_RELATIONSHIP}'/></Relationships>"
        )
        cases = (
            (
                "content-types-root-namespace.docx",
                DocxImporter(),
                changed_member(
                    docx,
                    "[Content_Types].xml",
                    fake_content_types_root,
                ),
            ),
            (
                "content-types-child-namespace.docx",
                DocxImporter(),
                changed_member(
                    docx,
                    "[Content_Types].xml",
                    fake_content_types_child,
                ),
            ),
            (
                "root-relationship-namespace.docx",
                DocxImporter(),
                changed_member(
                    docx,
                    "_rels/.rels",
                    relationships(
                        "word/document.xml",
                        OFFICE_DOCUMENT_RELATIONSHIP,
                        namespace="urn:fake:relationships",
                    ),
                ),
            ),
            (
                "root-relationship-type.docx",
                DocxImporter(),
                changed_member(
                    docx,
                    "_rels/.rels",
                    relationships(
                        "word/document.xml", SLIDE_RELATIONSHIP
                    ),
                ),
            ),
            (
                "document-root-namespace.docx",
                DocxImporter(),
                changed_member(
                    docx,
                    "word/document.xml",
                    "<w:document xmlns:w='urn:fake:word'>"
                    "<w:body><w:p><w:r><w:t>text</w:t></w:r></w:p>"
                    "</w:body></w:document>",
                ),
            ),
            (
                "slide-relationship-child-namespace.pptx",
                PptxImporter(),
                changed_member(
                    pptx,
                    "ppt/_rels/presentation.xml.rels",
                    fake_relationship_child,
                ),
            ),
            (
                "presentation-root-namespace.pptx",
                PptxImporter(),
                changed_member(
                    pptx,
                    "ppt/presentation.xml",
                    f"<p:presentation xmlns:p='urn:fake:presentation' "
                    f"xmlns:r='{OFFICE_RELATIONSHIPS}'>"
                    "<p:sldIdLst><p:sldId r:id='rId1'/></p:sldIdLst>"
                    "</p:presentation>",
                ),
            ),
            (
                "slide-relationship-type.pptx",
                PptxImporter(),
                changed_member(
                    pptx,
                    "ppt/_rels/presentation.xml.rels",
                    relationships(
                        "slides/slide1.xml", WORKSHEET_RELATIONSHIP
                    ),
                ),
            ),
            (
                "slide-content-type.pptx",
                PptxImporter(),
                changed_member(
                    pptx,
                    "[Content_Types].xml",
                    content_types(
                        "ppt/presentation.xml",
                        PRESENTATION_MAIN,
                        ("ppt/slides/slide1.xml", "application/xml"),
                    ),
                ),
            ),
            (
                "slide-root-namespace.pptx",
                PptxImporter(),
                changed_member(
                    pptx,
                    "ppt/slides/slide1.xml",
                    "<p:sld xmlns:p='urn:fake:presentation'/>",
                ),
            ),
            (
                "worksheet-relationship-root-namespace.xlsx",
                XlsxImporter(),
                changed_member(
                    xlsx,
                    "xl/_rels/workbook.xml.rels",
                    relationships(
                        "worksheets/sheet1.xml",
                        WORKSHEET_RELATIONSHIP,
                        namespace="urn:fake:relationships",
                    ),
                ),
            ),
            (
                "workbook-root-namespace.xlsx",
                XlsxImporter(),
                changed_member(
                    xlsx,
                    "xl/workbook.xml",
                    f"<workbook xmlns='urn:fake:spreadsheet' "
                    f"xmlns:r='{OFFICE_RELATIONSHIPS}'>"
                    "<sheets><sheet name='Sheet' r:id='rId1'/></sheets>"
                    "</workbook>",
                ),
            ),
            (
                "worksheet-relationship-type.xlsx",
                XlsxImporter(),
                changed_member(
                    xlsx,
                    "xl/_rels/workbook.xml.rels",
                    relationships(
                        "worksheets/sheet1.xml", SLIDE_RELATIONSHIP
                    ),
                ),
            ),
            (
                "worksheet-content-type.xlsx",
                XlsxImporter(),
                changed_member(
                    xlsx,
                    "[Content_Types].xml",
                    content_types(
                        "xl/workbook.xml",
                        WORKBOOK_MAIN,
                        (
                            "xl/worksheets/sheet1.xml",
                            "application/xml",
                        ),
                    ),
                ),
            ),
            (
                "worksheet-root-namespace.xlsx",
                XlsxImporter(),
                changed_member(
                    xlsx,
                    "xl/worksheets/sheet1.xml",
                    "<worksheet xmlns='urn:fake:spreadsheet'>"
                    "<sheetData/></worksheet>",
                ),
            ),
        )
        for filename, importer, members in cases:
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / filename
                    with zipfile.ZipFile(path, "w") as archive:
                        for name, payload in members:
                            archive.writestr(name, payload)
                    with self.assertRaises(DocumentImportError) as raised:
                        importer.import_document(path)
                self.assertEqual(
                    raised.exception.code, "invalid_office_archive"
                )

    def test_table_limits_cover_docx_pptx_and_reference_less_xlsx_cells(self):
        limits = replace(DEFAULT_DOCUMENT_LIMITS, max_table_columns=1)
        with self.assertRaises(DocumentImportError) as raised:
            DocxImporter().import_document(FIXTURES / "lesson.docx", limits)
        self.assertEqual(raised.exception.code, "table_too_large")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pptx = root / "table.pptx"
            with zipfile.ZipFile(pptx, "w") as archive:
                archive.writestr(
                    "[Content_Types].xml",
                    content_types(
                        "ppt/presentation.xml",
                        PRESENTATION_MAIN,
                        (
                            "ppt/slides/slide1.xml",
                            SLIDE_CONTENT_TYPE,
                        ),
                    ),
                )
                archive.writestr(
                    "_rels/.rels",
                    relationships(
                        "ppt/presentation.xml",
                        OFFICE_DOCUMENT_RELATIONSHIP,
                    ),
                )
                archive.writestr(
                    "ppt/presentation.xml",
                    f"<p:presentation xmlns:p='{PRESENTATION_NAMESPACE}' "
                    f"xmlns:r='{OFFICE_RELATIONSHIPS}'>"
                    "<p:sldIdLst><p:sldId r:id='rId1'/></p:sldIdLst>"
                    "</p:presentation>",
                )
                archive.writestr(
                    "ppt/_rels/presentation.xml.rels",
                    relationships(
                        "slides/slide1.xml", SLIDE_RELATIONSHIP
                    ),
                )
                archive.writestr(
                    "ppt/slides/slide1.xml",
                    f"<p:sld xmlns:p='{PRESENTATION_NAMESPACE}' "
                    "xmlns:a='http://schemas.openxmlformats.org/"
                    "drawingml/2006/main'><a:tbl><a:tr>"
                    "<a:tc><a:txBody><a:p><a:r><a:t>A</a:t></a:r></a:p>"
                    "</a:txBody></a:tc><a:tc><a:txBody><a:p><a:r>"
                    "<a:t>B</a:t></a:r></a:p></a:txBody></a:tc>"
                    "</a:tr></a:tbl></p:sld>",
                )
            with self.assertRaises(DocumentImportError) as raised:
                PptxImporter().import_document(pptx, limits)
            self.assertEqual(raised.exception.code, "table_too_large")

            xlsx = root / "reference-less.xlsx"
            with zipfile.ZipFile(xlsx, "w") as archive:
                archive.writestr(
                    "[Content_Types].xml",
                    content_types(
                        "xl/workbook.xml",
                        WORKBOOK_MAIN,
                        (
                            "xl/worksheets/sheet1.xml",
                            WORKSHEET_CONTENT_TYPE,
                        ),
                    ),
                )
                archive.writestr(
                    "_rels/.rels",
                    relationships(
                        "xl/workbook.xml",
                        OFFICE_DOCUMENT_RELATIONSHIP,
                    ),
                )
                archive.writestr(
                    "xl/workbook.xml",
                    f"<workbook xmlns='{SPREADSHEET_NAMESPACE}' "
                    f"xmlns:r='{OFFICE_RELATIONSHIPS}'>"
                    "<sheets><sheet name='Sheet' r:id='rId1'/></sheets>"
                    "</workbook>",
                )
                archive.writestr(
                    "xl/_rels/workbook.xml.rels",
                    relationships(
                        "worksheets/sheet1.xml",
                        WORKSHEET_RELATIONSHIP,
                    ),
                )
                archive.writestr(
                    "xl/worksheets/sheet1.xml",
                    f"<worksheet xmlns='{SPREADSHEET_NAMESPACE}'>"
                    "<sheetData><row><c t='inlineStr'><is><t>A</t>"
                    "</is></c><c t='inlineStr'><is><t>B</t></is></c></row>"
                    "</sheetData></worksheet>",
                )
            with self.assertRaises(DocumentImportError) as raised:
                XlsxImporter().import_document(xlsx, limits)
            self.assertEqual(raised.exception.code, "table_too_large")

    def test_long_valid_xlsx_header_does_not_overflow_block_metadata(self):
        header = "H" * 2001
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "long-header.xlsx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(
                    "[Content_Types].xml",
                    content_types(
                        "xl/workbook.xml",
                        WORKBOOK_MAIN,
                        (
                            "xl/worksheets/sheet1.xml",
                            WORKSHEET_CONTENT_TYPE,
                        ),
                    ),
                )
                archive.writestr(
                    "_rels/.rels",
                    relationships(
                        "xl/workbook.xml",
                        OFFICE_DOCUMENT_RELATIONSHIP,
                    ),
                )
                archive.writestr(
                    "xl/workbook.xml",
                    f"<workbook xmlns='{SPREADSHEET_NAMESPACE}' "
                    f"xmlns:r='{OFFICE_RELATIONSHIPS}'>"
                    "<sheets><sheet name='Sheet' r:id='rId1'/></sheets>"
                    "</workbook>",
                )
                archive.writestr(
                    "xl/_rels/workbook.xml.rels",
                    relationships(
                        "worksheets/sheet1.xml",
                        WORKSHEET_RELATIONSHIP,
                    ),
                )
                archive.writestr(
                    "xl/worksheets/sheet1.xml",
                    f"<worksheet xmlns='{SPREADSHEET_NAMESPACE}'>"
                    "<sheetData><row><c r='A1' t='inlineStr'>"
                    f"<is><t>{header}</t></is></c></row></sheetData></worksheet>",
                )
            document = create_native_importer_registry().import_document(path)
        table = document.sections[0].blocks[0]
        self.assertEqual(table.text, header)
        self.assertEqual(table.metadata, {"column_count": 1})

    def test_docx_grid_span_cannot_bypass_column_limit(self):
        limits = replace(DEFAULT_DOCUMENT_LIMITS, max_table_columns=1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "merged.docx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(
                    "[Content_Types].xml",
                    content_types("word/document.xml", WORD_MAIN),
                )
                archive.writestr(
                    "_rels/.rels",
                    relationships(
                        "word/document.xml",
                        OFFICE_DOCUMENT_RELATIONSHIP,
                    ),
                )
                archive.writestr(
                    "word/document.xml",
                    f"<w:document xmlns:w='{WORD_NAMESPACE}'>"
                    "<w:body><w:tbl><w:tr><w:tc>"
                    "<w:tcPr><w:gridSpan w:val='2'/></w:tcPr>"
                    "<w:p><w:r><w:t>A</w:t></w:r></w:p>"
                    "</w:tc></w:tr></w:tbl></w:body></w:document>",
                )
            with self.assertRaises(DocumentImportError) as raised:
                DocxImporter().import_document(path, limits)
        self.assertEqual(raised.exception.code, "table_too_large")


if __name__ == "__main__":
    unittest.main()
