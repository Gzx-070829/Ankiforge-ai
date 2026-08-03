import unittest

from ankiforge_ai.pipeline.card_quality import evaluate_card_quality
from ankiforge_ai.pipeline.review_workbench import ReviewCandidate, ReviewWorkbench


class CardQualityStatusTests(unittest.TestCase):
    def test_public_status_is_ready_review_or_blocked(self):
        ready = evaluate_card_quality(
            "交叉验证的主要作用是什么？",
            "评估模型对未见数据的泛化能力。",
        )
        review = evaluate_card_quality(
            "请解释以下内容。",
            "交叉验证用于评估模型的泛化能力。",
        )
        blocked = evaluate_card_quality("", "有效答案。")

        self.assertEqual(ready.status, "ready")
        self.assertEqual(review.status, "review")
        self.assertEqual(blocked.status, "blocked")
        self.assertEqual(ready.severity, "info")
        self.assertEqual(review.severity, "warning")
        self.assertEqual(blocked.severity, "blocking")

    def test_localized_summary_is_compact_and_does_not_claim_truth(self):
        ready = evaluate_card_quality(
            "What does cross-validation estimate?",
            "How well a model generalizes to unseen data.",
        )
        review = evaluate_card_quality(
            "Explain this material.",
            "Cross-validation estimates generalization.",
        )
        blocked = evaluate_card_quality("", "Answer")

        self.assertEqual(ready.summary("zh"), "本地检查未发现明显问题，仍请审核。")
        self.assertEqual(ready.summary("en"), "No obvious local issue found. Please review.")
        self.assertIn("需要确认", review.summary("zh"))
        self.assertIn("review", review.summary("en").casefold())
        self.assertIn("写入", blocked.summary("zh"))
        self.assertIn("write", blocked.summary("en").casefold())
        for value in (ready, review, blocked):
            self.assertNotIn("truth", value.summary("en").casefold())
            self.assertEqual(value.to_safe_dict()["status"], value.status)

    def test_review_stats_expose_public_names_without_changing_keep_gate(self):
        workbench = ReviewWorkbench.from_candidates(
            (
                ReviewCandidate.create(
                    "ready",
                    "What does ATP store?",
                    "Immediately usable cellular energy.",
                ),
                ReviewCandidate.create(
                    "review",
                    "Explain this material.",
                    "ATP stores immediately usable cellular energy.",
                ),
                ReviewCandidate.create("blocked", "", "Energy."),
            )
        )

        self.assertEqual(workbench.stats.ready_count, 1)
        self.assertEqual(workbench.stats.review_count, 1)
        self.assertEqual(workbench.stats.blocked_count, 1)
        with self.assertRaisesRegex(ValueError, "blocking"):
            workbench.keep("blocked")
        kept = workbench.keep_clean()
        self.assertEqual(kept.card("ready").decision.value, "kept")
        self.assertEqual(kept.card("review").decision.value, "pending")


if __name__ == "__main__":
    unittest.main()
