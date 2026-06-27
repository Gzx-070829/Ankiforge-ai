import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ankiforge_ai.pipeline.orchestrator import (
    PipelineRunResult,
    PipelineRunWithStatus,
    run_full_mock_pipeline,
    run_full_mock_pipeline_with_status,
    summarize_pipeline_run,
)


class PipelineRunStatusTests(unittest.TestCase):
    def test_original_runner_success_behavior_is_unchanged(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_full_mock_pipeline(self.write_markdown(temp_dir))

        self.assertIsInstance(result, PipelineRunResult)
        self.assertTrue(result.human_reviews)
        self.assertTrue(
            all(review.decision == "pending" for review in result.human_reviews)
        )

    def test_original_runner_still_raises_failures(self):
        missing_path = str(Path("missing") / "does-not-exist.md")

        with self.assertRaises(FileNotFoundError):
            run_full_mock_pipeline(missing_path)

    def test_safe_runner_success_returns_result_status_and_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            markdown_path = self.write_markdown(temp_dir)
            with patch(
                "urllib.request.urlopen",
                side_effect=AssertionError("Network access is not allowed."),
            ), patch(
                "socket.create_connection",
                side_effect=AssertionError("Network access is not allowed."),
            ):
                outcome = run_full_mock_pipeline_with_status(markdown_path)

        self.assertIsInstance(outcome, PipelineRunWithStatus)
        self.assertEqual(outcome.status.status, "success")
        self.assertEqual(outcome.status.failed_stage, "")
        self.assertEqual(outcome.status.error_message, "")
        self.assertEqual(outcome.status.error_type, "")
        self.assertIsNotNone(outcome.result)
        self.assertEqual(
            outcome.status.summary,
            summarize_pipeline_run(outcome.result),
        )
        self.assertIsInstance(outcome.status.to_dict(), dict)

    def test_safe_runner_returns_partial_for_middle_stage_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            markdown_path = self.write_markdown(temp_dir)
            with patch(
                "ankiforge_ai.pipeline.orchestrator.create_card_candidates",
                side_effect=RuntimeError("Card generation failed."),
            ):
                outcome = run_full_mock_pipeline_with_status(markdown_path)

        self.assertIsNone(outcome.result)
        self.assertEqual(outcome.status.status, "partial")
        self.assertEqual(outcome.status.failed_stage, "card_generation")
        self.assertEqual(outcome.status.error_type, "RuntimeError")
        self.assertEqual(outcome.status.error_message, "Card generation failed.")

    def test_safe_runner_returns_failed_for_source_analysis_failure(self):
        missing_path = str(Path("missing") / "does-not-exist.md")

        outcome = run_full_mock_pipeline_with_status(missing_path)

        self.assertIsNone(outcome.result)
        self.assertEqual(outcome.status.status, "failed")
        self.assertEqual(outcome.status.failed_stage, "source_analysis")
        self.assertEqual(outcome.status.error_type, "FileNotFoundError")
        self.assertTrue(outcome.status.error_message)

    def test_summary_failure_is_partial_and_preserves_pipeline_result(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            markdown_path = self.write_markdown(temp_dir)
            with patch(
                "ankiforge_ai.pipeline.orchestrator.summarize_pipeline_run",
                side_effect=ValueError("Summary failed."),
            ):
                outcome = run_full_mock_pipeline_with_status(markdown_path)

        self.assertIsNotNone(outcome.result)
        self.assertEqual(outcome.status.status, "partial")
        self.assertEqual(outcome.status.failed_stage, "summary")
        self.assertEqual(outcome.status.error_type, "ValueError")
        self.assertTrue(
            all(review.decision == "pending" for review in outcome.result.human_reviews)
        )

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
