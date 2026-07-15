import ast
import unittest
from pathlib import Path


class AISettingsEndpointConfirmationContractTests(unittest.TestCase):
    def test_dialog_assesses_before_accept_and_cancel_does_not_save(self):
        source = self.dialog_source()
        save = self.function_source(source, "_save")

        self.assertIn("assess_provider_endpoint", save)
        self.assertIn('decision.kind == "deny"', save)
        self.assertIn('decision.kind == "confirm"', save)
        self.assertIn("QMessageBox.question", save)
        self.assertIn("endpoint_confirmation_key", save)
        self.assertLess(
            save.index("BeginnerAIProviderRuntimeSettings"),
            save.index("QMessageBox.question"),
        )
        self.assertLess(
            save.index("if not confirmed"),
            save.index("self._accepted_settings = settings"),
        )

    def test_main_transfers_only_session_confirmation_state(self):
        source = self.main_source()
        handler = self.function_source(source, "_open_ai_settings")

        self.assertIn("confirmed_endpoint_keys=", handler)
        self.assertIn("dialog.endpoint_confirmation_key()", handler)
        self.assertIn("confirmed_endpoint_key=", handler)
        self.assertIn("dialog.clear_sensitive_data()", handler)
        self.assertIn("dialog.deleteLater()", handler)

    def test_panel_revalidates_confirmation_and_clears_it_on_discard(self):
        source = self.panel_source()
        setter = self.function_source(source, "set_ai_runtime_settings")
        discard = self.function_source(source, "discard_session")

        self.assertIn("assess_provider_endpoint", setter)
        self.assertIn("endpoint_confirmation_key", setter)
        self.assertIn("self._endpoint_confirmations", setter)
        self.assertIn("self._endpoint_confirmations.clear()", discard)

    @staticmethod
    def function_source(source, name):
        tree = ast.parse(source)
        node = next(
            item
            for item in ast.walk(tree)
            if isinstance(item, ast.FunctionDef) and item.name == name
        )
        return ast.get_source_segment(source, node) or ""

    @classmethod
    def root(cls):
        return Path(__file__).parents[1]

    @classmethod
    def dialog_source(cls):
        return (cls.root() / "ankiforge_ai" / "ui" / "ai_settings_dialog.py").read_text(
            encoding="utf-8"
        )

    @classmethod
    def main_source(cls):
        return (cls.root() / "ankiforge_ai" / "ui" / "main_dialog.py").read_text(
            encoding="utf-8"
        )

    @classmethod
    def panel_source(cls):
        return (cls.root() / "ankiforge_ai" / "ui" / "card_maker_panel.py").read_text(
            encoding="utf-8"
        )


if __name__ == "__main__":
    unittest.main()
