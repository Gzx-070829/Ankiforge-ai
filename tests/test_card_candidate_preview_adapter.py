import unittest
from copy import deepcopy

from ankiforge_ai.pipeline.card_candidate_preview_adapter import (
    CardCandidatePreviewItem,
    QualityIssuePreviewItem,
    build_card_candidate_preview_item,
    build_card_candidate_preview_items,
)
from ankiforge_ai.pipeline.human_review import create_human_review
from ankiforge_ai.pipeline.models import (
    CardCandidate,
    HumanReview,
    QualityGateResult,
    QualityIssue,
)


class CardCandidatePreviewAdapterTests(unittest.TestCase):
    def test_maps_complete_basic_card_candidate(self):
        candidate = self.candidate()
        quality = self.passed_quality(candidate)
        review = create_human_review(candidate, quality)

        item = build_card_candidate_preview_item(candidate, quality, review)

        self.assertIsInstance(item, CardCandidatePreviewItem)
        self.assertEqual(item.candidate_id, candidate.candidate_id)
        self.assertEqual(item.card_type, "basic")
        self.assertEqual(item.front, candidate.front)
        self.assertEqual(item.back, candidate.back)
        self.assertEqual(item.extra, candidate.extra)
        self.assertEqual(item.tags, tuple(candidate.tags))
        self.assertEqual(item.source, candidate.source)
        self.assertEqual(item.source_display, candidate.source_display)
        self.assertEqual(item.quality_status, "passed")
        self.assertEqual(item.quality_issues, ())
        self.assertEqual(item.review_decision, "pending")
        self.assertTrue(item.quality_allows_approval)

    def test_preserves_chinese_card_content(self):
        candidate = self.candidate(
            candidate_id="cc-cn",
            front="什么是过拟合？",
            back="模型过度拟合训练数据，导致泛化能力下降。",
            extra="例子：训练准确率高，但验证准确率低。",
            tags=["机器学习", "模型_评估"],
            source="机器学习笔记.md > 过拟合",
        )

        item = build_card_candidate_preview_item(candidate)

        self.assertEqual(item.front, "什么是过拟合？")
        self.assertEqual(item.back, "模型过度拟合训练数据，导致泛化能力下降。")
        self.assertEqual(item.extra, "例子：训练准确率高，但验证准确率低。")
        self.assertEqual(item.tags, ("机器学习", "模型_评估"))
        self.assertEqual(item.source, "机器学习笔记.md > 过拟合")
        self.assertEqual(item.source_display, "机器学习笔记.md > 过拟合")

    def test_maps_failed_quality_gate_and_issues(self):
        candidate = self.candidate()
        quality = self.failed_quality(candidate)

        item = build_card_candidate_preview_item(candidate, quality)

        self.assertEqual(item.quality_status, "failed")
        self.assertFalse(item.quality_allows_approval)
        self.assertEqual(len(item.quality_issues), 1)
        self.assertIsInstance(item.quality_issues[0], QualityIssuePreviewItem)
        self.assertEqual(item.quality_issues[0].code, "empty_back")
        self.assertEqual(item.quality_issues[0].severity, "error")

    def test_missing_quality_gate_is_unchecked(self):
        item = build_card_candidate_preview_item(self.candidate())

        self.assertEqual(item.quality_status, "unchecked")
        self.assertEqual(item.quality_issues, ())
        self.assertFalse(item.quality_allows_approval)
        self.assertEqual(item.review_decision, "")

    def test_quality_issues_and_tags_are_isolated(self):
        candidate = self.candidate()
        quality = self.failed_quality(candidate)

        item = build_card_candidate_preview_item(candidate, quality)
        candidate.tags.append("changed")
        quality.issues[0].message = "Changed after mapping"
        quality.issues.append(
            QualityIssue("missing_source", "Source is missing.", "warning")
        )

        self.assertEqual(item.tags, ("machine_learning", "generalization"))
        self.assertEqual(len(item.quality_issues), 1)
        self.assertEqual(item.quality_issues[0].message, "Back must not be empty.")

    def test_maps_all_human_review_decisions(self):
        candidate = self.candidate()
        quality = self.passed_quality(candidate)

        for decision in ["pending", "rejected", "needs_edit", "approved"]:
            with self.subTest(decision=decision):
                review = create_human_review(candidate, quality, decision=decision)
                item = build_card_candidate_preview_item(candidate, quality, review)
                self.assertEqual(item.review_decision, decision)

    def test_quality_candidate_id_mismatch_raises_value_error(self):
        candidate = self.candidate()
        quality = QualityGateResult(candidate_id="other", issues=[])

        with self.assertRaises(ValueError):
            build_card_candidate_preview_item(candidate, quality)

    def test_review_candidate_id_mismatch_raises_value_error(self):
        candidate = self.candidate()
        quality = self.passed_quality(candidate)
        review = self.review(candidate, candidate_id="other")

        with self.assertRaises(ValueError):
            build_card_candidate_preview_item(candidate, quality, review)

    def test_batch_mapping_preserves_candidate_order(self):
        candidates = [
            self.candidate("cc-2", front="第二张"),
            self.candidate("cc-1", front="第一张"),
        ]
        quality_results = [self.passed_quality(item) for item in candidates]
        reviews = [
            create_human_review(item, quality)
            for item, quality in zip(candidates, quality_results)
        ]

        items = build_card_candidate_preview_items(
            candidates,
            quality_results,
            reviews,
        )

        self.assertEqual([item.candidate_id for item in items], ["cc-2", "cc-1"])
        self.assertEqual([item.front for item in items], ["第二张", "第一张"])

    def test_batch_mapping_requires_equal_lengths(self):
        with self.assertRaises(ValueError):
            build_card_candidate_preview_items([self.candidate()], [])
        with self.assertRaises(ValueError):
            build_card_candidate_preview_items([self.candidate()], reviews=[])

    def test_adapter_does_not_modify_inputs(self):
        candidate = self.candidate()
        quality = self.failed_quality(candidate)
        review = create_human_review(candidate, quality, decision="needs_edit")
        originals = deepcopy((candidate, quality, review))

        build_card_candidate_preview_item(candidate, quality, review)

        self.assertEqual(candidate, originals[0])
        self.assertEqual(quality, originals[1])
        self.assertEqual(review, originals[2])

    def candidate(
        self,
        candidate_id="cc-1",
        front="What is overfitting?",
        back="It is excessive fitting to training data.",
        extra="Evidence and source context.",
        tags=None,
        source="notes.md > Overfitting",
    ):
        return CardCandidate(
            candidate_id=candidate_id,
            selection_id=f"selection-{candidate_id}",
            point_id=f"point-{candidate_id}",
            document_id="doc-1",
            chunk_id="chunk-1",
            source_display=source,
            heading_path=["Models", "Overfitting"],
            ordinal=0,
            card_type="basic",
            front=front,
            back=back,
            extra=extra,
            tags=list(tags or ["machine_learning", "generalization"]),
            source=source,
        )

    def passed_quality(self, candidate):
        return QualityGateResult(candidate_id=candidate.candidate_id, issues=[])

    def failed_quality(self, candidate):
        return QualityGateResult(
            candidate_id=candidate.candidate_id,
            issues=[
                QualityIssue(
                    code="empty_back",
                    message="Back must not be empty.",
                    severity="error",
                )
            ],
        )

    def review(self, candidate, candidate_id=None):
        return HumanReview(
            review_id="review-1",
            candidate_id=candidate_id or candidate.candidate_id,
            selection_id=candidate.selection_id,
            point_id=candidate.point_id,
            document_id=candidate.document_id,
            chunk_id=candidate.chunk_id,
            source_display=candidate.source_display,
            heading_path=list(candidate.heading_path),
            ordinal=candidate.ordinal,
            card_type=candidate.card_type,
            front=candidate.front,
            back=candidate.back,
            extra=candidate.extra,
            tags=list(candidate.tags),
            source=candidate.source,
            quality_passed=True,
            quality_issues=[],
        )


if __name__ == "__main__":
    unittest.main()
