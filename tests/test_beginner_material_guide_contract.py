import ast
import unittest
from pathlib import Path

from ankiforge_ai.ui.beginner_flow_models import (
    BEGINNER_FLOW_STEP_ORDER,
    BEGINNER_GUIDE_SAFETY_COPY,
    BEGINNER_STEP_COPY,
    COMPLETION_TITLE,
    REVIEW_STATE_EXPLANATIONS,
    BeginnerFlowSession,
    BeginnerFlowStep,
)


class BeginnerMaterialGuideContractTests(unittest.TestCase):
    def test_surface_step_titles_are_exact(self):
        titles = tuple(
            BEGINNER_STEP_COPY[step].title
            for step in BEGINNER_FLOW_STEP_ORDER
            if step is not BeginnerFlowStep.COMPLETED_NO_WRITE
        )

        self.assertEqual(
            titles,
            (
                "选择学习材料",
                "查看系统识别了什么",
                "选择要制卡的知识点",
                "审核候选卡",
                "查看距离真正写入还缺哪些条件",
            ),
        )

    def test_guide_navigation_does_not_create_pipeline_artifacts(self):
        session = BeginnerFlowSession()
        session.update_material("线性代数学习材料")

        for _ in range(5):
            session.advance_guide()

        self.assertEqual(
            session.current_step,
            BeginnerFlowStep.COMPLETED_NO_WRITE,
        )
        for name in self.artifact_field_names():
            self.assertNotEqual(getattr(session, name).value, "current")
        self.assertFalse(session.anki_write_allowed)

    def test_material_change_after_navigation_returns_to_first_step(self):
        session = BeginnerFlowSession()
        session.update_material("旧材料")
        session.advance_guide()
        session.advance_guide()

        session.update_material("新材料")

        self.assertEqual(session.current_step, BeginnerFlowStep.SELECT_MATERIAL)
        self.assertEqual(session.material_text, "新材料")
        self.assertEqual(session.last_clearing_reason, "material_changed")
        for name in self.artifact_field_names()[1:]:
            self.assertEqual(getattr(session, name).value, "cleared")

    def test_dialog_contains_guide_regions_and_disposable_session(self):
        source = self.dialog_source()

        for expected in (
            "欢迎使用新手模式",
            "离线只读安全状态",
            "五步流程导航",
            "当前步骤说明",
            "材料输入页",
            "材料预览",
            "BeginnerFlowSession()",
            "self.session.update_material",
            "self.session.clear_material",
            "self.session.close",
        ):
            self.assertIn(expected, source)

    def test_dialog_does_not_import_pipeline_or_side_effect_dependencies(self):
        source = self.dialog_source()
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

        for forbidden in (
            "config",
            "provider",
            "pipeline",
            "writer",
            "collection",
            "requests",
            "httpx",
            "aiohttp",
            "urllib",
            "socket",
        ):
            self.assertFalse(
                any(forbidden in module.lower() for module in imported_modules),
                forbidden,
            )

    def test_guide_buttons_are_navigation_only(self):
        source = self.dialog_source()
        tree = ast.parse(source)
        labels = {
            node.args[0].value
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "QPushButton"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        }

        self.assertEqual(labels, {"上一步", "继续", "清空材料", "关闭"})
        for label in labels:
            for forbidden in ("保存", "应用", "执行", "确认", "写入"):
                self.assertNotIn(forbidden, label)

    def test_safe_copy_and_completion_remain_explicit(self):
        self.assertEqual(COMPLETION_TITLE, "演练完成，尚未写入 Anki")
        self.assertEqual(
            BEGINNER_GUIDE_SAFETY_COPY,
            (
                "当前是离线只读演练",
                "不会联网",
                "不会调用 AI",
                "不会写入 Anki",
                "关闭后丢弃本次内容",
            ),
        )
        for explanation in REVIEW_STATE_EXPLANATIONS.values():
            self.assertIn("不代表写入授权", explanation)

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

    def dialog_source(self):
        return (
            self.repo_root() / "ankiforge_ai" / "ui" / "beginner_mode_dialog.py"
        ).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
