import ast
import json
import unittest
from pathlib import Path

import ankiforge_ai

from ankiforge_ai.ui.beginner_ai_card_drafts import (
    BeginnerAIProviderRuntimeSettings,
)
from ankiforge_ai.ui.product_i18n import PRODUCT_COPY


class LinearFlowSettingsModalTests(unittest.TestCase):
    def test_main_layout_is_linear_and_excludes_provider_form(self):
        builder = self.function_source(self.panel_source(), "_build_ui")

        self.assertIn("_build_create_panel", builder)
        self.assertIn("_build_review_panel", builder)
        self.assertIn("columns.addWidget(left, 45)", builder)
        self.assertIn("columns.addWidget(right, 55)", builder)
        self.assertNotIn("_build_provider_section", builder)

    def test_header_owns_ai_settings_action_and_status(self):
        main = self.main_source()
        builder = self.function_source(main, "_build_ui")

        self.assertIn("AiSettingsDialog", main)
        self.assertIn("self.ai_settings_btn", builder)
        self.assertIn("self.ai_status_label", builder)
        self.assertIn('setObjectName("AiSettingsButton")', builder)
        self.assertIn('setObjectName("AiStatusChip")', builder)
        self.assertIn("self._open_ai_settings", builder)

    def test_dialog_owns_provider_model_and_api_key(self):
        dialog_path = self.root() / "ankiforge_ai" / "ui" / "ai_settings_dialog.py"
        self.assertTrue(dialog_path.exists(), "AiSettingsDialog module is missing")
        source = dialog_path.read_text(encoding="utf-8")

        self.assertIn("class AiSettingsDialog(QDialog)", source)
        for name in ("provider_combo", "model_input", "api_key_input"):
            self.assertIn(f"self.{name}", source)
        self.assertEqual(source.count('QLabel(self.t("api_key_help"))'), 1)
        self.assertIn("QLineEdit.EchoMode.Password", source)
        self.assertNotIn("save_config", source)
        self.assertNotIn("write_config", source)

    def test_dialog_preserves_compatible_provider_connection_fields(self):
        source = self.dialog_source()
        handler = self.function_source(source, "_on_provider_changed")

        self.assertIn('provider_name == "OpenAI-compatible"', handler)
        self.assertIn("self.connection_container.setVisible", handler)
        self.assertIn("self.base_url_input", source)
        self.assertIn("self.timeout_input", source)

    def test_panel_keeps_only_safe_runtime_settings_in_memory(self):
        panel = self.panel_source()
        setter = self.function_source(panel, "set_ai_runtime_settings")
        discard = self.function_source(panel, "discard_session")

        self.assertIn("self._ai_runtime_settings = None", panel)
        self.assertIn("BeginnerAIProviderRuntimeSettings", setter)
        self.assertIn("self._ai_runtime_settings = settings", setter)
        self.assertIn("self._ai_runtime_settings = None", discard)
        for forbidden in ("save_config", "write_config", "setConfig"):
            self.assertNotIn(forbidden, panel)

        secret = "sk-session-only-never-persist"
        settings = BeginnerAIProviderRuntimeSettings(
            provider_name="OpenAI-compatible",
            base_url="https://provider.invalid/v1",
            model="model-name",
            api_key=secret,
        )
        safe_rendering = repr(settings) + str(settings.to_safe_dict())
        self.assertNotIn(secret, safe_rendering)

    def test_dialog_copy_is_complete_in_both_languages(self):
        expected = {
            "ai_settings": ("AI 设置", "AI Settings"),
            "ai_not_configured": ("AI 未配置", "AI not configured"),
            "save_session_settings": ("保存本次设置", "Save for this session"),
            "close": ("关闭", "Close"),
        }
        for key, (zh, en) in expected.items():
            self.assertEqual(PRODUCT_COPY["zh"][key], zh)
            self.assertEqual(PRODUCT_COPY["en"][key], en)
        self.assertEqual(set(PRODUCT_COPY["zh"]), set(PRODUCT_COPY["en"]))

    def test_generation_settings_remain_progressively_disclosed(self):
        builder = self.function_source(
            self.panel_source(),
            "_build_generation_section",
        )

        self.assertIn("self.card_mode_combo", builder)
        self.assertIn("self.generation_settings_container.setVisible(False)", builder)
        self.assertIn("self.generation_settings_btn", builder)

    def test_main_screen_avoids_forbidden_copy_and_debug_is_hidden(self):
        panel_builder = self.function_source(self.panel_source(), "_build_ui")
        main_builder = self.function_source(self.main_source(), "_build_ui")
        rendered = panel_builder + "\n" + main_builder

        for forbidden in (
            "这是 Anki 插件，不提供现成卡组",
            "请使用自己的 AI Provider API key",
            "每张卡都需要明确选择保留或丢弃",
            "PDF 请先复制文本或转换格式",
            "quality_score",
            "warning id",
            "blocking id",
        ):
            self.assertNotIn(forbidden, rendered)
        self.assertNotIn("advanced_toggle_btn", main_builder)
        self.assertNotIn("advanced_tools_panel", main_builder)

    def test_runtime_and_manifest_versions_match(self):
        manifest = json.loads(
            (self.root() / "ankiforge_ai" / "manifest.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(ankiforge_ai.__version__, manifest["version"])

    @classmethod
    def dialog_source(cls):
        return (
            cls.root() / "ankiforge_ai" / "ui" / "ai_settings_dialog.py"
        ).read_text(encoding="utf-8")

    @classmethod
    def main_source(cls):
        return (
            cls.root() / "ankiforge_ai" / "ui" / "main_dialog.py"
        ).read_text(encoding="utf-8")

    @classmethod
    def panel_source(cls):
        return (
            cls.root() / "ankiforge_ai" / "ui" / "card_maker_panel.py"
        ).read_text(encoding="utf-8")

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


if __name__ == "__main__":
    unittest.main()
