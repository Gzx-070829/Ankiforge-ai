import ast
import unittest
from pathlib import Path

from ankiforge_ai.ui.beginner_ai_card_drafts import (
    BeginnerAIProviderRuntimeSettings,
)
from ankiforge_ai.ui.product_i18n import PRODUCT_COPY


class SingleScreenCardMakerTests(unittest.TestCase):
    def test_main_window_embeds_one_single_screen_card_maker(self):
        main = self.main_source()
        panel = self.panel_source()

        self.assertIn("CardMakerPanel", self.function_source(main, "_build_ui"))
        self.assertIn('self.t("subtitle")', main)
        for key in (
            "create_cards_section",
            "material_section",
            "generation_settings",
            "cards_section",
            "write_section",
        ):
            self.assertIn(f'self.t("{key}")', panel)
        self.assertNotIn("五步流程导航", panel)
        self.assertNotIn("四步流程", panel)

    def test_product_body_uses_two_columns_with_visible_empty_state(self):
        builder = self.function_source(self.panel_source(), "_build_ui")
        cards = self.function_source(
            self.panel_source(),
            "_build_cards_section",
        )

        self.assertIn("columns = QHBoxLayout()", builder)
        self.assertIn("left_layout.addWidget", builder)
        self.assertIn("right_layout.addWidget", builder)
        self.assertIn('self.t("no_cards")', cards)
        self.assertIn('self.t("no_cards_help")', cards)
        self.assertIn("self.cards_scroll.setVisible(False)", cards)

    def test_default_product_surface_avoids_developer_vocabulary(self):
        main_surface = self.function_source(self.main_source(), "_build_ui")
        panel = self.panel_source()
        rendered = self.literal_strings(main_surface + "\n" + panel).casefold()

        for forbidden in (
            "新手模式",
            "旧版工作台",
            "只读演练",
            "演练完成，尚未写入 anki",
            "最终确认预览",
            "final confirmation preview",
            "write eligibility",
            "write plan",
            "human review",
            "candidate draft",
            "ready_preview",
            "ready_for_future_confirmation",
            "未来写入条件",
            "只读访问 collection",
        ):
            self.assertNotIn(forbidden, rendered)

    def test_advanced_debug_tools_are_absent_from_product_surface(self):
        build_ui = self.function_source(self.main_source(), "_build_ui")

        self.assertNotIn('self.t("advanced_debug")', build_ui)
        self.assertNotIn("advanced_tools_panel", build_ui)
        self.assertNotIn("advanced_toggle_btn", build_ui)
        self.assertNotIn("Mock Pipeline", build_ui)
        self.assertNotIn("Human Review", build_ui)
        self.assertNotIn("添加到 Anki", build_ui)
        self.assertIn("self.help_btn", build_ui)

    def test_compatible_provider_connection_settings_are_in_dialog(self):
        dialog = (
            self.root() / "ankiforge_ai" / "ui" / "ai_settings_dialog.py"
        ).read_text(encoding="utf-8")
        builder = self.function_source(dialog, "_build_ui")

        for key in ("provider", "model", "api_key", "base_url", "timeout"):
            self.assertIn(f'self.t("{key}")', builder)
        self.assertIn(
            "self.connection_container.setVisible(False)",
            builder,
        )
        self.assertNotIn("self.ai_advanced_btn", dialog)

    def test_api_key_is_session_only_and_redacted(self):
        secret = "sk-session-only-secret"
        settings = BeginnerAIProviderRuntimeSettings(
            provider_name="OpenAI-compatible",
            base_url="https://provider.invalid/v1",
            model="model-name",
            api_key=secret,
        )
        rendered = repr(settings) + str(settings) + str(settings.to_safe_dict())
        panel = self.panel_source()
        discard = self.function_source(panel, "discard_session")

        self.assertNotIn(secret, rendered)
        self.assertIn("self._ai_runtime_settings = None", discard)
        for forbidden in ("save_config", "write_config", "setConfig"):
            self.assertNotIn(forbidden, panel)

    def test_write_requires_custom_secondary_confirmation(self):
        handler = self.function_source(self.panel_source(), "_confirm_and_write")

        self.assertIn('self.t("confirm_write_title")', handler)
        self.assertIn('"confirm_write_body_v1"', handler)
        self.assertIn('self.t("cancel")', handler)
        self.assertIn('self.t("confirm_write")', handler)
        self.assertIn("if not confirmed", handler)
        self.assertLess(
            handler.index("if not confirmed"),
            handler.index("execute_beginner_write_if_confirmed"),
        )
        self.assertNotIn("add_note", handler)

    def test_duplicate_check_is_required_and_has_three_short_states(self):
        panel = self.panel_source()
        refresh = self.function_source(panel, "_refresh_product_state")

        self.assertIn('self.t("check_duplicates")', panel)
        self.assertEqual(PRODUCT_COPY["zh"]["duplicates_clear"], "已检查")
        self.assertEqual(PRODUCT_COPY["zh"]["duplicates_skipped"], "可能重复，已跳过")
        self.assertEqual(PRODUCT_COPY["zh"]["duplicates_unchecked"], "未检查")
        self.assertIn("self.write_preparation.can_write", refresh)
        self.assertIn("prepare_beginner_write", panel)

    def test_written_snapshot_disables_same_batch(self):
        refresh = self.function_source(
            self.panel_source(),
            "_refresh_product_state",
        )

        self.assertIn("has_completed_write_snapshot", refresh)
        self.assertIn('self.t("write_completed_button")', refresh)
        self.assertIn("self.write_btn.setEnabled(False)", refresh)

    @staticmethod
    def literal_strings(source):
        tree = ast.parse(source)
        return "\n".join(
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        )

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
