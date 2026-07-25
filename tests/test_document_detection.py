import json
import tempfile
import unittest
import zipfile
from dataclasses import replace
from pathlib import Path
from unittest import mock

from ankiforge_ai.document import (
    DEFAULT_DOCUMENT_LIMITS,
    DetectedFileType,
    DocumentImportError,
    detect_file_type,
)
from ankiforge_ai.document.detection import DETECTION_PREFIX_BYTES


class DocumentDetectionTests(unittest.TestCase):
    def test_utf_boms_and_plain_utf8_are_detected_without_returning_content(self):
        cases = (
            ("utf8.txt", b"\xef\xbb\xbfhello", "utf-8-sig"),
            ("utf16le.txt", b"\xff\xfeh\x00i\x00", "utf-16-le"),
            ("utf16be.txt", b"\xfe\xff\x00h\x00i", "utf-16-be"),
            ("utf32le.txt", b"\xff\xfe\x00\x00h\x00\x00\x00", "utf-32-le"),
            ("utf32be.txt", b"\x00\x00\xfe\xff\x00\x00\x00h", "utf-32-be"),
            ("utf8.txt", "你好".encode("utf-8"), "utf-8"),
        )
        for filename, payload, encoding in cases:
            with self.subTest(filename=filename, encoding=encoding):
                with self.binary_file(filename, payload) as path:
                    detected = detect_file_type(path)
                self.assertIsInstance(detected, DetectedFileType)
                self.assertEqual(detected.file_type, "text")
                self.assertEqual(detected.encoding, encoding)
                self.assertTrue(detected.is_text)
                self.assertNotIn("hello", repr(detected))
                self.assertNotIn("你好", repr(detected))

    def test_detection_reads_only_a_bounded_prefix_for_non_archives(self):
        payload = b"plain text\n" + b"x" * (DETECTION_PREFIX_BYTES * 2)
        with self.binary_file("large.txt", payload) as path:
            requested_sizes = []
            real_open = Path.open

            class TrackingReader:
                def __init__(self, wrapped):
                    self.wrapped = wrapped

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    self.wrapped.close()

                def read(self, size=-1):
                    requested_sizes.append(size)
                    return self.wrapped.read(size)

            def tracked_open(target, *args, **kwargs):
                return TrackingReader(real_open(target, *args, **kwargs))

            with mock.patch.object(Path, "open", tracked_open):
                detected = detect_file_type(path)

        self.assertEqual(detected.file_type, "text")
        self.assertEqual(requested_sizes, [DETECTION_PREFIX_BYTES])

    def test_binary_renamed_as_text_is_rejected_and_safe_mismatch_is_warned(self):
        with self.binary_file("renamed.txt", b"%PDF-1.7\nbinary") as path:
            with self.assertRaises(DocumentImportError) as raised:
                detect_file_type(path)
        self.assertEqual(raised.exception.code, "risky_extension_mismatch")

        with self.binary_file("notes.txt", b'{"topic":"safety"}') as path:
            detected = detect_file_type(path)
        self.assertEqual(detected.file_type, "json")
        self.assertEqual(detected.extension, ".txt")
        self.assertEqual(detected.warnings, ("extension_mismatch",))

        with self.binary_file("binary.txt", b"\x00\x01\x02\x03\x04") as path:
            with self.assertRaises(DocumentImportError) as raised:
                detect_file_type(path)
        self.assertEqual(raised.exception.code, "binary_extension_mismatch")

    def test_office_zip_types_are_identified_from_member_names_without_extraction(self):
        cases = (
            ("renamed.zip", "word/document.xml", "docx"),
            ("slides.bin", "ppt/presentation.xml", "pptx"),
            ("table.data", "xl/workbook.xml", "xlsx"),
        )
        for filename, member, file_type in cases:
            with self.subTest(file_type=file_type):
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / filename
                    with zipfile.ZipFile(path, "w") as archive:
                        archive.writestr("[Content_Types].xml", "<Types />")
                        archive.writestr(member, "<root />")
                    detected = detect_file_type(path)
                    self.assertEqual(
                        list(Path(directory).iterdir()), [path]
                    )
                self.assertEqual(detected.file_type, file_type)
                self.assertEqual(detected.warnings, ("extension_mismatch",))

    def test_epub_signature_uses_mimetype_and_container_members(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "book.epub"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("mimetype", "application/epub+zip")
                archive.writestr("META-INF/container.xml", "<container />")
                archive.writestr("OPS/chapter.xhtml", "<p>Chapter</p>")

            detected = detect_file_type(path)

        self.assertEqual(detected.file_type, "epub")
        self.assertEqual(detected.media_type, "application/epub+zip")
        self.assertFalse(detected.is_text)

    def test_archive_member_count_is_bounded_before_signature_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "many.docx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("[Content_Types].xml", "<Types />")
                archive.writestr("word/document.xml", "<document />")
            limits = replace(DEFAULT_DOCUMENT_LIMITS, max_archive_members=1)

            with self.assertRaises(DocumentImportError) as raised:
                detect_file_type(path, limits)

        self.assertEqual(raised.exception.code, "archive_too_many_members")

    def test_text_limit_is_applied_after_content_detection(self):
        limits = replace(
            DEFAULT_DOCUMENT_LIMITS,
            max_text_file_bytes=4,
            max_source_file_bytes=10,
        )
        with self.binary_file("large.txt", b"12345") as path:
            with self.assertRaises(DocumentImportError) as raised:
                detect_file_type(path, limits)
        self.assertEqual(raised.exception.code, "file_too_large")

    def test_macro_bearing_office_archives_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unsafe.docm"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("[Content_Types].xml", "<Types />")
                archive.writestr("word/document.xml", "<document />")
                archive.writestr("word/vbaProject.bin", b"macro")

            with self.assertRaises(DocumentImportError) as raised:
                detect_file_type(path)

        self.assertEqual(raised.exception.code, "office_macros_not_allowed")

    def test_json_notebook_and_xml_roots_override_ambiguous_extensions(self):
        notebook = json.dumps(
            {"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}
        ).encode("utf-8")
        cases = (
            ("data.data", b'{"items":[1,2]}', "json"),
            ("lesson.json", notebook, "ipynb"),
            ("feed.data", b'<?xml version="1.0"?><feed><item /></feed>', "xml"),
            ("page.xml", b"<html><body>safe</body></html>", "html"),
        )
        for filename, payload, expected in cases:
            with self.subTest(file_type=expected):
                with self.binary_file(filename, payload) as path:
                    detected = detect_file_type(path)
                self.assertEqual(detected.file_type, expected)

    def test_empty_malformed_json_xml_and_zip_have_structured_errors(self):
        cases = (
            ("empty.txt", b"", "empty_file"),
            ("bad.json", b'{"unfinished":', "malformed_file"),
            ("bad.xml", b"<root><unfinished></root>", "malformed_file"),
            ("bad.docx", b"PK\x03\x04not-a-real-zip", "invalid_archive"),
        )
        for filename, payload, code in cases:
            with self.subTest(filename=filename):
                with self.binary_file(filename, payload) as path:
                    with self.assertRaises(DocumentImportError) as raised:
                        detect_file_type(path)
                self.assertEqual(raised.exception.code, code)
                self.assertNotIn(str(path), repr(raised.exception))

    def test_known_container_suffix_without_required_signatures_is_rejected(self):
        with self.binary_file("fake.docx", b"this is plain text") as path:
            with self.assertRaises(DocumentImportError) as raised:
                detect_file_type(path)
        self.assertEqual(raised.exception.code, "malformed_file")

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "incomplete.docx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("word/document.xml", "<document />")
            with self.assertRaises(DocumentImportError) as raised:
                detect_file_type(path)
        self.assertEqual(raised.exception.code, "invalid_archive")

    def test_duplicate_case_or_unicode_normalized_archive_members_are_rejected(self):
        cases = (
            ("word/document.xml", "WORD/DOCUMENT.XML"),
            ("OPS/café.xhtml", "OPS/cafe\u0301.xhtml"),
        )
        for first, second in cases:
            with self.subTest(first=first, second=second):
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "ambiguous.zip"
                    with zipfile.ZipFile(path, "w") as archive:
                        archive.writestr(first, "first")
                        archive.writestr(second, "second")
                    with self.assertRaises(DocumentImportError) as raised:
                        detect_file_type(path)
                self.assertEqual(
                    raised.exception.code,
                    "duplicate_archive_member",
                )

    @staticmethod
    def binary_file(filename, payload):
        class BinaryFileContext:
            def __enter__(self):
                self.directory = tempfile.TemporaryDirectory()
                self.path = Path(self.directory.name) / filename
                self.path.write_bytes(payload)
                return self.path

            def __exit__(self, *_args):
                self.directory.cleanup()

        return BinaryFileContext()


if __name__ == "__main__":
    unittest.main()
