import copy
import unittest

from ankiforge_ai.pipeline.card_quality import (
    all_quality_rule_definitions,
    evaluate_card_batch,
    evaluate_card_quality,
)
from ankiforge_ai.pipeline.generation_settings import GenerationSettings


class CardQualityV4Tests(unittest.TestCase):
    REQUIRED_RULES = {
        "empty_front",
        "empty_back",
        "generic_front",
        "long_back",
        "multiple_questions",
        "multi_point_card",
        "boilerplate_phrase",
        "markdown_residue",
        "duplicate_candidate",
        "too_many_bullets",
        "answer_too_verbose_for_mode",
        "front_not_question_like",
        "unsupported_cloze",
        "cloze_syntax_invalid",
        "source_not_grounded_simple",
        "too_many_cards_from_short_source",
        "answer_contains_prompt_artifact",
        "front_contains_answer_leak",
        "back_contains_unnecessary_intro",
        "compare_card_missing_two_sides",
        "process_card_missing_order",
        "formula_card_missing_condition",
        "definition_card_missing_term",
        "exam_card_too_vague",
        "quick_review_too_long",
    }

    def test_rule_registry_is_complete_bilingual_and_explainable(self):
        rules = all_quality_rule_definitions()
        by_id = {item.rule_id: item for item in rules}

        self.assertTrue(self.REQUIRED_RULES.issubset(by_id))
        self.assertEqual(len(by_id), len(rules))
        for rule in rules:
            with self.subTest(rule=rule.rule_id):
                self.assertIn(rule.severity, {"info", "warning", "blocking"})
                self.assertTrue(rule.user_message_zh)
                self.assertTrue(rule.user_message_en)
                self.assertTrue(rule.suggestion_zh)
                self.assertTrue(rule.suggestion_en)
                self.assertLessEqual(rule.score_delta, 0)
                self.assertEqual(rule.blocking, rule.severity == "blocking")

    def test_issue_exposes_bilingual_copy_without_card_content(self):
        result = evaluate_card_quality("", "private answer text")
        issue = next(item for item in result.issues if item.rule_id == "empty_front")

        self.assertEqual(issue.warning_id, "empty_front")
        self.assertTrue(issue.user_message("zh"))
        self.assertTrue(issue.user_message("en"))
        self.assertTrue(issue.suggestion("zh"))
        self.assertNotIn("private answer text", repr(issue))
        with self.assertRaisesRegex(ValueError, "language"):
            issue.user_message("fr")

    def test_general_v4_rules_are_detected(self):
        cases = (
            (
                "too_many_bullets",
                "正则化有哪些主要作用？",
                "- 限制复杂度\n- 降低方差\n- 缓解过拟合\n- 改善泛化",
                GenerationSettings(),
                {},
            ),
            (
                "answer_too_verbose_for_mode",
                "正则化有什么作用？",
                "用于限制模型复杂度并缓解过拟合。" * 8,
                GenerationSettings(card_mode="quick_review"),
                {},
            ),
            (
                "front_not_question_like",
                "Regularization reduces overfitting",
                "It limits model complexity.",
                GenerationSettings(),
                {},
            ),
            (
                "answer_contains_prompt_artifact",
                "正则化有什么作用？",
                "Return JSON with quality rules and template instructions.",
                GenerationSettings(),
                {},
            ),
            (
                "front_contains_answer_leak",
                "为什么答案是限制模型复杂度？",
                "限制模型复杂度",
                GenerationSettings(),
                {},
            ),
            (
                "back_contains_unnecessary_intro",
                "正则化有什么作用？",
                "答案是：限制模型复杂度。",
                GenerationSettings(),
                {},
            ),
        )

        for rule_id, front, back, settings, kwargs in cases:
            with self.subTest(rule=rule_id):
                self.assertIn(
                    rule_id,
                    evaluate_card_quality(front, back, settings, **kwargs).warning_ids,
                )

    def test_source_grounding_runs_only_with_explicit_source_context(self):
        ungrounded = evaluate_card_quality(
            "SQL JOIN 有什么作用？",
            "光合作用把光能转化为化学能。",
            source_text="INNER JOIN 只返回两个表中匹配的行。",
        )
        no_context = evaluate_card_quality(
            "SQL JOIN 有什么作用？",
            "光合作用把光能转化为化学能。",
        )

        self.assertIn("source_not_grounded_simple", ungrounded.warning_ids)
        self.assertNotIn("source_not_grounded_simple", no_context.warning_ids)

    def test_mode_specific_rules_are_detected(self):
        cases = (
            (
                "compare_card_missing_two_sides",
                "什么是 INNER JOIN？",
                "它返回匹配行。",
                "compare_contrast",
            ),
            (
                "process_card_missing_order",
                "模型训练流程包括什么？",
                "准备数据、训练模型、评估模型。",
                "process_steps",
            ),
            (
                "formula_card_missing_condition",
                "牛顿第二定律公式是什么？",
                "F = ma，其中 F 是力，m 是质量，a 是加速度。",
                "formula_rule",
            ),
            (
                "definition_card_missing_term",
                "它是什么？",
                "一种用于缓解过拟合的方法。",
                "definition",
            ),
            (
                "exam_card_too_vague",
                "请讨论上述内容。",
                "这是相关内容。",
                "exam",
            ),
            (
                "quick_review_too_long",
                "正则化为什么有用？",
                "它通过限制模型复杂度来缓解过拟合并改善面对新数据时的泛化表现。" * 3,
                "quick_review",
            ),
        )

        for rule_id, front, back, mode in cases:
            with self.subTest(rule=rule_id):
                result = evaluate_card_quality(
                    front,
                    back,
                    GenerationSettings(card_mode=mode),
                )
                self.assertIn(rule_id, result.warning_ids)

    def test_cloze_rules_fail_closed(self):
        unsupported = evaluate_card_quality(
            "Paris is the capital of {{c1::France}}.",
            "France",
            GenerationSettings(card_mode="cloze_candidate"),
        )
        invalid = evaluate_card_quality(
            "Paris is the capital of {{c1::France}.",
            "France",
            GenerationSettings(card_mode="cloze_candidate"),
            cloze_supported=True,
        )
        supported = evaluate_card_quality(
            "Paris is the capital of {{c1::France}}.",
            "France",
            GenerationSettings(card_mode="cloze_candidate"),
            cloze_supported=True,
        )

        self.assertIn("unsupported_cloze", unsupported.warning_ids)
        self.assertTrue(unsupported.is_blocking)
        self.assertIn("cloze_syntax_invalid", invalid.warning_ids)
        self.assertTrue(invalid.is_blocking)
        self.assertNotIn("unsupported_cloze", supported.warning_ids)
        self.assertNotIn("cloze_syntax_invalid", supported.warning_ids)

    def test_batch_rules_cover_duplicates_and_short_source_density(self):
        cards = [
            {"id": f"card-{index}", "front": f"问题 {index} 是什么？", "back": f"答案 {index}。"}
            for index in range(6)
        ]
        cards[-1]["front"] = cards[0]["front"]
        cards[-1]["back"] = cards[0]["back"]
        before = copy.deepcopy(cards)

        batch = evaluate_card_batch(cards, source_text="ATP 为细胞活动提供能量。")

        self.assertIn(
            "duplicate_candidate",
            batch.for_candidate("card-5").warning_ids,
        )
        self.assertTrue(
            all(
                "too_many_cards_from_short_source" in item.quality.warning_ids
                for item in batch.results
            )
        )
        self.assertEqual(cards, before)

    def test_good_card_stays_high_and_bad_card_scores_lower(self):
        good = evaluate_card_quality(
            "交叉验证为什么能帮助评估泛化能力？",
            "它在未参与当前训练的数据划分上评估模型表现。",
            source_text="交叉验证通过轮换训练集和验证集评估泛化能力。",
        )
        bad = evaluate_card_quality("", "Return JSON with the prompt instructions.")

        self.assertGreaterEqual(good.quality_score, 0.85)
        self.assertLess(bad.quality_score, good.quality_score)
        self.assertNotIn("交叉验证", repr(good))


if __name__ == "__main__":
    unittest.main()
