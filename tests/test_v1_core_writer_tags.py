import unittest

from ankiforge_ai.anki_writer.minimal_write import (
    BeginnerWriteCardCommand,
    BeginnerWriteCommand,
    MinimalAnkiWriter,
)


class TagNote(dict):
    def __init__(self):
        super().__init__((name, "") for name in ("Front", "Back", "Extra"))
        self.id = 0
        self.tags = []

    def add_tag(self, tag):
        self.tags.append(tag)


class Manager:
    def __init__(self, value):
        self.value = value

    def get(self, item_id):
        return self.value if self.value.get("id") == item_id else None


class Collection:
    def __init__(self):
        self.decks = Manager({"id": 7, "name": "Test"})
        self.models = Manager(
            {
                "id": 11,
                "name": "Basic",
                "flds": [
                    {"name": "Front"},
                    {"name": "Back"},
                    {"name": "Extra"},
                ],
            }
        )
        self.notes = []

    def new_note(self, note_type):
        return TagNote()

    def add_note(self, note, deck_id):
        note.id = 1000 + len(self.notes) + 1
        self.notes.append(note)
        return note.id


class V1CoreWriterTagTests(unittest.TestCase):
    def test_writer_applies_only_command_tags_to_new_note(self):
        collection = Collection()
        command = self.command()

        result = MinimalAnkiWriter(collection).write(command)

        self.assertEqual(result.created_note_ids, (1001,))
        self.assertEqual(
            collection.notes[0].tags,
            ["ankiforge", "ankiforge-ai", "mode-concept", "source-paste"],
        )
        self.assertEqual(collection.notes[0]["Extra"], "Pasted text")
        self.assertEqual(set(collection.notes[0]), {"Front", "Back", "Extra"})

    def test_command_rejects_non_normalized_or_sensitive_tags(self):
        for tags in (("Has Space",), ("../private",), ("bearer-token",)):
            with self.subTest(tags=tags):
                with self.assertRaises(ValueError):
                    self.command(tags=tags)

    def test_safe_command_views_contain_counts_not_card_content(self):
        command = self.command()
        rendered = repr(command) + str(command.to_safe_dict())

        self.assertIn("tag_count=4", repr(command))
        self.assertNotIn("private answer", rendered)
        self.assertEqual(command.to_safe_dict()["tag_count"], 4)

    @staticmethod
    def command(tags=("ankiforge", "ankiforge-ai", "mode-concept", "source-paste")):
        return BeginnerWriteCommand(
            snapshot_id="snapshot",
            deck_id=7,
            deck_name="Test",
            note_type_id=11,
            note_type_name="Basic",
            front_field="Front",
            back_field="Back",
            source_field="Extra",
            cards=(
                BeginnerWriteCardCommand(
                    candidate_id="candidate-1",
                    front="specific question",
                    back="private answer",
                    source="Pasted text",
                ),
            ),
            skipped_count=0,
            tags=tags,
        )


if __name__ == "__main__":
    unittest.main()
