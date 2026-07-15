import ast
import unittest
from pathlib import Path

from ankiforge_ai.pipeline.ai_generation_limits import (
    MAX_AI_MATERIAL_CHARS,
    AIGenerationInputError,
    validate_ai_material_text,
)
from ankiforge_ai.pipeline.generation_settings import GenerationSettings
from ankiforge_ai.pipeline.openai_compatible_provider import (
    OpenAICompatibleTransportResponse,
)
from ankiforge_ai.ui.beginner_ai_card_drafts import (
    BeginnerAICardDraftGenerator,
    BeginnerAIDraftErrorCode,
    BeginnerAIProviderRuntimeSettings,
    _build_payload,
)


class RecordingTransport:
    def __init__(self):
        self.calls = []

    def post_json(self, **kwargs):
        self.calls.append(kwargs)
        return OpenAICompatibleTransportResponse(
            status_code=200,
            json_body={
                "choices": [
                    {
                        "message": {
                            "content": (
                                '[{"front":"Q","back":"A",'
                                '"source_excerpt":"S"}]'
                            )
                        }
                    }
                ]
            },
        )


class PR25MaterialLimitTests(unittest.TestCase):
    def setUp(self):
        self.settings = BeginnerAIProviderRuntimeSettings(
            provider_name="OpenAI-compatible",
            base_url="https://provider.example/v1",
            model="safe-model",
            api_key="fake-session-key",
        )

    def test_under_and_exact_limit_are_allowed(self):
        for material in (
            "x" * (MAX_AI_MATERIAL_CHARS - 1),
            "x" * MAX_AI_MATERIAL_CHARS,
        ):
            with self.subTest(length=len(material)):
                self.assertEqual(validate_ai_material_text(material), len(material))
                payload = _build_payload(self.settings, material)
                self.assertIn(material, payload["messages"][1]["content"])

    def test_safe_error_contains_only_code_and_length(self):
        material = "private-fragment-" + "x" * MAX_AI_MATERIAL_CHARS

        with self.assertRaises(AIGenerationInputError) as context:
            validate_ai_material_text(material)

        rendered = repr(context.exception) + str(context.exception)
        self.assertEqual(context.exception.code, "material_too_long")
        self.assertEqual(context.exception.char_count, len(material))
        self.assertNotIn("private-fragment", rendered)

    def test_core_blocks_before_transport(self):
        transport = RecordingTransport()
        material = "sensitive-material-" + "x" * MAX_AI_MATERIAL_CHARS

        result = BeginnerAICardDraftGenerator(transport).generate(
            settings=self.settings,
            material_text=material,
            generation_settings=GenerationSettings(),
        )

        self.assertFalse(result.success)
        self.assertEqual(
            result.error_code,
            BeginnerAIDraftErrorCode.MATERIAL_TOO_LONG,
        )
        self.assertEqual(transport.calls, [])
        self.assertNotIn("sensitive-material", repr(result) + str(result.to_safe_dict()))

    def test_ui_preflight_precedes_background_submission(self):
        source = self.panel_source()
        handler = self.function_source(source, "_generate_cards")

        self.assertIn("MAX_AI_MATERIAL_CHARS", source)
        self.assertIn('self._set_generation_message("material_too_long")', handler)
        self.assertIn("self._generation_controller.submit", handler)
        self.assertLess(
            handler.index('self._set_generation_message("material_too_long")'),
            handler.index("self._generation_controller.submit"),
        )

    def test_limit_copy_is_bilingual(self):
        from ankiforge_ai.ui.product_i18n import product_text

        self.assertEqual(
            product_text("zh", "material_too_long"),
            "材料过长，请拆分后再生成。",
        )
        self.assertEqual(
            product_text("en", "material_too_long"),
            "The material is too long. Please split it before generating cards.",
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
    def panel_source():
        return (
            Path(__file__).parents[1]
            / "ankiforge_ai"
            / "ui"
            / "card_maker_panel.py"
        ).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
