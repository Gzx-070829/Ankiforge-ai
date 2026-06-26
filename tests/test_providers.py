import unittest

from ankiforge_ai.ai.providers import create_provider
from ankiforge_ai.ai.providers.base import AIProviderConfig
from ankiforge_ai.ai.providers.mock_provider import MockAIProvider
from ankiforge_ai.ai.schemas import mock_generate_cards
from ankiforge_ai.importers.md_importer import MarkdownChunk


class ProviderTests(unittest.TestCase):
    def test_mock_provider_generates_one_basic_card_without_network(self):
        provider = MockAIProvider(AIProviderConfig(max_cards_per_chunk=3))
        chunk = MarkdownChunk(
            heading="间隔重复",
            level=1,
            content="间隔重复是一种利用遗忘曲线安排复习的学习方法。",
            source_path="note.md",
        )

        cards = provider.generate_cards(chunk)

        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].card_type, "basic")
        self.assertIn("间隔重复", cards[0].front)
        self.assertIn("mock", cards[0].tags)
        self.assertEqual(cards[0].source, "note.md > 间隔重复")

    def test_factory_allows_only_mock_in_v011(self):
        provider = create_provider(AIProviderConfig(ai_provider="mock"))

        self.assertIsInstance(provider, MockAIProvider)

        with self.assertRaises(ValueError):
            create_provider(AIProviderConfig(ai_provider="openai"))

    def test_legacy_mock_generate_cards_wrapper(self):
        chunk = MarkdownChunk(
            heading="Topic",
            level=1,
            content="Body",
            source_path="source.md",
        )

        cards = mock_generate_cards(chunk)

        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].back, "Body")


if __name__ == "__main__":
    unittest.main()
