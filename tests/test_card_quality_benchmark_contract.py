from pathlib import Path
import unittest

from ankiforge_ai.eval.card_quality_benchmark import (
    evaluate_benchmark_fixture_report,
    evaluate_benchmark_suite,
    load_benchmark_fixture,
)


class CardQualityBenchmarkContractTests(unittest.TestCase):
    def test_versioned_suite_covers_public_states_and_duplicate_classes(self):
        fixtures = tuple(
            load_benchmark_fixture(path)
            for path in sorted(
                (Path(__file__).parent / "fixtures" / "card_quality").glob("*.json")
            )
        )
        reports = tuple(evaluate_benchmark_fixture_report(item) for item in fixtures)
        summary = evaluate_benchmark_suite(fixtures)

        self.assertTrue(all(item.matches_expectations for item in reports))
        self.assertTrue(all(item.coverage_met for item in reports))
        self.assertEqual(
            {outcome.status for report in reports for outcome in report.outcomes},
            {"ready", "review", "blocked"},
        )
        self.assertTrue(
            {"exact", "canonical", "similar"}.issubset(
                {
                    outcome.duplicate_kind
                    for report in reports
                    for outcome in report.outcomes
                    if outcome.duplicate_kind is not None
                }
            )
        )
        self.assertGreater(summary.rule_counts.get("generic_front", 0), 0)
        self.assertGreater(summary.rule_counts.get("long_back", 0), 0)
        self.assertGreater(summary.rule_counts.get("multiple_questions", 0), 0)
        self.assertEqual(sum(summary.status_distribution.values()), summary.total_count)

    def test_reports_are_deterministic_safe_and_do_not_contain_fixture_bodies(self):
        path = Path(__file__).parent / "fixtures" / "card_quality" / "quality_edge_cases_zh.json"
        fixture = load_benchmark_fixture(path)

        first = evaluate_benchmark_fixture_report(fixture)
        second = evaluate_benchmark_fixture_report(fixture)

        self.assertEqual(first, second)
        rendered = repr(first)
        self.assertIn(fixture.fixture_id, rendered)
        self.assertNotIn(fixture.source_text, rendered)
        for card in fixture.mock_cards:
            if card.front:
                self.assertNotIn(card.front, rendered)
            if card.back:
                self.assertNotIn(card.back, rendered)


if __name__ == "__main__":
    unittest.main()
