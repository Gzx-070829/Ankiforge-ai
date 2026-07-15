import unittest

from ankiforge_ai.pipeline.example_materials import (
    all_example_materials,
    get_example_material,
)


class ExampleMaterialsTests(unittest.TestCase):
    REQUIRED_IDS = {
        "zh_concept",
        "en_concept",
        "term_definition",
        "exam_review",
        "quick_review",
        "markdown_notes",
        "compare_contrast",
        "process_steps",
        "formula_rule",
        "mistake_trap",
    }

    def test_registry_is_complete_stable_and_round_trippable(self):
        examples = all_example_materials()
        self.assertEqual({item.example_id for item in examples}, self.REQUIRED_IDS)
        self.assertEqual(examples, all_example_materials())
        for item in examples:
            self.assertIs(get_example_material(item.example_id), item)

    def test_examples_are_bilingual_offline_and_sized_for_onboarding(self):
        for item in all_example_materials():
            with self.subTest(example=item.example_id):
                self.assertTrue(item.title_zh and item.title_en)
                self.assertTrue(item.description_zh and item.description_en)
                self.assertTrue(item.material_text.strip())
                self.assertLessEqual(item.expected_card_count_range[0], 3)
                self.assertGreaterEqual(item.expected_card_count_range[1], 5)
                self.assertFalse(item.requires_network)
                rendered = item.material_text + item.source_label
                self.assertNotIn("C:\\", rendered)
                self.assertNotIn("https://", rendered)
                self.assertNotIn("api_key", rendered.casefold())
                self.assertNotIn("sk-", rendered.casefold())

    def test_safe_repr_does_not_include_material(self):
        item = all_example_materials()[0]
        self.assertNotIn(item.material_text, repr(item))

    def test_unknown_example_fails_closed(self):
        with self.assertRaises(ValueError):
            get_example_material("missing")


if __name__ == "__main__":
    unittest.main()
