import unittest

from ankiforge_ai.pipeline.write_traceability import SourceType
from ankiforge_ai.workbench import WorkbenchArtifactStatus, initial_workbench_state
from ankiforge_ai.workbench.transitions import (
    change_mapping,
    change_target,
    close_session,
    complete_generation,
    fail_generation,
    mark_duplicate_check_current,
    record_review_decision,
    start_generation,
    update_material,
    write_is_ready,
)


class WorkbenchTransitionTests(unittest.TestCase):
    def ready_state(self):
        state = update_material(
            initial_workbench_state(),
            char_count=20,
            source_type=SourceType.PASTE,
        )
        state = start_generation(state, request_id=1)
        state = complete_generation(
            state,
            request_id=1,
            candidate_ids=("card-1",),
        )
        state = record_review_decision(state, "card-1", "keep")
        return mark_duplicate_check_current(state)

    def test_material_change_invalidates_all_downstream_state(self):
        changed = update_material(
            self.ready_state(),
            char_count=25,
            source_type=SourceType.MARKDOWN,
        )

        self.assertEqual(changed.material.revision, 2)
        self.assertEqual(changed.generation.candidate_ids, ())
        self.assertEqual(changed.review.decisions, ())
        self.assertFalse(write_is_ready(changed))

    def test_stale_generation_completion_and_failure_are_ignored(self):
        state = update_material(
            initial_workbench_state(),
            char_count=10,
            source_type=SourceType.PASTE,
        )
        running = start_generation(state, request_id=2)

        self.assertIs(
            complete_generation(
                running,
                request_id=1,
                candidate_ids=("old-card",),
            ),
            running,
        )
        self.assertIs(
            fail_generation(
                running,
                request_id=1,
                error_code="provider_error",
            ),
            running,
        )

    def test_generation_failure_clears_candidates_review_and_write(self):
        state = update_material(
            initial_workbench_state(),
            char_count=10,
            source_type=SourceType.PASTE,
        )
        failed = fail_generation(
            start_generation(state, request_id=7),
            request_id=7,
            error_code="provider_error",
        )

        self.assertEqual(failed.generation.status, WorkbenchArtifactStatus.FAILED)
        self.assertEqual(failed.generation.error_code, "provider_error")
        self.assertEqual(failed.review.decisions, ())
        self.assertFalse(write_is_ready(failed))

    def test_review_must_cover_every_candidate_before_duplicate_check(self):
        state = update_material(
            initial_workbench_state(),
            char_count=10,
            source_type=SourceType.PASTE,
        )
        state = complete_generation(
            start_generation(state, request_id=1),
            request_id=1,
            candidate_ids=("card-1", "card-2"),
        )
        state = record_review_decision(state, "card-1", "keep")

        with self.assertRaises(ValueError):
            mark_duplicate_check_current(state)

    def test_write_requires_a_kept_card_and_matching_duplicate_snapshot(self):
        self.assertTrue(write_is_ready(self.ready_state()))

        state = update_material(
            initial_workbench_state(),
            char_count=10,
            source_type=SourceType.PASTE,
        )
        state = complete_generation(
            start_generation(state, request_id=1),
            request_id=1,
            candidate_ids=("card-1",),
        )
        state = record_review_decision(state, "card-1", "discard")

        self.assertFalse(write_is_ready(mark_duplicate_check_current(state)))

    def test_target_or_mapping_change_invalidates_duplicate_readiness(self):
        ready = self.ready_state()

        target_changed = change_target(ready)
        mapping_changed = change_mapping(ready)

        self.assertFalse(write_is_ready(target_changed))
        self.assertFalse(write_is_ready(mapping_changed))
        self.assertEqual(target_changed.write.target_revision, 1)
        self.assertEqual(mapping_changed.write.mapping_revision, 1)

    def test_closed_state_rejects_mutation(self):
        closed = close_session(initial_workbench_state())

        with self.assertRaises(RuntimeError):
            update_material(
                closed,
                char_count=1,
                source_type=SourceType.PASTE,
            )


if __name__ == "__main__":
    unittest.main()
