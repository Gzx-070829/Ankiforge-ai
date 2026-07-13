import copy
import unittest

from ankiforge_ai.pipeline.card_quality import (
    evaluate_card_batch,
    evaluate_card_quality,
)
from ankiforge_ai.pipeline.generation_settings import GenerationSettings


class CardQualityTests(unittest.TestCase):
    def test_empty_front_and_back_are_blocking(self):
        front = evaluate_card_quality("", "有效答案")
        back = evaluate_card_quality("有效问题是什么？", "")

        self.assertEqual(front.severity, "blocking")
        self.assertIn("empty_front", front.warning_ids)
        self.assertEqual(back.severity, "blocking")
        self.assertIn("empty_back", back.warning_ids)

    def test_short_and_generic_front_are_warnings(self):
        short = evaluate_card_quality("啥？", "这是一个答案。")
        generic = evaluate_card_quality("请解释以下内容。", "内容说明。")

        self.assertIn("short_front", short.warning_ids)
        self.assertIn("generic_front", generic.warning_ids)
        self.assertEqual(generic.severity, "warning")

    def test_long_back_respects_answer_length(self):
        long_answer = "这是较长的答案。" * 40

        short = evaluate_card_quality(
            "为什么需要交叉验证？",
            long_answer,
            GenerationSettings(answer_length="short"),
        )
        medium = evaluate_card_quality(
            "为什么需要交叉验证？",
            long_answer,
            GenerationSettings(answer_length="medium"),
        )

        self.assertIn("long_back", short.warning_ids)
        self.assertNotIn("long_back", medium.warning_ids)

    def test_multiple_questions_and_points_are_warnings(self):
        result = evaluate_card_quality(
            "什么是过拟合？它有什么影响？",
            "1. 训练误差低\n2. 泛化误差高\n3. 容易记住噪声",
        )

        self.assertIn("multiple_questions", result.warning_ids)
        self.assertIn("multi_point_card", result.warning_ids)

    def test_boilerplate_and_markdown_residue_are_warnings(self):
        result = evaluate_card_quality(
            "根据材料可知，什么是早停？",
            "**早停**会在验证集表现不再改善时停止训练。",
        )

        self.assertIn("boilerplate_phrase", result.warning_ids)
        self.assertIn("markdown_residue", result.warning_ids)

    def test_good_chinese_card_has_high_score(self):
        result = evaluate_card_quality(
            "交叉验证为什么能帮助评估泛化能力？",
            "它在未参与当前训练的数据划分上评估模型表现。",
        )

        self.assertGreaterEqual(result.quality_score, 0.85)
        self.assertEqual(result.severity, "info")
        self.assertEqual(result.warning_ids, ())

    def test_batch_marks_later_duplicate_without_mutating_cards(self):
        cards = [
            {"id": "one", "front": "什么是过拟合？", "back": "泛化能力下降。"},
            {"id": "two", "front": " 什么是过拟合？ ", "back": "泛化能力下降。"},
        ]
        before = copy.deepcopy(cards)

        batch = evaluate_card_batch(cards)

        self.assertNotIn("duplicate_candidate", batch.for_candidate("one").warning_ids)
        self.assertIn("duplicate_candidate", batch.for_candidate("two").warning_ids)
        self.assertEqual(cards, before)

    def test_card_like_preview_fields_are_supported(self):
        class Preview:
            id = "preview-1"
            front_preview = "早停如何降低过拟合风险？"
            back_preview = "验证表现不再改善时停止训练。"

        result = evaluate_card_batch((Preview(),)).for_candidate("preview-1")

        self.assertGreaterEqual(result.quality_score, 0.85)

    def test_safe_repr_never_contains_card_text(self):
        private = "private material that must not appear"
        result = evaluate_card_quality("具体问题是什么？", private)

        self.assertNotIn(private, repr(result))
        self.assertNotIn(private, str(result.to_safe_dict()))
        self.assertEqual(result.to_safe_dict()["issue_count"], len(result.issues))


if __name__ == "__main__":
    unittest.main()
