import ast
from pathlib import Path
import unittest

from ankiforge_ai.ui.product_styles import PRODUCT_DARK_STYLESHEET
from ankiforge_ai.ui.style_tokens import product_palette


class WarmCharcoalVisualContractTests(unittest.TestCase):
    def test_palette_is_warm_neutral_with_one_soft_orange_accent(self):
        palette = product_palette()

        self.assertEqual(palette["app_bg"], "#211D1A")
        self.assertEqual(palette["surface"], "#29231F")
        self.assertEqual(palette["text_primary"], "#F5EEE8")
        self.assertEqual(palette["accent"], "#D98A55")
        self.assertEqual(palette["accent_hover"], "#E39A65")
        self.assertEqual(set(palette), {
            "app_bg", "surface", "surface_elevated", "input_bg", "hover_bg",
            "border_subtle", "border_strong", "text_primary", "text_secondary",
            "text_muted", "accent", "accent_hover", "accent_soft", "success",
            "accent_border", "accent_text", "success_bg", "success_border",
            "success_text", "warning", "warning_bg", "warning_border",
            "warning_text", "danger", "danger_bg", "danger_border", "danger_text",
            "disabled_bg", "disabled_text", "disabled_border",
        })

    def test_primary_actions_use_soft_orange_with_dark_readable_text(self):
        primary = PRODUCT_DARK_STYLESHEET.split(
            'QWidget#CardMakerPanel QPushButton[role="primary"],'
        )[1].split("}", 1)[0]

        self.assertIn("background-color: #D98A55", primary)
        self.assertIn("color: #211D1A", primary)
        self.assertIn("font-weight: 600", primary)

    def test_generated_anki_card_template_css_is_not_imported_or_restyled(self):
        source = self.read("ankiforge_ai/ui/product_styles.py")
        tree = ast.parse(source)

        self.assertNotIn("theme/style.css", source)
        self.assertNotIn("ankiforge_ai.theme", source)
        self.assertFalse(
            any(
                isinstance(node, ast.ImportFrom)
                and node.module
                and "theme" in node.module
                for node in ast.walk(tree)
            )
        )

    def test_offline_mock_uses_the_same_palette_and_labels_itself(self):
        preview = self.read("docs/assets/ui_preview_v0_15.html")

        for color in ("#211d1a", "#29231f", "#d98a55", "#f5eee8"):
            self.assertIn(color, preview.casefold())
        self.assertIn("Create → Review → Write", preview)
        self.assertIn("Mock UI preview", preview)
        self.assertNotIn("sk-", preview.casefold())

    def test_visual_document_keeps_behavior_and_card_template_out_of_scope(self):
        document = self.read("docs/visual_design_v0_15.md").casefold()
        acceptance = self.read("docs/manual_anki_acceptance.md").casefold()

        for required in (
            "warm charcoal",
            "soft orange",
            "create → review → write",
            "generated anki card template",
            "no new controls",
            "ui_preview_v0_15.html",
        ):
            self.assertIn(required, document)
        for required in (
            "warm charcoal",
            "soft orange",
            "high dpi",
            "focus",
            "disabled",
        ):
            self.assertIn(required, acceptance)

    @staticmethod
    def root():
        return Path(__file__).parents[1]

    def read(self, relative_path):
        return (self.root() / relative_path).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
