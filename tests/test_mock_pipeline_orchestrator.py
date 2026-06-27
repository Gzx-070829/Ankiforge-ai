import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ankiforge_ai.pipeline.models import HumanReview
from ankiforge_ai.pipeline.orchestrator import (
    PipelineRunResult,
    run_full_mock_pipeline,
)


class MockPipelineOrchestratorTests(unittest.TestCase):
    def test_run_full_mock_pipeline_happy_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            markdown_path = self.write_markdown(temp_dir)

            result = run_full_mock_pipeline(markdown_path)

        self.assertIsInstance(result, PipelineRunResult)
        self.assertEqual(result.source_document.file_name, "notes.md")
        self.assertEqual(len(result.chunks), 2)
        self.assertEqual(len(result.knowledge_points), 2)
        self.assertEqual(len(result.human_selections), 2)
        self.assertEqual(len(result.card_candidates), 2)
        self.assertEqual(len(result.quality_results), 2)
        self.assertEqual(len(result.human_reviews), 2)
        self.assertTrue(all(isinstance(review, HumanReview) for review in result.human_reviews))
        self.assertEqual(
            [candidate.candidate_id for candidate in result.card_candidates],
            [quality.candidate_id for quality in result.quality_results],
        )
        self.assertEqual(
            [candidate.candidate_id for candidate in result.card_candidates],
            [review.candidate_id for review in result.human_reviews],
        )

    def test_run_full_mock_pipeline_with_selected_point_ids(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            markdown_path = self.write_markdown(temp_dir)
            all_points = run_full_mock_pipeline(markdown_path).knowledge_points
            selected_id = all_points[1].point_id

            result = run_full_mock_pipeline(
                markdown_path,
                selected_point_ids=[selected_id],
            )

        self.assertEqual(len(result.knowledge_points), 2)
        self.assertEqual(
            [selection.point_id for selection in result.human_selections],
            [selected_id],
        )
        self.assertEqual(len(result.card_candidates), 1)
        self.assertEqual(result.card_candidates[0].point_id, selected_id)
        self.assertEqual(len(result.quality_results), 1)
        self.assertEqual(len(result.human_reviews), 1)

    def test_run_full_mock_pipeline_does_not_approve_reviews(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_full_mock_pipeline(self.write_markdown(temp_dir))

        self.assertTrue(all(item.passed for item in result.quality_results))
        self.assertTrue(result.human_reviews)
        self.assertTrue(
            all(review.decision == "pending" for review in result.human_reviews)
        )

    def test_run_full_mock_pipeline_is_offline_and_no_anki_dependency(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            markdown_path = self.write_markdown(temp_dir)
            with patch(
                "urllib.request.urlopen",
                side_effect=AssertionError("Network access is not allowed."),
            ), patch(
                "socket.create_connection",
                side_effect=AssertionError("Network access is not allowed."),
            ):
                result = run_full_mock_pipeline(markdown_path)

        self.assertEqual(len(result.human_reviews), 2)

    def write_markdown(self, directory):
        markdown_path = Path(directory) / "notes.md"
        markdown_path.write_text(
            "# Overfitting\n"
            "Overfitting memorizes noise in the training data.\n\n"
            "## Regularization\n"
            "Regularization helps a model generalize to unseen data.\n",
            encoding="utf-8",
        )
        return str(markdown_path)


if __name__ == "__main__":
    unittest.main()
