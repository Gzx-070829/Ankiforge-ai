import unittest

from ankiforge_ai.pipeline.generation_settings import (
    CARD_MODES,
    GenerationSettings,
    all_card_mode_profiles,
    selectable_card_mode_profiles,
)
from ankiforge_ai.pipeline.prompt_profile import build_prompt_profile


class PromptProfileV4Tests(unittest.TestCase):
    EXPECTED_MODES = (
        "concept",
        "definition",
        "exam",
        "quick_review",
        "compare_contrast",
        "process_steps",
        "formula_rule",
        "mistake_trap",
        "cloze_candidate",
    )

    def test_generation_settings_accept_all_registered_modes(self):
        self.assertEqual(CARD_MODES, self.EXPECTED_MODES)
        self.assertEqual(
            tuple(item.mode_id for item in all_card_mode_profiles()),
            self.EXPECTED_MODES,
        )
        for mode_id in self.EXPECTED_MODES:
            self.assertEqual(GenerationSettings(card_mode=mode_id).card_mode, mode_id)

    def test_cloze_profile_is_not_selectable_until_write_support_exists(self):
        self.assertNotIn(
            "cloze_candidate",
            tuple(item.mode_id for item in selectable_card_mode_profiles()),
        )

    def test_each_mode_builds_distinct_template_aware_prompt(self):
        prompts = {
            mode_id: build_prompt_profile(
                GenerationSettings(card_mode=mode_id)
            ).as_prompt_text()
            for mode_id in self.EXPECTED_MODES
        }

        self.assertEqual(len(set(prompts.values())), len(self.EXPECTED_MODES))
        expected_terms = {
            "concept": "cause",
            "definition": "definition",
            "exam": "scoring",
            "quick_review": "one fact",
            "compare_contrast": "both sides",
            "process_steps": "explicit order",
            "formula_rule": "applicable condition",
            "mistake_trap": "misconception",
            "cloze_candidate": "cloze",
        }
        for mode_id, term in expected_terms.items():
            with self.subTest(mode=mode_id):
                self.assertIn(term, prompts[mode_id].casefold())

    def test_compatible_template_override_changes_prompt(self):
        settings = GenerationSettings(card_mode="concept")
        default = build_prompt_profile(settings)
        basic = build_prompt_profile(settings, template_id="basic_qa")

        self.assertEqual(default.template_id, "concept")
        self.assertEqual(basic.template_id, "basic_qa")
        self.assertNotEqual(default.template_guidance, basic.template_guidance)

    def test_incompatible_template_override_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "compatible"):
            build_prompt_profile(
                GenerationSettings(card_mode="exam"),
                template_id="formula_rule",
            )

    def test_prompt_contract_is_structured_and_contains_no_secret_or_path(self):
        profile = build_prompt_profile(
            GenerationSettings(
                card_mode="compare_contrast",
                card_count="fewer",
                answer_length="medium",
                language="zh",
            )
        )
        prompt = profile.as_prompt_text()

        self.assertEqual(profile.card_limit, 3)
        self.assertIn("Simplified Chinese", prompt)
        for phrase in (
            "one knowledge point",
            "do not invent",
            "markdown table",
            "template instructions",
        ):
            self.assertIn(phrase, prompt.casefold())
        for forbidden in (
            "api_key",
            "authorization",
            "bearer ",
            "c:\\users\\",
            "/users/",
        ):
            self.assertNotIn(forbidden, prompt.casefold())


if __name__ == "__main__":
    unittest.main()
