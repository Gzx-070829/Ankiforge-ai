import unittest

from ankiforge_ai.pipeline.review_workbench import (
    ReviewCandidate,
    ReviewDecision,
    ReviewWorkbench,
)
from ankiforge_ai.ui.beginner_flow_models import (
    BeginnerAICardDraft,
    BeginnerArtifactState,
    BeginnerFlowSession,
    BeginnerReviewDecision,
)


class ReviewWorkbenchV4Tests(unittest.TestCase):
    def clean_candidate(self, candidate_id="card-1"):
        return ReviewCandidate.create(
            candidate_id=candidate_id,
            front="What does regularization reduce?",
            back="It reduces overfitting by constraining model complexity.",
            source="Machine learning notes",
        )

    def warning_candidate(self, candidate_id="card-warning"):
        return ReviewCandidate.create(
            candidate_id=candidate_id,
            front="AI?",
            back="Artificial intelligence.",
            source="Glossary",
        )

    def blocking_candidate(self, candidate_id="card-blocking"):
        return ReviewCandidate.create(
            candidate_id=candidate_id,
            front="",
            back="An answer without a question.",
            source="Draft",
        )

    def test_generated_candidates_start_pending_and_stats_are_complete(self):
        workbench = ReviewWorkbench.from_candidates(
            (self.clean_candidate(), self.warning_candidate())
        )

        self.assertTrue(
            all(card.decision is ReviewDecision.PENDING for card in workbench.cards)
        )
        self.assertEqual(workbench.stats.total_count, 2)
        self.assertEqual(workbench.stats.pending_count, 2)
        self.assertEqual(workbench.stats.kept_count, 0)
        self.assertEqual(workbench.stats.discarded_count, 0)
        self.assertEqual(workbench.stats.warning_count, 1)
        self.assertEqual(workbench.stats.blocking_count, 0)

    def test_blocking_candidate_cannot_be_kept(self):
        workbench = ReviewWorkbench.from_candidates((self.blocking_candidate(),))

        with self.assertRaisesRegex(ValueError, "blocking"):
            workbench.keep("card-blocking")

    def test_warning_candidate_can_be_kept(self):
        workbench = ReviewWorkbench.from_candidates((self.warning_candidate(),))

        updated = workbench.keep("card-warning")

        self.assertIs(updated.card("card-warning").decision, ReviewDecision.KEPT)
        self.assertEqual(updated.stats.kept_count, 1)

    def test_edit_revalidates_resets_decision_and_invalidates_write_artifacts(self):
        workbench = ReviewWorkbench.from_candidates((self.clean_candidate(),))
        workbench = workbench.keep("card-1").with_current_write_artifacts()

        updated = workbench.edit("card-1", front="", back="Still has an answer")

        card = updated.card("card-1")
        self.assertIs(card.decision, ReviewDecision.PENDING)
        self.assertTrue(card.quality.is_blocking)
        self.assertFalse(updated.duplicate_check_current)
        self.assertFalse(updated.write_preview_current)

    def test_restore_returns_original_candidate_and_revalidates(self):
        original = self.clean_candidate()
        workbench = ReviewWorkbench.from_candidates((original,))
        edited = workbench.edit(
            "card-1",
            front="A changed question?",
            back="A changed answer.",
        )

        restored = edited.restore("card-1")

        card = restored.card("card-1")
        self.assertEqual(card.front, original.front)
        self.assertEqual(card.back, original.back)
        self.assertIs(card.decision, ReviewDecision.PENDING)

    def test_copy_uses_current_content_but_creates_new_pending_original(self):
        workbench = ReviewWorkbench.from_candidates((self.clean_candidate(),))
        edited = workbench.edit(
            "card-1",
            front="How does L2 regularization help?",
            back="It penalizes large weights.",
        )

        copied = edited.copy("card-1", "card-2")

        clone = copied.card("card-2")
        self.assertEqual(clone.front, "How does L2 regularization help?")
        self.assertEqual(clone.original_front, clone.front)
        self.assertIs(clone.decision, ReviewDecision.PENDING)
        self.assertEqual(copied.stats.total_count, 2)

    def test_bulk_actions_discard_blocking_and_keep_only_clean_cards(self):
        workbench = ReviewWorkbench.from_candidates(
            (
                self.clean_candidate(),
                self.warning_candidate(),
                self.blocking_candidate(),
            )
        )

        updated = workbench.discard_blocking().keep_clean()

        self.assertIs(updated.card("card-1").decision, ReviewDecision.KEPT)
        self.assertIs(
            updated.card("card-warning").decision,
            ReviewDecision.PENDING,
        )
        self.assertIs(
            updated.card("card-blocking").decision,
            ReviewDecision.DISCARDED,
        )

    def test_review_mutations_invalidate_duplicate_and_write_preview(self):
        current = ReviewWorkbench.from_candidates(
            (self.clean_candidate(),)
        ).with_current_write_artifacts()

        for updated in (
            current.keep("card-1"),
            current.discard("card-1"),
            current.copy("card-1", "card-2"),
        ):
            with self.subTest(updated=updated):
                self.assertFalse(updated.duplicate_check_current)
                self.assertFalse(updated.write_preview_current)

    def test_repr_and_safe_dict_do_not_include_card_content(self):
        secret_material = "private study material that must not be copied to logs"
        candidate = ReviewCandidate.create(
            "private-card",
            secret_material,
            secret_material,
            secret_material,
        )
        workbench = ReviewWorkbench.from_candidates((candidate,))

        self.assertNotIn(secret_material, repr(candidate))
        self.assertNotIn(secret_material, repr(workbench))
        self.assertNotIn(secret_material, str(workbench.to_safe_dict()))

    def test_beginner_session_exposes_current_review_workbench_snapshot(self):
        session = BeginnerFlowSession()
        session.apply_ai_candidate_card_drafts(
            (
                BeginnerAICardDraft(
                    id="draft-1",
                    front="What is overfitting?",
                    back="Poor generalization after fitting training data too closely.",
                    source_excerpt="Overfitting notes",
                ),
            )
        )
        session.select_anki_deck(7, "Test Deck")
        session.select_anki_note_type(11, "Basic", ("Front", "Back"))
        session.set_anki_field_mapping("Front", "Back", None)
        session.apply_duplicate_check_preview(1, 0)
        session.apply_final_confirmation_preview(1, 0)

        before = session.review_workbench_snapshot()
        session.set_candidate_review_decision(
            "candidate-draft-1",
            BeginnerReviewDecision.LOOKS_GOOD,
        )
        after = session.review_workbench_snapshot()

        self.assertTrue(before.duplicate_check_current)
        self.assertTrue(before.write_preview_current)
        self.assertIs(
            after.card("candidate-draft-1").decision,
            ReviewDecision.KEPT,
        )
        self.assertFalse(after.duplicate_check_current)
        self.assertFalse(after.write_preview_current)
        self.assertIs(
            session.duplicate_check_preview_state,
            BeginnerArtifactState.CLEARED,
        )
        self.assertIs(
            session.final_confirmation_preview_state,
            BeginnerArtifactState.CLEARED,
        )

    def test_beginner_session_uses_review_gate_for_blocking_keep(self):
        session = BeginnerFlowSession()
        session.apply_ai_candidate_card_drafts(
            (
                BeginnerAICardDraft(
                    id="blocked",
                    front="",
                    back="Answer without a front.",
                    source_excerpt="Draft",
                ),
            )
        )

        with self.assertRaisesRegex(ValueError, "blocking"):
            session.set_candidate_review_decision(
                "candidate-blocked",
                BeginnerReviewDecision.LOOKS_GOOD,
            )

    def test_beginner_session_bulk_keep_clean_leaves_warning_and_blocking_pending(self):
        session = BeginnerFlowSession()
        session.apply_ai_candidate_card_drafts(
            (
                BeginnerAICardDraft(
                    id="clean",
                    front="What is cross-validation used for?",
                    back="It estimates generalization on held-out data.",
                    source_excerpt=(
                        "Cross-validation estimates generalization on held-out data."
                    ),
                ),
                BeginnerAICardDraft(
                    id="warning",
                    front="AI?",
                    back="Artificial intelligence.",
                    source_excerpt="Glossary",
                ),
                BeginnerAICardDraft(
                    id="blocking",
                    front="",
                    back="Missing question.",
                    source_excerpt="Draft",
                ),
            )
        )

        kept = session.keep_clean_candidates()
        snapshot = session.review_workbench_snapshot()

        self.assertEqual(kept, 1)
        self.assertIs(
            snapshot.card("candidate-clean").decision,
            ReviewDecision.KEPT,
        )
        self.assertIs(
            snapshot.card("candidate-warning").decision,
            ReviewDecision.PENDING,
        )
        self.assertIs(
            snapshot.card("candidate-blocking").decision,
            ReviewDecision.PENDING,
        )

    def test_beginner_session_restore_returns_the_original_ai_candidate(self):
        session = BeginnerFlowSession()
        session.apply_ai_candidate_card_drafts(
            (
                BeginnerAICardDraft(
                    id="draft-1",
                    front="Original question?",
                    back="Original answer.",
                    source_excerpt="Original source",
                ),
            )
        )
        session.replace_candidate_content(
            "candidate-draft-1",
            "Edited question?",
            "Edited answer.",
        )

        session.restore_candidate_content("candidate-draft-1")
        restored = session.review_workbench_snapshot().card("candidate-draft-1")

        self.assertEqual(restored.front, "Original question?")
        self.assertEqual(restored.back, "Original answer.")
        self.assertIs(restored.decision, ReviewDecision.PENDING)

    def test_beginner_session_copy_returns_new_pending_candidate(self):
        session = BeginnerFlowSession()
        session.apply_ai_candidate_card_drafts(
            (
                BeginnerAICardDraft(
                    id="draft-1",
                    front="Question to copy?",
                    back="Answer to copy.",
                    source_excerpt="Source",
                ),
            )
        )

        copied_id = session.copy_candidate("candidate-draft-1")
        snapshot = session.review_workbench_snapshot()

        self.assertEqual(copied_id, "candidate-draft-1-copy-1")
        self.assertEqual(snapshot.stats.total_count, 2)
        self.assertEqual(snapshot.card(copied_id).front, "Question to copy?")
        self.assertIs(snapshot.card(copied_id).decision, ReviewDecision.PENDING)


if __name__ == "__main__":
    unittest.main()
