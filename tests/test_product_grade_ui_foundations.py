import ast
import unittest
from pathlib import Path


class ProductGradeUiFoundationTests(unittest.TestCase):
    def test_style_tokens_are_centralized_and_complete(self):
        source = self.read("ankiforge_ai/ui/style_tokens.py")
        for name, value in {
            "APP_BG": "#0D1117",
            "SURFACE": "#111827",
            "SURFACE_ELEVATED": "#161B22",
            "INPUT_BG": "#0F141B",
            "ACCENT": "#7C5CFF",
            "SUCCESS": "#22C55E",
            "WARNING": "#F59E0B",
            "DANGER": "#EF4444",
        }.items():
            self.assertIn(f'{name} = "{value}"', source)
        for name, value in {
            "SPACING_XS": 4,
            "SPACING_SM": 8,
            "SPACING_MD": 12,
            "SPACING_LG": 16,
            "SPACING_XL": 24,
            "SPACING_XXL": 32,
        }.items():
            self.assertIn(f"{name} = {value}", source)

    def test_main_header_has_help_and_no_legacy_settings_persistence(self):
        source = self.read("ankiforge_ai/ui/main_dialog.py")
        builder = self.function_source(source, "_build_ui")

        self.assertIn("HelpDialog", source)
        self.assertIn("self.help_btn", builder)
        self.assertIn("self._open_help", builder)
        for forbidden in (
            "save_config",
            "api_key_input",
            "_build_legacy_workbench",
            "advanced_toggle_btn",
            "legacy_entry_btn",
        ):
            self.assertNotIn(forbidden, source)

    def test_help_dialog_contains_only_product_onboarding_actions(self):
        source = self.read("ankiforge_ai/ui/help_dialog.py")
        for key in (
            "help_addon_identity",
            "help_own_material",
            "help_provider",
            "help_session_key",
            "help_review",
            "help_confirmation",
            "help_test_deck",
            "help_pdf",
        ):
            self.assertIn(key, source)
        for forbidden in ("urlopen", "requests", "save_config", "api_key"):
            self.assertNotIn(forbidden, source)

    def test_product_copy_has_help_keys_in_both_languages(self):
        source = self.read("ankiforge_ai/ui/product_i18n.py")
        tree = ast.parse(source)
        catalog = next(
            node.value
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "PRODUCT_COPY"
                for target in node.targets
            )
        )
        value = ast.literal_eval(catalog)
        self.assertEqual(set(value["zh"]), set(value["en"]))
        for key in ("help", "help_title", "help_close", "example_picker_title"):
            self.assertIn(key, value["zh"])

    def test_card_maker_uses_selectable_modes_and_central_style_tokens(self):
        source = self.read("ankiforge_ai/ui/card_maker_panel.py")

        self.assertIn("selectable_card_mode_profiles", source)
        self.assertIn("for profile in selectable_card_mode_profiles()", source)
        self.assertNotIn('(\"quick_review\", \"mode_quick_review\")', source)
        self.assertIn("from .style_tokens import", source)
        self.assertNotIn("SPACING_XS = 4", source)

    def test_review_surface_exposes_product_actions_and_safe_quality_copy(self):
        source = self.read("ankiforge_ai/ui/card_maker_panel.py")
        builder = self.function_source(source, "_build_cards_section")
        renderer = self.function_source(source, "_render_cards")

        for name in ("review_stats_label", "keep_clean_btn"):
            self.assertIn(f"self.{name}", builder)
        for key in ("copy", "restore"):
            self.assertIn(f'self.t("{key}")', renderer)
        self.assertIn("issue.user_message(self.language)", renderer)
        self.assertIn("issue.suggestion(self.language)", renderer)
        self.assertNotIn("warning_id", renderer)

    @classmethod
    def read(cls, relative):
        return (Path(__file__).parents[1] / relative).read_text(encoding="utf-8")

    @staticmethod
    def function_source(source, name):
        tree = ast.parse(source)
        node = next(
            item
            for item in ast.walk(tree)
            if isinstance(item, ast.FunctionDef) and item.name == name
        )
        return ast.get_source_segment(source, node) or ""


if __name__ == "__main__":
    unittest.main()
