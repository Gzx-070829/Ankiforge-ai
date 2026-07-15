import unittest

from ankiforge_ai.pipeline.user_errors import (
    USER_ERROR_CODES,
    get_user_error,
)


class UserErrorCatalogTests(unittest.TestCase):
    EXPECTED_CODES = {
        "no_material",
        "ai_not_configured",
        "api_key_empty",
        "provider_call_failed",
        "pdf_not_parsed",
        "no_kept_cards",
        "duplicate_not_checked",
        "mapping_incomplete",
        "blocking_cards_exist",
        "write_failed",
        "unsupported_note_type",
        "import_failed",
        "docx_partial_extraction",
        "model_empty",
        "provider_empty",
    }

    def test_required_codes_are_complete_and_stable(self):
        self.assertEqual(set(USER_ERROR_CODES), self.EXPECTED_CODES)

    def test_every_error_has_safe_natural_copy_in_both_languages(self):
        for code in USER_ERROR_CODES:
            for language in ("zh", "en"):
                with self.subTest(code=code, language=language):
                    item = get_user_error(code, language)
                    self.assertEqual(item.code, code)
                    self.assertIn(item.severity, {"info", "warning", "error"})
                    self.assertTrue(item.message.strip())
                    self.assertTrue(item.suggested_action.strip())
                    rendered = item.message + item.suggested_action
                    self.assertNotIn("Traceback", rendered)
                    self.assertNotIn("C:\\", rendered)
                    self.assertNotIn("sk-", rendered.casefold())

    def test_unknown_code_and_language_fail_closed(self):
        with self.assertRaises(ValueError):
            get_user_error("unknown", "zh")
        with self.assertRaises(ValueError):
            get_user_error("no_material", "fr")

    def test_repr_is_structural(self):
        item = get_user_error("provider_call_failed", "zh")
        self.assertNotIn(item.message, repr(item))
        self.assertNotIn(item.suggested_action, repr(item))


if __name__ == "__main__":
    unittest.main()
