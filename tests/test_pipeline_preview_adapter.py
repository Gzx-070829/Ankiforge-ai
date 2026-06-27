import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from ankiforge_ai.pipeline.orchestrator import (
    PipelineRunStatus,
    PipelineRunWithStatus,
    run_full_mock_pipeline_with_status,
)
from ankiforge_ai.pipeline.preview_adapter import (
    PREVIEW_MAX_CHARS,
    ReadOnlyPipelinePreviewData,
    build_read_only_pipeline_preview,
)


class PipelinePreviewAdapterTests(unittest.TestCase):
    def test_success_status_and_summary_counts_are_converted(self):
        outcome = self.success_outcome()

        preview = build_read_only_pipeline_preview(outcome)

        self.assertIsInstance(preview, ReadOnlyPipelinePreviewData)
        self.assertEqual(preview.run_status, "success")
        self.assertEqual(preview.failed_stage, "")
        self.assertEqual(preview.error_message, "")
        self.assertEqual(preview.summary_counts["chunk_count"], 2)
        self.assertEqual(preview.summary_counts["card_candidate_count"], 2)
        self.assertEqual(preview.summary_counts["pending_review_count"], 2)

    def test_failed_and_partial_statuses_are_converted(self):
        for status_name in ("failed", "partial"):
            with self.subTest(status=status_name):
                outcome = PipelineRunWithStatus(
                    result=None,
                    status=PipelineRunStatus(
                        status=status_name,
                        failed_stage="card_generation",
                        error_message="Generation stopped.",
                        error_type="RuntimeError",
                    ),
                )

                preview = build_read_only_pipeline_preview(outcome)

                self.assertEqual(preview.run_status, status_name)
                self.assertEqual(preview.failed_stage, "card_generation")
                self.assertEqual(preview.error_message, "Generation stopped.")
                self.assertEqual(preview.summary_counts, {})
                self.assertEqual(preview.cards, ())

    def test_card_quality_and_review_data_are_converted(self):
        outcome = self.success_outcome()

        preview = build_read_only_pipeline_preview(outcome)

        self.assertEqual(len(preview.cards), 2)
        first = preview.cards[0]
        self.assertEqual(first.candidate_id, outcome.result.card_candidates[0].candidate_id)
        self.assertTrue(first.front_preview)
        self.assertTrue(first.back_preview)
        self.assertTrue(first.quality_passed)
        self.assertEqual(first.quality_issue_count, 0)
        self.assertEqual(first.review_decision, "pending")

    def test_card_text_is_normalized_and_truncated_for_preview(self):
        outcome = self.success_outcome()
        outcome.result.card_candidates[0].front = "Word\n" * 80

        preview = build_read_only_pipeline_preview(outcome)

        self.assertLessEqual(len(preview.cards[0].front_preview), PREVIEW_MAX_CHARS)
        self.assertNotIn("\n", preview.cards[0].front_preview)
        self.assertTrue(preview.cards[0].front_preview.endswith("..."))

    def test_adapter_does_not_modify_pipeline_outcome_or_result(self):
        outcome = self.success_outcome()
        original = deepcopy(outcome)

        build_read_only_pipeline_preview(outcome)

        self.assertEqual(outcome, original)

    def success_outcome(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            markdown_path = Path(temp_dir) / "notes.md"
            markdown_path.write_text(
                "# Overfitting\n"
                "Overfitting memorizes noise in training data.\n\n"
                "## Regularization\n"
                "Regularization helps models generalize to unseen data.\n",
                encoding="utf-8",
            )
            return run_full_mock_pipeline_with_status(str(markdown_path))


if __name__ == "__main__":
    unittest.main()
