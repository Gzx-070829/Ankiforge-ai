import json
import unittest

from ankiforge_ai.pipeline.human_selection import (
    build_selection_id,
    create_human_selection,
    create_human_selections,
)
from ankiforge_ai.pipeline.models import HumanSelection, KnowledgePoint


class HumanSelectionTests(unittest.TestCase):
    def test_creates_selection_with_default_values(self):
        selection = create_human_selection(self.point())

        self.assertIsInstance(selection, HumanSelection)
        self.assertEqual(selection.decision, "selected")
        self.assertEqual(selection.note, "")

    def test_inherits_metadata_and_content(self):
        point = self.point()

        selection = create_human_selection(point)

        self.assertEqual(selection.point_id, point.point_id)
        self.assertEqual(selection.document_id, point.document_id)
        self.assertEqual(selection.chunk_id, point.chunk_id)
        self.assertEqual(selection.source_display, point.source_display)
        self.assertEqual(selection.heading_path, point.heading_path)
        self.assertEqual(selection.ordinal, point.ordinal)
        self.assertEqual(selection.title, point.title)
        self.assertEqual(selection.explanation, point.explanation)
        self.assertEqual(selection.evidence, point.evidence)
        self.assertEqual(selection.tags, point.tags)
        self.assertEqual(selection.importance, point.importance)

    def test_mutable_lists_are_copied(self):
        point = self.point()

        selection = create_human_selection(point)
        point.heading_path.append("Changed")
        point.tags.append("changed")

        self.assertEqual(selection.heading_path, ["Models", "Overfitting"])
        self.assertEqual(selection.tags, ["ml", "generalization"])

    def test_accepts_supported_decisions_and_note(self):
        for decision in ("selected", "rejected", "deferred"):
            with self.subTest(decision=decision):
                selection = create_human_selection(
                    self.point(),
                    decision=decision,
                    note="Review later",
                )
                self.assertEqual(selection.decision, decision)
                self.assertEqual(selection.note, "Review later")

    def test_invalid_decision_raises_value_error(self):
        with self.assertRaises(ValueError):
            create_human_selection(self.point(), decision="unknown")

    def test_batch_selects_matching_points_in_point_order(self):
        first = self.point(point_id="kp-1", title="First", ordinal=0)
        second = self.point(point_id="kp-2", title="Second", ordinal=1)
        third = self.point(point_id="kp-3", title="Third", ordinal=2)

        selections = create_human_selections(
            [first, second, third],
            ["kp-3", "kp-1"],
        )

        self.assertEqual(
            [selection.point_id for selection in selections],
            ["kp-1", "kp-3"],
        )
        self.assertTrue(all(item.decision == "selected" for item in selections))

    def test_empty_points_and_selected_ids_returns_empty_list(self):
        self.assertEqual(create_human_selections([], []), [])

    def test_unknown_selected_id_raises_value_error(self):
        with self.assertRaises(ValueError):
            create_human_selections([self.point()], ["missing"])

        with self.assertRaises(ValueError):
            create_human_selections([], ["missing"])

    def test_to_dict_is_json_serializable(self):
        selection = create_human_selection(self.point())

        data = selection.to_dict()

        self.assertEqual(data["selection_id"], selection.selection_id)
        json.dumps(data, ensure_ascii=False)

    def test_selection_id_is_deterministic_and_ignores_mutable_state(self):
        point = self.point()

        selected = create_human_selection(point)
        deferred = create_human_selection(
            point,
            decision="deferred",
            note="Needs another look",
        )

        self.assertEqual(build_selection_id(point.point_id), f"hs_{point.point_id}")
        self.assertEqual(selected.selection_id, deferred.selection_id)

    def point(self, point_id="kp-1", title="Overfitting", ordinal=0):
        return KnowledgePoint(
            point_id=point_id,
            document_id="doc-1",
            chunk_id="chunk-1",
            source_display="ml.md > Models > Overfitting",
            heading_path=["Models", "Overfitting"],
            ordinal=ordinal,
            title=title,
            explanation="The model memorizes training noise.",
            evidence="Training accuracy rises while validation accuracy falls.",
            tags=["ml", "generalization"],
            importance="high",
        )


if __name__ == "__main__":
    unittest.main()
