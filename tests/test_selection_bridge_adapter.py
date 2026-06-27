import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from ankiforge_ai.pipeline.models import KnowledgePoint
from ankiforge_ai.pipeline.orchestrator import (
    extract_mock_knowledge_points,
    run_full_mock_pipeline,
    run_full_mock_pipeline_with_status,
)
from ankiforge_ai.pipeline.selection_bridge_adapter import (
    KnowledgePointPreviewItem,
    build_knowledge_point_preview_items,
    create_selections_from_preview_choice,
)


class SelectionBridgeAdapterTests(unittest.TestCase):
    def test_knowledge_point_converts_to_preview_item(self):
        point = self.point()

        item = build_knowledge_point_preview_items([point])[0]

        self.assertIsInstance(item, KnowledgePointPreviewItem)
        self.assertEqual(item.point_id, point.point_id)
        self.assertEqual(item.title, point.title)
        self.assertEqual(item.importance, point.importance)
        self.assertEqual(item.tags, tuple(point.tags))
        self.assertEqual(item.source_display, point.source_display)
        self.assertTrue(item.explanation)
        self.assertTrue(item.evidence)
        self.assertTrue(item.default_selected)

    def test_preview_items_copy_mutable_tags_and_do_not_modify_points(self):
        point = self.point()
        original = deepcopy(point)

        item = build_knowledge_point_preview_items([point])[0]
        self.assertEqual(point, original)
        point.tags.append("changed")

        self.assertEqual(item.tags, ("ml", "generalization"))
        self.assertEqual(original.tags, ["ml", "generalization"])
        self.assertEqual(point.title, original.title)

    def test_partial_choice_delegates_to_existing_selection_rules(self):
        points = [self.point("kp-1", "First"), self.point("kp-2", "Second")]

        selections = create_selections_from_preview_choice(points, ["kp-2"])

        self.assertEqual([item.point_id for item in selections], ["kp-2"])
        self.assertTrue(all(item.decision == "selected" for item in selections))

    def test_unknown_point_id_preserves_existing_value_error(self):
        with self.assertRaises(ValueError):
            create_selections_from_preview_choice([self.point()], ["missing"])

    def test_mock_extraction_helper_stops_at_knowledge_points(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            markdown_path = self.write_markdown(temp_dir)

            points = extract_mock_knowledge_points(markdown_path)

        self.assertEqual(len(points), 2)
        self.assertEqual([point.title for point in points], ["First", "Second"])

    def test_selected_ids_only_advance_matching_points_and_reviews_stay_pending(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            markdown_path = self.write_markdown(temp_dir)
            points = extract_mock_knowledge_points(markdown_path)
            selected_id = points[1].point_id
            with patch(
                "urllib.request.urlopen",
                side_effect=AssertionError("Network access is not allowed."),
            ), patch(
                "socket.create_connection",
                side_effect=AssertionError("Network access is not allowed."),
            ):
                outcome = run_full_mock_pipeline_with_status(
                    markdown_path,
                    selected_point_ids=[selected_id],
                )

        self.assertEqual(outcome.status.status, "success")
        self.assertEqual(len(outcome.result.human_selections), 1)
        self.assertEqual(len(outcome.result.card_candidates), 1)
        self.assertEqual(len(outcome.result.quality_results), 1)
        self.assertEqual(len(outcome.result.human_reviews), 1)
        self.assertEqual(outcome.result.card_candidates[0].point_id, selected_id)
        self.assertEqual(outcome.result.human_reviews[0].decision, "pending")

    def test_empty_selected_ids_advance_no_points_without_defaulting_to_all(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            outcome = run_full_mock_pipeline_with_status(
                self.write_markdown(temp_dir),
                selected_point_ids=[],
            )

        self.assertEqual(outcome.status.status, "success")
        self.assertEqual(len(outcome.result.knowledge_points), 2)
        self.assertEqual(outcome.result.human_selections, [])
        self.assertEqual(outcome.result.card_candidates, [])
        self.assertEqual(outcome.result.quality_results, [])
        self.assertEqual(outcome.result.human_reviews, [])
        self.assertEqual(outcome.status.summary.selected_count, 0)
        self.assertEqual(outcome.status.summary.card_candidate_count, 0)

    def test_original_full_pipeline_still_selects_all_points_by_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_full_mock_pipeline(self.write_markdown(temp_dir))

        self.assertEqual(len(result.knowledge_points), 2)
        self.assertEqual(len(result.human_selections), 2)
        self.assertEqual(len(result.card_candidates), 2)

    def point(self, point_id="kp-1", title="Overfitting"):
        return KnowledgePoint(
            point_id=point_id,
            document_id="doc-1",
            chunk_id="chunk-1",
            source_display="notes.md > Models > Overfitting",
            heading_path=["Models", "Overfitting"],
            ordinal=0,
            title=title,
            explanation="The model memorizes training noise.",
            evidence="Validation performance falls.",
            tags=["ml", "generalization"],
            importance="high",
        )

    def write_markdown(self, directory):
        markdown_path = Path(directory) / "notes.md"
        markdown_path.write_text(
            "# First\nFirst concept has enough explanation text.\n\n"
            "## Second\nSecond concept also has enough explanation text.\n",
            encoding="utf-8",
        )
        return str(markdown_path)


if __name__ == "__main__":
    unittest.main()
