import ast
import json
import unittest
from pathlib import Path

import ankiforge_ai

from ankiforge_ai.ui.product_i18n import PRODUCT_COPY
from ankiforge_ai.ui.product_styles import PRODUCT_DARK_STYLESHEET


class UIRescueV0122Tests(unittest.TestCase):
    def test_left_column_uses_three_independent_product_sections(self):
        source = self.panel_source()
        builder = self.function_source(source, "_build_ui")

        self.assertIn("def _build_generation_section", source)
        self.assertIn("def _build_provider_section", source)
        self.assertNotIn("_build_ai_section()", builder)
        self.assertLess(
            builder.index("_build_material_section()"),
            builder.index("_build_generation_section()"),
        )
        self.assertLess(
            builder.index("_build_generation_section()"),
            builder.index("_build_provider_section()"),
        )
        self.assertIn("columns.setSpacing(COLUMN_GAP)", builder)
        self.assertIn("columns.addWidget(left, 48)", builder)
        self.assertIn("columns.addWidget(right, 52)", builder)

    def test_provider_model_and_api_key_are_separate_stable_form_rows(self):
        source = self.panel_source()
        builder = self.function_source(source, "_build_provider_section")

        self.assertIn("provider_form = QFormLayout()", builder)
        self.assertEqual(
            builder.count("self._add_form_row(\n            provider_form,"),
            3,
        )
        self.assertEqual(
            builder.count("self._add_form_row(\n            advanced_form,"),
            2,
        )
        self.assertLess(
            builder.index("self.provider_combo"),
            builder.index("self.model_input"),
        )
        self.assertLess(
            builder.index("self.model_input"),
            builder.index("self.api_key_input"),
        )
        self.assertIn("self._add_form_hint(", builder)
        self.assertNotIn("provider_model_row", builder)
        self.assertNotIn("api_key_section_label", builder)

    def test_shared_form_contract_prevents_label_and_control_overlap(self):
        source = self.panel_source()
        form_label = self.function_source(source, "_make_form_label")
        configure_control = self.function_source(source, "_configure_form_control")
        configure_form = self.function_source(source, "_configure_form_layout")

        self.assertIn("FORM_LABEL_WIDTH", form_label)
        self.assertIn("setFixedWidth", form_label)
        self.assertIn("setWordWrap(False)", form_label)
        self.assertIn("CONTROL_HEIGHT", configure_control)
        self.assertIn("setMinimumHeight", configure_control)
        self.assertIn("DontWrapRows", configure_form)
        self.assertIn("AllNonFixedFieldsGrow", configure_form)

    def test_generation_settings_are_a_real_section_and_default_collapsed(self):
        source = self.panel_source()
        builder = self.function_source(source, "_build_generation_section")

        self.assertIn('self._make_section("generation_settings")', builder)
        self.assertLess(
            builder.index("self.card_mode_combo"),
            builder.index("self.generation_settings_container"),
        )
        self.assertIn("self.generation_settings_container.setVisible(False)", builder)
        self.assertIn('self.t("more_options")', builder)
        self.assertNotIn("generation_preferences_label", builder)

    def test_material_section_contains_no_persistent_policy_paragraph(self):
        material = self.function_source(
            self.panel_source(),
            "_build_material_section",
        )
        zh = PRODUCT_COPY["zh"]
        en = PRODUCT_COPY["en"]

        self.assertNotIn("first_run_guidance_label", material)
        self.assertEqual(zh["material_help"], "粘贴材料，或导入 Markdown / TXT / DOCX。")
        self.assertEqual(en["material_help"], "Paste material, or import Markdown / TXT / DOCX.")
        self.assertEqual(zh["material_placeholder"], "粘贴学习材料，或拖入文件")
        self.assertEqual(en["material_placeholder"], "Paste study material, or drop a file")

    def test_legacy_advanced_entry_is_hidden_on_normal_surface(self):
        build_ui = self.function_source(self.main_source(), "_build_ui")

        self.assertIn("self.advanced_toggle_btn.setVisible(False)", build_ui)
        self.assertIn("self.advanced_tools_panel.setVisible(False)", build_ui)
        self.assertNotIn("advanced_link_row.addWidget", build_ui)

    def test_control_and_typography_tokens_match_design_pass(self):
        source = self.panel_source()

        for contract in (
            "SPACING_XS = 4",
            "SPACING_SM = 8",
            "SPACING_MD = 12",
            "SPACING_LG = 16",
            "COLUMN_GAP = 24",
            "FORM_LABEL_WIDTH = 96",
            "CONTROL_HEIGHT = 40",
            "BUTTON_HEIGHT = 36",
            "PRIMARY_BUTTON_HEIGHT = 44",
            "SECTION_PADDING = 18",
        ):
            self.assertIn(contract, source)
        self.assertIn("font-size: 18px", PRODUCT_DARK_STYLESHEET)
        self.assertIn("font-size: 16px", PRODUCT_DARK_STYLESHEET)
        self.assertIn("font-size: 13px", PRODUCT_DARK_STYLESHEET)
        self.assertIn("font-size: 12px", PRODUCT_DARK_STYLESHEET)
        self.assertIn("border-radius: 8px", PRODUCT_DARK_STYLESHEET)

    def test_write_summary_copy_is_multiline_and_user_facing(self):
        for language in ("zh", "en"):
            summary = PRODUCT_COPY[language]["write_summary"]
            self.assertGreaterEqual(summary.count("\n"), 3)
            self.assertNotIn("｜", summary)
            self.assertNotIn("|", summary)
            self.assertNotIn("source=", summary.casefold())
            self.assertNotIn("blocking=", summary.casefold())
            self.assertIn("{skipped}", summary)

        render = self.function_source(
            self.panel_source(),
            "_render_write_summary",
        )
        self.assertIn("skipped=", render)
        self.assertIn("self.write_command.skipped_count", render)

    def test_disabled_generate_action_explains_what_is_missing(self):
        refresh = self.function_source(
            self.panel_source(),
            "_refresh_product_state",
        )

        self.assertIn("self.generate_btn.setToolTip(", refresh)
        self.assertIn('self.t("generation_requirements")', refresh)

    def test_runtime_version_and_bilingual_catalog_are_ready_for_0122(self):
        manifest = json.loads(
            (self.root() / "ankiforge_ai" / "manifest.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(ankiforge_ai.__version__, "0.12.2")
        self.assertEqual(manifest["version"], "0.12.2")
        self.assertEqual(set(PRODUCT_COPY["zh"]), set(PRODUCT_COPY["en"]))

    @staticmethod
    def function_source(source, name):
        tree = ast.parse(source)
        node = next((
            item
            for item in ast.walk(tree)
            if isinstance(item, ast.FunctionDef) and item.name == name
        ), None)
        return ast.get_source_segment(source, node) if node is not None else ""

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


if __name__ == "__main__":
    unittest.main()
