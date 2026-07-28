import socket
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


class DocumentIntelligenceBenchmarkTests(unittest.TestCase):
    def test_all_mandated_local_scenarios_have_literal_routes_and_coverage(self):
        from ankiforge_ai.eval.document_intelligence_benchmark import evaluate_document_intelligence_suite

        summary = evaluate_document_intelligence_suite(ROOT / "tests" / "fixtures")
        expected = {
            "python": ("code_understanding", 2, 2), "sql": ("code_understanding", 1, 1),
            "bci_eegnet": ("definition", 2, 2), "math": ("concept", 2, 2),
            "vocabulary": ("definition", 2, 2), "biology": ("definition", 2, 2),
            "history": ("concept", 2, 2), "process": ("process_steps", 2, 2),
            "comparison": ("compare_contrast", 2, 2), "table": ("table_relationship", 1, 1),
            "transcript": ("transcript_summary_candidate", 1, 1), "bilingual": ("definition", 2, 2),
            "ppt": ("concept", 2, 2), "xlsx": ("formula_rule", 2, 2),
        }
        self.assertEqual(tuple(summary["fixtures"]), tuple(expected))
        for fixture_id, (route, chunks, points) in expected.items():
            item = summary["fixtures"][fixture_id]
            with self.subTest(item=fixture_id):
                self.assertEqual(item["route"], route)
                self.assertEqual(item["chunk_count"], chunks)
                self.assertEqual(item["point_count"], points)
                self.assertTrue(item["parse_passed"])
                self.assertTrue(item["structure_preserved"])
                self.assertTrue(item["source_locations_preserved"])
                self.assertTrue(item["plan_grounded"])
                self.assertEqual(len(item["chunk_sizes"]), chunks)
                self.assertTrue(all(size > 0 for size in item["chunk_sizes"]))
        self.assertEqual(
            {
                fixture_id: (
                    item["warning_count"],
                    item["blocking_count"],
                    item["duplicate_count"],
                )
                for fixture_id, item in summary["fixtures"].items()
                if any(
                    (
                        item["warning_count"],
                        item["blocking_count"],
                        item["duplicate_count"],
                    )
                )
            },
            {
                "python": (1, 0, 1),
                "history": (1, 0, 0),
                "comparison": (1, 0, 1),
                "table": (0, 1, 0),
                "transcript": (1, 0, 0),
                "ppt": (1, 0, 1),
            },
        )

    def test_metrics_and_failure_reasons_are_deterministic_and_network_free(self):
        from ankiforge_ai.eval.document_intelligence_benchmark import evaluate_document_intelligence_suite

        fixtures = ROOT / "tests" / "fixtures"
        with mock.patch.object(socket, "create_connection", side_effect=AssertionError("network call")):
            first = evaluate_document_intelligence_suite(fixtures)
            second = evaluate_document_intelligence_suite(fixtures)
        self.assertEqual(first, second)
        self.assertEqual(first["metrics"], {
            "fixture_count": 14, "parse_pass_rate": "14/14", "structure_preservation_rate": "14/14",
            "source_location_coverage_rate": "14/14", "planning_coverage_rate": "14/14",
            "template_routing_accuracy": "14/14", "duplicate_rate": "3/28",
            "warning_rate": "5/28", "blocking_rate": "1/28",
            "chunk_count_distribution": {"1": 3, "2": 11},
            "chunk_size_distribution": {
                "0-32": 14, "33-64": 4, "65-128": 7, "129+": 0,
            },
            "quality_fixture_kind": "synthetic_local_rule_smoke",
            "planning_coverage": {"covered_points": 25, "total_points": 25},
        })
        self.assertEqual(first["failed_fixture_reasons"], {})

    def test_missing_fixtures_return_safe_failure_metrics_instead_of_crashing(self):
        from ankiforge_ai.eval.document_intelligence_benchmark import evaluate_document_intelligence_suite

        with tempfile.TemporaryDirectory() as empty_root:
            summary = evaluate_document_intelligence_suite(empty_root)

        self.assertEqual(len(summary["failed_fixture_reasons"]), 14)
        self.assertEqual(summary["metrics"]["parse_pass_rate"], "0/14")
        self.assertEqual(
            summary["metrics"]["chunk_count_distribution"],
            {"0": 14},
        )
        self.assertEqual(
            summary["metrics"]["chunk_size_distribution"],
            {"0-32": 0, "33-64": 0, "65-128": 0, "129+": 0},
        )


if __name__ == "__main__":
    unittest.main()
