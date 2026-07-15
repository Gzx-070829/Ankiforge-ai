import unittest

from ankiforge_ai.pipeline.field_mapping import (
    assess_field_mapping,
    suggest_field_mapping,
)
from ankiforge_ai.pipeline.generation_settings import GenerationSettings
from ankiforge_ai.ui.beginner_flow_models import BeginnerFlowSession


class FieldMappingV3Tests(unittest.TestCase):
    def test_basic_note_type_mapping_is_suggested(self):
        suggestion = suggest_field_mapping(("Front", "Back"), "Basic")

        self.assertEqual(suggestion.front_field, "Front")
        self.assertEqual(suggestion.back_field, "Back")
        self.assertIsNone(suggestion.source_field)
        self.assertTrue(suggestion.complete)

    def test_chinese_field_mapping_is_suggested(self):
        suggestion = suggest_field_mapping(("正面", "背面", "来源"), "基础")

        self.assertEqual(suggestion.front_field, "正面")
        self.assertEqual(suggestion.back_field, "背面")
        self.assertEqual(suggestion.source_field, "来源")

    def test_question_answer_and_source_aliases_are_supported(self):
        suggestion = suggest_field_mapping(
            ("Question", "Answer", "Source"),
            "Study Note",
        )

        self.assertEqual(
            (
                suggestion.front_field,
                suggestion.back_field,
                suggestion.source_field,
            ),
            ("Question", "Answer", "Source"),
        )

    def test_source_is_optional_and_mapping_can_still_be_complete(self):
        result = assess_field_mapping(
            available_fields=("Front", "Back"),
            front_field="Front",
            back_field="Back",
            source_field=None,
            note_type_name="Basic",
        )

        self.assertTrue(result.complete)
        self.assertTrue(result.source_optional)
        self.assertEqual(result.blocking_reasons, ())

    def test_incomplete_or_unknown_mapping_blocks_writing(self):
        missing = assess_field_mapping(
            ("Front", "Back"),
            front_field="Front",
            back_field=None,
        )
        unknown = assess_field_mapping(
            ("Front", "Back"),
            front_field="Question",
            back_field="Back",
        )

        self.assertFalse(missing.complete)
        self.assertIn("back_field_required", missing.blocking_reasons)
        self.assertFalse(unknown.complete)
        self.assertIn("mapped_field_missing", unknown.blocking_reasons)

    def test_reusing_one_field_for_multiple_roles_is_blocked(self):
        result = assess_field_mapping(
            ("Front", "Back"),
            front_field="Front",
            back_field="Front",
        )

        self.assertFalse(result.complete)
        self.assertIn("mapped_fields_not_unique", result.blocking_reasons)

    def test_uncertain_names_are_not_guessed_by_position(self):
        suggestion = suggest_field_mapping(("Alpha", "Beta", "Gamma"), "Custom")

        self.assertIsNone(suggestion.front_field)
        self.assertIsNone(suggestion.back_field)
        self.assertIsNone(suggestion.source_field)
        self.assertFalse(suggestion.complete)

    def test_cloze_incompatible_mapping_is_blocked(self):
        result = assess_field_mapping(
            ("Front", "Back"),
            front_field="Front",
            back_field="Back",
            note_type_name="Basic",
            template_id="cloze_candidate",
        )

        self.assertFalse(result.complete)
        self.assertFalse(result.cloze_compatible)
        self.assertIn("cloze_note_type_incompatible", result.blocking_reasons)

    def test_cloze_note_type_with_text_field_is_compatible(self):
        result = assess_field_mapping(
            ("Text", "Back Extra"),
            front_field="Text",
            back_field="Back Extra",
            note_type_name="Cloze",
            template_id="cloze_candidate",
        )

        self.assertTrue(result.complete)
        self.assertTrue(result.cloze_compatible)

    def test_suggestion_and_assessment_do_not_mutate_field_input(self):
        fields = ["正面", "背面", "来源"]
        before = list(fields)

        suggestion = suggest_field_mapping(fields, "基础")
        assess_field_mapping(
            fields,
            suggestion.front_field,
            suggestion.back_field,
            suggestion.source_field,
            note_type_name="基础",
        )

        self.assertEqual(fields, before)

    def test_beginner_session_exposes_suggestion_and_current_assessment(self):
        session = BeginnerFlowSession()
        session.select_anki_deck(7, "测试牌组")
        session.select_anki_note_type(11, "基础", ("正面", "背面", "来源"))

        suggestion = session.suggest_anki_field_mapping()
        session.set_anki_field_mapping(
            suggestion.front_field,
            suggestion.back_field,
            suggestion.source_field,
        )
        assessment = session.assess_anki_field_mapping()

        self.assertEqual(suggestion.front_field, "正面")
        self.assertEqual(suggestion.back_field, "背面")
        self.assertEqual(suggestion.source_field, "来源")
        self.assertTrue(assessment.complete)

    def test_beginner_session_blocks_incompatible_cloze_assessment(self):
        session = BeginnerFlowSession(
            generation_settings=GenerationSettings(card_mode="cloze_candidate")
        )
        session.select_anki_deck(7, "Test Deck")
        session.select_anki_note_type(11, "Basic", ("Front", "Back"))
        session.set_anki_field_mapping("Front", "Back", None)

        assessment = session.assess_anki_field_mapping()

        self.assertFalse(assessment.complete)
        self.assertIn(
            "cloze_note_type_incompatible",
            assessment.blocking_reasons,
        )


if __name__ == "__main__":
    unittest.main()
