import ast
import json
import unittest
from pathlib import Path

import ankiforge_ai

from ankiforge_ai.ui.product_i18n import PRODUCT_COPY


class ProviderFormLayoutHotfixTests(unittest.TestCase):
    def test_provider_form_is_owned_by_session_dialog(self):
        panel = self.panel_source()
        dialog = self.dialog_source()
        main_builder = self.function_source(panel, "_build_ui")

        self.assertNotIn("_build_provider_section", main_builder)
        self.assertNotIn("self.provider_combo", panel)
        for name in ("provider_combo", "model_input", "api_key_input"):
            self.assertIn(f"self.{name}", dialog)

    def test_dialog_row_helper_has_fixed_label_and_stretching_control(self):
        helper = self.function_source(self.dialog_source(), "_make_form_row")

        self.assertIn("row.setSpacing(FORM_HORIZONTAL_GAP)", helper)
        self.assertIn("label.setFixedWidth(FORM_LABEL_WIDTH)", helper)
        self.assertIn("label.setMinimumHeight(CONTROL_HEIGHT)", helper)
        self.assertIn("self._configure_control(control)", helper)
        self.assertIn("Qt.AlignmentFlag.AlignTop", helper)
        self.assertIn("row.addWidget(control, 1, Qt.AlignmentFlag.AlignTop)", helper)

    def test_api_key_hint_is_nested_once_below_the_dialog_input(self):
        builder = self.function_source(self.dialog_source(), "_build_ui")

        self.assertEqual(builder.count('QLabel(self.t("api_key_help"))'), 1)
        self.assertNotIn("session_note_label", builder)
        self.assertIn('self.api_key_help_label.setProperty("role", "muted")', builder)
        self.assertIn("api_key_layout.setSpacing(HINT_TOP_MARGIN)", builder)
        self.assertLess(
            builder.index("api_key_layout.addWidget(self.api_key_input)"),
            builder.index("api_key_layout.addWidget(self.api_key_help_label)"),
        )

    def test_main_screen_has_no_provider_more_settings_disclosure(self):
        panel = self.panel_source()
        main_builder = self.function_source(panel, "_build_ui")

        self.assertNotIn("self.ai_advanced_btn", panel)
        self.assertNotIn("_build_provider_section", main_builder)
        self.assertIn("self.generation_settings_btn", panel)

    def test_connection_fields_only_appear_for_openai_compatible(self):
        handler = self.function_source(
            self.dialog_source(),
            "_on_provider_changed",
        )

        self.assertIn('provider_name == "OpenAI-compatible"', handler)
        self.assertIn("self.connection_container.setVisible", handler)

    def test_generate_button_is_at_bottom_of_create_panel(self):
        builder = self.function_source(self.panel_source(), "_build_create_panel")

        self.assertIn("self._build_material_section()", builder)
        self.assertIn("self._build_generation_section()", builder)
        self.assertIn("layout.addWidget(self.generate_btn)", builder)
        self.assertLess(
            builder.index("self._build_generation_section()"),
            builder.index("layout.addWidget(self.generate_btn)"),
        )

    def test_api_key_placeholder_is_not_a_duplicate_policy_hint(self):
        self.assertEqual(PRODUCT_COPY["zh"]["api_key_placeholder"], "输入 API key")
        self.assertEqual(PRODUCT_COPY["en"]["api_key_placeholder"], "Enter API key")
        self.assertEqual(
            PRODUCT_COPY["zh"]["api_key_help"],
            "仅本次使用，不会保存。",
        )
        self.assertEqual(
            PRODUCT_COPY["en"]["api_key_help"],
            "Used only for this session. Not saved.",
        )

    def test_runtime_and_manifest_versions_are_0125(self):
        manifest = json.loads(
            (self.root() / "ankiforge_ai" / "manifest.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(ankiforge_ai.__version__, manifest["version"])

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

    @classmethod
    def panel_source(cls):
        return (
            cls.root() / "ankiforge_ai" / "ui" / "card_maker_panel.py"
        ).read_text(encoding="utf-8")

    @classmethod
    def dialog_source(cls):
        return (
            cls.root() / "ankiforge_ai" / "ui" / "ai_settings_dialog.py"
        ).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
