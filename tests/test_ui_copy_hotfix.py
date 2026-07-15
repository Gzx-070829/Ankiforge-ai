import ast
import unittest
from pathlib import Path

from ankiforge_ai.ui.product_i18n import PRODUCT_COPY
from ankiforge_ai.ui.product_styles import PRODUCT_DARK_STYLESHEET


class UICopyHotfixTests(unittest.TestCase):
    def test_ai_layout_keeps_preferences_in_flow_and_provider_in_dialog(self):
        source = self.panel_source()
        layout = self.function_source(source, "_build_ui")
        generation = self.function_source(source, "_build_generation_section")
        dialog = self.dialog_source()

        self.assertIn("self._build_create_panel()", layout)
        self.assertNotIn("self._build_provider_section()", layout)
        self.assertLess(
            dialog.index("self.provider_combo"),
            dialog.index("self.model_input"),
        )
        self.assertLess(
            dialog.index("self.model_input"),
            dialog.index("self.api_key_input"),
        )
        self.assertIn("self.card_mode_combo", generation)
        self.assertIn("self._make_form_row", dialog)
        self.assertNotIn("provider_model_row", dialog)

    def test_generation_details_stay_collapsed_and_primary_action_is_full_width(self):
        source = self.panel_source()
        generation = self.function_source(source, "_build_generation_section")
        create_panel = self.function_source(source, "_build_create_panel")

        self.assertIn("self.generation_settings_container.setVisible(False)", generation)
        self.assertIn("layout.addWidget(self.generate_btn)", create_panel)
        self.assertNotIn("self.generate_btn.setFixedSize", create_panel)

    def test_empty_cards_do_not_show_review_instruction(self):
        builder = self.function_source(self.panel_source(), "_build_cards_section")
        render = self.function_source(self.panel_source(), "_render_cards")

        self.assertIn("self.review_required_label.setVisible(False)", builder)
        self.assertIn("self.review_required_label.setVisible(False)", render)
        self.assertIn("self.review_required_label.setVisible(True)", render)

    def test_quality_ui_uses_plain_status_not_numeric_score(self):
        render = self.function_source(self.panel_source(), "_render_cards")

        self.assertNotIn('self.t("quality_score"', render)
        self.assertNotIn("quality.quality_score", render)
        self.assertIn('self.t(f"quality_status_{quality.severity}")', render)

    def test_chinese_main_copy_is_short_and_product_facing(self):
        zh = PRODUCT_COPY["zh"]

        self.assertEqual(
            zh["material_help"],
            "粘贴材料，或导入 Markdown / TXT / DOCX。",
        )
        self.assertEqual(zh["material_placeholder"], "粘贴学习材料，或拖入文件")
        self.assertEqual(
            zh["first_run_guidance"],
            "第一次使用？可以先试试示例材料，并写入测试牌组。",
        )
        self.assertEqual(
            zh["review_required"],
            "请检查卡片内容，保留需要写入 Anki 的卡片。",
        )
        self.assertEqual(
            zh["write_summary_empty"],
            "完成审核和重复检查后，将显示写入摘要。",
        )
        self.assertEqual(zh["duplicates_clear"], "已检查")
        self.assertEqual(zh["quality_generic_front"], "问题可能太泛")
        self.assertEqual(zh["quality_multi_point_card"], "可能包含多个知识点")
        self.assertEqual(zh["advanced_settings"], "更多设置")

    def test_advanced_entry_is_quiet_and_has_no_debug_copy(self):
        rendered = "\n".join(
            value
            for catalog in PRODUCT_COPY.values()
            for value in catalog.values()
        ).casefold()

        self.assertEqual(PRODUCT_COPY["zh"]["advanced_debug"], "高级")
        self.assertEqual(PRODUCT_COPY["en"]["advanced_debug"], "Advanced")
        self.assertNotIn("调试工具", rendered)
        self.assertNotIn("debug tools", rendered)
        build_ui = self.function_source(self.main_source(), "_build_ui")
        self.assertNotIn("advanced_toggle_btn", build_ui)
        self.assertNotIn("advanced_tools_panel", build_ui)
        self.assertIn("self.help_btn", build_ui)

    def test_bilingual_catalog_remains_complete(self):
        self.assertEqual(set(PRODUCT_COPY["zh"]), set(PRODUCT_COPY["en"]))

    def test_primary_disabled_button_looks_inactive_without_looking_broken(self):
        disabled_block = PRODUCT_DARK_STYLESHEET.split(
            'QWidget#CardMakerPanel QPushButton[role="primary"]:disabled {'
        )[1].split("}", 1)[0]

        self.assertIn("background-color: #292347", disabled_block)
        self.assertIn("color: #8F83C7", disabled_block)
        self.assertIn("border-color: #3C3266", disabled_block)

    @staticmethod
    def function_source(source, name):
        tree = ast.parse(source)
        node = next(
            item
            for item in ast.walk(tree)
            if isinstance(item, ast.FunctionDef) and item.name == name
        )
        return ast.get_source_segment(source, node) or ""

    @staticmethod
    def root():
        return Path(__file__).parents[1]

    def panel_source(self):
        return (
            self.root() / "ankiforge_ai" / "ui" / "card_maker_panel.py"
        ).read_text(encoding="utf-8")

    def main_source(self):
        return (
            self.root() / "ankiforge_ai" / "ui" / "main_dialog.py"
        ).read_text(encoding="utf-8")

    def dialog_source(self):
        return (
            self.root() / "ankiforge_ai" / "ui" / "ai_settings_dialog.py"
        ).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
