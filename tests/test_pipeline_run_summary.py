import tempfile
import unittest
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

from ankiforge_ai.pipeline.models import QualityGateResult, QualityIssue
from ankiforge_ai.pipeline.orchestrator import (
    PipelineRunSummary,
    run_full_mock_pipeline,
    summarize_pipeline_run,
)


class PipelineRunSummaryTests(unittest.TestCase):
    def test_full_mock_pipeline_summary_counts_are_correct(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_full_mock_pipeline(self.write_markdown(temp_dir))

        summary = summarize_pipeline_run(result)

        self.assertIsInstance(summary, PipelineRunSummary)
        self.assertEqual(summary.source_filename, "notes.md")
        self.assertEqual(summary.source_document_id, result.source_document.document_id)
        self.assertEqual(summary.chunk_count, 2)
        self.assertEqual(summary.knowledge_point_count, 2)
        self.assertEqual(summary.human_selection_count, 2)
        self.assertEqual(summary.selected_count, 2)
        self.assertEqual(summary.rejected_count, 0)
        self.assertEqual(summary.deferred_count, 0)
        self.assertEqual(summary.card_candidate_count, 2)
        self.assertEqual(summary.quality_passed_count, 2)
        self.assertEqual(summary.quality_failed_count, 0)
        self.assertEqual(summary.human_review_count, 2)
        self.assertIsInstance(summary.to_dict(), dict)

    def test_selected_point_subset_summary_counts_are_correct(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            markdown_path = self.write_markdown(temp_dir)
            all_points = run_full_mock_pipeline(markdown_path).knowledge_points
            result = run_full_mock_pipeline(
                markdown_path,
                selected_point_ids=[all_points[0].point_id],
            )

        summary = summarize_pipeline_run(result)

        self.assertEqual(summary.knowledge_point_count, 2)
        self.assertEqual(summary.human_selection_count, 1)
        self.assertEqual(summary.selected_count, 1)
        self.assertEqual(summary.rejected_count, 0)
        self.assertEqual(summary.deferred_count, 0)
        self.assertEqual(summary.card_candidate_count, 1)

    def test_reviews_remain_pending_and_are_not_approved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_full_mock_pipeline(self.write_markdown(temp_dir))

        summary = summarize_pipeline_run(result)

        self.assertEqual(summary.pending_review_count, 2)
        self.assertEqual(summary.approved_review_count, 0)
        self.assertEqual(summary.rejected_review_count, 0)
        self.assertEqual(summary.needs_edit_review_count, 0)
        self.assertTrue(all(review.decision == "pending" for review in result.human_reviews))

    def test_quality_counts_come_from_quality_gate_results(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_full_mock_pipeline(self.write_markdown(temp_dir))

        mixed_result = replace(
            result,
            quality_results=[
                QualityGateResult(candidate_id="cc-pass", issues=[]),
                QualityGateResult(
                    candidate_id="cc-fail",
                    issues=[QualityIssue("error", "Blocking issue.", "error")],
                ),
            ],
        )

        summary = summarize_pipeline_run(mixed_result)

        self.assertEqual(summary.quality_passed_count, 1)
        self.assertEqual(summary.quality_failed_count, 1)

    def test_summarize_does_not_modify_pipeline_result(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_full_mock_pipeline(self.write_markdown(temp_dir))
        original = deepcopy(result)

        summarize_pipeline_run(result)

        self.assertEqual(result, original)

    def test_empty_pipeline_stages_are_counted_safely(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_full_mock_pipeline(self.write_markdown(temp_dir))
        empty_result = replace(
            result,
            chunks=[],
            knowledge_points=[],
            human_selections=[],
            card_candidates=[],
            quality_results=[],
            human_reviews=[],
        )

        summary = summarize_pipeline_run(empty_result)

        count_values = [
            value
            for key, value in summary.to_dict().items()
            if key.endswith("_count")
        ]
        self.assertTrue(count_values)
        self.assertTrue(all(value == 0 for value in count_values))

    def write_markdown(self, directory):
        markdown_path = Path(directory) / "notes.md"
        markdown_path.write_text(
            "# Overfitting\n"
            "Overfitting memorizes noise in training data.\n\n"
            "## Regularization\n"
            "Regularization helps models generalize to unseen data.\n",
            encoding="utf-8",
        )
        return str(markdown_path)


if __name__ == "__main__":
    unittest.main()
