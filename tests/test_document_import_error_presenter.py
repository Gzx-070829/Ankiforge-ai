import unittest

from ankiforge_ai.ui.document_import_error_presenter import (
    present_document_import_issue,
)


class DocumentImportErrorPresenterTests(unittest.TestCase):
    def test_emitted_warning_and_error_codes_have_safe_bilingual_guidance(self):
        codes = (
            "extension_mismatch",
            "hidden_sheet_skipped",
            "notebook_output_too_large",
            "notebook_binary_output_skipped",
            "unsupported_type",
            "optional_importer_unavailable",
            "optional_backend_missing",
            "backend_timeout",
            "backend_failed",
            "backend_invalid_output",
            "file_too_large",
            "document_too_complex",
            "invalid_office_archive",
            "unsafe_xml",
            "material_preview_truncated",
        )
        for language in ("zh", "en"):
            for code in codes:
                with self.subTest(language=language, code=code):
                    view = present_document_import_issue(
                        code,
                        language=language,
                    )
                    self.assertTrue(view.message)
                    self.assertTrue(view.action)
                    self.assertNotIn(code, view.display_text)
                    self.assertNotIn("Traceback", view.display_text)

    def test_pdf_fallback_and_backend_setup_are_actionable(self):
        unsupported = present_document_import_issue(
            "unsupported_type",
            language="en",
        ).display_text
        missing = present_document_import_issue(
            "optional_backend_missing",
            language="zh",
        ).display_text

        self.assertIn("PDF", unsupported)
        self.assertIn("copy", unsupported.casefold())
        self.assertIn("支持能力", missing)
        self.assertIn("本次会话", missing)

    def test_unknown_safe_code_uses_generic_copy_instead_of_raising(self):
        view = present_document_import_issue(
            "future_safe_error",
            language="en",
        )

        self.assertIn("Document import", view.message)


if __name__ == "__main__":
    unittest.main()
