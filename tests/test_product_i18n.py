import ast
import unittest
from pathlib import Path

from ankiforge_ai.ui.product_i18n import (
    DEFAULT_PRODUCT_LANGUAGE,
    PRODUCT_COPY,
    PRODUCT_LANGUAGES,
    product_text,
)


class ProductI18nTests(unittest.TestCase):
    def test_default_language_is_chinese(self):
        self.assertEqual(DEFAULT_PRODUCT_LANGUAGE, "zh")
        self.assertEqual(PRODUCT_LANGUAGES, ("zh", "en"))
        self.assertEqual(product_text("zh", "material_section"), "学习材料")
        self.assertEqual(product_text("zh", "generate_cards"), "生成卡片")
        self.assertEqual(product_text("zh", "write_to_anki"), "写入 Anki")
        self.assertEqual(product_text("zh", "language_toggle"), "English")

    def test_english_catalog_contains_complete_product_path(self):
        self.assertEqual(
            set(PRODUCT_COPY["zh"]),
            set(PRODUCT_COPY["en"]),
        )
        self.assertEqual(product_text("en", "material_section"), "Study Material")
        self.assertEqual(product_text("en", "generate_cards"), "Generate Cards")
        self.assertEqual(product_text("en", "write_to_anki"), "Write to Anki")
        self.assertEqual(product_text("en", "language_toggle"), "中文")

    def test_language_toggle_has_stable_non_truncated_size(self):
        build_ui = self.function_source(self.main_source(), "_build_ui")

        self.assertIn("self.language_toggle_btn.setFixedSize(88, 30)", build_ui)
        self.assertIn("Qt.AlignmentFlag.AlignVCenter", build_ui)

    def test_chinese_surface_has_no_english_field_labels(self):
        zh = PRODUCT_COPY["zh"]
        labels = "\n".join(
            zh[key]
            for key in (
                "deck",
                "note_type",
                "front_mapping",
                "back_mapping",
                "source_mapping",
            )
        )

        for forbidden in ("Deck", "Note type", "Front", "Back", "Source"):
            self.assertNotIn(forbidden, labels)

    def test_english_surface_has_plain_english_field_labels(self):
        en = PRODUCT_COPY["en"]

        self.assertEqual(en["deck"], "Deck")
        self.assertEqual(en["note_type"], "Note type")
        self.assertEqual(en["front_mapping"], "Front →")
        self.assertEqual(en["back_mapping"], "Back →")
        self.assertEqual(en["source_mapping"], "Source →")

    def test_main_window_toggle_is_memory_only_and_updates_panel(self):
        source = self.main_source()
        init = self.function_source(source, "__init__")
        toggle = self.function_source(source, "toggle_language")

        self.assertIn("self.ui_language = DEFAULT_PRODUCT_LANGUAGE", init)
        self.assertIn('"en" if self.ui_language == "zh" else "zh"', toggle)
        self.assertIn("self.card_maker_panel.set_language", toggle)
        self.assertNotIn("save_config", toggle)
        self.assertNotIn("write_config", toggle)

    def test_product_catalog_avoids_internal_terms(self):
        rendered = "\n".join(
            value
            for catalog in PRODUCT_COPY.values()
            for value in catalog.values()
        ).casefold()
        for forbidden in (
            "新手模式",
            "旧版工作台",
            "只读演练",
            "演练完成，尚未写入 anki",
            "最终确认预览",
            "future confirmation",
            "final confirmation preview",
            "write eligibility",
            "eligibility",
            "write plan",
            "human review",
            "candidate draft",
            "ready_preview",
            "ready_for_future_confirmation",
            "未来写入条件",
            "尚未满足条件列表",
            "只读访问 collection",
        ):
            self.assertNotIn(forbidden, rendered)

    def test_deepseek_product_defaults_are_current(self):
        source = self.panel_source()
        builder = self.function_source(source, "_build_ai_section")

        self.assertLess(builder.index('"DeepSeek"'), builder.index('"OpenAI"'))
        self.assertIn("deepseek-v4-flash", builder)
        self.assertIn("https://api.deepseek.com", builder)
        self.assertNotIn("https://api.deepseek.com/v1", builder)
        self.assertIn("deepseek-v4-pro", PRODUCT_COPY["zh"]["model_failure_help"])
        self.assertIn("deepseek-v4-pro", PRODUCT_COPY["en"]["model_failure_help"])

    def test_confirmation_and_results_format_in_both_languages(self):
        self.assertEqual(
            product_text("zh", "confirm_write_body", count=2, deck="Test"),
            "将写入 2 张卡片到「Test」。",
        )
        self.assertEqual(
            product_text("en", "confirm_write_body", count=2, deck="Test"),
            "This will write 2 cards to “Test”.",
        )
        self.assertEqual(
            product_text("en", "write_success", count=2),
            "Wrote 2 cards. You can now check them in Anki.",
        )

    def test_panel_never_persists_language_or_api_key(self):
        source = self.panel_source()
        set_language = self.function_source(source, "set_language")
        discard = self.function_source(source, "discard_session")

        self.assertNotIn("config", set_language.casefold())
        self.assertNotIn("save", set_language.casefold())
        self.assertIn("self.api_key_input.clear()", discard)
        for forbidden in ("save_config", "write_config", "setConfig"):
            self.assertNotIn(forbidden, source)

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

    def main_source(self):
        return (
            self.root() / "ankiforge_ai" / "ui" / "main_dialog.py"
        ).read_text(encoding="utf-8")

    def panel_source(self):
        return (
            self.root() / "ankiforge_ai" / "ui" / "card_maker_panel.py"
        ).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
