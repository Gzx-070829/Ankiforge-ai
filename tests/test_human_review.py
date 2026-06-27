import json
import unittest
from dataclasses import replace

from ankiforge_ai.pipeline.human_review import (
    build_review_id,
    create_human_review,
    create_human_reviews,
)
from ankiforge_ai.pipeline.models import (
    CardCandidate,
    HumanReview,
    QualityGateResult,
    QualityIssue,
)


class HumanReviewTests(unittest.TestCase):
    def test_creates_pending_review_with_default_note(self):
        review = create_human_review(self.candidate(), self.quality_result())

        self.assertIsInstance(review, HumanReview)
        self.assertEqual(review.decision, "pending")
        self.assertEqual(review.reviewer_note, "")

    def test_inherits_candidate_metadata_and_content(self):
        candidate = self.candidate()

        review = create_human_review(candidate, self.quality_result())

        self.assertEqual(review.candidate_id, candidate.candidate_id)
        self.assertEqual(review.selection_id, candidate.selection_id)
        self.assertEqual(review.point_id, candidate.point_id)
        self.assertEqual(review.document_id, candidate.document_id)
        self.assertEqual(review.chunk_id, candidate.chunk_id)
        self.assertEqual(review.source_display, candidate.source_display)
        self.assertEqual(review.heading_path, candidate.heading_path)
        self.assertEqual(review.ordinal, candidate.ordinal)
        self.assertEqual(review.card_type, candidate.card_type)
        self.assertEqual(review.front, candidate.front)
        self.assertEqual(review.back, candidate.back)
        self.assertEqual(review.extra, candidate.extra)
        self.assertEqual(review.tags, candidate.tags)
        self.assertEqual(review.source, candidate.source)

    def test_candidate_lists_are_copied(self):
        candidate = self.candidate()

        review = create_human_review(candidate, self.quality_result())
        candidate.heading_path.append("Changed")
        candidate.tags.append("changed")

        self.assertEqual(review.heading_path, ["Models", "Overfitting"])
        self.assertEqual(review.tags, ["ml", "generalization"])

    def test_quality_state_and_issues_are_copied(self):
        issue = QualityIssue("front_too_long", "Front is too long.", "warning")
        result = self.quality_result([issue])

        review = create_human_review(self.candidate(), result)

        self.assertTrue(review.quality_passed)
        self.assertEqual(review.quality_issues, result.issues)
        self.assertIsNot(review.quality_issues, result.issues)
        self.assertIsNot(review.quality_issues[0], result.issues[0])

        issue.code = "changed"
        result.issues.append(QualityIssue("new", "New issue.", "warning"))
        self.assertEqual(review.quality_issues[0].code, "front_too_long")
        self.assertEqual(len(review.quality_issues), 1)

    def test_review_id_is_stable_and_ignores_mutable_content(self):
        candidate = self.candidate()
        changed = replace(
            candidate,
            front="Changed front",
            back="Changed back",
            extra="Changed extra",
        )
        warning_result = self.quality_result(
            [QualityIssue("notice", "A warning.", "warning")]
        )

        pending = create_human_review(candidate, self.quality_result())
        rejected = create_human_review(
            changed,
            warning_result,
            decision="rejected",
            reviewer_note="Not suitable",
        )

        self.assertEqual(build_review_id(candidate.candidate_id), "hr_cc-1")
        self.assertEqual(pending.review_id, rejected.review_id)

    def test_mismatched_candidate_id_raises_value_error(self):
        with self.assertRaises(ValueError):
            create_human_review(
                self.candidate(candidate_id="cc-1"),
                self.quality_result(candidate_id="cc-2"),
            )

    def test_invalid_decision_raises_value_error(self):
        with self.assertRaises(ValueError):
            create_human_review(
                self.candidate(),
                self.quality_result(),
                decision="unknown",
            )

    def test_failed_quality_gate_cannot_be_approved(self):
        result = self.quality_result(
            [QualityIssue("empty_front", "Front is empty.", "error")]
        )

        with self.assertRaises(ValueError):
            create_human_review(self.candidate(), result, decision="approved")

    def test_failed_quality_gate_allows_non_approved_decisions(self):
        result = self.quality_result(
            [QualityIssue("empty_front", "Front is empty.", "error")]
        )

        for decision in ("pending", "rejected", "needs_edit"):
            with self.subTest(decision=decision):
                review = create_human_review(
                    self.candidate(),
                    result,
                    decision=decision,
                )
                self.assertEqual(review.decision, decision)
                self.assertFalse(review.quality_passed)

    def test_passed_quality_gate_can_be_approved(self):
        review = create_human_review(
            self.candidate(),
            self.quality_result(),
            decision="approved",
            reviewer_note="Ready",
        )

        self.assertEqual(review.decision, "approved")
        self.assertEqual(review.reviewer_note, "Ready")
        self.assertTrue(review.quality_passed)

    def test_batch_preserves_candidate_order(self):
        first = self.candidate(candidate_id="cc-1")
        second = self.candidate(candidate_id="cc-2")

        reviews = create_human_reviews(
            [first, second],
            [
                self.quality_result(candidate_id="cc-1"),
                self.quality_result(candidate_id="cc-2"),
            ],
        )

        self.assertEqual(
            [review.candidate_id for review in reviews],
            ["cc-1", "cc-2"],
        )

    def test_batch_length_mismatch_raises_value_error(self):
        with self.assertRaises(ValueError):
            create_human_reviews([self.candidate()], [])

        with self.assertRaises(ValueError):
            create_human_reviews([], [self.quality_result()])

    def test_batch_position_mismatch_raises_value_error(self):
        with self.assertRaises(ValueError):
            create_human_reviews(
                [
                    self.candidate(candidate_id="cc-1"),
                    self.candidate(candidate_id="cc-2"),
                ],
                [
                    self.quality_result(candidate_id="cc-2"),
                    self.quality_result(candidate_id="cc-1"),
                ],
            )

    def test_empty_batches_return_empty_list(self):
        self.assertEqual(create_human_reviews([], []), [])

    def test_to_dict_is_json_serializable(self):
        result = self.quality_result(
            [QualityIssue("notice", "A warning.", "warning")]
        )
        review = create_human_review(self.candidate(), result)

        data = review.to_dict()

        self.assertEqual(data["review_id"], review.review_id)
        self.assertTrue(data["quality_passed"])
        self.assertEqual(data["quality_issues"][0]["code"], "notice")
        json.dumps(data, ensure_ascii=False)

    def candidate(self, candidate_id="cc-1"):
        return CardCandidate(
            candidate_id=candidate_id,
            selection_id="hs-1",
            point_id="kp-1",
            document_id="doc-1",
            chunk_id="chunk-1",
            source_display="ml.md > Models > Overfitting",
            heading_path=["Models", "Overfitting"],
            ordinal=0,
            card_type="basic",
            front="What is overfitting?",
            back="It is excessive fitting to training data.",
            extra="Evidence and source context.",
            tags=["ml", "generalization"],
            source="ml.md > Models > Overfitting",
        )

    def quality_result(self, issues=None, candidate_id="cc-1"):
        return QualityGateResult(
            candidate_id=candidate_id,
            issues=list(issues or []),
        )


if __name__ == "__main__":
    unittest.main()
