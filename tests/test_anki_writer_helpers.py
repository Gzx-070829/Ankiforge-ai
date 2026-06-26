import unittest

from ankiforge_ai.ai.schemas import GeneratedCard
from ankiforge_ai.anki_writer.add_cards import (
    _note_ids_for_model,
    format_tags_field,
    make_duplicate_key,
    normalize_duplicate_text,
    split_new_and_duplicate_cards,
)


class AnkiWriterHelperTests(unittest.TestCase):
    def test_format_tags_field_deduplicates_and_skips_empty_tags(self):
        self.assertEqual(
            format_tags_field(["AnkiForge", "", "mock", "AnkiForge", None]),
            "AnkiForge mock",
        )

    def test_duplicate_text_strips_and_collapses_whitespace(self):
        self.assertEqual(
            normalize_duplicate_text("  什么是\n  过拟合？ \t "),
            "什么是 过拟合？",
        )

    def test_duplicate_key_normalizes_front_and_source(self):
        self.assertEqual(
            make_duplicate_key(" Front\nQuestion  ", " note.md   >   Heading "),
            ("Front Question", "note.md > Heading"),
        )

    def test_note_ids_for_model_uses_model_id_db_query(self):
        collection = FakeCollection(note_ids=[10, 11, 12])

        note_ids = _note_ids_for_model(collection, {"id": 12345})

        self.assertEqual(note_ids, [10, 11, 12])
        self.assertEqual(
            collection.db.calls,
            [("select id from notes where mid = ?", 12345)],
        )

    def test_note_ids_for_model_returns_empty_without_model_id(self):
        collection = FakeCollection(note_ids=[10])

        self.assertEqual(_note_ids_for_model(collection, {}), [])
        self.assertEqual(collection.db.calls, [])

    def test_split_new_and_duplicate_cards_normalizes_existing_keys(self):
        cards = [
            GeneratedCard(
                card_type="basic",
                front="Front Question",
                back="A1",
                source="note.md > Heading",
            )
        ]

        writable, skipped = split_new_and_duplicate_cards(
            cards,
            existing_keys={make_duplicate_key(" Front\nQuestion ", " note.md   >   Heading ")},
        )

        self.assertEqual(writable, [])
        self.assertEqual(skipped, 1)

    def test_existing_regression_front_and_source_are_skipped(self):
        cards = [
            GeneratedCard(
                card_type="basic",
                front="什么是「和欠拟合的区别」？",
                back="A",
                source="ankiforge_test.md > 和欠拟合的区别",
            )
        ]

        writable, skipped = split_new_and_duplicate_cards(
            cards,
            existing_keys={
                make_duplicate_key(
                    "什么是「和欠拟合的区别」？",
                    "ankiforge_test.md > 和欠拟合的区别",
                )
            },
        )

        self.assertEqual(writable, [])
        self.assertEqual(skipped, 1)

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


class FakeCollection:
    def __init__(self, note_ids):
        self.db = FakeDb(note_ids)


class FakeDb:
    def __init__(self, note_ids):
        self.note_ids = note_ids
        self.calls = []

    def list(self, query, model_id):
        self.calls.append((query, model_id))
        return self.note_ids


if __name__ == "__main__":
    unittest.main()
