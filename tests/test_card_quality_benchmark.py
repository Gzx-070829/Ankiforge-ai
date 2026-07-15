import copy
import json
from pathlib import Path
import unittest

from ankiforge_ai.eval.card_quality_benchmark import (
    evaluate_benchmark_fixture,
    evaluate_benchmark_suite,
    load_benchmark_fixture,
)


class CardQualityBenchmarkTests(unittest.TestCase):
    REQUIRED_FIELDS = {
        "fixture_id",
        "source_text",
        "recommended_mode",
        "expected_good_patterns",
        "expected_bad_patterns",
        "expected_min_cards",
        "expected_max_cards",
        "notes",
        "mock_cards",
    }

    def test_ten_multidisciplinary_json_fixtures_have_safe_schema(self):
        paths = self.fixture_paths()

        self.assertEqual(len(paths), 10)
        for path in paths:
            with self.subTest(path=path.name):
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(set(payload), self.REQUIRED_FIELDS)
                self.assertLessEqual(
                    payload["expected_min_cards"],
                    len(payload["mock_cards"]),
                )
                self.assertLessEqual(
                    len(payload["mock_cards"]),
                    payload["expected_max_cards"],
                )
                rendered = json.dumps(payload, ensure_ascii=False).casefold()
                for forbidden in (
                    "sk-live-",
                    "bearer ey",
                    "authorization:",
                    "c:\\users\\",
                    "collection.anki2",
                ):
                    self.assertNotIn(forbidden, rendered)

    def test_each_fixture_evaluates_offline_with_no_blocking_cards(self):
        for path in self.fixture_paths():
            with self.subTest(path=path.name):
                fixture = load_benchmark_fixture(path)
                summary = evaluate_benchmark_fixture(fixture)

                self.assertEqual(summary.total_count, len(fixture.mock_cards))
                self.assertEqual(summary.blocking_count, 0)
                self.assertEqual(
                    summary.total_count,
                    summary.pass_count + summary.warning_count + summary.blocking_count,
                )
                self.assertEqual(
                    set(summary.score_distribution),
                    {"high", "medium", "low"},
                )

    def test_suite_summary_aggregates_candidate_states_deterministically(self):
        fixtures = tuple(load_benchmark_fixture(path) for path in self.fixture_paths())

        first = evaluate_benchmark_suite(fixtures)
        second = evaluate_benchmark_suite(fixtures)

        self.assertEqual(first, second)
        self.assertGreater(first.total_count, 10)
        self.assertEqual(first.blocking_count, 0)
        self.assertEqual(
            first.total_count,
            sum(first.score_distribution.values()),
        )

    def test_inline_fixture_reports_pass_warning_and_blocking_without_mutation(self):
        payload = {
            "fixture_id": "inline-quality-states",
            "source_text": "交叉验证用于评估模型的泛化能力。",
            "recommended_mode": "concept",
            "expected_good_patterns": ["具体问题"],
            "expected_bad_patterns": ["空正面", "泛化问题"],
            "expected_min_cards": 3,
            "expected_max_cards": 3,
            "notes": "Deterministic state coverage.",
            "mock_cards": [
                {
                    "id": "good",
                    "front": "交叉验证有什么作用？",
                    "back": "它用于评估模型的泛化能力。",
                },
                {
                    "id": "warning",
                    "front": "请解释以下内容。",
                    "back": "交叉验证用于评估泛化能力。",
                },
                {"id": "blocking", "front": "", "back": "评估泛化能力。"},
            ],
        }
        before = copy.deepcopy(payload)

        summary = evaluate_benchmark_fixture(payload)

        self.assertEqual(summary.pass_count, 1)
        self.assertEqual(summary.warning_count, 1)
        self.assertEqual(summary.blocking_count, 1)
        self.assertEqual(payload, before)
        self.assertNotIn(payload["source_text"], repr(summary))

    @classmethod
    def fixture_paths(cls):
        return sorted(
            (Path(__file__).parent / "fixtures" / "card_quality").glob("*.json")
        )


if __name__ == "__main__":
    unittest.main()
