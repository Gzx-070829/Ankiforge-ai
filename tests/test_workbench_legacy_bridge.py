import unittest

from ankiforge_ai.ui.beginner_flow_models import (
    BeginnerAICardDraft,
    BeginnerFlowSession,
    BeginnerReviewDecision,
)
from ankiforge_ai.workbench import WorkbenchArtifactStatus
from ankiforge_ai.workbench.legacy_bridge import project_legacy_session
from ankiforge_ai.workbench.store import WorkbenchSessionStore


class WorkbenchLegacyBridgeTests(unittest.TestCase):
    def session_with_candidate(self):
        session = BeginnerFlowSession()
        session.update_material("alpha beta gamma")
        session.apply_ai_candidate_card_drafts(
            (
                BeginnerAICardDraft(
                    id="draft-1",
                    front="What is alpha?",
                    back="Alpha is the first concept.",
                    source_excerpt="alpha beta gamma",
                ),
            )
        )
        return session

    def test_projection_tracks_counts_ids_and_revisions_without_content(self):
        session = self.session_with_candidate()
        session.set_candidate_review_decision(
            "candidate-draft-1",
            BeginnerReviewDecision.LOOKS_GOOD,
        )

        projected = project_legacy_session(session)

        self.assertTrue(projected.material.has_material)
        self.assertEqual(projected.material.char_count, 16)
        self.assertEqual(projected.material.revision, session.material_revision)
        self.assertEqual(projected.generation.candidate_ids, ("candidate-draft-1",))
        self.assertEqual(projected.review.decisions[0].decision, "keep")
        self.assertEqual(projected.review.status, WorkbenchArtifactStatus.COMPLETE)
        self.assertNotIn("alpha beta gamma", repr(projected))

    def test_running_projection_uses_only_the_active_request_identity(self):
        session = BeginnerFlowSession()
        session.update_material("new material")
        session.begin_ai_candidate_generation()

        projected = project_legacy_session(session, active_request_id=9)

        self.assertEqual(projected.generation.request_id, 9)
        self.assertEqual(projected.generation.status, WorkbenchArtifactStatus.RUNNING)
        self.assertEqual(projected.generation.candidate_ids, ())

    def test_store_synchronization_replaces_an_immutable_snapshot(self):
        session = BeginnerFlowSession()
        store = WorkbenchSessionStore.from_legacy(session)
        first = store.state
        session.update_material("new material")

        second = store.synchronize(session)

        self.assertIsNot(first, second)
        self.assertIs(second, store.state)

    def test_store_tracks_target_and_mapping_revisions_without_hashes(self):
        session = self.session_with_candidate()
        session.set_candidate_review_decision(
            "candidate-draft-1",
            BeginnerReviewDecision.LOOKS_GOOD,
        )
        session.select_anki_deck(7, "Test Deck")
        session.select_anki_note_type(11, "Basic", ("Front", "Back"))
        session.set_anki_field_mapping("Front", "Back", None)
        session.apply_duplicate_check_preview(1, 0)
        store = WorkbenchSessionStore.from_legacy(session)

        current = store.state
        self.assertEqual(current.write.target_revision, 1)
        self.assertEqual(current.write.mapping_revision, 1)
        self.assertEqual(current.write.status, WorkbenchArtifactStatus.CURRENT)

        session.select_anki_deck(8, "Second Deck")
        changed = store.synchronize(session)

        self.assertEqual(changed.write.target_revision, 2)
        self.assertEqual(changed.write.mapping_revision, 1)
        self.assertEqual(changed.write.status, WorkbenchArtifactStatus.STALE)
        self.assertIsNone(changed.write.duplicate_candidate_revision)

    def test_store_repr_and_state_never_contain_material_or_target_names(self):
        secret_material = "private study material"
        private_deck = "Personal Medical Deck"
        session = BeginnerFlowSession()
        session.update_material(secret_material)
        session.select_anki_deck(7, private_deck)

        store = WorkbenchSessionStore.from_legacy(session)
        rendered = repr(store) + repr(store.state)

        self.assertNotIn(secret_material, rendered)
        self.assertNotIn(private_deck, rendered)

    def test_closed_store_discards_state_and_rejects_reuse(self):
        store = WorkbenchSessionStore.from_legacy(self.session_with_candidate())

        closed = store.close()

        self.assertTrue(closed.closed)
        self.assertEqual(closed.generation.candidate_ids, ())
        with self.assertRaises(RuntimeError):
            store.synchronize(BeginnerFlowSession())


if __name__ == "__main__":
    unittest.main()
