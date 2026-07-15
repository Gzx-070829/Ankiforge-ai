import unittest

from ankiforge_ai.anki_writer.field_content import (
    duplicate_key_from_anki_html,
    duplicate_key_from_plain_text,
    plain_text_from_anki_html,
    render_plain_text_anki_html,
)
from ankiforge_ai.anki_writer.minimal_write import (
    BeginnerWriteCardCommand,
    BeginnerWriteCommand,
    MinimalAnkiWriter,
)


class FakeManager:
    def __init__(self, value):
        self.value = value

    def get(self, item_id):
        return self.value if self.value.get("id") == item_id else None


class FakeNote(dict):
    def __init__(self):
        super().__init__(Front="", Back="", Source="")
        self.id = 101


class FakeCollection:
    def __init__(self):
        self.decks = FakeManager({"id": 7, "name": "Test"})
        self.models = FakeManager(
            {
                "id": 11,
                "name": "Basic",
                "flds": [
                    {"name": "Front"},
                    {"name": "Back"},
                    {"name": "Source"},
                ],
            }
        )
        self.created_note = None

    def new_note(self, note_type):
        return FakeNote()

    def add_note(self, note, deck_id):
        self.created_note = note
        return note.id


class AnkiFieldContentTests(unittest.TestCase):
    def test_plain_text_is_escaped_and_newlines_become_br(self):
        rendered = render_plain_text_anki_html(
            "<script>alert(1)</script>\r\n"
            "<img src=x onerror=alert(1)>\rA < B & C > D\n中文"
        )

        self.assertNotIn("<script>", rendered)
        self.assertNotIn("<img", rendered)
        self.assertEqual(rendered.count("<br>"), 3)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", rendered)
        self.assertIn("A &lt; B &amp; C &gt; D", rendered)
        self.assertIn("中文", rendered)

    def test_quotes_are_escaped_for_safe_html_fields(self):
        self.assertEqual(
            render_plain_text_anki_html('say "yes" and it\'s safe'),
            "say &quot;yes&quot; and it&#x27;s safe",
        )

    def test_written_html_round_trips_to_the_same_duplicate_key(self):
        for text in (
            "<tag>",
            "line one\r\nline two",
            "literal &lt; entity",
            "A < B & C > D",
        ):
            with self.subTest(text=text):
                rendered = render_plain_text_anki_html(text)
                self.assertEqual(
                    duplicate_key_from_plain_text(text),
                    duplicate_key_from_anki_html(rendered),
                )

    def test_existing_escaped_html_and_br_match_raw_candidate(self):
        self.assertEqual(
            duplicate_key_from_plain_text("<tag>"),
            duplicate_key_from_anki_html("&lt;tag&gt;"),
        )
        self.assertEqual(
            duplicate_key_from_plain_text("Line 1\nLine 2"),
            duplicate_key_from_anki_html("Line 1<br>Line 2"),
        )
        self.assertEqual(plain_text_from_anki_html("&lt;tag&gt;"), "<tag>")

    def test_existing_html_break_and_block_variants_are_canonical_plain_text(self):
        cases = (
            ("Line 1<br/>Line 2", "Line 1\nLine 2"),
            ("Line 1<br />Line 2", "Line 1\nLine 2"),
            ("Line 1<BR>Line 2", "Line 1\nLine 2"),
            ("<div>One</div><p>Two</p>", "One\nTwo\n"),
            ("<b>bold</b>", "bold"),
        )
        for field_html, expected in cases:
            with self.subTest(field_html=field_html):
                self.assertEqual(plain_text_from_anki_html(field_html), expected)

    def test_literal_entity_text_is_escaped_once_and_round_trips(self):
        rendered = render_plain_text_anki_html("literal &lt; entity")

        self.assertEqual(rendered, "literal &amp;lt; entity")
        self.assertNotIn("&amp;amp;lt;", rendered)
        self.assertEqual(
            duplicate_key_from_anki_html(rendered),
            duplicate_key_from_plain_text("literal &lt; entity"),
        )

    def test_minimal_writer_renders_front_back_and_source_once(self):
        collection = FakeCollection()
        command = BeginnerWriteCommand(
            snapshot_id="snapshot",
            deck_id=7,
            deck_name="Test",
            note_type_id=11,
            note_type_name="Basic",
            front_field="Front",
            back_field="Back",
            source_field="Source",
            cards=(
                BeginnerWriteCardCommand(
                    candidate_id="candidate",
                    front="<tag>",
                    back="A & B\n<script>",
                    source="<img onerror=alert(1)>",
                ),
            ),
        )

        result = MinimalAnkiWriter(collection).write(command)

        self.assertEqual(result.success_count, 1)
        self.assertEqual(collection.created_note["Front"], "&lt;tag&gt;")
        self.assertEqual(
            collection.created_note["Back"],
            "A &amp; B<br>&lt;script&gt;",
        )
        self.assertEqual(
            collection.created_note["Source"],
            "&lt;img onerror=alert(1)&gt;",
        )
        self.assertNotIn("&amp;lt;tag&amp;gt;", collection.created_note["Front"])


if __name__ == "__main__":
    unittest.main()
