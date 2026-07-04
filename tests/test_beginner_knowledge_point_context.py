import ast
import json
import unittest
from pathlib import Path

from ankiforge_ai.ui.beginner_flow_models import (
    BEGINNER_GUIDE_STEP_NOTES,
    BEGINNER_NO_SELECTED_KNOWLEDGE_COPY,
    BEGINNER_STEP_COPY,
    COMPLETION_TITLE,
    BeginnerArtifactState,
    BeginnerCandidateCardPreview,
    BeginnerFlowSession,
    BeginnerFlowStep,
    BeginnerKnowledgePointPreview,
)


class BeginnerKnowledgePointContextTests(unittest.TestCase):
    def test_empty_material_does_not_create_knowledge_points(self):
        session = BeginnerFlowSession()
        session.update_material(" \n；。")

        recognized = session.refresh_mock_recognition_from_material()

        self.assertEqual(recognized, ())
        self.assertEqual(session.recognized_knowledge_points, ())

    def test_recognition_uses_only_current_material(self):
        session = BeginnerFlowSession()
        session.update_material("旧内容甲。旧内容乙。")
        session.select_material()
        session.update_material("新内容一；新内容二")

        recognized = session.refresh_mock_recognition_from_material()
        rendered = "\n".join(
            point.title + point.explanation + point.source_excerpt
            for point in recognized
        )

        self.assertIn("新内容一", rendered)
        self.assertIn("新内容二", rendered)
        self.assertNotIn("旧内容", rendered)

    def test_candidates_come_only_from_selected_knowledge_point_ids(self):
        session = self.recognized_session()
        all_ids = tuple(point.id for point in session.recognized_knowledge_points)
        selected_ids = (all_ids[0], all_ids[2])

        session.select_knowledge_points(selected_ids)
        candidates = session.build_candidate_previews_from_selection()

        self.assertEqual(
            tuple(item.knowledge_point_id for item in candidates),
            selected_ids,
        )
        self.assertEqual(session.selected_knowledge_point_ids, selected_ids)
        self.assertEqual(session.candidate_count, len(selected_ids))

    def test_no_selection_has_exact_step_four_empty_copy(self):
        session = self.recognized_session()
        session.select_knowledge_points(())

        candidates = session.build_candidate_previews_from_selection()

        self.assertEqual(candidates, ())
        self.assertEqual(
            BEGINNER_STEP_COPY[
                BeginnerFlowStep.REVIEW_CANDIDATE_CARDS
            ].empty_state,
            BEGINNER_NO_SELECTED_KNOWLEDGE_COPY,
        )

    def test_selection_change_clears_old_candidates_review_and_later_previews(self):
        session = self.context_session()
        next_id = session.recognized_knowledge_points[1].id

        session.select_knowledge_points((next_id,))

        self.assertEqual(session.selected_knowledge_point_ids, (next_id,))
        self.assertEqual(session.candidate_card_previews, ())
        self.assertEqual(session.candidate_review_decisions, {})
        self.assertEqual(session.candidate_cards_state, BeginnerArtifactState.CLEARED)
        self.assertEqual(session.review_state, BeginnerArtifactState.CLEARED)
        self.assert_later_previews_cleared(session)

    def test_review_change_clears_later_previews(self):
        session = self.context_session()
        candidate_id = session.candidate_card_previews[0].id
        session.eligibility_state = BeginnerArtifactState.CURRENT
        session.write_plan_preview_state = BeginnerArtifactState.CURRENT
        session.final_confirmation_preview_state = BeginnerArtifactState.CURRENT

        session.set_candidate_review_decision(candidate_id, "needs_revision")

        self.assertEqual(
            session.candidate_review_decisions[candidate_id],
            "needs_revision",
        )
        self.assertEqual(session.review_state, BeginnerArtifactState.CURRENT)
        self.assert_later_previews_cleared(session)

    def test_material_change_clears_entire_context_chain(self):
        session = self.context_session()
        session.eligibility_state = BeginnerArtifactState.CURRENT
        session.write_plan_preview_state = BeginnerArtifactState.CURRENT
        session.final_confirmation_preview_state = BeginnerArtifactState.CURRENT

        session.update_material("替换后的材料")

        self.assertEqual(session.recognized_knowledge_points, ())
        self.assertEqual(session.selected_knowledge_point_ids, ())
        self.assertEqual(session.candidate_card_previews, ())
        self.assertEqual(session.candidate_review_decisions, {})
        self.assertEqual(session.recognition_state, BeginnerArtifactState.CLEARED)
        self.assertEqual(
            session.knowledge_selection_state,
            BeginnerArtifactState.CLEARED,
        )
        self.assertEqual(session.candidate_cards_state, BeginnerArtifactState.CLEARED)
        self.assertEqual(session.review_state, BeginnerArtifactState.CLEARED)
        self.assert_later_previews_cleared(session)

    def test_close_discards_material_recognition_selection_candidates_and_review(self):
        session = self.context_session()

        session.close()

        self.assertEqual(session.material_text, "")
        self.assertEqual(session.recognized_knowledge_points, ())
        self.assertEqual(session.selected_knowledge_point_ids, ())
        self.assertEqual(session.candidate_card_previews, ())
        self.assertEqual(session.candidate_review_decisions, {})

    def test_preview_repr_and_safe_dict_do_not_leak_material(self):
        secret = "不应出现在安全输出中的私密学习片段"
        session = BeginnerFlowSession()
        session.update_material(secret)
        session.select_material()
        session.mark_recognition_inspected()
        point_id = session.recognized_knowledge_points[0].id
        session.select_knowledge_points((point_id,))
        session.build_candidate_previews_from_selection()

        rendered = " ".join(
            (
                repr(session),
                repr(session.recognized_knowledge_points[0]),
                repr(session.candidate_card_previews[0]),
                json.dumps(session.to_safe_dict(), ensure_ascii=False),
            )
        )

        self.assertNotIn(secret, rendered)
        self.assertEqual(session.to_safe_dict()["recognized_knowledge_point_count"], 1)
        self.assertNotIn("recognized_knowledge_points", session.to_safe_dict())
        self.assertNotIn("candidate_card_previews", session.to_safe_dict())

    def test_step_copy_and_offline_recognition_notice_are_stable(self):
        self.assertEqual(
            BEGINNER_STEP_COPY[BeginnerFlowStep.INSPECT_RECOGNITION].title,
            "查看系统识别了什么",
        )
        self.assertEqual(
            BEGINNER_STEP_COPY[BeginnerFlowStep.CHOOSE_KNOWLEDGE_POINTS].title,
            "选择要制卡的知识点",
        )
        self.assertEqual(
            BEGINNER_STEP_COPY[BeginnerFlowStep.REVIEW_CANDIDATE_CARDS].title,
            "审核候选卡",
        )
        self.assertEqual(
            BEGINNER_GUIDE_STEP_NOTES[BeginnerFlowStep.INSPECT_RECOGNITION],
            "当前使用离线演练识别，不会联网，也不会调用 AI。",
        )
        self.assertEqual(COMPLETION_TITLE, "演练完成，尚未写入 Anki")

    def test_dialog_uses_session_context_methods(self):
        source = self.dialog_source()
        for call in (
            "self.session.mark_recognition_inspected",
            "self.session.select_knowledge_points",
            "self.session.build_candidate_previews_from_selection",
            "self.session.set_candidate_review_decision",
        ):
            self.assertIn(call, source)
        self.assertIn("这些候选卡来自你刚才选择的知识点。", source)

    def test_dialog_has_no_dangerous_action_copy(self):
        tree = ast.parse(self.dialog_source())
        string_literals = tuple(
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        )
        rendered = "\n".join(string_literals)
        self.assertIn("确认写入选中的卡片", rendered)

        for forbidden in (
            "保存",
            "应用",
            "执行",
            "添加到 Anki",
            "写入成功",
            "已写入",
            "已准备好写入",
            "可以直接写入",
            "Provider 设置",
            "API Key",
            "confirm write",
            "approve and write",
        ):
            self.assertNotIn(forbidden, rendered)

    def test_pr4_models_are_preview_types_not_formal_pipeline_outputs(self):
        self.assertEqual(
            BeginnerKnowledgePointPreview.__module__,
            "ankiforge_ai.ui.beginner_flow_models",
        )
        self.assertEqual(
            BeginnerCandidateCardPreview.__module__,
            "ankiforge_ai.ui.beginner_flow_models",
        )
        model_source = self.model_source()
        tree = ast.parse(model_source)
        imported_names = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertNotIn("GeneratedCard", imported_names)
        self.assertNotIn("WriteReadyPreviewItem", imported_names)

    @staticmethod
    def recognized_session():
        session = BeginnerFlowSession()
        session.update_material("概念甲。概念乙；概念丙")
        session.select_material()
        session.mark_recognition_inspected()
        return session

    def context_session(self):
        session = self.recognized_session()
        point_id = session.recognized_knowledge_points[0].id
        session.select_knowledge_points((point_id,))
        session.build_candidate_previews_from_selection()
        candidate_id = session.candidate_card_previews[0].id
        session.set_candidate_review_decision(candidate_id, "reviewed")
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
