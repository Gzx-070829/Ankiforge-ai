import tempfile
import unittest
import zipfile
from pathlib import Path

from ankiforge_ai.document import (
    DEFAULT_DOCUMENT_LIMITS,
    DocumentImportError,
    ImporterCapability,
    SupportLevel,
)
from ankiforge_ai.document.importers.base import DocumentImporter, ImportInspection
from ankiforge_ai.document.importers import (
    DocumentImporterRegistry as ExportedDocumentImporterRegistry,
)
from ankiforge_ai.document.registry import DocumentImporterRegistry


def capability(
    importer_id,
    support_level=SupportLevel.NATIVE_TEXT,
    extensions=(".txt",),
    fallback_importer_ids=(),
):
    return ImporterCapability(
        importer_id=importer_id,
        display_name_en=importer_id,
        display_name_zh=importer_id,
        support_level=support_level,
        supported_extensions=extensions,
        supports_structure=support_level is SupportLevel.NATIVE_STRUCTURED,
        supports_tables=False,
        supports_images=False,
        supports_formulas=False,
        external_dependencies=(),
        unavailable_reason_key=None,
        security_notes=("local_files_only", "no_execution"),
        fallback_importer_ids=fallback_importer_ids,
    )


class FakeImporter(DocumentImporter):
    def __init__(self, importer_id, extensions=(".txt",), result=None, error=None):
        self.importer_id = importer_id
        self.supported_extensions = extensions
        self.result = result
        self.error = error
        self.import_calls = 0

    def availability(self):
        return True

    def inspect(self, path, limits=DEFAULT_DOCUMENT_LIMITS):
        return ImportInspection(
            importer_id=self.importer_id,
            source_label=Path(path).name,
            detected_file_type="text",
            warnings=(),
        )

    def import_document(self, path, limits=DEFAULT_DOCUMENT_LIMITS):
        self.import_calls += 1
        if self.error is not None:
            raise self.error
        return self.result


class DocumentRegistryTests(unittest.TestCase):
    def test_importers_package_exports_the_registry(self):
        self.assertIs(ExportedDocumentImporterRegistry, DocumentImporterRegistry)

    def test_support_levels_are_exact_and_capability_sequences_are_immutable(self):
        self.assertEqual(
            tuple(level.value for level in SupportLevel),
            (
                "native_structured",
                "native_text",
                "optional_advanced",
                "fallback_only",
                "unsupported",
            ),
        )
        extensions = [".md"]
        notes = ["no_execution"]
        item = ImporterCapability(
            importer_id="markdown",
            display_name_en="Markdown",
            display_name_zh="Markdown",
            support_level=SupportLevel.NATIVE_STRUCTURED,
            supported_extensions=extensions,
            supports_structure=True,
            supports_tables=True,
            supports_images=False,
            supports_formulas=False,
            external_dependencies=[],
            unavailable_reason_key=None,
            security_notes=notes,
            fallback_importer_ids=[],
        )
        extensions.append(".txt")
        notes.append("changed")

        self.assertEqual(item.supported_extensions, (".md",))
        self.assertEqual(item.security_notes, ("no_execution",))

    def test_capability_matrix_has_stable_level_then_id_order(self):
        registry = DocumentImporterRegistry()
        for item in (
            capability("z_text"),
            capability("z_optional", SupportLevel.OPTIONAL_ADVANCED),
            capability("z_structured", SupportLevel.NATIVE_STRUCTURED),
            capability("a_text"),
            capability("z_fallback", SupportLevel.FALLBACK_ONLY),
            capability("z_unsupported", SupportLevel.UNSUPPORTED),
        ):
            registry.register(item, lambda: FakeImporter("unused"))

        self.assertEqual(
            tuple(item.importer_id for item in registry.capabilities()),
            (
                "z_structured",
                "a_text",
                "z_text",
                "z_optional",
                "z_fallback",
                "z_unsupported",
            ),
        )

    def test_registration_and_capability_queries_do_not_invoke_lazy_factory(self):
        registry = DocumentImporterRegistry()
        calls = []

        def absent_factory():
            calls.append("called")
            raise ModuleNotFoundError("optional_backend")

        registry.register(
            capability("optional", SupportLevel.OPTIONAL_ADVANCED, (".pdf",)),
            absent_factory,
        )

        self.assertEqual(calls, [])
        self.assertEqual(registry.capabilities()[0].importer_id, "optional")
        self.assertEqual(calls, [])
        with self.assertRaises(DocumentImportError) as raised:
            registry.create_importer("optional")
        self.assertEqual(raised.exception.code, "optional_importer_unavailable")
        self.assertEqual(raised.exception.safe_details, {"importer_id": "optional"})
        self.assertEqual(calls, ["called"])
        self.assertNotIn("optional_backend", repr(raised.exception))

    def test_optional_factory_runtime_failure_is_wrapped_without_raw_output(self):
        registry = DocumentImporterRegistry()

        def broken_factory():
            raise RuntimeError(
                r"C:\Users\alice\private.pdf sk-test-not-a-real-key"
            )

        registry.register(
            capability("broken", SupportLevel.OPTIONAL_ADVANCED, (".pdf",)),
            broken_factory,
        )
        with self.assertRaises(DocumentImportError) as raised:
            registry.create_importer("broken")

        self.assertEqual(raised.exception.code, "optional_importer_unavailable")
        self.assertNotIn(r"C:\Users", repr(raised.exception))
        self.assertNotIn("sk-test-not-a-real-key", repr(raised.exception))

    def test_default_selection_is_deterministic_and_excludes_optional_fallback(self):
        registry = DocumentImporterRegistry()
        created = []

        def factory(importer_id):
            def create():
                created.append(importer_id)
                return FakeImporter(importer_id)

            return create

        for item in (
            capability("z_native"),
            capability("fallback", SupportLevel.FALLBACK_ONLY),
            capability("optional", SupportLevel.OPTIONAL_ADVANCED),
            capability("a_native"),
        ):
            registry.register(item, factory(item.importer_id))

        with self.text_file() as path:
            selected = registry.select_importer(path)

        self.assertEqual(selected.importer_id, "a_native")
        self.assertEqual(created, ["a_native"])

    def test_explicit_importer_selection_can_choose_optional(self):
        registry = DocumentImporterRegistry()
        optional = FakeImporter("optional", (".txt",))
        registry.register(
            capability("optional", SupportLevel.OPTIONAL_ADVANCED),
            lambda: optional,
        )

        with self.text_file() as path:
            selected = registry.select_importer(path, importer_id="optional")

        self.assertIs(selected, optional)

    def test_explicit_selection_cannot_choose_unsupported_capability(self):
        registry = DocumentImporterRegistry()
        registry.register(
            capability("unsupported", SupportLevel.UNSUPPORTED),
            lambda: FakeImporter("unsupported"),
        )
        with self.text_file() as path:
            with self.assertRaises(DocumentImportError) as raised:
                registry.select_importer(path, importer_id="unsupported")
        self.assertEqual(raised.exception.code, "unsupported_type")

    def test_fallback_runs_only_when_explicit_and_named_by_primary_capability(self):
        primary_error = DocumentImportError(
            code="primary_failed",
            message_key="document.error.primary_failed",
            action_key="document.action.choose_fallback",
        )
        primary = FakeImporter("primary", error=primary_error)
        fallback = FakeImporter("fallback", result="safe-result")
        registry = DocumentImporterRegistry()
        registry.register(
            capability("primary", fallback_importer_ids=("fallback",)),
            lambda: primary,
        )
        registry.register(
            capability("fallback", SupportLevel.FALLBACK_ONLY),
            lambda: fallback,
        )

        with self.text_file() as path:
            with self.assertRaises(DocumentImportError) as raised:
                registry.import_document(path, importer_id="primary")
            self.assertIs(raised.exception, primary_error)
            result = registry.import_document(
                path,
                importer_id="primary",
                fallback_importer_id="fallback",
            )

        self.assertEqual(result, "safe-result")
        self.assertEqual(primary.import_calls, 2)
        self.assertEqual(fallback.import_calls, 1)

    def test_unnamed_fallback_and_duplicate_registration_have_safe_errors(self):
        registry = DocumentImporterRegistry()
        primary = FakeImporter(
            "primary",
            error=DocumentImportError(
                code="primary_failed",
                message_key="document.error.primary_failed",
                action_key="document.action.choose_fallback",
            ),
        )
        registry.register(capability("primary"), lambda: primary)
        registry.register(
            capability("fallback", SupportLevel.FALLBACK_ONLY),
            lambda: FakeImporter("fallback"),
        )
        with self.assertRaises(DocumentImportError) as raised:
            registry.register(capability("primary"), lambda: primary)
        self.assertEqual(raised.exception.code, "duplicate_importer")

        with self.text_file() as path:
            with self.assertRaises(DocumentImportError) as raised:
                registry.import_document(
                    path,
                    importer_id="primary",
                    fallback_importer_id="fallback",
                )
        self.assertEqual(raised.exception.code, "fallback_not_allowed")

    def test_unexpected_primary_and_fallback_exceptions_are_safely_wrapped(self):
        raw_secret = r"C:\Users\alice\private.txt sk-live-secret-1234567890"
        registry = DocumentImporterRegistry()
        primary = FakeImporter("primary", error=RuntimeError(raw_secret))
        failing_fallback = FakeImporter(
            "fallback",
            error=RuntimeError(raw_secret),
        )
        registry.register(
            capability("primary", fallback_importer_ids=("fallback",)),
            lambda: primary,
        )
        registry.register(
            capability("fallback", SupportLevel.FALLBACK_ONLY),
            lambda: failing_fallback,
        )

        with self.text_file() as path:
            with self.assertRaises(DocumentImportError) as raised:
                registry.import_document(path, importer_id="primary")
            self.assertEqual(
                raised.exception.code,
                "importer_execution_failed",
            )
            self.assertNotIn(raw_secret, repr(raised.exception))
            self.assertNotIn(raw_secret, str(raised.exception))
            self.assertIsNone(raised.exception.__cause__)
            self.assertTrue(raised.exception.__suppress_context__)

            with self.assertRaises(DocumentImportError) as raised:
                registry.import_document(
                    path,
                    importer_id="primary",
                    fallback_importer_id="fallback",
                )
            self.assertEqual(
                raised.exception.code,
                "importer_execution_failed",
            )
            self.assertEqual(
                raised.exception.safe_details,
                {"importer_id": "fallback"},
            )
            self.assertNotIn(raw_secret, repr(raised.exception))

    def test_signature_type_routes_renamed_and_extensionless_inputs(self):
        registry = DocumentImporterRegistry()
        text = FakeImporter("text", (".txt", ".log"))
        json_importer = FakeImporter("json", (".json",))
        docx = FakeImporter("docx", (".docx",))
        pdf = FakeImporter("pdf", (".pdf",))
        registry.register(capability("text", extensions=(".txt", ".log")), lambda: text)
        registry.register(capability("json", extensions=(".json",)), lambda: json_importer)
        registry.register(
            capability(
                "docx",
                SupportLevel.NATIVE_STRUCTURED,
                extensions=(".docx",),
            ),
            lambda: docx,
        )
        registry.register(
            capability("pdf", SupportLevel.FALLBACK_ONLY, extensions=(".pdf",)),
            lambda: pdf,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            renamed_json = root / "lesson.txt"
            renamed_json.write_text('{"topic":"safe"}', encoding="utf-8")
            extensionless_json = root / "json_source"
            extensionless_json.write_text('{"topic":"safe"}', encoding="utf-8")
            extensionless_docx = root / "office_source"
            with zipfile.ZipFile(extensionless_docx, "w") as archive:
                archive.writestr("[Content_Types].xml", "<Types />")
                archive.writestr("word/document.xml", "<document />")
            extensionless_pdf = root / "pdf_source"
            extensionless_pdf.write_bytes(b"%PDF-1.7\nsafe")

            self.assertIs(registry.select_importer(renamed_json), json_importer)
            self.assertIs(registry.select_importer(extensionless_json), json_importer)
            self.assertIs(registry.select_importer(extensionless_docx), docx)
            with self.assertRaises(DocumentImportError) as raised:
                registry.select_importer(extensionless_pdf)
            self.assertEqual(raised.exception.code, "unsupported_type")
            self.assertIs(
                registry.select_importer(extensionless_pdf, importer_id="pdf"),
                pdf,
            )

    def test_custom_safe_text_suffix_can_select_its_registered_importer(self):
        registry = DocumentImporterRegistry()
        custom_text = FakeImporter("custom_text", (".foo",))
        generic_text = FakeImporter("generic_text", (".txt", ".log"))
        json_importer = FakeImporter("json", (".json",))
        xml_importer = FakeImporter("xml", (".xml",))
        registry.register(
            capability("custom_text", extensions=(".foo",)),
            lambda: custom_text,
        )
        registry.register(
            capability("generic_text", extensions=(".txt", ".log")),
            lambda: generic_text,
        )
        registry.register(
            capability("json", extensions=(".json",)),
            lambda: json_importer,
        )
        registry.register(
            capability(
                "xml",
                SupportLevel.NATIVE_STRUCTURED,
                extensions=(".xml",),
            ),
            lambda: xml_importer,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            custom = root / "lesson.foo"
            custom.write_text("plain custom text", encoding="utf-8")
            renamed_json = root / "data.txt"
            renamed_json.write_text('{"safe":true}', encoding="utf-8")
            renamed_xml = root / "feed.foo"
            renamed_xml.write_text("<feed><item /></feed>", encoding="utf-8")

            self.assertIs(registry.select_importer(custom), custom_text)
            self.assertIs(
                registry.select_importer(custom, importer_id="custom_text"),
                custom_text,
            )
            self.assertIs(registry.select_importer(renamed_json), json_importer)
            self.assertIs(registry.select_importer(renamed_xml), xml_importer)

    @staticmethod
    def text_file():
        class TextFileContext:
            def __enter__(self):
                self.directory = tempfile.TemporaryDirectory()
                self.path = Path(self.directory.name) / "lesson.txt"
                self.path.write_text("safe text", encoding="utf-8")
                return self.path

            def __exit__(self, *_args):
                self.directory.cleanup()

        return TextFileContext()


if __name__ == "__main__":
    unittest.main()
