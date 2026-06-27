import json
import unittest
from dataclasses import replace

from ankiforge_ai.pipeline.card_candidates import (
    build_candidate_id,
    create_card_candidate,
    create_card_candidates,
)
from ankiforge_ai.pipeline.models import CardCandidate, HumanSelection


class CardCandidateTests(unittest.TestCase):
    def test_creates_basic_candidate_from_selected_selection(self):
        candidate = create_card_candidate(self.selection())

        self.assertIsInstance(candidate, CardCandidate)
        self.assertEqual(candidate.card_type, "basic")
        self.assertEqual(candidate.front, "What is Overfitting?")
        self.assertEqual(candidate.back, "The model memorizes training noise.")
        self.assertEqual(candidate.source, candidate.source_display)
        self.assertIn("Validation accuracy falls.", candidate.extra)
        self.assertIn(candidate.source_display, candidate.extra)

    def test_inherits_selection_metadata(self):
        selection = self.selection()

        candidate = create_card_candidate(selection)

        self.assertEqual(candidate.selection_id, selection.selection_id)
        self.assertEqual(candidate.point_id, selection.point_id)
        self.assertEqual(candidate.document_id, selection.document_id)
        self.assertEqual(candidate.chunk_id, selection.chunk_id)
        self.assertEqual(candidate.source_display, selection.source_display)
        self.assertEqual(candidate.heading_path, selection.heading_path)
        self.assertEqual(candidate.ordinal, selection.ordinal)
        self.assertEqual(candidate.tags, selection.tags)

    def test_mutable_lists_are_copied(self):
        selection = self.selection()

        candidate = create_card_candidate(selection)
        selection.heading_path.append("Changed")
        selection.tags.append("changed")

        self.assertEqual(candidate.heading_path, ["Models", "Overfitting"])
        self.assertEqual(candidate.tags, ["ml", "generalization"])

    def test_candidate_id_is_deterministic_and_ignores_card_content(self):
        selection = self.selection()
        changed_content = replace(
            selection,
            title="Changed title",
            explanation="Changed explanation",
            evidence="Changed evidence",
        )

        original = create_card_candidate(selection)
        changed = create_card_candidate(changed_content)

        self.assertEqual(
            build_candidate_id(selection.selection_id),
            f"cc_{selection.selection_id}_0",
        )
        self.assertEqual(original.candidate_id, changed.candidate_id)
        self.assertNotEqual(original.front, changed.front)
        self.assertNotEqual(original.back, changed.back)
        self.assertNotEqual(original.extra, changed.extra)

    def test_rejected_or_deferred_single_selection_raises_value_error(self):
        for decision in ("rejected", "deferred"):
            with self.subTest(decision=decision):
                with self.assertRaises(ValueError):
                    create_card_candidate(self.selection(decision=decision))

    def test_batch_only_generates_selected_candidates_in_input_order(self):
        first = self.selection(selection_id="hs-1", point_id="kp-1", title="First")
        rejected = self.selection(
            selection_id="hs-2",
            point_id="kp-2",
            title="Rejected",
            decision="rejected",
        )
        third = self.selection(selection_id="hs-3", point_id="kp-3", title="Third")
        deferred = self.selection(
            selection_id="hs-4",
            point_id="kp-4",
            title="Deferred",
            decision="deferred",
        )

        candidates = create_card_candidates([first, rejected, third, deferred])

        self.assertEqual(
            [candidate.selection_id for candidate in candidates],
            ["hs-1", "hs-3"],
        )
        self.assertEqual(
            [candidate.front for candidate in candidates],
            ["What is First?", "What is Third?"],
        )

    def test_empty_selection_list_returns_empty_list(self):
        self.assertEqual(create_card_candidates([]), [])

    def test_to_dict_is_json_serializable(self):
        candidate = create_card_candidate(self.selection())

        data = candidate.to_dict()

        self.assertEqual(data["candidate_id"], candidate.candidate_id)
        self.assertEqual(data["card_type"], "basic")
        json.dumps(data, ensure_ascii=False)

    def selection(
        self,
        selection_id="hs-kp-1",
        point_id="kp-1",
        title="Overfitting",
        decision="selected",
    ):
        return HumanSelection(
            selection_id=selection_id,
            point_id=point_id,
            document_id="doc-1",
            chunk_id="chunk-1",
            source_display="ml.md > Models > Overfitting",
            heading_path=["Models", "Overfitting"],
            ordinal=0,
            title=title,
            explanation="The model memorizes training noise.",
            evidence="Validation accuracy falls.",
            tags=["ml", "generalization"],
            importance="high",
            decision=decision,
            note="",
        )


if __name__ == "__main__":
    unittest.main()
