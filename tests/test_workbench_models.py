import unittest
from dataclasses import FrozenInstanceError

from ankiforge_ai.pipeline.write_traceability import SourceType
from ankiforge_ai.workbench.models import (
    GenerationState,
    MaterialState,
    ReviewDecisionRecord,
    ReviewState,
    WorkbenchArtifactStatus,
    WorkbenchSessionState,
    WriteState,
    initial_workbench_state,
)


class WorkbenchModelsTests(unittest.TestCase):
    def test_initial_state_contains_only_safe_empty_values(self):
        state = initial_workbench_state()

        self.assertFalse(state.material.has_material)
        self.assertEqual(state.material.source_type, SourceType.PASTE)
        self.assertEqual(
            state.generation.status,
            WorkbenchArtifactStatus.EMPTY,
        )
        self.assertEqual(state.review.decisions, ())
        self.assertFalse(state.closed)
        self.assertNotIn("api_key", repr(state).casefold())

    def test_state_is_immutable(self):
        state = initial_workbench_state()

        with self.assertRaises(FrozenInstanceError):
            state.closed = True

    def test_material_state_rejects_inconsistent_presence(self):
        with self.assertRaises(ValueError):
            MaterialState(revision=0, has_material=True, char_count=0)

        with self.assertRaises(ValueError):
            MaterialState(revision=0, has_material=False, char_count=1)

    def test_generation_state_rejects_duplicate_candidate_ids(self):
        with self.assertRaises(ValueError):
            GenerationState(
                request_id=1,
                status=WorkbenchArtifactStatus.COMPLETE,
                candidate_revision=1,
                candidate_ids=("card-1", "card-1"),
            )

    def test_review_decision_uses_bounded_safe_identifiers_and_values(self):
        with self.assertRaises(ValueError):
            ReviewDecisionRecord(candidate_id="../card", decision="keep")

        with self.assertRaises(ValueError):
            ReviewDecisionRecord(candidate_id="card-1", decision="approve")

    def test_write_snapshot_revisions_are_all_present_or_all_absent(self):
        with self.assertRaises(ValueError):
            WriteState(
                duplicate_candidate_revision=1,
                duplicate_target_revision=None,
                duplicate_mapping_revision=1,
            )

    def test_session_rejects_review_for_another_candidate_revision(self):
        with self.assertRaises(ValueError):
            WorkbenchSessionState(
                generation=GenerationState(
                    request_id=1,
                    status=WorkbenchArtifactStatus.COMPLETE,
                    candidate_revision=2,
                    candidate_ids=("card-1",),
                ),
                review=ReviewState(
                    candidate_revision=1,
                    status=WorkbenchArtifactStatus.CURRENT,
                ),
            )

    def test_state_repr_contains_counts_not_material_or_card_content(self):
        state = WorkbenchSessionState(
            material=MaterialState(
                revision=1,
                has_material=True,
                char_count=25,
                source_type=SourceType.PASTE,
            )
        )

        rendered = repr(state)

        self.assertIn("material_revision=1", rendered)
        self.assertIn("material_chars=25", rendered)
        self.assertNotIn("material_text", rendered)


if __name__ == "__main__":
    unittest.main()
