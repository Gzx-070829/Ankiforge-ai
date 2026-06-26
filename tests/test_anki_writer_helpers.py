import unittest

from ankiforge_ai.ai.schemas import GeneratedCard
from ankiforge_ai.anki_writer.add_cards import (
    format_tags_field,
    make_duplicate_key,
    split_new_and_duplicate_cards,
)


class AnkiWriterHelperTests(unittest.TestCase):
    def test_format_tags_field_deduplicates_and_skips_empty_tags(self):
        self.assertEqual(
            format_tags_field(["AnkiForge", "", "mock", "AnkiForge", None]),
            "AnkiForge mock",
        )

    def test_duplicate_key_trims_front_and_source(self):
        self.assertEqual(
            make_duplicate_key(" Front  ", " note.md > Heading "),
            ("Front", "note.md > Heading"),
        )

    def test_split_new_and_duplicate_cards_skips_existing_and_batch_duplicates(self):
        cards = [
            GeneratedCard(
                card_type="basic",
                front="Q1",
                back="A1",
                source="note.md > One",
            ),
            GeneratedCard(
                card_type="basic",
                front="Q2",
                back="A2",
                source="note.md > Two",
            ),
            GeneratedCard(
                card_type="basic",
                front="Q2",
                back="A2 again",
                source="note.md > Two",
            ),
            GeneratedCard(
                card_type="basic",
                front="Q3",
                back="A3",
                source="note.md > Three",
                approved=False,
            ),
        ]

        writable, skipped = split_new_and_duplicate_cards(
            cards,
            existing_keys={("Q1", "note.md > One")},
        )

        self.assertEqual([card.front for card in writable], ["Q2"])
        self.assertEqual(skipped, 2)

    def test_split_new_and_duplicate_cards_validates_required_fields(self):
        cards = [
            GeneratedCard(
                card_type="basic",
                front="",
                back="A",
                source="note.md > One",
            )
        ]

        with self.assertRaises(ValueError):
            split_new_and_duplicate_cards(cards, existing_keys=set())


if __name__ == "__main__":
    unittest.main()
