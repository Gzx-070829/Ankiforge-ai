import unittest

from ankiforge_ai.pipeline import card_templates


class CardTemplateV4Tests(unittest.TestCase):
    EXPECTED_TEMPLATE_IDS = (
        "basic_qa",
        "concept",
        "definition",
        "exam_answer",
        "quick_review",
        "compare_contrast",
        "process_steps",
        "formula_rule",
        "mistake_trap",
        "cloze_candidate",
    )

    def test_all_templates_are_enumerable_and_complete(self):
        templates = card_templates.all_card_templates()

        self.assertEqual(
            tuple(item.template_id for item in templates),
            self.EXPECTED_TEMPLATE_IDS,
        )
        for item in templates:
            with self.subTest(template=item.template_id):
                self.assertTrue(item.mode_id)
                self.assertTrue(item.display_name_zh)
                self.assertTrue(item.display_name_en)
                self.assertTrue(item.description_zh)
                self.assertTrue(item.description_en)
                self.assertTrue(item.best_for)
                self.assertTrue(item.front_guidance)
                self.assertTrue(item.back_guidance)
                self.assertTrue(item.ideal_front_shape)
                self.assertTrue(item.ideal_back_shape)
                self.assertTrue(item.common_bad_patterns)
                self.assertTrue(item.quality_priorities)
                self.assertTrue(item.compatible_note_type_hints)

    def test_each_mode_resolves_a_deterministic_default_template(self):
        expected = {
            "concept": "concept",
            "definition": "definition",
            "exam": "exam_answer",
            "quick_review": "quick_review",
            "compare_contrast": "compare_contrast",
            "process_steps": "process_steps",
            "formula_rule": "formula_rule",
            "mistake_trap": "mistake_trap",
            "cloze_candidate": "cloze_candidate",
        }

        for mode_id, template_id in expected.items():
            with self.subTest(mode=mode_id):
                resolved = card_templates.default_template_for_mode(mode_id)
                self.assertEqual(resolved.template_id, template_id)

    def test_cloze_is_registered_but_not_selectable_until_safe(self):
        cloze = card_templates.get_card_template("cloze_candidate")

        self.assertTrue(cloze.supports_cloze)
        self.assertFalse(cloze.selectable)
        self.assertNotIn(
            "cloze_candidate",
            tuple(item.template_id for item in card_templates.selectable_card_templates()),
        )

    def test_unknown_template_and_mode_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "template"):
            card_templates.get_card_template("unknown")
        with self.assertRaisesRegex(ValueError, "mode"):
            card_templates.default_template_for_mode("unknown")

    def test_safe_repr_does_not_dump_template_guidance(self):
        item = card_templates.get_card_template("concept")

        self.assertIn("template_id='concept'", repr(item))
        self.assertNotIn(item.front_guidance, repr(item))


if __name__ == "__main__":
    unittest.main()
