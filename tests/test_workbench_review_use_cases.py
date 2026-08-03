import unittest

from ankiforge_ai.workbench.review_use_cases import (
    MAX_REVIEW_CARD_TEXT_CHARS,
    ReviewUseCases,
)


class FakeReviewPort:
    def __init__(self):
        self.calls = []

    def snapshot(self):
        self.calls.append(("snapshot",))
        return "snapshot"

    def set_decision(self, candidate_id, decision):
        self.calls.append(("decision", candidate_id, decision))

    def replace_content(self, candidate_id, front, back):
        self.calls.append(("replace", candidate_id, front, back))

    def restore_content(self, candidate_id):
        self.calls.append(("restore", candidate_id))

    def keep_clean(self):
        self.calls.append(("keep_clean",))
        return 2

    def discard_blocking(self):
        self.calls.append(("discard_blocking",))
        return 1


class WorkbenchReviewUseCasesTests(unittest.TestCase):
    def test_use_cases_delegate_only_declared_review_operations(self):
        port = FakeReviewPort()
        use_cases = ReviewUseCases(port)

        self.assertEqual(use_cases.snapshot(), "snapshot")
        use_cases.set_decision("card-1", "keep")
        use_cases.replace_content("card-1", "front", "back")
        use_cases.restore_content("card-1")
        self.assertEqual(use_cases.keep_clean(), 2)
        self.assertEqual(use_cases.discard_blocking(), 1)

        self.assertEqual(port.calls[1], ("decision", "card-1", "keep"))
        self.assertEqual(port.calls[2], ("replace", "card-1", "front", "back"))

    def test_invalid_decisions_and_candidate_ids_fail_before_delegation(self):
        port = FakeReviewPort()
        use_cases = ReviewUseCases(port)

        with self.assertRaises(ValueError):
            use_cases.set_decision("../card", "keep")
        with self.assertRaises(ValueError):
            use_cases.set_decision("card-1", "approve")

        self.assertEqual(port.calls, [])

    def test_edit_content_is_bounded_before_delegation(self):
        port = FakeReviewPort()
        use_cases = ReviewUseCases(port)

        with self.assertRaises(ValueError):
            use_cases.replace_content(
                "card-1",
                "x" * (MAX_REVIEW_CARD_TEXT_CHARS + 1),
                "back",
            )

        self.assertEqual(port.calls, [])

    def test_repr_never_contains_port_or_card_content(self):
        class PrivatePort(FakeReviewPort):
            def __repr__(self):
                return "private study content"

        rendered = repr(ReviewUseCases(PrivatePort()))

        self.assertNotIn("private study content", rendered)


if __name__ == "__main__":
    unittest.main()
