import unittest

from ankiforge_ai.document import SourceSpan
from ankiforge_ai.ui.beginner_flow_models import (
    BeginnerAICardDraft,
    BeginnerFlowSession,
)


class CandidateNearDuplicateReviewTests(unittest.TestCase):
    def make_session(self):
        span = SourceSpan(
            document_id="doc-biology",
            source_label="biology.md",
            locator_kind="section",
            locator_value="Cellular energy",
        )
        session = BeginnerFlowSession()
        session.update_material("ATP stores immediately usable cellular energy.")
        session.begin_ai_candidate_generation()
        session.apply_ai_candidate_card_drafts(
            (
                BeginnerAICardDraft(
                    id="first",
                    front="How does ATP provide immediately usable cellular energy?",
                    back="ATP provides immediately usable energy for cellular work.",
                    source_excerpt="ATP stores immediately usable cellular energy.",
                    source_span=span,
                ),
                BeginnerAICardDraft(
                    id="second",
                    front="How does ATP provide usable cellular energy?",
                    back="ATP provides usable energy for cellular work.",
                    source_excerpt="ATP stores immediately usable cellular energy.",
                    source_span=span,
                ),
            )
        )
        return session

    def test_all_candidates_remain_visible_and_later_match_has_pair_evidence(self):
        session = self.make_session()

        self.assertEqual(len(session.candidate_card_previews), 2)
        second = session.quality_for_candidate("candidate-second")
        issue = next(
            item for item in second.issues if item.rule_id == "duplicate_candidate"
        )
        self.assertEqual(issue.related_candidate_id, "candidate-first")
        self.assertEqual(issue.evidence_code, "shared_source_token_overlap")
        self.assertGreaterEqual(issue.similarity, 0.75)
        self.assertEqual(second.status, "review")
        self.assertNotIn("cellular energy", repr(issue).casefold())

    def test_edit_recalculates_advisory_match_instead_of_leaving_stale_warning(self):
        session = self.make_session()

        session.replace_candidate_content(
            "candidate-second",
            "What is the role of DNA polymerase?",
            "It synthesizes DNA during replication.",
        )

        quality = session.quality_for_candidate("candidate-second")
        self.assertNotIn("duplicate_candidate", quality.warning_ids)
        self.assertEqual(len(session.candidate_card_previews), 2)

    def test_copy_is_never_deleted_and_is_marked_for_review(self):
        session = self.make_session()
        session.replace_candidate_content(
            "candidate-second",
            "What is the role of DNA polymerase?",
            "It synthesizes DNA during replication.",
        )

        copied_id = session.copy_candidate("candidate-first")

        self.assertEqual(len(session.candidate_card_previews), 3)
        copied_quality = session.quality_for_candidate(copied_id)
        issue = next(
            item for item in copied_quality.issues if item.rule_id == "duplicate_candidate"
        )
        self.assertEqual(issue.related_candidate_id, "candidate-first")
        self.assertEqual(issue.evidence_code, "exact_text")


if __name__ == "__main__":
    unittest.main()
