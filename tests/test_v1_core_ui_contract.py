import ast
import unittest
from pathlib import Path

from ankiforge_ai.pipeline.generation_settings import GenerationSettings
from ankiforge_ai.ui.product_i18n import PRODUCT_COPY, product_text


class V1CoreUIContractTests(unittest.TestCase):
    def test_generation_controls_keep_mode_visible_and_details_collapsed(self):
        builder = self.function_source("_build_generation_section")

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
        builder = self.function_source("_build_generation_section")
        handler = self.function_source("_generate_cards")

        self.assertEqual(
            GenerationSettings(),
            GenerationSettings(
                card_mode="concept",
                card_count="balanced",
                answer_length="short",
                language="auto",
            ),
        )
        self.assertIn("selectable_card_mode_profiles", builder)
        self.assertIn("self.card_count_combo.setCurrentIndex(2)", builder)
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
        self.assertNotIn('"quality_score"', render)
        self.assertNotIn("warning_id", render)
        self.assertIn("issue.user_message(self.language)", render)
        self.assertIn("issue.suggestion(self.language)", render)
        self.assertIn("replace_candidate_content", edit)
        self.assertIn("_clear_duplicate_state", edit)

    def test_blocking_discard_and_overall_quality_summary_exist(self):
        builder = self.function_source("_build_cards_section")
        handler = self.function_source("_discard_blocking_cards")

        self.assertIn("self.quality_summary_label", builder)
        self.assertIn("self.discard_blocking_btn", builder)
        self.assertIn("discard_blocking_candidates", handler)

    def test_final_confirmation_is_followed_by_a_fresh_duplicate_gate(self):
        handler = self.function_source("_confirm_and_write")

        self.assertIn("confirmed_snapshot_id = command.snapshot_id", handler)
        self.assertIn("self._check_duplicates()", handler)
        self.assertIn("fresh_command = self.write_command", handler)
        self.assertIn('self._set_write_message("duplicate_state_changed")', handler)
        self.assertLess(
            handler.index("self._check_duplicates()"),
            handler.index("execute_beginner_write_if_confirmed"),
        )

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

    def test_field_mapping_ui_uses_bilingual_suggestions_and_assessment(self):
        populate = self.function_source("_populate_field_options")
        update = self.function_source("_update_mapping")

        self.assertIn("self.session.suggest_anki_field_mapping()", populate)
        self.assertIn("suggestion.front_field", populate)
        self.assertIn("suggestion.back_field", populate)
        self.assertIn("suggestion.source_field", populate)
        self.assertIn("self.session.assess_anki_field_mapping()", update)
        self.assertIn("if not assessment.complete", update)

    def test_postwrite_ui_uses_safe_traceability_metadata(self):
        handler = self.function_source("_confirm_and_write")
        renderer = self.function_source("_render_write_summary")

        self.assertIn("create_last_write_batch_record", handler)
        for field in ("batch_id", "timestamp_utc", "note_type", "source_label"):
            self.assertIn(f"{field}=", handler)
        self.assertIn("result.batch_id", renderer)
        self.assertIn("result.timestamp_utc", renderer)
        self.assertNotIn("created_note_ids", renderer)

    def test_first_run_copy_is_a_lightweight_test_deck_tip(self):
        self.assertEqual(
            product_text("zh", "first_run_guidance"),
            "第一次使用？可以先试试示例材料，并写入测试牌组。",
        )
        self.assertEqual(
            product_text("en", "first_run_guidance"),
            "New here? Try the example material and write to a test deck first.",
        )

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
