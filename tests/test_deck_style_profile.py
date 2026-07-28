from dataclasses import FrozenInstanceError
from collections.abc import Mapping
import unittest

from ankiforge_ai.intelligence.deck_style import (
    DEFAULT_DECK_STYLE_MAX_NOTES,
    REAL_DECK_STYLE_SAMPLING_ENABLED,
    DeckStyleProfile,
    build_deck_style_query,
    summarize_deck_style,
)


class GuardedNotes:
    def __init__(self, notes, hard_limit):
        self.notes = notes
        self.hard_limit = hard_limit
        self.yield_count = 0

    def __iter__(self):
        for note in self.notes:
            self.yield_count += 1
            if self.yield_count > self.hard_limit:
                raise AssertionError("note source consumed beyond the approved cap")
            yield note


class ExplodingNotes:
    def __iter__(self):
        raise AssertionError("disabled deck style must not read notes")


class GuardedFields(Mapping):
    def __init__(self):
        self.yield_count = 0

    def __len__(self):
        return 0

    def __iter__(self):
        for index in range(100):
            self.yield_count += 1
            if self.yield_count > 33:
                raise AssertionError("field mapping consumed beyond max+1")
            yield f"Field-{index}"

    def __getitem__(self, key):
        return "value"


class DeckStyleProfileTests(unittest.TestCase):
    def test_disabled_default_does_not_read_notes_or_name_a_deck(self):
        query = build_deck_style_query()
        profile = summarize_deck_style(ExplodingNotes(), query=query)

        self.assertFalse(query.enabled)
        self.assertFalse(profile.enabled)
        self.assertIsNone(query.selected_deck_id)
        self.assertEqual(profile.sampled_note_count, 0)
        self.assertEqual(profile.field_names, ())
        self.assertEqual(profile.to_provider_payload(), {"enabled": False})

    def test_query_is_selected_deck_only_read_only_and_at_most_twenty(self):
        query = build_deck_style_query(
            enabled=True,
            selected_deck_id=123,
            selected_deck_label="Biology::Cell Energy",
            max_notes=20,
        )

        self.assertEqual(query.selected_deck_id, 123)
        self.assertEqual(query.selected_deck_label, "Biology::Cell Energy")
        self.assertEqual(query.max_notes, DEFAULT_DECK_STYLE_MAX_NOTES)
        self.assertFalse(query.include_descendants)
        self.assertFalse(query.allow_full_scan)
        self.assertFalse(query.allow_mutation)
        self.assertTrue(query.aggregate_only)

    def test_summarizer_reads_no_more_than_twenty_notes_without_mutation(self):
        original = [
            {
                "fields": {"Front": f"Question {index}", "Back": f"Answer {index}"},
                "front_field": "Front",
                "back_field": "Back",
                "tags": ["biology"],
                "template_hint": "basic",
            }
            for index in range(25)
        ]
        guarded = GuardedNotes(original, hard_limit=20)
        query = build_deck_style_query(
            enabled=True,
            selected_deck_id=123,
            selected_deck_label="Biology",
        )

        profile = summarize_deck_style(guarded, query=query)

        self.assertEqual(guarded.yield_count, 20)
        self.assertEqual(profile.sampled_note_count, 20)
        self.assertEqual(original[0]["fields"]["Front"], "Question 0")
        self.assertEqual(original[0]["tags"], ["biology"])

    def test_profile_contains_only_hand_checked_aggregate_statistics(self):
        notes = (
            {
                "fields": {
                    "Front": "<b>ATP?</b>",
                    "Back": "- Energy\n- Carrier",
                },
                "front_field": "Front",
                "back_field": "Back",
                "tags": ["biology", "exam"],
                "template_hint": "basic",
            },
            {
                "fields": {
                    "Front": "What is DNA?",
                    "Back": "Genetic material",
                    "Extra": "chapter one",
                },
                "front_field": "Front",
                "back_field": "Back",
                "tags": ["biology"],
                "template_hint": "basic",
            },
        )
        query = build_deck_style_query(
            enabled=True,
            selected_deck_id=123,
            selected_deck_label="Biology",
        )

        profile = summarize_deck_style(notes, query=query)

        self.assertIsInstance(profile, DeckStyleProfile)
        self.assertEqual(profile.sampled_note_count, 2)
        self.assertEqual(profile.field_names, ("Front", "Back", "Extra"))
        self.assertEqual(profile.front_length_range, (4, 12))
        self.assertEqual(profile.back_length_range, (16, 18))
        self.assertEqual(profile.bullet_ratio, 0.5)
        self.assertEqual(profile.html_ratio, 0.5)
        self.assertEqual(
            profile.common_layout_patterns,
            ("plain", "bulleted", "html"),
        )
        self.assertEqual(profile.common_tags, ("biology", "exam"))
        self.assertEqual(profile.preferred_template_hints, ("basic",))

    def test_default_provider_payload_contains_aggregates_not_note_content(self):
        front_secret = "PRIVATE FRONT CONTENT"
        back_secret = "PRIVATE BACK CONTENT"
        query = build_deck_style_query(
            enabled=True,
            selected_deck_id=123,
            selected_deck_label="Biology",
        )
        profile = summarize_deck_style(
            (
                {
                    "fields": {"Front": front_secret, "Back": back_secret},
                    "front_field": "Front",
                    "back_field": "Back",
                    "tags": ["biology"],
                    "template_hint": "basic",
                },
            ),
            query=query,
        )

        payload = profile.to_provider_payload()
        rendered = repr(profile)

        self.assertEqual(payload["sampled_note_count"], 1)
        self.assertEqual(payload["field_names"], ("Front", "Back"))
        self.assertFalse(payload["examples_included"])
        self.assertNotIn(front_secret, repr(payload))
        self.assertNotIn(back_secret, repr(payload))
        self.assertNotIn(front_secret, rendered)
        self.assertNotIn(back_secret, rendered)
        self.assertNotIn("123", repr(payload))

    def test_profile_is_frozen_and_owns_immutable_aggregate_sequences(self):
        profile = DeckStyleProfile(
            enabled=True,
            selected_deck_id=123,
            selected_deck_label="Biology",
            sampled_note_count=1,
            field_names=["Front", "Back"],
            front_length_range=(4, 4),
            back_length_range=(6, 6),
            bullet_ratio=0.0,
            html_ratio=0.0,
            common_layout_patterns=["plain"],
            common_tags=["biology"],
            preferred_template_hints=["basic"],
        )

        self.assertIsInstance(profile.field_names, tuple)
        self.assertIsInstance(profile.common_tags, tuple)
        with self.assertRaises(FrozenInstanceError):
            profile.sampled_note_count = 2

    def test_html_only_note_is_not_mislabeled_as_plain_layout(self):
        query = build_deck_style_query(
            enabled=True,
            selected_deck_id=123,
            selected_deck_label="Biology",
        )

        profile = summarize_deck_style(
            (
                {
                    "fields": {
                        "Front": "<b>Question</b>",
                        "Back": "<i>Answer</i>",
                    },
                    "front_field": "Front",
                    "back_field": "Back",
                    "tags": [],
                    "template_hint": "basic",
                },
            ),
            query=query,
        )

        self.assertEqual(profile.common_layout_patterns, ("html",))

    def test_unsafe_deck_labels_invalid_counts_and_real_sampling_are_rejected(self):
        for label in (
            "C:\\Users\\private\\deck",
            "/private/deck",
            "../private",
            "bad\x00label",
            "x" * 121,
        ):
            with self.subTest(label=label):
                with self.assertRaisesRegex(ValueError, "deck label"):
                    build_deck_style_query(
                        enabled=True,
                        selected_deck_id=123,
                        selected_deck_label=label,
                    )
        for count in (True, 0, 21, 1.5):
            with self.subTest(count=count):
                with self.assertRaises((TypeError, ValueError)):
                    build_deck_style_query(
                        enabled=True,
                        selected_deck_id=123,
                        selected_deck_label="Biology",
                        max_notes=count,
                    )
        self.assertFalse(REAL_DECK_STYLE_SAMPLING_ENABLED)
        with self.assertRaisesRegex(ValueError, "real sampling"):
            build_deck_style_query(
                enabled=True,
                selected_deck_id=123,
                selected_deck_label="Biology",
                enable_real_sampling=True,
            )

    def test_note_schema_is_bounded_and_requires_named_front_back_fields(self):
        query = build_deck_style_query(
            enabled=True,
            selected_deck_id=123,
            selected_deck_label="Biology",
        )
        invalid_notes = (
            {"fields": {"Front": "Q"}, "front_field": "Front", "back_field": "Back"},
            {"fields": {"Front": "Q", "Back": "A"}, "front_field": 1, "back_field": "Back"},
            {"fields": {"Front": "Q", "Back": object()}, "front_field": "Front", "back_field": "Back"},
        )

        for note in invalid_notes:
            with self.subTest(note=note):
                with self.assertRaises((TypeError, ValueError)):
                    summarize_deck_style((note,), query=query)

    def test_field_mapping_and_nested_note_values_are_capped_before_materialization(self):
        query = build_deck_style_query(
            enabled=True,
            selected_deck_id=123,
            selected_deck_label="Biology",
        )
        fields = GuardedFields()
        with self.assertRaisesRegex(ValueError, "note fields"):
            summarize_deck_style(
                (
                    {
                        "fields": fields,
                        "front_field": "Field-0",
                        "back_field": "Field-1",
                        "tags": (),
                    },
                ),
                query=query,
            )
        self.assertEqual(fields.yield_count, 33)

        invalid_nested = (
            {
                "fields": {"Front": "Q", "Back": "x" * 12_001},
                "front_field": "Front",
                "back_field": "Back",
                "tags": (),
            },
            {
                "fields": {"Front": "Q", "Back": "A"},
                "front_field": "Front",
                "back_field": "Back",
                "tags": tuple(f"tag-{index}" for index in range(17)),
            },
        )
        for note in invalid_nested:
            with self.subTest(kind=len(note["tags"])):
                with self.assertRaises(ValueError):
                    summarize_deck_style((note,), query=query)


if __name__ == "__main__":
    unittest.main()
