import ast
import unittest
from pathlib import Path

from ankiforge_ai.ui.product_i18n import PRODUCT_COPY, product_text


class V1CoreUIContractTests(unittest.TestCase):
    def test_generation_controls_keep_mode_visible_and_details_collapsed(self):
        builder = self.function_source("_build_ai_section")

        self.assertIn("self.card_mode_combo", builder)
        self.assertIn('self.t("card_mode")', builder)
        self.assertIn("self.generation_settings_container.setVisible(False)", builder)
        for control in (
            "card_count_combo",
            "answer_length_combo",
            "output_language_combo",
        ):
            self.assertIn(f"self.{control}", builder)
        self.assertLess(
            builder.index("self.card_mode_combo"),
            builder.index("self.generation_settings_container"),
        )

    def test_generation_defaults_are_exact_and_passed_to_explicit_generate(self):
        builder = self.function_source("_build_ai_section")
        handler = self.function_source("_generate_cards")

        for value in ("concept", "balanced", "short", "auto"):
            self.assertIn(f'"{value}"', builder)
        self.assertIn("self._current_generation_settings()", handler)
        self.assertIn("generation_settings=", handler)
        self.assertNotIn(".generate(", self.function_source("__init__"))

    def test_generated_cards_are_not_automatically_approved(self):
        handler = self.function_source("_generate_cards")

        self.assertIn("self.session.apply_ai_candidate_card_drafts", handler)
        self.assertNotIn("set_candidate_review_decision", handler)
        self.assertNotIn("BeginnerReviewDecision.LOOKS_GOOD", handler)

    def test_review_cards_render_quality_and_edit_through_session(self):
        render = self.function_source("_render_cards")
        edit = self.function_source("_edit_card")

        self.assertIn("quality_for_candidate", render)
        self.assertIn('"quality_score"', render)
        self.assertIn("warning_id", render)
        self.assertIn("replace_candidate_content", edit)
        self.assertIn("_clear_duplicate_state", edit)

    def test_blocking_discard_and_overall_quality_summary_exist(self):
        builder = self.function_source("_build_cards_section")
        handler = self.function_source("_discard_blocking_cards")

        self.assertIn("self.quality_summary_label", builder)
        self.assertIn("self.discard_blocking_btn", builder)
        self.assertIn("discard_blocking_candidates", handler)

    def test_write_section_contains_compact_summary(self):
        builder = self.function_source("_build_write_section")
        prepare = self.function_source("_prepare_current_write")

        self.assertIn("self.write_summary_label", builder)
        self.assertIn("build_write_summary", prepare)
        for value in (
            "target_deck",
            "note_type",
            "field_mapping",
            "source_label",
            "warning_count",
            "blocking_count",
            "duplicate_behavior",
            "tags",
        ):
            self.assertIn(value, prepare)

    def test_first_run_copy_explains_product_and_safety(self):
        for language in ("zh", "en"):
            text = product_text(language, "first_run_guidance").casefold()
            for idea in (
                ("anki 插件", "anki add-on"),
                ("自己的学习材料", "your own study material"),
                ("api key", "api key"),
                ("审核", "review"),
                ("确认", "confirm"),
                ("测试牌组", "test deck"),
            ):
                self.assertTrue(any(term in text for term in idea))

    def test_quality_copy_is_complete_in_both_languages(self):
        self.assertEqual(set(PRODUCT_COPY["zh"]), set(PRODUCT_COPY["en"]))
        for warning_id in (
            "empty_front",
            "empty_back",
            "short_front",
            "generic_front",
            "long_back",
            "multiple_questions",
            "multi_point_card",
            "boilerplate_phrase",
            "markdown_residue",
            "duplicate_candidate",
        ):
            for language in ("zh", "en"):
                self.assertTrue(product_text(language, f"quality_{warning_id}"))
                self.assertTrue(
                    product_text(language, f"quality_{warning_id}_suggestion")
                )

    @staticmethod
    def root():
        return Path(__file__).parents[1]

    @classmethod
    def panel_source(cls):
        return (
            cls.root() / "ankiforge_ai" / "ui" / "card_maker_panel.py"
        ).read_text(encoding="utf-8")

    @classmethod
    def function_source(cls, name):
        source = cls.panel_source()
        tree = ast.parse(source)
        node = next(
            item
            for item in ast.walk(tree)
            if isinstance(item, ast.FunctionDef) and item.name == name
        )
        return ast.get_source_segment(source, node) or ""


if __name__ == "__main__":
    unittest.main()
