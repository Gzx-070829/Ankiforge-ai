import unittest

from ankiforge_ai.pipeline.generation_settings import GenerationSettings
from ankiforge_ai.pipeline.write_traceability import (
    LastWriteBatchRecord,
    SourceType,
)
from ankiforge_ai.ui.beginner_flow_models import (
    BeginnerAICardDraft,
    BeginnerArtifactState,
    BeginnerFlowSession,
    BeginnerReviewDecision,
)


class V1CoreReviewWorkflowTests(unittest.TestCase):
    def test_session_defaults_are_safe_and_nonpersistent(self):
        session = BeginnerFlowSession()

        self.assertEqual(session.generation_settings, GenerationSettings())
        self.assertEqual(session.source_type, SourceType.PASTE)
        self.assertEqual(session.candidate_quality_results, {})
        self.assertIsNone(session.last_write_batch)
        self.assertFalse(session.persistent)

    def test_generated_candidates_start_unreviewed_with_quality(self):
        session = self.session_with_drafts(self.good_draft())
        candidate = session.candidate_card_previews[0]

        self.assertEqual(session.candidate_review_decisions, {})
        quality = session.quality_for_candidate(candidate.id)
        self.assertGreaterEqual(quality.quality_score, 0.85)
        self.assertFalse(quality.is_blocking)

    def test_local_edit_recalculates_quality_and_invalidates_downstream(self):
        session = self.session_with_drafts(self.good_draft())
        candidate_id = session.candidate_card_previews[0].id
        session.set_candidate_review_decision(candidate_id, "looks_good")
        session.duplicate_check_preview_state = BeginnerArtifactState.CURRENT
        session.final_confirmation_preview_state = BeginnerArtifactState.CURRENT

        session.replace_candidate_content(candidate_id, "", "仍有答案")

        quality = session.quality_for_candidate(candidate_id)
        self.assertTrue(quality.is_blocking)
        self.assertIn("empty_front", quality.warning_ids)
        self.assertNotIn(candidate_id, session.candidate_review_decisions)
        self.assertEqual(
            session.duplicate_check_preview_state,
            BeginnerArtifactState.CLEARED,
        )
        self.assertEqual(
            session.final_confirmation_preview_state,
            BeginnerArtifactState.CLEARED,
        )

    def test_blocking_card_cannot_be_kept_but_can_be_discarded(self):
        session = self.session_with_drafts(self.good_draft())
        candidate_id = session.candidate_card_previews[0].id
        session.replace_candidate_content(candidate_id, "", "仍有答案")

        with self.assertRaisesRegex(ValueError, "blocking"):
            session.set_candidate_review_decision(candidate_id, "looks_good")
        session.set_candidate_review_decision(candidate_id, "skip_for_now")

        self.assertEqual(
            session.candidate_review_decisions[candidate_id],
            BeginnerReviewDecision.SKIP_FOR_NOW,
        )

    def test_warning_card_can_be_explicitly_kept(self):
        session = self.session_with_drafts(
            BeginnerAICardDraft(
                id="warning",
                front="请解释以下内容。",
                back="这是一个简短答案。",
                source_excerpt="材料片段",
            )
        )
        candidate_id = session.candidate_card_previews[0].id

        self.assertEqual(
            session.quality_for_candidate(candidate_id).severity,
            "warning",
        )
        session.set_candidate_review_decision(candidate_id, "looks_good")
        self.assertEqual(
            session.candidate_review_decisions[candidate_id],
            BeginnerReviewDecision.LOOKS_GOOD,
        )

    def test_generation_settings_change_invalidates_old_ai_output(self):
        session = self.session_with_drafts(self.good_draft())

        session.set_generation_settings(GenerationSettings(card_mode="exam"))

        self.assertEqual(session.generation_settings.card_mode, "exam")
        self.assertEqual(session.candidate_card_previews, ())
        self.assertEqual(session.candidate_quality_results, {})
        self.assertEqual(session.candidate_review_decisions, {})

    def test_discard_blocking_candidates_removes_only_blocking_cards(self):
        session = self.session_with_drafts(self.good_draft(), self.second_draft())
        blocking_id = session.candidate_card_previews[0].id
        session.replace_candidate_content(blocking_id, "", "仍有答案")

        discarded = session.discard_blocking_candidates()

        self.assertEqual(discarded, 1)
        self.assertEqual(len(session.candidate_card_previews), 1)
        self.assertNotEqual(session.candidate_card_previews[0].id, blocking_id)

    def test_discarding_all_blocking_candidates_returns_to_empty_review_state(self):
        session = self.session_with_drafts(self.good_draft())
        candidate_id = session.candidate_card_previews[0].id
        session.replace_candidate_content(candidate_id, "", "仍有答案")
        session.set_candidate_review_decision(candidate_id, "skip_for_now")

        discarded = session.discard_blocking_candidates()

        self.assertEqual(discarded, 1)
        self.assertEqual(session.candidate_card_previews, ())
        self.assertEqual(session.candidate_cards_state, BeginnerArtifactState.CLEARED)
        self.assertEqual(session.review_state, BeginnerArtifactState.CLEARED)

    def test_last_write_batch_is_in_memory_and_safe(self):
        session = BeginnerFlowSession()
        record = LastWriteBatchRecord(
            snapshot_id="snapshot",
            created_note_ids=(1001,),
            requested_count=1,
            skipped_count=0,
            failed_count=0,
            target_deck="Private deck name",
            tags=("ankiforge",),
            source_type=SourceType.PASTE,
        )

        session.record_last_write_batch(record)

        self.assertIs(session.last_write_batch, record)
        self.assertNotIn("Private deck name", repr(session))
        session.close()
        self.assertIsNone(session.last_write_batch)

    @staticmethod
    def good_draft():
        return BeginnerAICardDraft(
            id="good",
            front="交叉验证为什么能帮助评估泛化能力？",
            back="它在未参与当前训练的数据划分上评估模型表现。",
            source_excerpt="交叉验证用于评估泛化能力",
        )

    @staticmethod
    def second_draft():
        return BeginnerAICardDraft(
            id="second",
            front="早停如何降低过拟合风险？",
            back="验证表现不再改善时停止训练。",
            source_excerpt="早停用于控制过拟合",
        )

    @staticmethod
    def session_with_drafts(*drafts):
        session = BeginnerFlowSession()
        session.apply_ai_candidate_card_drafts(drafts)
        return session


if __name__ == "__main__":
    unittest.main()
