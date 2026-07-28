import ast
import unittest
from pathlib import Path

from ankiforge_ai.ui.product_i18n import PRODUCT_COPY
from ankiforge_ai.ui.product_styles import PRODUCT_DARK_STYLESHEET


class UIConvergenceV014Tests(unittest.TestCase):
    def test_material_editor_precedes_a_compact_inline_import_row(self):
        material = self.function_source("_build_material_section")

        self.assertIn('setObjectName("MaterialImportRow")', material)
        self.assertIn("self.material_import_hint_label", material)
        self.assertLess(
            material.index("layout.addWidget(self.material_input, 1)"),
            material.index("self.material_import_hint_label"),
        )
        self.assertLess(
            material.index("self.material_import_hint_label"),
            material.index("self.document_queue_container"),
        )

    def test_intelligence_controls_are_inside_collapsed_generation_settings(self):
        generation = self.function_source("_build_generation_section")

        self.assertLess(
            generation.index("self.card_mode_combo"),
            generation.index("self.generation_settings_container"),
        )
        self.assertIn("advanced_form = QFormLayout()", generation)
        self.assertLess(
            generation.index("advanced_form = QFormLayout()"),
            generation.index("self.intelligence_level_combo"),
        )
        self.assertIn(
            "self.generation_settings_container.setVisible(False)",
            generation,
        )

    def test_copy_and_styles_keep_import_secondary_and_settings_quiet(self):
        for language in ("zh", "en"):
            self.assertTrue(PRODUCT_COPY[language]["material_import_hint"])
            self.assertTrue(PRODUCT_COPY[language]["more_options"])
        self.assertIn("QFrame#MaterialImportRow", PRODUCT_DARK_STYLESHEET)
        self.assertIn(
            "QFrame#GenerationSettingsDisclosure",
            PRODUCT_DARK_STYLESHEET,
        )

    @classmethod
    def panel_source(cls):
        return (
            cls.root() / "ankiforge_ai" / "ui" / "card_maker_panel.py"
        ).read_text(encoding="utf-8")

    @classmethod
    def function_source(cls, name):
        source = cls.panel_source()
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


if __name__ == "__main__":
    unittest.main()
