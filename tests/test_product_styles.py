import ast
import unittest
from pathlib import Path

from ankiforge_ai.ui.product_styles import PRODUCT_DARK_STYLESHEET


class ProductStyleTests(unittest.TestCase):
    def test_dark_palette_and_scoped_panels_are_defined(self):
        for color in (
            "#202124",
            "#2B2D30",
            "#1F2023",
            "#3F4248",
            "#F4F4F5",
            "#9CA3AF",
            "#6B7280",
            "#3B82F6",
            "#2563EB",
            "#3A3D42",
            "#7A7F87",
        ):
            self.assertIn(color, PRODUCT_DARK_STYLESHEET)
        self.assertIn("QDialog#AnkiForgeMainDialog", PRODUCT_DARK_STYLESHEET)
        self.assertIn("QWidget#CardMakerPanel", PRODUCT_DARK_STYLESHEET)
        self.assertIn('QGroupBox[productPanel="true"]', PRODUCT_DARK_STYLESHEET)

    def test_inputs_share_one_focus_and_shape_language(self):
        for selector in ("QTextEdit", "QLineEdit", "QComboBox", "QSpinBox"):
            self.assertIn(selector, PRODUCT_DARK_STYLESHEET)
        self.assertIn("border-radius: 6px", PRODUCT_DARK_STYLESHEET)
        self.assertIn("border: 1px solid #3B82F6", PRODUCT_DARK_STYLESHEET)

    def test_generate_and_write_buttons_share_primary_role(self):
        source = self.panel_source()
        generate = self.function_source(source, "_build_ai_section")
        write = self.function_source(source, "_build_write_section")

        self.assertIn('self.generate_btn.setProperty("role", "primary")', generate)
        self.assertIn('self.write_btn.setProperty("role", "primary")', write)
        self.assertIn('QPushButton[role="primary"]', PRODUCT_DARK_STYLESHEET)
        self.assertIn('QPushButton[role="primary"]:disabled', PRODUCT_DARK_STYLESHEET)

    def test_secondary_and_subtle_actions_do_not_compete(self):
        source = self.panel_source()

        self.assertIn('self.choose_markdown_btn.setProperty("role", "secondary")', source)
        self.assertIn('self.example_btn.setProperty("role", "secondary")', source)
        self.assertIn('self.duplicate_btn.setProperty("role", "secondary")', source)
        self.assertIn('self.ai_advanced_btn.setProperty("role", "subtle")', source)
        self.assertIn("AdvancedDebugLink", self.main_source())

    def test_empty_state_is_centered_without_changing_two_column_layout(self):
        source = self.panel_source()
        cards = self.function_source(source, "_build_cards_section")
        builder = self.function_source(source, "_build_ui")

        self.assertIn("CardsEmptyState", cards)
        self.assertEqual(cards.count("Qt.AlignmentFlag.AlignCenter"), 2)
        self.assertIn("columns = QHBoxLayout()", builder)
        self.assertIn("columns.setSpacing(20)", builder)

    def test_styles_module_has_no_business_runtime_dependencies(self):
        source = self.style_source()
        tree = ast.parse(source)

        self.assertFalse(any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in tree.body))
        for forbidden in (
            "provider",
            "writer",
            "duplicate",
            "collection",
            "api_key",
            "config",
        ):
            self.assertNotIn(forbidden, source.casefold())

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

    def style_source(self):
        return (
            self.root() / "ankiforge_ai" / "ui" / "product_styles.py"
        ).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
