import unittest

from ankiforge_ai.ai.validators import (
    CardValidationError,
    cards_from_json_text,
    validate_cards_payload,
)
from ankiforge_ai.importers.md_importer import MarkdownChunk


class ValidatorTests(unittest.TestCase):
    def test_validates_basic_cards_and_adds_local_source(self):
        chunk = MarkdownChunk(
            heading="过拟合",
            level=2,
            content="过拟合是模型记住训练集噪声。",
            source_path=r"C:\notes\ml.md",
        )
        payload = {
            "cards": [
                {
                    "card_type": "basic",
                    "front": "什么是过拟合？",
                    "back": "模型记住训练集噪声。",
                    "extra": "需要验证集检测。",
                    "tags": ["ml", "ai", "ml"],
                    "source": "model must not control this",
                }
            ]
        }

        cards = validate_cards_payload(payload, chunk, max_cards_per_chunk=3)

        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].source, "ml.md > 过拟合")
        self.assertEqual(cards[0].tags, ["ml", "ai"])

    def test_rejects_non_basic_cards_in_v02(self):
        chunk = MarkdownChunk("Heading", 1, "Body", "note.md")

        with self.assertRaises(CardValidationError):
            validate_cards_payload(
                {"cards": [{"card_type": "cloze", "front": "Q", "back": "A"}]},
                chunk,
                max_cards_per_chunk=3,
            )

    def test_rejects_empty_front_or_back(self):
        chunk = MarkdownChunk("Heading", 1, "Body", "note.md")

        with self.assertRaises(CardValidationError):
            validate_cards_payload(
                {"cards": [{"card_type": "basic", "front": "", "back": "A"}]},
                chunk,
                max_cards_per_chunk=3,
            )

    def test_rejects_invalid_json(self):
        chunk = MarkdownChunk("Heading", 1, "Body", "note.md")

        with self.assertRaises(CardValidationError):
            cards_from_json_text("not json", chunk, max_cards_per_chunk=3)

    def test_limits_cards_to_max_cards_per_chunk(self):
        chunk = MarkdownChunk("Heading", 1, "Body", "note.md")
        payload = {
            "cards": [
                {"card_type": "basic", "front": "Q1", "back": "A1"},
                {"card_type": "basic", "front": "Q2", "back": "A2"},
            ]
        }

        cards = validate_cards_payload(payload, chunk, max_cards_per_chunk=1)

        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].front, "Q1")


if __name__ == "__main__":
    unittest.main()
