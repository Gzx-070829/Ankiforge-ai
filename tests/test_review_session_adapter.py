import unittest

from ankiforge_ai.ui.review_session_adapter import LegacyReviewSessionAdapter


class FakeLegacySession:
    def __init__(self):
        self.calls = []

    def review_workbench_snapshot(self):
        self.calls.append(("snapshot",))
        return "snapshot"

    def set_candidate_review_decision(self, candidate_id, decision):
        self.calls.append(("decision", candidate_id, decision))

    def replace_candidate_content(self, candidate_id, front, back):
        self.calls.append(("replace", candidate_id, front, back))

    def restore_candidate_content(self, candidate_id):
        self.calls.append(("restore", candidate_id))

    def keep_clean_candidates(self):
        self.calls.append(("keep_clean",))
        return 2

    def discard_blocking_candidates(self):
        self.calls.append(("discard_blocking",))
        return 1


class ReviewSessionAdapterTests(unittest.TestCase):
    def test_adapter_maps_workbench_decisions_to_legacy_values(self):
        session = FakeLegacySession()
        adapter = LegacyReviewSessionAdapter(session)

        adapter.set_decision("card-1", "keep")
        adapter.set_decision("card-2", "needs_edit")
        adapter.set_decision("card-3", "discard")
        adapter.set_decision("card-4", None)

        self.assertEqual(
            session.calls,
            [
                ("decision", "card-1", "looks_good"),
                ("decision", "card-2", "needs_revision"),
                ("decision", "card-3", "skip_for_now"),
                ("decision", "card-4", None),
            ],
        )

    def test_adapter_delegates_remaining_review_operations(self):
        session = FakeLegacySession()
        adapter = LegacyReviewSessionAdapter(session)

        self.assertEqual(adapter.snapshot(), "snapshot")
        adapter.replace_content("card-1", "front", "back")
        adapter.restore_content("card-1")
        self.assertEqual(adapter.keep_clean(), 2)
        self.assertEqual(adapter.discard_blocking(), 1)

        self.assertIn(("replace", "card-1", "front", "back"), session.calls)


if __name__ == "__main__":
    unittest.main()
