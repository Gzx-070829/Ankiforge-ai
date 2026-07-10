import ast
import unittest
from pathlib import Path

from ankiforge_ai.ui.beginner_flow_models import (
    ADVANCED_WORKBENCH_WARNING,
    BEGINNER_GUIDE_SAFETY_COPY,
    BEGINNER_STEP_COPY,
    COMPLETION_TITLE,
    REVIEW_STATE_EXPLANATIONS,
)
from ankiforge_ai.ui.product_i18n import PRODUCT_COPY


class BeginnerModeEntryContractTests(unittest.TestCase):
    def test_pr1_model_remains_importable_and_complete(self):
        self.assertTrue(BEGINNER_STEP_COPY)
        self.assertEqual(COMPLETION_TITLE, "演练完成，尚未写入 Anki")

    def test_beginner_entry_and_advanced_entry_copy_exist(self):
        source = self.main_dialog_source()

        self.assertIn("CardMakerPanel", source)
        self.assertIn("product_i18n", source)
        self.assertEqual(PRODUCT_COPY["zh"]["subtitle"], "把学习材料变成 Anki 卡片")
        self.assertEqual(PRODUCT_COPY["zh"]["advanced_debug"], "高级 / 调试工具")
        self.assertEqual(PRODUCT_COPY["zh"]["open_legacy_flow"], "打开旧流程工具")
        self.assertEqual(PRODUCT_COPY["zh"]["open_debug_panel"], "打开旧调试面板")
        self.assertIn("可能包含真实 Anki 写入入口", ADVANCED_WORKBENCH_WARNING)

    def test_beginner_copy_states_network_is_explicit_click_only(self):
        entry_source = self.function_source("_build_ui")
        safety_copy = "\n".join(BEGINNER_GUIDE_SAFETY_COPY)
        product_source = self.card_maker_panel_source()

        self.assertNotIn("只读演练", entry_source)
        self.assertIn("generate_btn.clicked.connect", product_source)
        self.assertIn("BeginnerAICardDraftGenerator().generate", product_source)
        self.assertIn("打开窗口不会联网", safety_copy)
        self.assertIn("主动点击 AI 生成按钮", safety_copy)
        self.assertIn("二次确认才会创建 Anki note", safety_copy)

    def test_beginner_dialog_reads_core_copy_from_pr1_model(self):
        source = self.beginner_dialog_source()
        tree = ast.parse(source)
        imported_names = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and node.module == "beginner_flow_models"
            for alias in node.names
        }

        self.assertTrue(
            {
                "BEGINNER_FLOW_STEP_ORDER",
                "BEGINNER_GUIDE_SAFETY_COPY",
                "BEGINNER_GUIDE_STEP_NOTES",
                "BEGINNER_STEP_COPY",
                "COMPLETION_TITLE",
                "BeginnerFlowSession",
            }.issubset(imported_names)
        )
        self.assertIn("五步流程导航", source)
        self.assertIn("新手模式（默认只读，确认后可写入）", source)

    def test_beginner_buttons_do_not_imply_execution(self):
        zh = PRODUCT_COPY["zh"]

        self.assertEqual(zh["open_legacy_flow"], "打开旧流程工具")
        self.assertEqual(zh["choose_file"], "选择文件")
        self.assertEqual(zh["use_example"], "使用示例")
        self.assertEqual(zh["generate_cards"], "生成卡片")
        self.assertEqual(zh["edit"], "编辑")
        self.assertEqual(zh["keep"], "保留")
        self.assertEqual(zh["discard"], "丢弃")
        self.assertEqual(zh["check_duplicates"], "检查重复")
        self.assertEqual(zh["write_to_anki"], "写入 Anki")

    def test_legacy_workbench_is_lazy_and_hidden_by_default(self):
        init_source = self.function_source("__init__")
        build_ui_source = self.function_source("_build_ui")
        legacy_source = self.function_source("_build_legacy_workbench")

        self.assertNotIn("load_config", init_source)
        self.assertNotIn("load_config", build_ui_source)
        self.assertIn("setVisible(False)", build_ui_source)
        self.assertIn("load_config", legacy_source)

    def test_new_entry_handlers_are_isolated_from_legacy_runtime_paths(self):
        for handler_name in ("show_beginner_mode", "show_legacy_workbench"):
            handler_source = self.function_source(handler_name)
            with self.subTest(handler=handler_name):
                for forbidden in (
                    "add_to_anki",
                    "self.cards",
                    "provider",
                    "writer",
                    "mw.col",
                    "config",
                    "load_config",
                    "save_config",
                    "run_full_mock_pipeline_with_status",
                    "create_provider",
                ):
                    self.assertNotIn(forbidden, handler_source.lower())
        beginner_source = self.function_source("show_beginner_mode")
        self.assertIn("collection", beginner_source)
        self.assertNotIn("add_note", beginner_source)

    def test_new_dialog_has_no_runtime_or_network_dependencies(self):
        source = self.beginner_dialog_source()
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

        self.assertIn("anki_writer.minimal_write", imported_modules)
        for forbidden in (
            "config",
            "provider",
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

    def test_review_preview_states_still_do_not_mean_authorization(self):
        for state in (
            "approved",
            "eligible",
            "ready_preview",
            "ready_for_future_confirmation",
        ):
            self.assertIn("不代表写入授权", REVIEW_STATE_EXPLANATIONS[state])

    def test_beginner_copy_avoids_misleading_write_results(self):
        source = self.beginner_dialog_source()
        beginner_entry = self.function_source("_build_ui")
        combined = source + beginner_entry + COMPLETION_TITLE

        for forbidden in (
            "已准备好写入",
            "可以直接写入",
            "写入成功",
            "完成写入",
            "已写入",
        ):
            self.assertNotIn(forbidden, combined)

    @staticmethod
    def assigned_button_label(source, attribute_name):
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not (
                isinstance(target, ast.Attribute)
                and target.attr == attribute_name
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "QPushButton"
                and node.value.args
                and isinstance(node.value.args[0], ast.Constant)
            ):
                continue
            return node.value.args[0].value
        raise AssertionError(f"button {attribute_name!r} was not found")

    @staticmethod
    def literal_button_labels(source):
        tree = ast.parse(source)
        return {
            node.args[0].value
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "QPushButton"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        }

    def function_source(self, function_name):
        source = self.main_dialog_source()
        tree = ast.parse(source)
        dialog_class = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "MainDialog"
        )
        function = next(
            node
            for node in dialog_class.body
            if isinstance(node, ast.FunctionDef) and node.name == function_name
        )
        return ast.get_source_segment(source, function) or ""

    def main_dialog_source(self):
        return (self.repo_root() / "ankiforge_ai" / "ui" / "main_dialog.py").read_text(
            encoding="utf-8"
        )

    def beginner_dialog_source(self):
        return (
            self.repo_root() / "ankiforge_ai" / "ui" / "beginner_mode_dialog.py"
        ).read_text(encoding="utf-8")

    def card_maker_panel_source(self):
        return (
            self.repo_root() / "ankiforge_ai" / "ui" / "card_maker_panel.py"
        ).read_text(encoding="utf-8")

    @staticmethod
    def repo_root():
        return Path(__file__).parents[1]


if __name__ == "__main__":
    unittest.main()
