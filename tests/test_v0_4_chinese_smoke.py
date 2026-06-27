import socket
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

from ankiforge_ai.pipeline.controlled_write_bridge import (
    build_pipeline_write_eligibility,
    build_write_ready_preview_items,
)
from ankiforge_ai.pipeline.orchestrator import run_full_mock_pipeline
from ankiforge_ai.pipeline.source_analyzer import analyze_markdown_file


FIXTURE_PATH = (
    Path(__file__).parents[1]
    / "docs"
    / "fixtures"
    / "chinese_learning_source.md"
)


class V04ChineseSmokeTests(unittest.TestCase):
    def test_source_analyzer_preserves_chinese_content(self):
        document, chunks = analyze_markdown_file(str(FIXTURE_PATH))

        self.assertEqual(document.file_name, "chinese_learning_source.md")
        self.assertEqual(len(chunks), 5)
        self.assertEqual(chunks[0].heading_path, ["线性代数学习要点"])
        self.assertEqual(
            chunks[1].heading_path,
            ["线性代数学习要点", "线性无关"],
        )
        self.assertIn("线性无关", chunks[1].text)
        self.assertEqual(
            chunks[1].source_display,
            "chinese_learning_source.md > 线性代数学习要点 > 线性无关",
        )

    def test_full_mock_pipeline_runs_offline_with_chinese_source(self):
        result = self._run_pipeline_offline()

        self.assertEqual(len(result.chunks), 5)
        self.assertEqual(len(result.knowledge_points), 5)
        self.assertEqual(len(result.card_candidates), 5)
        self.assertEqual(len(result.human_reviews), 5)
        self.assertIn("线性无关", result.knowledge_points[1].title)
        self.assertIn("齐次方程", result.knowledge_points[1].explanation)
        self.assertIn("线性无关", result.card_candidates[1].front)
        self.assertIn("齐次方程", result.card_candidates[1].back)
        self.assertIn("线性代数学习要点", result.card_candidates[1].source)
        self.assertTrue(
            all(review.decision == "pending" for review in result.human_reviews)
        )

    def test_pending_reviews_are_not_write_eligible(self):
        result = self._run_pipeline_offline()
        eligibilities = [
            build_pipeline_write_eligibility(candidate, quality, review)
            for candidate, quality, review in zip(
                result.card_candidates,
                result.quality_results,
                result.human_reviews,
            )
        ]

        self.assertTrue(eligibilities)
        self.assertTrue(all(not item.eligible for item in eligibilities))
        self.assertTrue(
            all("review_not_approved" in item.reasons for item in eligibilities)
        )
        self.assertEqual(
            build_write_ready_preview_items(
                result.card_candidates,
                result.quality_results,
                result.human_reviews,
            ),
            [],
        )

    @staticmethod
    def _run_pipeline_offline():
        with patch.object(
            urllib.request,
            "urlopen",
            side_effect=AssertionError("Network access is not allowed."),
        ), patch.object(
            socket,
            "create_connection",
            side_effect=AssertionError("Network access is not allowed."),
        ):
            return run_full_mock_pipeline(str(FIXTURE_PATH))


if __name__ == "__main__":
    unittest.main()
