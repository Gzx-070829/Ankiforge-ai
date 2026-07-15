import unittest

from ankiforge_ai.pipeline.generation_settings import (
    GenerationSettings,
    all_card_mode_profiles,
    card_limit_for_settings,
    coerce_generation_settings,
    get_card_mode_profile,
)


class GenerationSettingsTests(unittest.TestCase):
    def test_all_modes_are_enumerable_and_bilingual(self):
        profiles = all_card_mode_profiles()

        self.assertEqual(
            tuple(profile.mode_id for profile in profiles),
            (
                "concept",
                "definition",
                "exam",
                "quick_review",
                "compare_contrast",
                "process_steps",
                "formula_rule",
                "mistake_trap",
                "cloze_candidate",
            ),
        )
        for profile in profiles:
            self.assertTrue(profile.display_name_zh)
            self.assertTrue(profile.display_name_en)
            self.assertTrue(profile.description_zh)
            self.assertTrue(profile.description_en)
            self.assertTrue(profile.prompt_guidance)
            self.assertTrue(profile.quality_priorities)

    def test_defaults_match_product_contract(self):
        settings = GenerationSettings()

        self.assertEqual(settings.card_mode, "concept")
        self.assertEqual(settings.card_count, "balanced")
        self.assertEqual(settings.answer_length, "short")
        self.assertEqual(settings.language, "auto")
        self.assertEqual(card_limit_for_settings(settings), 5)

    def test_card_count_maps_to_conservative_limits(self):
        self.assertEqual(card_limit_for_settings(GenerationSettings(card_count="auto")), 5)
        self.assertEqual(card_limit_for_settings(GenerationSettings(card_count="fewer")), 3)
        self.assertEqual(card_limit_for_settings(GenerationSettings(card_count="balanced")), 5)
        self.assertEqual(card_limit_for_settings(GenerationSettings(card_count="more")), 8)

    def test_unknown_values_raise_clear_validation_errors(self):
        for field, value in (
            ("card_mode", "mystery"),
            ("card_count", "many"),
            ("answer_length", "essay"),
            ("language", "fr"),
        ):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, field):
                    GenerationSettings(**{field: value})

        with self.assertRaisesRegex(ValueError, "card_mode"):
            get_card_mode_profile("unknown")

    def test_none_coerces_to_defaults_and_existing_instance_is_reused(self):
        default = coerce_generation_settings(None)
        explicit = GenerationSettings(card_mode="exam")

        self.assertEqual(default, GenerationSettings())
        self.assertIs(coerce_generation_settings(explicit), explicit)

    def test_repr_and_safe_dict_contain_only_nonsensitive_choices(self):
        settings = GenerationSettings(card_mode="exam", language="zh")
        rendered = repr(settings)

        self.assertIn("card_mode='exam'", rendered)
        self.assertEqual(
            settings.to_safe_dict(),
            {
                "card_mode": "exam",
                "card_count": "balanced",
                "answer_length": "short",
                "language": "zh",
            },
        )
        for marker in ("api_key", "authorization", "bearer", "password"):
            self.assertNotIn(marker, rendered.casefold())


if __name__ == "__main__":
    unittest.main()
