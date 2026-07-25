import tempfile
import unittest
import zipfile
from dataclasses import replace
from pathlib import Path
from unittest import mock

from ankiforge_ai.document import DEFAULT_DOCUMENT_LIMITS, DocumentImportError
from ankiforge_ai.document.archive_safety import open_validated_archive
from ankiforge_ai.document.xml_safety import parse_xml_bounded


FIXTURES = Path(__file__).parent / "fixtures"


class DocumentArchiveXmlSecurityTests(unittest.TestCase):
    def test_doctype_and_entity_are_rejected_before_parsing(self):
        payloads = (
            (FIXTURES / "security" / "xxe.xml").read_bytes(),
            b"<!ENTITY x 'expanded'><root />",
            '<?\u0078ml version="1.0"?><!DOCTYPE root><root />'.encode("utf-16"),
        )
        for payload in payloads:
            with self.subTest(prefix=payload[:8]):
                with self.assertRaises(DocumentImportError) as raised:
                    parse_xml_bounded(payload)
                self.assertEqual(raised.exception.code, "xml_not_safe")

    def test_xml_depth_element_and_text_limits_fail_closed(self):
        cases = (
            (
                b"<a><b><c>text</c></b></a>",
                replace(DEFAULT_DOCUMENT_LIMITS, max_xml_depth=2),
            ),
            (
                b"<a><b/><c/></a>",
                replace(DEFAULT_DOCUMENT_LIMITS, max_xml_elements=2),
            ),
            (
                b"<a>12345</a>",
                replace(DEFAULT_DOCUMENT_LIMITS, max_text_chars=4),
            ),
            (
                b"<a value='12345' />",
                replace(DEFAULT_DOCUMENT_LIMITS, max_text_chars=4),
            ),
        )
        for payload, limits in cases:
            with self.subTest(limits=limits):
                with self.assertRaises(DocumentImportError) as raised:
                    parse_xml_bounded(payload, limits)
                self.assertEqual(raised.exception.code, "document_too_complex")

    def test_office_macro_member_is_rejected_before_any_member_is_read(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "macro.docx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("[Content_Types].xml", "<Types />")
                archive.writestr("word/document.xml", "<document />")
                archive.writestr("word/vbaProject.bin", b"macro")
            with self.assertRaises(DocumentImportError) as raised:
                with open_validated_archive(path):
                    pass
        self.assertEqual(raised.exception.code, "office_macros_not_allowed")

    def test_malformed_xml_has_structured_error_without_payload_leak(self):
        secret = "PRIVATE_PAYLOAD"
        with self.assertRaises(DocumentImportError) as raised:
            parse_xml_bounded(f"<root>{secret}</broken>".encode())
        self.assertEqual(raised.exception.code, "malformed_file")
        self.assertNotIn(secret, repr(raised.exception))

    def test_archive_rejects_traversal_symlink_duplicate_and_encrypted_members(self):
        cases = []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            traversal = root / "traversal.zip"
            with zipfile.ZipFile(traversal, "w") as archive:
                archive.writestr("../outside.txt", "unsafe")
            cases.append((traversal, "unsafe_archive_member"))

            symlink = root / "symlink.zip"
            with zipfile.ZipFile(symlink, "w") as archive:
                info = zipfile.ZipInfo("link")
                info.create_system = 3
                info.external_attr = 0o120777 << 16
                archive.writestr(info, "target")
            cases.append((symlink, "unsafe_archive_member"))

            duplicate = root / "duplicate.zip"
            with zipfile.ZipFile(duplicate, "w") as archive:
                archive.writestr("OPS/café.xhtml", "one")
                archive.writestr("OPS/cafe\u0301.xhtml", "two")
            cases.append((duplicate, "duplicate_archive_member"))

            encrypted = root / "encrypted.zip"
            with zipfile.ZipFile(encrypted, "w") as archive:
                archive.writestr("secret.txt", "secret")
            payload = bytearray(encrypted.read_bytes())
            local = payload.find(b"PK\x03\x04")
            central = payload.find(b"PK\x01\x02")
            payload[local + 6 : local + 8] = (
                int.from_bytes(payload[local + 6 : local + 8], "little") | 1
            ).to_bytes(2, "little")
            payload[central + 8 : central + 10] = (
                int.from_bytes(payload[central + 8 : central + 10], "little") | 1
            ).to_bytes(2, "little")
            encrypted.write_bytes(payload)
            cases.append((encrypted, "encrypted_archive_member"))

            for path, code in cases:
                with self.subTest(code=code):
                    with self.assertRaises(DocumentImportError) as raised:
                        with open_validated_archive(path):
                            pass
                    self.assertEqual(raised.exception.code, code)
                    self.assertNotIn(str(root), repr(raised.exception))
            self.assertFalse((root / "outside.txt").exists())

    def test_archive_member_aggregate_count_and_ratio_limits_fail_closed(self):
        settings = (
            (
                replace(DEFAULT_DOCUMENT_LIMITS, max_archive_members=1),
                [("a", b"1"), ("b", b"2")],
                "archive_too_many_members",
            ),
            (
                replace(DEFAULT_DOCUMENT_LIMITS, max_member_bytes=1),
                [("a", b"12")],
                "archive_member_too_large",
            ),
            (
                replace(DEFAULT_DOCUMENT_LIMITS, max_archive_uncompressed_bytes=2),
                [("a", b"12"), ("b", b"3")],
                "archive_too_large",
            ),
            (
                replace(DEFAULT_DOCUMENT_LIMITS, max_archive_compression_ratio=1.0),
                [("a", b"0" * 100)],
                "suspicious_archive_compression",
            ),
        )
        for limits, members, code in settings:
            with self.subTest(code=code):
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "bounded.zip"
                    with zipfile.ZipFile(
                        path, "w", compression=zipfile.ZIP_DEFLATED
                    ) as archive:
                        for name, payload in members:
                            archive.writestr(name, payload)
                    with self.assertRaises(DocumentImportError) as raised:
                        with open_validated_archive(path, limits):
                            pass
                self.assertEqual(raised.exception.code, code)

    def test_archive_handle_is_closed_when_validation_rejects_it(self):
        class TrackingArchive:
            def __init__(self):
                self.closed = False

            def infolist(self):
                return [zipfile.ZipInfo("a"), zipfile.ZipInfo("b")]

            def close(self):
                self.closed = True

        archive = TrackingArchive()
        limits = replace(DEFAULT_DOCUMENT_LIMITS, max_archive_members=1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.zip"
            path.write_bytes(b"placeholder")
            with mock.patch(
                "ankiforge_ai.document.archive_safety.zipfile.ZipFile",
                return_value=archive,
            ):
                with self.assertRaises(DocumentImportError):
                    with open_validated_archive(path, limits):
                        pass
        self.assertTrue(archive.closed)


if __name__ == "__main__":
    unittest.main()
