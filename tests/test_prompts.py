import unittest

from ankiforge_ai.ai.prompts import SYSTEM_PROMPT, build_user_prompt
from ankiforge_ai.importers.md_importer import MarkdownChunk


class PromptTests(unittest.TestCase):
    def test_prompt_contains_anki_quality_constraints(self):
        chunk = MarkdownChunk(
            heading="过拟合",
            level=2,
            content="过拟合是模型记住训练集噪声。",
            source_path="ml.md",
        )

        prompt = build_user_prompt(chunk, max_cards_per_chunk=3)
        combined = f"{SYSTEM_PROMPT}\n{prompt}".lower()

        self.assertIn("valid json", combined)
        self.assertIn("atomic knowledge point", combined)
        self.assertIn("long-term review", combined)
        self.assertIn("extra should include", combined)
        self.assertIn("do not copy a whole markdown paragraph", combined)
        self.assertIn("2-5 short stable tags", combined)


if __name__ == "__main__":
    unittest.main()
