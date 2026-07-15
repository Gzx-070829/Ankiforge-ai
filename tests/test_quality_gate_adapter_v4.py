import unittest

from ankiforge_ai.pipeline.card_quality import evaluate_card_quality
from ankiforge_ai.pipeline.quality_gate import canonical_quality_to_gate


class QualityGateAdapterV4Tests(unittest.TestCase):
    def test_canonical_blocking_and_warning_severities_are_adapted(self):
        quality = evaluate_card_quality("", "答案是：有效答案。")

        result = canonical_quality_to_gate("candidate-1", quality)

        self.assertEqual(result.candidate_id, "candidate-1")
        issues = {item.code: item for item in result.issues}
        self.assertEqual(issues["empty_front"].severity, "error")
        self.assertEqual(
            issues["back_contains_unnecessary_intro"].severity,
            "warning",
        )
        self.assertFalse(result.passed)

    def test_adapter_uses_user_copy_not_internal_identifiers_as_message(self):
        quality = evaluate_card_quality(
            "请解释以下内容。",
            "这是一个直接答案。",
        )

        zh = canonical_quality_to_gate("candidate-1", quality, language="zh")
        en = canonical_quality_to_gate("candidate-1", quality, language="en")

        self.assertNotEqual(zh.issues[0].message, zh.issues[0].code)
        self.assertNotEqual(en.issues[0].message, en.issues[0].code)
        self.assertNotEqual(zh.issues[0].message, en.issues[0].message)

    def test_adapter_rejects_invalid_candidate_or_language(self):
        quality = evaluate_card_quality("有效问题是什么？", "有效答案。")

        with self.assertRaisesRegex(ValueError, "candidate_id"):
            canonical_quality_to_gate("", quality)
        with self.assertRaisesRegex(ValueError, "language"):
            canonical_quality_to_gate("candidate-1", quality, language="fr")


if __name__ == "__main__":
    unittest.main()
