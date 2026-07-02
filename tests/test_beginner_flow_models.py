import ast
import json
import unittest
from pathlib import Path

from ankiforge_ai.ui.beginner_flow_models import (
    ADVANCED_WORKBENCH_WARNING,
    BEGINNER_FLOW_STEP_ORDER,
    BEGINNER_GUIDE_SAFETY_COPY,
    BEGINNER_SAFETY_STATUS_COPY,
    BEGINNER_STEP_COPY,
    BEGINNER_TERM_COPY,
    COMPLETION_FACTS,
    COMPLETION_SUMMARY,
    COMPLETION_TITLE,
    REVIEW_STATE_EXPLANATIONS,
    BeginnerArtifactState,
    BeginnerFlowSession,
    BeginnerFlowStep,
)


class BeginnerFlowModelTests(unittest.TestCase):
    def test_default_session_is_offline_read_only_and_non_persistent(self):
        session = BeginnerFlowSession()

        self.assertEqual(session.current_step, BeginnerFlowStep.SELECT_MATERIAL)
        self.assertTrue(session.is_offline_read_only)
        self.assertFalse(session.network_allowed)
        self.assertFalse(session.provider_call_allowed)
        self.assertFalse(session.api_key_read_allowed)
        self.assertFalse(session.duplicate_check_allowed)
        self.assertTrue(session.anki_collection_access_allowed)
        self.assertTrue(session.anki_collection_read_allowed)
        self.assertFalse(session.anki_collection_write_allowed)
        self.assertFalse(session.anki_write_allowed)
        self.assertFalse(session.persistent)
        self.assertEqual(session.material_text, "")
        self.assertEqual(session.material_char_count, 0)

    def test_step_order_is_stable(self):
        self.assertEqual(
            tuple(step.value for step in BEGINNER_FLOW_STEP_ORDER),
            (
                "select_material",
                "inspect_recognition",
                "choose_knowledge_points",
                "review_candidate_cards",
                "check_before_write",
                "completed_no_write",
            ),
        )

    def test_happy_path_moves_through_every_step_without_write_capability(self):
        session = BeginnerFlowSession()
        visited = [session.current_step]

        session.update_material("机器学习笔记")
        session.select_material()
        visited.append(session.current_step)
        session.mark_recognition_inspected()
        visited.append(session.current_step)
        session.change_knowledge_selection(2)
        visited.append(session.current_step)
        session.change_candidate_cards(2)
        self.assertEqual(
            session.current_step,
            BeginnerFlowStep.REVIEW_CANDIDATE_CARDS,
        )
        session.change_review_decision(2)
        visited.append(session.current_step)
        session.mark_prewrite_check_inspected()
        visited.append(session.current_step)

        self.assertEqual(tuple(visited), BEGINNER_FLOW_STEP_ORDER)
        self.assertFalse(session.duplicate_check_allowed)
        self.assertTrue(session.anki_collection_read_allowed)
        self.assertFalse(session.anki_collection_write_allowed)
        self.assertFalse(session.anki_write_allowed)

    def test_every_step_has_plain_chinese_copy(self):
        self.assertEqual(set(BEGINNER_STEP_COPY), set(BEGINNER_FLOW_STEP_ORDER))
        for copy in BEGINNER_STEP_COPY.values():
            with self.subTest(title=copy.title):
                self.assertTrue(copy.title.strip())
                self.assertTrue(copy.description.strip())
                self.assertTrue(copy.primary_action.strip())
                self.assertTrue(copy.empty_state.strip())

    def test_safety_status_copy_is_complete(self):
        combined = "\n".join(BEGINNER_SAFETY_STATUS_COPY)
        for expected in (
            "当前为只读演练",
            "打开窗口不会联网",
            "主动点击 AI 生成按钮",
            "API key 只用于当前窗口，不会保存",
            "不会执行 duplicate check",
            "只读访问 Anki collection",
            "不会修改 Anki collection",
            "不会写入 Anki",
            "关闭后本次演练丢弃",
        ):
            self.assertIn(expected, combined)

        self.assertEqual(
            BEGINNER_GUIDE_SAFETY_COPY,
            (
                "当前是只读演练",
                "打开窗口不会联网",
                "只有主动点击 AI 生成按钮才会联网",
                "API key 只用于当前窗口",
                "只有点击读取按钮才会只读访问 Anki collection",
                "不会修改 Anki collection",
                "不会写入 Anki",
                "关闭后丢弃本次内容",
            ),
        )

    def test_completion_copy_is_safe_and_exact(self):
        copy = "\n".join((COMPLETION_TITLE, COMPLETION_SUMMARY, *COMPLETION_FACTS))

        self.assertEqual(COMPLETION_TITLE, "演练完成，尚未写入 Anki")
        for forbidden in (
            "完成写入",
            "写入成功",
            "已写入",
            "已准备好写入",
            "可以直接写入",
        ):
            self.assertNotIn(forbidden, copy)
        for expected in (
            "未创建 note",
            "未修改卡组",
            "未保存本次演练",
            "未修改 Anki collection",
            "未写入 Anki",
        ):
            self.assertIn(expected, COMPLETION_FACTS)

    def test_review_states_never_imply_authorization(self):
        self.assertEqual(
            set(REVIEW_STATE_EXPLANATIONS),
            {
                "approved",
                "eligible",
                "ready_preview",
                "ready_for_future_confirmation",
            },
        )
        for state, explanation in REVIEW_STATE_EXPLANATIONS.items():
            with self.subTest(state=state):
                self.assertIn("不代表写入授权", explanation)

    def test_material_change_clears_all_downstream_state(self):
        session = self.completed_session()

        session.update_material("更新后的材料")

        self.assertEqual(session.current_step, BeginnerFlowStep.SELECT_MATERIAL)
        self.assertEqual(session.recognition_state, BeginnerArtifactState.CLEARED)
        self.assert_downstream_cleared(session)
        self.assertEqual(session.selected_knowledge_point_count, 0)
        self.assertEqual(session.candidate_count, 0)
        self.assertEqual(session.reviewed_candidate_count, 0)
        self.assertEqual(session.last_clearing_reason, "material_changed")

    def test_material_text_count_and_preview_are_in_memory(self):
        session = BeginnerFlowSession()
        material = "第一段\n" + "知识" * 200

        session.update_material(material)

        self.assertEqual(session.material_text, material)
        self.assertEqual(session.material_char_count, len(material))
        self.assertEqual(session.material_preview(20)[-3:], "...")
        self.assertLessEqual(len(session.material_preview(20)), 20)
        self.assertEqual(session.material_preview(len(material)), material)

    def test_clear_material_discards_text_and_clears_downstream(self):
        session = self.completed_session()

        session.clear_material()

        self.assertEqual(session.material_text, "")
        self.assertEqual(session.material_char_count, 0)
        self.assertEqual(session.current_step, BeginnerFlowStep.SELECT_MATERIAL)
        self.assertEqual(session.recognition_state, BeginnerArtifactState.CLEARED)
        self.assert_downstream_cleared(session)
        self.assertEqual(session.last_clearing_reason, "material_cleared")

    def test_knowledge_selection_change_clears_candidates_and_downstream(self):
        session = self.completed_session()

        session.change_knowledge_selection(1)

        self.assertEqual(
            session.knowledge_selection_state,
            BeginnerArtifactState.CURRENT,
        )
        self.assertEqual(session.candidate_cards_state, BeginnerArtifactState.CLEARED)
        self.assertEqual(session.review_state, BeginnerArtifactState.CLEARED)
        self.assert_prewrite_cleared(session)
        self.assertEqual(session.last_clearing_reason, "knowledge_selection_changed")

    def test_candidate_change_clears_review_and_downstream(self):
        session = self.completed_session()

        session.change_candidate_cards(1)

        self.assertEqual(session.candidate_cards_state, BeginnerArtifactState.CURRENT)
        self.assertEqual(session.review_state, BeginnerArtifactState.CLEARED)
        self.assert_prewrite_cleared(session)
        self.assertEqual(session.last_clearing_reason, "candidate_cards_changed")

    def test_review_change_clears_all_prewrite_previews(self):
        session = self.completed_session()

        session.change_review_decision(1)

        self.assertEqual(session.review_state, BeginnerArtifactState.CURRENT)
        self.assert_prewrite_cleared(session)
        self.assertEqual(session.last_clearing_reason, "review_decision_changed")

    def test_back_navigation_clears_downstream_results(self):
        session = self.completed_session()

        session.go_back(BeginnerFlowStep.CHOOSE_KNOWLEDGE_POINTS)

        self.assertEqual(
            session.current_step,
            BeginnerFlowStep.CHOOSE_KNOWLEDGE_POINTS,
        )
        self.assertEqual(session.candidate_cards_state, BeginnerArtifactState.CLEARED)
        self.assertEqual(session.review_state, BeginnerArtifactState.CLEARED)
        self.assert_prewrite_cleared(session)
        self.assertEqual(session.last_clearing_reason, "navigation_back")

    def test_close_discards_all_state_and_prevents_reuse(self):
        session = self.completed_session()

        session.close()

        self.assertTrue(session.closed)
        self.assertEqual(session.current_step, BeginnerFlowStep.SELECT_MATERIAL)
        self.assertEqual(session.material_revision, 0)
        self.assertEqual(session.material_text, "")
        self.assertEqual(session.material_char_count, 0)
        self.assertEqual(session.selected_knowledge_point_count, 0)
        self.assertEqual(session.candidate_count, 0)
        self.assertEqual(session.reviewed_candidate_count, 0)
        for name in self.artifact_field_names():
            self.assertEqual(getattr(session, name), BeginnerArtifactState.EMPTY)
        self.assertEqual(session.last_clearing_reason, "session_closed")
        with self.assertRaisesRegex(RuntimeError, "cannot be reused"):
            session.select_material()

    def test_term_mapping_is_complete(self):
        self.assertEqual(
            dict(BEGINNER_TERM_COPY),
            {
                "Human Review": "人工审核",
                "Write Eligibility": "是否满足未来写入条件",
                "Write Plan": "未来写入方式预览",
                "Final confirmation contract": "真正写入前还需确认什么",
                "Provider draft": "AI 服务草稿",
                "GeneratedCard": "正式待写入卡片",
                "WriteReadyPreviewItem": "写入就绪对象",
            },
        )

    def test_advanced_workbench_warning_is_explicit_without_pipeline_claims(self):
        self.assertEqual(
            ADVANCED_WORKBENCH_WARNING,
            "旧版工作台（高级）包含开发/调试入口，可能包含真实 Anki 写入入口。"
            "请确认你理解风险后再进入。",
        )
        self.assertNotIn("新 pipeline", ADVANCED_WORKBENCH_WARNING)

    def test_session_shape_has_no_sensitive_or_runtime_objects(self):
        field_names = set(BeginnerFlowSession.public_field_names())
        self.assertIn("material_text", field_names)
        for forbidden in (
            "api_key",
            "provider_config",
            "write_authorization",
            "final_confirmation",
            "anki_collection",
            "writer",
            "duplicate_checker",
            "persisted_file_path",
            "saved_draft_path",
            "source_text",
            "candidate_front",
            "candidate_back",
            "candidate_source",
            "review_note",
        ):
            self.assertNotIn(forbidden, field_names)

    def test_repr_and_safe_dict_cannot_leak_unstored_user_content(self):
        session = self.completed_session()
        secrets = (
            "private source paragraph",
            "private candidate front",
            "private candidate back",
            "private reviewer note",
        )
        session.update_material(secrets[0])

        rendered = repr(session) + json.dumps(session.to_safe_dict())

        for secret in secrets:
            self.assertNotIn(secret, rendered)
        self.assertTrue(session.to_safe_dict()["material_present"])
        self.assertEqual(
            session.to_safe_dict()["material_char_count"],
            len(secrets[0]),
        )
        self.assertNotIn("material_text", session.to_safe_dict())

    def test_module_has_no_forbidden_runtime_imports_or_calls(self):
        path = self.repo_root() / "ankiforge_ai" / "ui" / "beginner_flow_models.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_modules = {
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        imported_modules.update(
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        called_names = {
            node.func.id
            if isinstance(node.func, ast.Name)
            else node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, (ast.Name, ast.Attribute))
        }

        for forbidden_module in (
            "PyQt",
            "PySide",
            "aqt",
            "anki",
            "provider",
            "config",
            "secret_store",
            "writer",
            "controlled_write_bridge",
            "requests",
            "httpx",
            "aiohttp",
            "urllib",
            "socket",
        ):
            self.assertFalse(
                any(forbidden_module in module for module in imported_modules),
                forbidden_module,
            )
        for forbidden_call in (
            "add_note",
            "add_to_anki",
            "write_to_anki",
            "create_provider",
            "add_cards_to_deck",
        ):
            self.assertNotIn(forbidden_call, called_names)

    @staticmethod
    def completed_session():
        session = BeginnerFlowSession()
        session.update_material("机器学习笔记")
        session.select_material()
        session.mark_recognition_inspected()
        session.change_knowledge_selection(2)
        session.change_candidate_cards(2)
        session.change_review_decision(2)
        session.mark_prewrite_check_inspected()
        return session

    def assert_downstream_cleared(self, session):
        self.assertEqual(
            session.knowledge_selection_state,
            BeginnerArtifactState.CLEARED,
        )
        self.assertEqual(session.candidate_cards_state, BeginnerArtifactState.CLEARED)
        self.assertEqual(session.review_state, BeginnerArtifactState.CLEARED)
        self.assert_prewrite_cleared(session)

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
    def artifact_field_names():
        return (
            "recognition_state",
            "knowledge_selection_state",
            "candidate_cards_state",
            "review_state",
            "eligibility_state",
            "write_plan_preview_state",
            "final_confirmation_preview_state",
        )

    @staticmethod
    def repo_root():
        return Path(__file__).parents[1]


if __name__ == "__main__":
    unittest.main()
