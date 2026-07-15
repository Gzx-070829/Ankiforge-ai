import ast
import unittest
from pathlib import Path


class AsyncCardGenerationIntegrationContractTests(unittest.TestCase):
    def test_click_handler_submits_snapshot_without_sync_provider_call(self):
        source = self.panel_source()
        handler = self.function_source(source, "_generate_cards")

        self.assertIn("self._generation_controller.submit", handler)
        self.assertIn("material_text=material_text", handler)
        self.assertIn("runtime_settings=settings", handler)
        self.assertIn("generation_settings=generation_settings", handler)
        self.assertIn("endpoint_confirmation_key=", handler)
        self.assertNotIn("BeginnerAICardDraftGenerator().generate", handler)
        self.assertNotIn("QApplication.processEvents", handler)
        self.assertGreater(
            handler.rindex("self._refresh_product_state()"),
            handler.index("self._generation_controller.submit"),
        )

    def test_completion_handler_is_separate_and_never_auto_approves(self):
        source = self.panel_source()
        handler = self.function_source(source, "_handle_generation_completion")

        self.assertIn("completion.result", handler)
        self.assertIn("self.session.apply_ai_candidate_card_drafts", handler)
        self.assertNotIn("set_candidate_review_decision", handler)
        self.assertNotIn("BeginnerReviewDecision.LOOKS_GOOD", handler)

    def test_upstream_change_and_discard_invalidate_late_callbacks(self):
        source = self.panel_source()
        upstream = self.function_source(source, "_after_upstream_change")
        discard = self.function_source(source, "discard_session")

        self.assertIn("self._generation_controller.invalidate()", upstream)
        self.assertIn("self._generation_controller.close()", discard)

    def test_running_state_cannot_be_reenabled_by_refresh(self):
        refresh = self.function_source(self.panel_source(), "_refresh_product_state")

        self.assertIn("self._generation_controller.running", refresh)
        self.assertIn('self.t("generation_running")', refresh)
        self.assertIn("self.generate_btn.setEnabled(False)", refresh)

    def test_main_dialog_teardown_covers_reject_and_close(self):
        source = self.main_source()
        teardown = self.function_source(source, "_teardown_session")
        reject = self.function_source(source, "reject")
        close = self.function_source(source, "closeEvent")

        self.assertIn("discard_session", teardown)
        self.assertIn("_teardown_session", reject)
        self.assertIn("_teardown_session", close)

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
    def panel_source(cls):
        return (cls.root() / "ankiforge_ai" / "ui" / "card_maker_panel.py").read_text(
            encoding="utf-8"
        )

    @classmethod
    def main_source(cls):
        return (cls.root() / "ankiforge_ai" / "ui" / "main_dialog.py").read_text(
            encoding="utf-8"
        )


if __name__ == "__main__":
    unittest.main()
