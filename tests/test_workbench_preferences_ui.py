import ast
from pathlib import Path
import unittest


class WorkbenchPreferencesUiContractTests(unittest.TestCase):
    def test_main_dialog_loads_preferences_before_building_controls(self):
        source = self.source("ankiforge_ai/ui/main_dialog.py")
        initializer = self.method_source(source, "MainDialog", "__init__")

        self.assertIn("WorkbenchPreferencesAdapter", source)
        self.assertLess(
            initializer.index("self._preferences_adapter.load()"),
            initializer.index("self._build_ui()"),
        )
        self.assertIn("ui_language", initializer)
        self.assertIn("preferences=self._preferences", source)
        self.assertIn("preferences_changed=self._save_preferences", source)

    def test_panel_notifies_only_with_a_safe_preference_value(self):
        source = self.source("ankiforge_ai/ui/card_maker_panel.py")

        self.assertIn("WorkbenchPreferences", source)
        self.assertIn("def _notify_preferences_changed", source)
        self.assertNotIn("api_key=", self.function_source(source, "_current_preferences"))
        self.assertNotIn("base_url=", self.function_source(source, "_current_preferences"))
        self.assertIn("self._ai_runtime_settings = None", self.function_source(source, "discard_session"))

    def test_ai_dialog_uses_provider_and_model_preferences_without_a_credential(self):
        source = self.source("ankiforge_ai/ui/ai_settings_dialog.py")
        initializer = self.method_source(source, "AiSettingsDialog", "__init__")
        loader = self.method_source(source, "AiSettingsDialog", "_load_settings")

        self.assertIn("preferred_provider_name", initializer)
        self.assertIn("preferred_model_name", initializer)
        self.assertIn("preferred_provider_name", loader)
        self.assertIn("preferred_model_name", loader)
        self.assertIn("self.api_key_input.clear()", loader)

    @staticmethod
    def root():
        return Path(__file__).parents[1]

    def source(self, relative_path):
        return (self.root() / relative_path).read_text(encoding="utf-8")

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
    def method_source(source, class_name, method_name):
        tree = ast.parse(source)
        class_node = next(
            item
            for item in tree.body
            if isinstance(item, ast.ClassDef) and item.name == class_name
        )
        node = next(
            item
            for item in class_node.body
            if isinstance(item, ast.FunctionDef) and item.name == method_name
        )
        return ast.get_source_segment(source, node) or ""


if __name__ == "__main__":
    unittest.main()
