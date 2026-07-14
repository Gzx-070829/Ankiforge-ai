import ast
import unittest
from pathlib import Path

from ankiforge_ai.ui.product_styles import PRODUCT_DARK_STYLESHEET


class ProductStyleTests(unittest.TestCase):
    def test_dark_palette_and_scoped_panels_are_defined(self):
        for color in (
            "#0D1117",
            "#111827",
            "#161B22",
            "#0F141B",
            "#1C2430",
            "#263241",
            "#334155",
            "#F8FAFC",
            "#CBD5E1",
            "#7D8EA3",
            "#7C5CFF",
            "#8B73FF",
        ):
            self.assertIn(color, PRODUCT_DARK_STYLESHEET)
        self.assertIn("QDialog#AnkiForgeMainDialog", PRODUCT_DARK_STYLESHEET)
        self.assertIn("QWidget#CardMakerPanel", PRODUCT_DARK_STYLESHEET)
        self.assertIn('QFrame[workflowPanel="true"]', PRODUCT_DARK_STYLESHEET)
        self.assertNotIn('QGroupBox[productPanel="true"]', PRODUCT_DARK_STYLESHEET)

    def test_inputs_share_one_focus_and_shape_language(self):
        for selector in ("QTextEdit", "QLineEdit", "QComboBox", "QSpinBox"):
            self.assertIn(selector, PRODUCT_DARK_STYLESHEET)
        self.assertIn("border-radius: 10px", PRODUCT_DARK_STYLESHEET)
        self.assertIn("border: 1px solid #7C5CFF", PRODUCT_DARK_STYLESHEET)

    def test_generate_and_write_buttons_share_primary_role(self):
        source = self.panel_source()
        generate = self.function_source(source, "_build_create_panel")
        write = self.function_source(source, "_build_write_section")
        configure = self.function_source(source, "_configure_primary_button")

        self.assertIn('button.setProperty("role", "primary")', configure)
        self.assertIn("self._configure_primary_button(self.generate_btn)", generate)
        self.assertIn("self._configure_primary_button(self.write_btn)", write)
        self.assertIn('QPushButton[role="primary"]', PRODUCT_DARK_STYLESHEET)
        self.assertIn('QPushButton[role="primary"]:disabled', PRODUCT_DARK_STYLESHEET)

    def test_secondary_and_subtle_actions_do_not_compete(self):
        source = self.panel_source()

        configure = self.function_source(source, "_configure_secondary_button")
        self.assertIn('button.setProperty("role", "secondary")', configure)
        self.assertIn("self._configure_secondary_button(self.choose_file_btn)", source)
        self.assertIn("self._configure_secondary_button(self.example_btn)", source)
        self.assertIn("self._configure_secondary_button(self.duplicate_btn)", source)
        self.assertIn(
            'self.generation_settings_btn.setProperty("role", "subtle")',
            source,
        )
        self.assertNotIn("self.ai_advanced_btn", source)
        self.assertIn("AdvancedDebugLink", self.main_source())

    def test_empty_state_is_centered_without_changing_two_column_layout(self):
        source = self.panel_source()
        cards = self.function_source(source, "_build_cards_section")
        builder = self.function_source(source, "_build_ui")

        self.assertIn("CardsEmptyState", cards)
        self.assertEqual(cards.count("Qt.AlignmentFlag.AlignCenter"), 3)
        self.assertIn("columns = QHBoxLayout()", builder)
        self.assertIn("columns.setSpacing(COLUMN_GAP)", builder)
        self.assertIn("columns.addWidget(left, 45)", builder)
        self.assertIn("columns.addWidget(right, 55)", builder)

    def test_sections_use_spacing_and_only_elevate_write_footer(self):
        source = self.panel_source()
        factory = self.function_source(source, "_make_section")

        self.assertIn("title = QLabel", factory)
        self.assertIn('title.setProperty("role", "sectionTitle")', factory)
        self.assertIn("card = QFrame()", factory)
        self.assertIn('card.setProperty("sectionCard", elevated)', factory)
        self.assertIn('card.setProperty("sectionBody", not elevated)', factory)
        self.assertIn("section_layout.setSpacing(SPACING_SM)", factory)
        self.assertNotIn("QGroupBox", factory)
        for builder_name in (
            "_build_material_section",
            "_build_generation_section",
            "_build_cards_section",
            "_build_write_section",
        ):
            builder = self.function_source(source, builder_name)
            self.assertIn("self._make_section", builder)
        write = self.function_source(source, "_build_write_section")
        self.assertIn('elevated=True', write)
        self.assertIn('setObjectName("WriteFooter")', write)

    def test_ai_fields_live_in_the_settings_dialog(self):
        source = self.panel_source()
        generation = self.function_source(source, "_build_generation_section")
        dialog = self.dialog_source()

        self.assertIn('self._make_section("generation_settings")', generation)
        self.assertNotIn('self._make_section("ai_provider")', source)
        self.assertIn("class AiSettingsDialog", dialog)
        self.assertIn("self.api_key_input", dialog)
        self.assertNotIn("QGridLayout", generation + dialog)

    def test_import_area_and_status_messages_have_clear_visual_roles(self):
        source = self.panel_source()
        material = self.function_source(source, "_build_material_section")
        render_import = self.function_source(
            source,
            "_render_source_import_feedback",
        )

        self.assertIn('setObjectName("MaterialDropArea")', material)
        self.assertIn('"source_import_error_"', render_import)
        self.assertIn("setVisible(bool(warnings))", render_import)
        for role in ("success", "warning", "error", "status"):
            self.assertIn(
                f'QLabel[role="{role}"]',
                PRODUCT_DARK_STYLESHEET,
            )
        self.assertIn("QTextEdit#MaterialDropArea", PRODUCT_DARK_STYLESHEET)

    def test_write_configuration_uses_consistent_form_spacing(self):
        builder = self.function_source(self.panel_source(), "_build_write_section")

        self.assertIn("self._configure_form_layout(form)", builder)
        self.assertEqual(builder.count("self._make_form_label("), 5)
        self.assertIn("self._add_form_row(form, self.deck_label", builder)

    def test_styles_module_has_no_business_runtime_dependencies(self):
        source = self.style_source()
        tree = ast.parse(source)

        self.assertFalse(any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in tree.body))
        for forbidden in (
            "from ..ai",
            "from ..anki_writer",
            "from .read_only_duplicate_check",
            "collection.",
            "api_key =",
            "load_config",
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

    def dialog_source(self):
        return (
            self.root() / "ankiforge_ai" / "ui" / "ai_settings_dialog.py"
        ).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
