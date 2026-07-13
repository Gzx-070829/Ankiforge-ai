import unittest

from ankiforge_ai.ai.prompts import build_user_prompt
from ankiforge_ai.importers.md_importer import MarkdownChunk
from ankiforge_ai.pipeline.generation_settings import GenerationSettings
from ankiforge_ai.pipeline.prompt_profile import build_prompt_profile
from ankiforge_ai.ui.beginner_ai_card_drafts import _build_payload
from ankiforge_ai.ui.beginner_ai_card_drafts import BeginnerAIProviderRuntimeSettings


class PromptProfileTests(unittest.TestCase):
    def test_modes_produce_distinct_guidance(self):
        prompts = {
            mode: build_prompt_profile(GenerationSettings(card_mode=mode)).guidance
            for mode in ("concept", "definition", "exam", "quick_review")
        }

        self.assertEqual(len(set(prompts.values())), 4)
        self.assertIn("cause", prompts["concept"].casefold())
        self.assertIn("definition", prompts["definition"].casefold())
        self.assertIn("exam", prompts["exam"].casefold())
        self.assertIn("one fact", prompts["quick_review"].casefold())

    def test_language_guidance_is_explicit(self):
        auto = build_prompt_profile(GenerationSettings(language="auto"))
        zh = build_prompt_profile(GenerationSettings(language="zh"))
        en = build_prompt_profile(GenerationSettings(language="en"))

        self.assertIn("material's language", auto.language_guidance)
        self.assertIn("Simplified Chinese", zh.language_guidance)
        self.assertIn("English", en.language_guidance)

    def test_quality_rules_are_present_in_every_profile(self):
        profile = build_prompt_profile(GenerationSettings())
        combined = profile.as_prompt_text().casefold()

        for phrase in (
            "one knowledge point",
            "specific",
            "concise",
            "do not invent",
            "generate fewer",
            "according to the material",
        ):
            self.assertIn(phrase, combined)

    def test_legacy_markdown_prompt_accepts_omitted_settings(self):
        chunk = MarkdownChunk(
            heading="过拟合",
            level=2,
            content="过拟合会降低泛化能力。",
            source_path="ml.md",
        )

        legacy = build_user_prompt(chunk, 3)
        configured = build_user_prompt(
            chunk,
            3,
            GenerationSettings(card_mode="exam", language="zh"),
        )

        self.assertIn("Maximum cards: 3", legacy)
        self.assertIn("exam", configured.casefold())
        self.assertIn("Simplified Chinese", configured)

    def test_beginner_payload_uses_settings_without_exposing_credentials(self):
        runtime = BeginnerAIProviderRuntimeSettings(
            provider_name="OpenAI-compatible",
            base_url="https://provider.invalid/v1",
            model="test-model",
            api_key="temporary-test-credential",
            timeout_seconds=10,
        )
        settings = GenerationSettings(
            card_mode="definition",
            card_count="fewer",
            answer_length="medium",
            language="en",
        )

        payload = _build_payload(runtime, "Material", settings=settings)
        rendered = str(payload)

        self.assertIn("definition", rendered.casefold())
        self.assertIn("Create at most 3", rendered)
        self.assertIn("English", rendered)
        self.assertNotIn(runtime.api_key, rendered)


if __name__ == "__main__":
    unittest.main()
