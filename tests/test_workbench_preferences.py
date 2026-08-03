import unittest

from ankiforge_ai.workbench.preferences import (
    PREFERENCES_SCHEMA_VERSION,
    WorkbenchPreferences,
)


class WorkbenchPreferencesTests(unittest.TestCase):
    def test_defaults_match_the_simple_product_flow(self):
        preferences = WorkbenchPreferences.defaults()

        self.assertEqual(preferences.ui_language, "zh")
        self.assertEqual(preferences.provider_name, "DeepSeek")
        self.assertEqual(preferences.model_name, "deepseek-v4-flash")
        self.assertEqual(preferences.card_mode, "concept")
        self.assertEqual(preferences.card_count, "balanced")
        self.assertEqual(preferences.answer_length, "short")
        self.assertEqual(preferences.output_language, "auto")
        self.assertEqual(preferences.intelligence_level, "standard")

    def test_safe_mapping_round_trip_is_versioned_and_exact(self):
        original = WorkbenchPreferences.defaults().with_updates(
            ui_language="en",
            provider_name="OpenAI",
            model_name="gpt-4o-mini",
            card_mode="definition",
            card_count="fewer",
            answer_length="medium",
            output_language="en",
            intelligence_level="fast",
        )

        payload = original.to_safe_dict()

        self.assertEqual(payload["schema_version"], PREFERENCES_SCHEMA_VERSION)
        self.assertEqual(WorkbenchPreferences.from_mapping(payload), original)
        self.assertEqual(
            set(payload),
            {
                "schema_version",
                "ui_language",
                "provider_name",
                "model_name",
                "card_mode",
                "card_count",
                "answer_length",
                "output_language",
                "intelligence_level",
            },
        )

    def test_unknown_or_sensitive_fields_are_rejected(self):
        base = WorkbenchPreferences.defaults().to_safe_dict()
        for field in (
            "api_key",
            "token",
            "secret",
            "password",
            "authorization",
            "bearer",
            "cookie",
            "base_url",
            "material_text",
            "source_path",
            "candidate_content",
            "review_state",
            "write_history",
        ):
            with self.subTest(field=field):
                payload = dict(base)
                payload[field] = "must-never-be-written"
                with self.assertRaises(ValueError):
                    WorkbenchPreferences.from_mapping(payload)

    def test_invalid_values_and_secret_shaped_model_fail_closed(self):
        base = WorkbenchPreferences.defaults().to_safe_dict()
        cases = (
            ("ui_language", "fr"),
            ("provider_name", "Unknown provider"),
            ("card_mode", "cloze_candidate"),
            ("card_count", "unlimited"),
            ("answer_length", "essay"),
            ("output_language", "fr"),
            ("intelligence_level", "maximum"),
            ("model_name", "sk-live-abcdefghijklmnopqrstuvwxyz012345"),
            ("model_name", "Bearer eyJhbGciOiJIUzI1NiJ9.payload"),
            ("model_name", "https://private.example/model"),
            ("model_name", "C:\\Users\\person\\model"),
            ("model_name", "x" * 129),
        )
        for field, value in cases:
            with self.subTest(field=field, value=value[:20]):
                payload = dict(base)
                payload[field] = value
                with self.assertRaises(ValueError):
                    WorkbenchPreferences.from_mapping(payload)

    def test_repr_does_not_include_the_model_value(self):
        preferences = WorkbenchPreferences.defaults().with_updates(
            model_name="private-local-model-label"
        )

        self.assertNotIn("private-local-model-label", repr(preferences))


if __name__ == "__main__":
    unittest.main()
