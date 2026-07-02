import ast
import unittest
from pathlib import Path

from ankiforge_ai.ui.beginner_flow_models import (
    BEGINNER_EXAMPLE_MATERIAL,
    BEGINNER_MATERIAL_EMPTY_HINT,
    COMPLETION_TITLE,
    BeginnerArtifactState,
    BeginnerFlowSession,
)


class BeginnerExampleMaterialTests(unittest.TestCase):
    def test_example_material_is_non_empty_built_in_learning_text(self):
        self.assertTrue(BEGINNER_EXAMPLE_MATERIAL.strip())
        for topic in ("过拟合", "正则化", "交叉验证", "早停"):
            self.assertIn(topic, BEGINNER_EXAMPLE_MATERIAL)

    def test_loading_example_updates_only_disposable_session(self):
        session = BeginnerFlowSession()

        session.load_example_material()

        self.assertEqual(session.material_text, BEGINNER_EXAMPLE_MATERIAL)
        self.assertFalse(session.persistent)
        self.assertFalse(session.network_allowed)
        self.assertTrue(session.anki_collection_read_allowed)
        self.assertFalse(session.anki_collection_write_allowed)
        self.assertFalse(session.anki_write_allowed)

    def test_loading_example_clears_all_downstream_state(self):
        session = self.populated_session()

        session.load_example_material()

        self.assertEqual(session.material_text, BEGINNER_EXAMPLE_MATERIAL)
        self.assertEqual(session.recognized_knowledge_points, ())
        self.assertEqual(session.selected_knowledge_point_ids, ())
        self.assertEqual(session.candidate_card_previews, ())
        self.assertEqual(session.candidate_review_decisions, {})
        for name in self.downstream_state_names():
            self.assertEqual(getattr(session, name), BeginnerArtifactState.CLEARED)
        self.assertEqual(session.last_clearing_reason, "material_changed")

    def test_reloading_same_example_also_clears_downstream_state(self):
        session = BeginnerFlowSession()
        session.load_example_material()
        session.select_material()
        session.mark_recognition_inspected()
        point_id = session.recognized_knowledge_points[0].id
        session.select_knowledge_points((point_id,))
        session.build_candidate_previews_from_selection()

        session.load_example_material()

        self.assertEqual(session.material_text, BEGINNER_EXAMPLE_MATERIAL)
        for name in self.downstream_state_names():
            self.assertEqual(getattr(session, name), BeginnerArtifactState.CLEARED)
        self.assertEqual(session.last_clearing_reason, "example_material_reloaded")

    def test_clear_removes_example_and_all_downstream_state(self):
        session = BeginnerFlowSession()
        session.load_example_material()
        session.select_material()
        session.mark_recognition_inspected()
        point_id = session.recognized_knowledge_points[0].id
        session.select_knowledge_points((point_id,))
        session.build_candidate_previews_from_selection()

        session.clear_material()

        self.assertEqual(session.material_text, "")
        self.assertNotIn(BEGINNER_EXAMPLE_MATERIAL, repr(session))
        for name in self.downstream_state_names():
            self.assertEqual(getattr(session, name), BeginnerArtifactState.CLEARED)
        self.assertEqual(session.last_clearing_reason, "material_cleared")

    def test_closed_and_new_sessions_do_not_retain_example(self):
        session = BeginnerFlowSession()
        session.load_example_material()

        session.close()
        new_session = BeginnerFlowSession()

        self.assertEqual(session.material_text, "")
        self.assertEqual(new_session.material_text, "")

    def test_first_run_copy_and_completion_are_stable(self):
        self.assertIn("粘贴自己的学习材料", BEGINNER_MATERIAL_EMPTY_HINT)
        self.assertIn("使用示例材料", BEGINNER_MATERIAL_EMPTY_HINT)
        self.assertEqual(COMPLETION_TITLE, "演练完成，尚未写入 Anki")

    def test_dialog_example_handler_is_session_only(self):
        source = self.dialog_source()
        tree = ast.parse(source)
        handler = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == "_use_example_material"
        )
        rendered = ast.unparse(handler)

        self.assertIn("self.session.load_example_material()", rendered)
        self.assertIn("self.material_input.setPlainText", rendered)
        for forbidden in (
            "config",
            "provider",
            "api_key",
            "collection",
            "writer",
            "add_note",
            "requests",
            "httpx",
            "urllib",
        ):
            self.assertNotIn(forbidden, rendered.lower())

    def test_new_surface_copy_has_no_dangerous_action_language(self):
        surface_copy = "\n".join(
            (
                "使用示例材料",
                BEGINNER_MATERIAL_EMPTY_HINT,
            )
        )
        for forbidden in (
            "保存",
            "应用",
            "执行",
            "确认写入",
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
            self.assertNotIn(forbidden, surface_copy)

    @staticmethod
    def populated_session():
        session = BeginnerFlowSession()
        session.update_material("旧材料甲。旧材料乙。")
        session.select_material()
        session.mark_recognition_inspected()
        point_id = session.recognized_knowledge_points[0].id
        session.select_knowledge_points((point_id,))
        session.build_candidate_previews_from_selection()
        candidate_id = session.candidate_card_previews[0].id
        session.set_candidate_review_decision(candidate_id, "looks_good")
        session.eligibility_state = BeginnerArtifactState.CURRENT
        session.write_plan_preview_state = BeginnerArtifactState.CURRENT
        session.final_confirmation_preview_state = BeginnerArtifactState.CURRENT
        return session

    @staticmethod
    def downstream_state_names():
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
    def dialog_source():
        return (
            Path(__file__).parents[1]
            / "ankiforge_ai"
            / "ui"
            / "beginner_mode_dialog.py"
        ).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
