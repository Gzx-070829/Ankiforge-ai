from dataclasses import FrozenInstanceError
import unittest

from ankiforge_ai.intelligence.call_budget import (
    CallBudget,
    CallBudgetError,
    CallPurpose,
)
from ankiforge_ai.intelligence.models import IntelligenceLevel


class IntelligenceCallBudgetTests(unittest.TestCase):
    def test_level_policies_have_exact_ranges_and_standard_default(self):
        standard = CallBudget()
        fast = CallBudget.for_level(IntelligenceLevel.FAST)
        deep = CallBudget.for_level(IntelligenceLevel.DEEP)

        self.assertEqual(
            (fast.minimum_calls, fast.call_limit),
            (1, 3),
        )
        self.assertEqual(
            (standard.level, standard.minimum_calls, standard.call_limit),
            (IntelligenceLevel.STANDARD, 3, 8),
        )
        self.assertEqual(
            (deep.minimum_calls, deep.call_limit),
            (4, 12),
        )

    def test_every_supported_call_purpose_is_reserved_before_dispatch(self):
        budget = CallBudget.for_level(IntelligenceLevel.DEEP)

        for count, purpose in enumerate(
            (
                CallPurpose.PLANNER,
                CallPurpose.GENERATE,
                CallPurpose.CRITIC,
                CallPurpose.REPAIR,
                CallPurpose.SUPPLEMENT,
            ),
            start=1,
        ):
            budget = budget.reserve(purpose)
            self.assertEqual(budget.call_count, count)
            self.assertEqual(budget.reservations[-1].purpose, purpose)
            self.assertEqual(budget.reservations[-1].sequence, count)

    def test_failed_dispatched_call_remains_billed_without_automatic_retry(self):
        budget = CallBudget.for_level(IntelligenceLevel.DEEP)
        reserved = budget.reserve(CallPurpose.GENERATE)

        try:
            raise RuntimeError("private provider output")
        except RuntimeError:
            pass

        self.assertEqual(budget.call_count, 0)
        self.assertEqual(reserved.call_count, 1)
        self.assertEqual(len(reserved.reservations), 1)
        self.assertFalse(hasattr(reserved, "retry"))

    def test_deep_rejects_thirteenth_call_with_structured_safe_error(self):
        budget = CallBudget.for_level(IntelligenceLevel.DEEP)
        for _index in range(12):
            budget = budget.reserve(CallPurpose.GENERATE)

        with self.assertRaises(CallBudgetError) as raised:
            budget.reserve(CallPurpose.GENERATE)

        error = raised.exception
        self.assertEqual(error.reason_code, "call_budget_exhausted")
        self.assertEqual(error.call_count, 12)
        self.assertEqual(error.call_limit, 12)
        self.assertNotIn("provider", repr(error).casefold())

    def test_fast_and_standard_enforce_level_specific_ceilings(self):
        for level, limit in (
            (IntelligenceLevel.FAST, 3),
            (IntelligenceLevel.STANDARD, 8),
        ):
            with self.subTest(level=level):
                budget = CallBudget.for_level(level)
                for _index in range(limit):
                    budget = budget.reserve(CallPurpose.GENERATE)
                with self.assertRaisesRegex(
                    CallBudgetError,
                    "call_budget_exhausted",
                ):
                    budget.reserve(CallPurpose.GENERATE)

    def test_level_disallows_unplanned_expensive_stages(self):
        fast = CallBudget.for_level(IntelligenceLevel.FAST)
        standard = CallBudget.for_level(IntelligenceLevel.STANDARD)

        for purpose in (
            CallPurpose.PLANNER,
            CallPurpose.CRITIC,
            CallPurpose.REPAIR,
            CallPurpose.SUPPLEMENT,
        ):
            with self.subTest(purpose=purpose):
                with self.assertRaisesRegex(CallBudgetError, "call_not_allowed"):
                    fast.reserve(purpose)
        for purpose in (CallPurpose.CRITIC, CallPurpose.SUPPLEMENT):
            with self.subTest(purpose=purpose):
                with self.assertRaisesRegex(CallBudgetError, "call_not_allowed"):
                    standard.reserve(purpose)

    def test_budget_is_immutable_and_validates_exact_integers(self):
        budget = CallBudget()

        with self.assertRaises(FrozenInstanceError):
            budget.call_limit = 12
        for value in (True, 1.0, float("nan"), float("inf"), -1):
            with self.subTest(value=value):
                with self.assertRaises((TypeError, ValueError)):
                    CallBudget(call_count=value)

    def test_reservation_repr_contains_only_purpose_and_counts(self):
        reserved = CallBudget.for_level(IntelligenceLevel.DEEP).reserve(
            CallPurpose.GENERATE
        )

        self.assertIn("generate", repr(reserved))
        self.assertIn("calls=1/12", repr(reserved))
        self.assertNotIn("material", repr(reserved))

    def test_structured_error_rejects_unsafe_codes_and_invalid_counts(self):
        unsafe = (
            "../private",
            "C:\\Users\\private\\key",
            "private provider body",
            "UPPER_CODE",
            "",
        )
        for reason_code in unsafe:
            with self.subTest(reason_code=reason_code):
                with self.assertRaisesRegex(ValueError, "reason_code"):
                    CallBudgetError(
                        reason_code,
                        call_count=0,
                        call_limit=3,
                    )
        for call_count, call_limit in ((True, 3), (1.5, 3), (4, 3), (0, 13)):
            with self.subTest(
                call_count=call_count,
                call_limit=call_limit,
            ):
                with self.assertRaises((TypeError, ValueError)):
                    CallBudgetError(
                        "call_budget_exhausted",
                        call_count=call_count,
                        call_limit=call_limit,
                    )


if __name__ == "__main__":
    unittest.main()
