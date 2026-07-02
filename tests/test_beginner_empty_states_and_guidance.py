import ast
import unittest
from pathlib import Path

from ankiforge_ai.ui.beginner_flow_models import (
    BEGINNER_KNOWLEDGE_SELECTION_GUIDANCE,
    BEGINNER_MATERIAL_EMPTY_HINT,
    BEGINNER_NO_CANDIDATE_PREVIEWS_COPY,
    BEGINNER_NO_SELECTED_KNOWLEDGE_COPY,
    BEGINNER_PREWRITE_INCOMPLETE_REVIEW_COPY,
    BEGINNER_RECOGNITION_EMPTY_MATERIAL_COPY,
    BEGINNER_RECOGNITION_NO_RESULTS_COPY,
    BEGINNER_REVIEW_CHOICE_GUIDANCE,
    COMPLETION_TITLE,
    BeginnerArtifactState,
    BeginnerFlowSession,
    BeginnerFlowStep,
)


class BeginnerEmptyStatesAndGuidanceTests(unittest.TestCase):
    def test_step_one_empty_copy_explains_both_choices_and_safety(self):
        self.assertIn("粘贴自己的学习材料", BEGINNER_MATERIAL_EMPTY_HINT)
        self.assertIn("使用示例材料", BEGINNER_MATERIAL_EMPTY_HINT)
        self.assertIn("不会写入 Anki", BEGINNER_MATERIAL_EMPTY_HINT)

    def test_recognition_empty_copy_does_not_claim_real_ai_failed(self):
        self.assertIn("返回第一步", BEGINNER_RECOGNITION_EMPTY_MATERIAL_COPY)
        self.assertIn("使用示例材料", BEGINNER_RECOGNITION_EMPTY_MATERIAL_COPY)
        self.assertIn("更完整的学习材料", BEGINNER_RECOGNITION_NO_RESULTS_COPY)
        self.assertIn("离线演练规则", BEGINNER_RECOGNITION_NO_RESULTS_COPY)
        for copy in (
            BEGINNER_RECOGNITION_EMPTY_MATERIAL_COPY,
            BEGINNER_RECOGNITION_NO_RESULTS_COPY,
        ):
            self.assertNotIn("AI 识别失败", copy)
            self.assertNotIn("真实 AI", copy)
            self.assertIn("不会写入 Anki", copy)

    def test_very_short_material_reaches_offline_no_result_state(self):
        session = BeginnerFlowSession()
        session.update_material("短句")

        session.select_material()

        self.assertEqual(session.current_step, BeginnerFlowStep.INSPECT_RECOGNITION)
        self.assertEqual(session.recognized_knowledge_points, ())

    def test_knowledge_selection_guidance_explains_candidate_source(self):
        self.assertIn("至少选择一个", BEGINNER_KNOWLEDGE_SELECTION_GUIDANCE)
        self.assertIn("只会来自你选中的知识点", BEGINNER_KNOWLEDGE_SELECTION_GUIDANCE)
        self.assertIn("不会写入 Anki", BEGINNER_KNOWLEDGE_SELECTION_GUIDANCE)

    def test_candidate_empty_copy_gives_safe_next_step(self):
        self.assertIn("回到上一步", BEGINNER_NO_SELECTED_KNOWLEDGE_COPY)
        self.assertIn("调整材料或知识点选择", BEGINNER_NO_CANDIDATE_PREVIEWS_COPY)
        for copy in (
            BEGINNER_NO_SELECTED_KNOWLEDGE_COPY,
            BEGINNER_NO_CANDIDATE_PREVIEWS_COPY,
        ):
            self.assertIn("不会写入 Anki", copy)
            self.assertNotIn("已准备好", copy)
            self.assertNotIn("可以直接", copy)

    def test_review_choice_copy_explicitly_denies_authorization(self):
        for choice in ("看起来可以", "需要修改", "暂时不要"):
            self.assertIn(choice, BEGINNER_REVIEW_CHOICE_GUIDANCE)
        self.assertIn("不是写入授权", BEGINNER_REVIEW_CHOICE_GUIDANCE)
        self.assertIn("只用于本次离线演练", BEGINNER_REVIEW_CHOICE_GUIDANCE)

    def test_incomplete_review_can_view_conditions_without_current_previews(self):
        session = self.candidate_session()

        session.view_prewrite_conditions()

        self.assertEqual(session.current_step, BeginnerFlowStep.CHECK_BEFORE_WRITE)
        self.assertFalse(session.candidate_review_complete)
        self.assert_prewrite_cleared(session)
        self.assertEqual(session.last_clearing_reason, "review_incomplete")

        session.finish_prewrite_walkthrough()

        self.assertEqual(session.current_step, BeginnerFlowStep.COMPLETED_NO_WRITE)
        self.assert_prewrite_cleared(session)

    def test_partly_reviewed_session_is_also_non_blocking_and_non_authorizing(self):
        session = self.candidate_session()
        candidate = session.candidate_card_previews[0]
        session.set_candidate_review_decision(candidate.id, "looks_good")

        session.view_prewrite_conditions()
        session.finish_prewrite_walkthrough()

        self.assertEqual(session.current_step, BeginnerFlowStep.COMPLETED_NO_WRITE)
        self.assertFalse(session.candidate_review_complete)
        self.assert_prewrite_cleared(session)
        self.assertFalse(session.anki_write_allowed)

    def test_prewrite_incomplete_copy_allows_reading_without_misleading(self):
        self.assertIn("先回到上一步审核候选卡", BEGINNER_PREWRITE_INCOMPLETE_REVIEW_COPY)
        self.assertIn("也可以继续查看", BEGINNER_PREWRITE_INCOMPLETE_REVIEW_COPY)
        self.assertIn("不会写入 Anki", BEGINNER_PREWRITE_INCOMPLETE_REVIEW_COPY)

    def test_dialog_uses_non_blocking_explanatory_navigation(self):
        source = self.dialog_source()
        self.assertIn("self.session.view_prewrite_conditions()", source)
        self.assertIn("self.session.finish_prewrite_walkthrough()", source)
        update_source = self.function_source(source, "_update_primary_action_state")
        self.assertNotIn("candidate_review_decisions", update_source)
        self.assertNotIn("complete_candidate_review", update_source)

    def test_completion_and_new_copy_avoid_misleading_write_claims(self):
        self.assertEqual(COMPLETION_TITLE, "演练完成，尚未写入 Anki")
        rendered = "\n".join(
            (
                BEGINNER_MATERIAL_EMPTY_HINT,
                BEGINNER_RECOGNITION_EMPTY_MATERIAL_COPY,
                BEGINNER_RECOGNITION_NO_RESULTS_COPY,
                BEGINNER_KNOWLEDGE_SELECTION_GUIDANCE,
                BEGINNER_NO_SELECTED_KNOWLEDGE_COPY,
                BEGINNER_NO_CANDIDATE_PREVIEWS_COPY,
                BEGINNER_REVIEW_CHOICE_GUIDANCE,
                BEGINNER_PREWRITE_INCOMPLETE_REVIEW_COPY,
            )
        )
        for forbidden in (
            "写入成功",
            "已写入",
            "已准备好写入",
            "可以直接写入",
            "confirm write",
            "approve and write",
        ):
            self.assertNotIn(forbidden, rendered)

    def test_models_do_not_import_formal_pipeline_outputs(self):
        tree = ast.parse(self.model_source())
        imported_names = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertNotIn("GeneratedCard", imported_names)
        self.assertNotIn("WriteReadyPreviewItem", imported_names)

    @staticmethod
    def candidate_session():
        session = BeginnerFlowSession()
        session.update_material("过拟合会影响泛化。正则化可以限制模型复杂度。")
        session.select_material()
        session.mark_recognition_inspected()
        ids = tuple(point.id for point in session.recognized_knowledge_points)
        session.select_knowledge_points(ids)
        session.build_candidate_previews_from_selection()
        return session

    def assert_prewrite_cleared(self, session):
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
    def function_source(source, function_name):
        tree = ast.parse(source)
        node = next(
            item
            for item in ast.walk(tree)
            if isinstance(item, ast.FunctionDef) and item.name == function_name
        )
        return ast.unparse(node)

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
