import ast
import unittest
from pathlib import Path

from ankiforge_ai.ui.beginner_flow_models import (
    BEGINNER_FUTURE_CONDITIONS,
    BEGINNER_PREWRITE_SUMMARY,
    BEGINNER_REVIEW_DECISION_COPY,
    BEGINNER_REVIEW_SAFETY_NOTE,
    BEGINNER_TECHNICAL_DETAILS_COPY,
    BEGINNER_TERM_COPY,
    COMPLETION_TITLE,
    REVIEW_STATE_EXPLANATIONS,
    BeginnerArtifactState,
    BeginnerFlowSession,
    BeginnerFlowStep,
    BeginnerReviewDecision,
)


class BeginnerReviewProgressiveDisclosureTests(unittest.TestCase):
    def test_plain_language_review_choices_are_stable(self):
        self.assertEqual(
            dict(BEGINNER_REVIEW_DECISION_COPY),
            {
                BeginnerReviewDecision.LOOKS_GOOD: "看起来可以",
                BeginnerReviewDecision.NEEDS_CHANGES: "需要修改",
                BeginnerReviewDecision.SKIP_FOR_NOW: "暂时不要",
            },
        )

    def test_review_choices_live_only_in_session_memory(self):
        session = self.candidate_session()
        decisions = tuple(BeginnerReviewDecision)

        for candidate, decision in zip(
            session.candidate_card_previews,
            decisions,
        ):
            session.set_candidate_review_decision(candidate.id, decision)

        self.assertEqual(
            tuple(session.candidate_review_decisions.values()),
            decisions,
        )
        self.assertFalse(session.persistent)
        self.assertNotIn("candidate_review_decisions", session.to_safe_dict())

    def test_review_choice_change_clears_every_later_preview(self):
        session = self.candidate_session()
        session.eligibility_state = BeginnerArtifactState.CURRENT
        session.write_plan_preview_state = BeginnerArtifactState.CURRENT
        session.final_confirmation_preview_state = BeginnerArtifactState.CURRENT

        session.set_candidate_review_decision(
            session.candidate_card_previews[0].id,
            BeginnerReviewDecision.LOOKS_GOOD,
        )

        self.assert_later_previews_cleared(session)
        self.assertEqual(session.last_clearing_reason, "candidate_review_changed")

    def test_review_completion_requires_one_choice_per_candidate(self):
        session = self.candidate_session()
        with self.assertRaisesRegex(ValueError, "every candidate"):
            session.complete_candidate_review()

        for candidate in session.candidate_card_previews:
            session.set_candidate_review_decision(
                candidate.id,
                BeginnerReviewDecision.SKIP_FOR_NOW,
            )
        session.complete_candidate_review()

        self.assertEqual(session.current_step, BeginnerFlowStep.CHECK_BEFORE_WRITE)
        self.assertEqual(session.review_state, BeginnerArtifactState.CURRENT)
        self.assertEqual(session.reviewed_candidate_count, session.candidate_count)
        self.assert_later_previews_cleared(session)

    def test_material_change_clears_review_choices_and_later_previews(self):
        session = self.reviewed_session()

        session.update_material("另一份材料")

        self.assertEqual(session.candidate_review_decisions, {})
        self.assertEqual(session.review_state, BeginnerArtifactState.CLEARED)
        self.assert_later_previews_cleared(session)

    def test_selection_change_clears_review_choices_and_later_previews(self):
        session = self.reviewed_session()
        remaining_id = session.recognized_knowledge_points[-1].id

        session.select_knowledge_points((remaining_id,))

        self.assertEqual(session.candidate_review_decisions, {})
        self.assertEqual(session.review_state, BeginnerArtifactState.CLEARED)
        self.assert_later_previews_cleared(session)

    def test_future_conditions_are_all_pending_plain_language_items(self):
        self.assertEqual(
            tuple(condition.title for condition in BEGINNER_FUTURE_CONDITIONS),
            ("目标牌组", "笔记类型", "字段映射", "重复检查", "最终确认"),
        )
        self.assertTrue(
            all(
                condition.status == "未来需要确认"
                for condition in BEGINNER_FUTURE_CONDITIONS
            )
        )
        self.assertEqual(
            BEGINNER_PREWRITE_SUMMARY,
            "当前只是离线演练。即使你已经审核候选卡，也不会写入 Anki。",
        )

    def test_future_condition_copy_never_claims_write_readiness(self):
        combined = "\n".join(
            (
                BEGINNER_PREWRITE_SUMMARY,
                *(condition.title for condition in BEGINNER_FUTURE_CONDITIONS),
                *(condition.status for condition in BEGINNER_FUTURE_CONDITIONS),
                *(condition.explanation for condition in BEGINNER_FUTURE_CONDITIONS),
            )
        )
        for forbidden in (
            "已准备好写入",
            "可以直接写入",
            "写入成功",
            "完成写入",
            "已写入",
        ):
            self.assertNotIn(forbidden, combined)

    def test_surface_terms_are_plain_chinese(self):
        self.assertEqual(BEGINNER_TERM_COPY["Human Review"], "人工审核")
        self.assertEqual(
            BEGINNER_TERM_COPY["Write Eligibility"],
            "是否满足未来写入条件",
        )
        self.assertEqual(
            BEGINNER_TERM_COPY["Write Plan"],
            "未来写入方式预览",
        )
        self.assertEqual(
            BEGINNER_TERM_COPY["Final confirmation contract"],
            "真正写入前还需确认什么",
        )

    def test_technical_details_are_optional_and_deny_authorization(self):
        self.assertTrue(BEGINNER_TECHNICAL_DETAILS_COPY)
        for detail in BEGINNER_TECHNICAL_DETAILS_COPY:
            self.assertIn("不代表写入授权", detail)
        for explanation in REVIEW_STATE_EXPLANATIONS.values():
            self.assertIn("不代表写入授权", explanation)

    def test_dialog_defaults_technical_details_to_collapsed(self):
        source = self.dialog_source()
        self.assertIn("self.technical_details_expanded = False", source)
        self.assertIn('QPushButton("查看技术详情")', source)
        self.assertIn('"隐藏技术详情"', source)
        self.assertIn("self.technical_toggle_btn.setFlat(True)", source)
        self.assertIn("self.next_btn.setDefault(True)", source)
        self.assertIn("self.session.view_prewrite_conditions()", source)
        self.assertIn("self.session.finish_prewrite_walkthrough()", source)

    def test_dialog_review_controls_are_session_driven_radio_choices(self):
        source = self.dialog_source()
        self.assertIn("QRadioButton(label)", source)
        self.assertIn("BEGINNER_REVIEW_DECISION_COPY.items()", source)
        self.assertIn("self.session.set_candidate_review_decision", source)
        self.assertIn("正面预览", source)
        self.assertIn("背面预览", source)
        self.assertIn("来源片段", source)
        self.assertEqual(
            BEGINNER_REVIEW_SAFETY_NOTE,
            "你的选择只用于本次离线演练，不会写入 Anki。",
        )

    def test_dialog_does_not_duplicate_future_condition_copy(self):
        source = self.dialog_source()
        for condition in BEGINNER_FUTURE_CONDITIONS:
            self.assertNotIn(f'"{condition.title}"', source)
        self.assertIn("for index, condition in enumerate", source)

    def test_pr5_does_not_import_or_construct_formal_output_models(self):
        tree = ast.parse(self.model_source())
        imported_names = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        called_names = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        for forbidden in ("GeneratedCard", "WriteReadyPreviewItem"):
            self.assertNotIn(forbidden, imported_names)
            self.assertNotIn(forbidden, called_names)

    def test_completion_copy_remains_exact(self):
        self.assertEqual(COMPLETION_TITLE, "演练完成，尚未写入 Anki")

    @staticmethod
    def candidate_session():
        session = BeginnerFlowSession()
        session.update_material("知识甲。知识乙。知识丙。")
        session.select_material()
        session.mark_recognition_inspected()
        ids = tuple(point.id for point in session.recognized_knowledge_points)
        session.select_knowledge_points(ids)
        session.build_candidate_previews_from_selection()
        return session

    def reviewed_session(self):
        session = self.candidate_session()
        for candidate in session.candidate_card_previews:
            session.set_candidate_review_decision(
                candidate.id,
                BeginnerReviewDecision.LOOKS_GOOD,
            )
        session.complete_candidate_review()
        return session

    def assert_later_previews_cleared(self, session):
        self.assertEqual(session.eligibility_state, BeginnerArtifactState.CLEARED)
        self.assertEqual(
            session.write_plan_preview_state,
            BeginnerArtifactState.CLEARED,
        )
        self.assertEqual(
            session.final_confirmation_preview_state,
            BeginnerArtifactState.CLEARED,
        )

    @staticmethod
    def repo_root():
        return Path(__file__).parents[1]

    def dialog_source(self):
        return (
            self.repo_root() / "ankiforge_ai" / "ui" / "beginner_mode_dialog.py"
        ).read_text(encoding="utf-8")

    def model_source(self):
        return (
            self.repo_root() / "ankiforge_ai" / "ui" / "beginner_flow_models.py"
        ).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
