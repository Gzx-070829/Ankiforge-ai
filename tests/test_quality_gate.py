import json
import unittest
from dataclasses import replace

from ankiforge_ai.pipeline.models import (
    CardCandidate,
    QualityGateResult,
    QualityIssue,
)
from ankiforge_ai.pipeline.quality_gate import (
    run_quality_gate,
    run_quality_gate_for_candidates,
    validate_quality_issue,
)


class QualityGateTests(unittest.TestCase):
    def test_valid_basic_candidate_passes(self):
        result = run_quality_gate(self.candidate())

        self.assertTrue(result.passed)
        self.assertEqual(result.issues, [])

    def test_empty_front_is_error_and_fails(self):
        result = run_quality_gate(replace(self.candidate(), front="  "))

        self.assertIn("empty_front", self.codes(result))
        self.assertFalse(result.passed)

    def test_empty_back_is_error_and_fails(self):
        result = run_quality_gate(replace(self.candidate(), back="\n"))

        self.assertIn("empty_back", self.codes(result))
        self.assertFalse(result.passed)

    def test_identical_stripped_front_and_back_is_warning(self):
        result = run_quality_gate(
            replace(self.candidate(), front="  Same content", back="Same content  ")
        )

        self.assertEqual(self.codes(result), ["front_back_same"])
        self.assertTrue(result.passed)

    def test_long_front_is_warning(self):
        result = run_quality_gate(replace(self.candidate(), front="F" * 201))

        self.assertEqual(self.codes(result), ["front_too_long"])
        self.assertTrue(result.passed)

    def test_short_back_is_warning(self):
        result = run_quality_gate(replace(self.candidate(), back="Short"))

        self.assertEqual(self.codes(result), ["back_too_short"])
        self.assertTrue(result.passed)

    def test_missing_source_is_warning(self):
        result = run_quality_gate(replace(self.candidate(), source="  "))

        self.assertEqual(self.codes(result), ["missing_source"])
        self.assertTrue(result.passed)

    def test_unsupported_card_type_is_error(self):
        result = run_quality_gate(replace(self.candidate(), card_type="cloze"))

        self.assertEqual(self.codes(result), ["unsupported_card_type"])
        self.assertFalse(result.passed)

    def test_issue_order_follows_rule_order(self):
        candidate = replace(
            self.candidate(),
            card_type="cloze",
            front="",
            back="",
            source="",
        )

        result = run_quality_gate(candidate)

        self.assertEqual(
            self.codes(result),
            [
                "unsupported_card_type",
                "empty_front",
                "empty_back",
                "front_back_same",
                "back_too_short",
                "missing_source",
            ],
        )
        self.assertFalse(result.passed)

    def test_quality_issue_validation(self):
        issue = QualityIssue("notice", "A useful warning.", "warning")
        self.assertIs(validate_quality_issue(issue), issue)

        invalid_issues = [
            QualityIssue("", "Message", "warning"),
            QualityIssue(None, "Message", "warning"),
            QualityIssue("code", "", "warning"),
            QualityIssue("code", None, "warning"),
            QualityIssue("code", "Message", "info"),
        ]
        for invalid in invalid_issues:
            with self.subTest(issue=invalid):
                with self.assertRaises(ValueError):
                    validate_quality_issue(invalid)

    def test_passed_cannot_be_supplied_to_result_constructor(self):
        with self.assertRaises(TypeError):
            QualityGateResult(candidate_id="cc-1", issues=[], passed=False)

    def test_passed_is_read_only_and_tracks_current_issues(self):
        warning = QualityIssue("notice", "A useful warning.", "warning")
        error = QualityIssue("problem", "A blocking error.", "error")
        result = QualityGateResult(candidate_id="cc-1", issues=[warning])

        self.assertTrue(result.passed)
        with self.assertRaises(AttributeError):
            result.passed = False

        result.issues.append(error)
        self.assertFalse(result.passed)

        result.issues.remove(error)
        self.assertTrue(result.passed)

    def test_batch_results_preserve_candidate_order(self):
        first = self.candidate(candidate_id="cc-1")
        second = self.candidate(candidate_id="cc-2", front="")

        results = run_quality_gate_for_candidates([first, second])

        self.assertEqual(
            [result.candidate_id for result in results],
            ["cc-1", "cc-2"],
        )
        self.assertEqual([result.passed for result in results], [True, False])

    def test_empty_candidate_list_returns_empty_list(self):
        self.assertEqual(run_quality_gate_for_candidates([]), [])

    def test_models_are_json_serializable(self):
        issue = QualityIssue("notice", "A useful warning.", "warning")
        result = QualityGateResult(candidate_id="cc-1", issues=[issue])

        issue_data = issue.to_dict()
        result_data = result.to_dict()

        self.assertEqual(issue_data["severity"], "warning")
        self.assertTrue(result_data["passed"])
        self.assertEqual(result_data["issues"][0]["code"], "notice")
        json.dumps(issue_data, ensure_ascii=False)
        json.dumps(result_data, ensure_ascii=False)

    def codes(self, result):
        return [issue.code for issue in result.issues]

    def candidate(
        self,
        candidate_id="cc-1",
        front="What is regularization?",
    ):
        return CardCandidate(
            candidate_id=candidate_id,
            selection_id="hs-1",
            point_id="kp-1",
            document_id="doc-1",
            chunk_id="chunk-1",
            source_display="ml.md > Regularization",
            heading_path=["Regularization"],
            ordinal=0,
            card_type="basic",
            front=front,
            back="It reduces model overfitting.",
            extra="Evidence and source context.",
            tags=["ml"],
            source="ml.md > Regularization",
        )


if __name__ == "__main__":
    unittest.main()
