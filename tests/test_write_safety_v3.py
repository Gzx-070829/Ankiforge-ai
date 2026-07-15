import unittest
from dataclasses import replace

from ankiforge_ai.pipeline.write_safety import (
    WriteSafetySnapshot,
    evaluate_write_safety,
)
from ankiforge_ai.ui.beginner_final_confirmation import (
    build_beginner_final_confirmation_preview,
)
from ankiforge_ai.ui.beginner_flow_models import (
    BeginnerAICardDraft,
    BeginnerAIGenerationState,
    BeginnerFlowSession,
    BeginnerReviewDecision,
)
from ankiforge_ai.ui.beginner_real_write import (
    execute_beginner_write_if_confirmed,
    prepare_beginner_write,
)
from ankiforge_ai.ui.read_only_anki_targets import (
    BeginnerAnkiDeckOption,
    BeginnerAnkiNoteTypeOption,
    build_beginner_field_mapping_preview,
)
from ankiforge_ai.ui.read_only_duplicate_check import (
    BeginnerDuplicateCandidateResult,
    BeginnerDuplicateCheckPreview,
    BeginnerDuplicatePreviewState,
    BeginnerDuplicateStatus,
)


class RecordingWriter:
    def __init__(self):
        self.commands = []

    def write(self, command):
        self.commands.append(command)
        return "written"


class WriteSafetyV3Tests(unittest.TestCase):
    def ready_snapshot(self):
        return WriteSafetySnapshot(
            kept_count=3,
            blocking_write_count=0,
            mapping_complete=True,
            duplicate_check_complete=True,
            final_confirmation_confirmed=True,
            target_valid=True,
            generation_complete=True,
        )

    def test_all_seven_gates_are_required_for_write_authorization(self):
        decision = evaluate_write_safety(self.ready_snapshot())

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.blocking_reasons, ())
        self.assertEqual(decision.writable_count, 3)

    def test_each_missing_gate_blocks_with_a_stable_reason(self):
        failures = (
            ("kept_count", 0, "no_kept_cards"),
            ("blocking_write_count", 1, "blocking_cards_in_write_list"),
            ("mapping_complete", False, "mapping_incomplete"),
            ("duplicate_check_complete", False, "duplicate_not_checked"),
            (
                "final_confirmation_confirmed",
                False,
                "final_confirmation_required",
            ),
            ("target_valid", False, "write_target_invalid"),
            ("generation_complete", False, "generation_in_progress"),
        )

        for field_name, value, reason in failures:
            with self.subTest(gate=field_name):
                snapshot = replace(self.ready_snapshot(), **{field_name: value})
                decision = evaluate_write_safety(snapshot)
                self.assertFalse(decision.allowed)
                self.assertIn(reason, decision.blocking_reasons)

    def test_blocking_count_cannot_exceed_kept_count(self):
        with self.assertRaisesRegex(ValueError, "blocking_write_count"):
            WriteSafetySnapshot(
                kept_count=1,
                blocking_write_count=2,
                mapping_complete=True,
                duplicate_check_complete=True,
                final_confirmation_confirmed=True,
                target_valid=True,
                generation_complete=True,
            )

    def test_counts_reject_booleans_and_negative_values(self):
        for value in (-1, True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    replace(self.ready_snapshot(), kept_count=value)

    def test_gate_flags_require_real_booleans(self):
        with self.assertRaisesRegex(ValueError, "mapping_complete"):
            replace(self.ready_snapshot(), mapping_complete=1)

    def test_decision_safe_dict_contains_only_structural_state(self):
        decision = evaluate_write_safety(
            replace(
                self.ready_snapshot(),
                duplicate_check_complete=False,
                final_confirmation_confirmed=False,
            )
        )

        self.assertEqual(
            decision.to_safe_dict(),
            {
                "allowed": False,
                "writable_count": 3,
                "blocking_reason_count": 2,
                "blocking_reasons": (
                    "duplicate_not_checked",
                    "final_confirmation_required",
                ),
            },
        )

    def test_evaluation_is_deterministic_and_does_not_mutate_snapshot(self):
        snapshot = replace(
            self.ready_snapshot(),
            mapping_complete=False,
            generation_complete=False,
        )

        first = evaluate_write_safety(snapshot)
        second = evaluate_write_safety(snapshot)

        self.assertEqual(first, second)
        self.assertFalse(snapshot.mapping_complete)
        self.assertFalse(snapshot.generation_complete)

    def test_prepared_command_carries_six_preflight_gates_and_confirmation_is_final(self):
        preparation = self.complete_preparation()
        command = preparation.command
        writer = RecordingWriter()

        self.assertIsNotNone(command)
        self.assertIsNotNone(command.safety_snapshot)
        self.assertFalse(command.safety_snapshot.final_confirmation_confirmed)
        self.assertIsNone(
            execute_beginner_write_if_confirmed(False, writer, command)
        )
        result = execute_beginner_write_if_confirmed(True, writer, command)

        self.assertEqual(result, "written")
        self.assertEqual(len(writer.commands), 1)
        self.assertTrue(
            writer.commands[0].safety_snapshot.final_confirmation_confirmed
        )
        self.assertFalse(command.safety_snapshot.final_confirmation_confirmed)

    def test_execution_rejects_stale_duplicate_or_generation_gate(self):
        command = self.complete_preparation().command
        failures = (
            ("duplicate_check_complete", False, "duplicate_not_checked"),
            ("generation_complete", False, "generation_in_progress"),
        )

        for field_name, value, reason in failures:
            with self.subTest(gate=field_name):
                writer = RecordingWriter()
                unsafe = replace(
                    command,
                    safety_snapshot=replace(
                        command.safety_snapshot,
                        **{field_name: value},
                    ),
                )
                with self.assertRaisesRegex(ValueError, reason):
                    execute_beginner_write_if_confirmed(True, writer, unsafe)
                self.assertEqual(writer.commands, [])

    def test_running_generation_blocks_write_preparation(self):
        session, mapping, duplicate_preview, final_preview = self.complete_context()
        session.ai_generation_state = BeginnerAIGenerationState.RUNNING

        preparation = prepare_beginner_write(
            session,
            final_preview,
            mapping,
            duplicate_preview,
        )

        self.assertIsNone(preparation.command)
        self.assertIn(
            "AI 生成流程尚未结束",
            preparation.missing_conditions,
        )

    def complete_preparation(self):
        session, mapping, duplicate_preview, final_preview = self.complete_context()
        return prepare_beginner_write(
            session,
            final_preview,
            mapping,
            duplicate_preview,
        )

    def complete_context(self):
        session = BeginnerFlowSession()
        session.apply_ai_candidate_card_drafts(
            (
                BeginnerAICardDraft(
                    id="draft-1",
                    front="What is regularization?",
                    back="A constraint that reduces overfitting.",
                    source_excerpt="Regularization notes",
                ),
            )
        )
        session.set_candidate_review_decision(
            "candidate-draft-1",
            BeginnerReviewDecision.LOOKS_GOOD,
        )
        session.select_anki_deck(7, "Test Deck")
        session.select_anki_note_type(
            11,
            "Basic",
            ("Front", "Back", "Extra"),
        )
        session.set_anki_field_mapping("Front", "Back", "Extra")
        mapping = build_beginner_field_mapping_preview(
            deck=BeginnerAnkiDeckOption(7, "Test Deck"),
            note_type=BeginnerAnkiNoteTypeOption(11, "Basic"),
            available_fields=("Front", "Back", "Extra"),
            front_field="Front",
            back_field="Back",
            source_field="Extra",
        )
        duplicate_preview = BeginnerDuplicateCheckPreview(
            state=BeginnerDuplicatePreviewState.SUCCESS,
            results=(
                BeginnerDuplicateCandidateResult(
                    candidate_id="candidate-draft-1",
                    status=BeginnerDuplicateStatus.NO_OBVIOUS_DUPLICATE,
                ),
            ),
        )
        session.apply_duplicate_check_preview(1, 0)
        final_preview = build_beginner_final_confirmation_preview(
            session,
            mapping,
            duplicate_preview,
        )
        session.apply_final_confirmation_preview(
            final_preview.candidate_count,
            len(final_preview.missing_conditions),
        )
        return session, mapping, duplicate_preview, final_preview


if __name__ == "__main__":
    unittest.main()
