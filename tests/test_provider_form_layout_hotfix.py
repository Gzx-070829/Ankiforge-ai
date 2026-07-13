import ast
import json
import unittest
from pathlib import Path

import ankiforge_ai

from ankiforge_ai.ui.product_i18n import PRODUCT_COPY


class ProviderFormLayoutHotfixTests(unittest.TestCase):
    def test_provider_uses_explicit_vertical_rows_instead_of_form_hint_rows(self):
        builder = self.function_source("_build_provider_section")

        self.assertIn("provider_rows = QVBoxLayout()", builder)
        self.assertIn("provider_rows.setSpacing(ROW_GAP)", builder)
        self.assertNotIn("provider_form = QFormLayout()", builder)
        for label, control in (
            ("self.provider_label", "self.provider_combo"),
            ("self.model_label", "self.model_input"),
            ("self.api_key_label", "self.api_key_field"),
        ):
            self.assertIn(
                f"self._make_provider_form_row(\n                {label},\n                {control},",
                builder,
            )

    def test_provider_row_helper_has_fixed_label_and_stretching_control(self):
        helper = self.function_source("_make_provider_form_row")

        self.assertIn("row.setSpacing(FORM_HORIZONTAL_GAP)", helper)
        self.assertIn("label.setFixedWidth(FORM_LABEL_WIDTH)", helper)
        self.assertIn("label.setMinimumHeight(CONTROL_HEIGHT)", helper)
        self.assertIn("label.setWordWrap(False)", helper)
        self.assertIn("self._configure_form_control(control)", helper)
        self.assertIn("Qt.AlignmentFlag.AlignTop", helper)
        self.assertIn("row.addWidget(control, 1, Qt.AlignmentFlag.AlignTop)", helper)

    def test_api_key_hint_is_nested_once_below_the_input(self):
        builder = self.function_source("_build_provider_section")

        self.assertEqual(builder.count('QLabel(self.t("api_key_help"))'), 1)
        self.assertIn('self.api_key_help_label.setProperty("role", "muted")', builder)
        self.assertIn("self._configure_form_control(self.api_key_input)", builder)
        self.assertIn("api_key_field_layout.setSpacing(HINT_TOP_MARGIN)", builder)
        self.assertLess(
            builder.index("api_key_field_layout.addWidget(self.api_key_input)"),
            builder.index("api_key_field_layout.addWidget(self.api_key_help_label)"),
        )
        self.assertNotIn("self._add_form_hint", builder)

    def test_default_provider_card_has_no_more_settings_disclosure(self):
        builder = self.function_source("_build_provider_section")

        self.assertNotIn("self.ai_advanced_btn", builder)
        self.assertNotIn('self.t("advanced_settings")', builder)
        self.assertIn("self.provider_connection_container.setVisible(False)", builder)

    def test_connection_fields_only_appear_for_openai_compatible(self):
        handler = self.function_source("_on_provider_changed")

        self.assertIn(
            "self.provider_connection_container.setVisible(\n"
            '            _provider_name == "OpenAI-compatible"\n'
            "        )",
            handler,
        )

    def test_generate_button_has_space_after_the_provider_form(self):
        builder = self.function_source("_build_provider_section")

        self.assertIn("layout.addSpacing(SPACING_LG)", builder)
        self.assertLess(
            builder.index("layout.addSpacing(SPACING_LG)"),
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

    def test_runtime_and_manifest_versions_are_0123(self):
        manifest = json.loads(
            (self.root() / "ankiforge_ai" / "manifest.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(ankiforge_ai.__version__, "0.12.3")
        self.assertEqual(manifest["version"], "0.12.3")

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

    @classmethod
    def panel_source(cls):
        return (
            cls.root() / "ankiforge_ai" / "ui" / "card_maker_panel.py"
        ).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
