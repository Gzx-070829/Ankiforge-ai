import unittest

from ankiforge_ai.importers.md_importer import MarkdownChunk
from ankiforge_ai.ui.review_helpers import (
    ALL_CHUNKS_LABEL,
    cap_cards,
    cap_cards_per_chunk,
    chunks_for_combo_index,
    format_chunk_label,
    invert_flags,
    keep_items_by_flags,
    remove_items_by_flags,
    summarize_text,
    tags_from_text,
    tags_to_text,
)


class ReviewHelperTests(unittest.TestCase):
    def test_format_chunk_label(self):
        chunk = MarkdownChunk("过拟合", 2, "Body", "note.md")

        self.assertEqual(format_chunk_label(chunk), "H2 过拟合")

    def test_format_chunk_label_for_untitled(self):
        chunk = MarkdownChunk("", 0, "Body", "note.md")

        self.assertEqual(format_chunk_label(chunk), "Untitled Untitled")

    def test_chunks_for_combo_index_all(self):
        chunks = [
            MarkdownChunk("A", 1, "A body", "note.md"),
            MarkdownChunk("B", 2, "B body", "note.md"),
        ]

        selected, label = chunks_for_combo_index(chunks, 0, current_only=False)

        self.assertEqual(selected, chunks)
        self.assertEqual(label, ALL_CHUNKS_LABEL)

    def test_chunks_for_combo_index_current(self):
        chunks = [
            MarkdownChunk("A", 1, "A body", "note.md"),
            MarkdownChunk("B", 2, "B body", "note.md"),
        ]

        first, first_label = chunks_for_combo_index(chunks, 1, current_only=True)
        second, second_label = chunks_for_combo_index(chunks, 2, current_only=True)

        self.assertEqual(first, [chunks[0]])
        self.assertEqual(first_label, "H1 A")
        self.assertEqual(second, [chunks[1]])
        self.assertEqual(second_label, "H2 B")

    def test_chunks_for_combo_index_requires_heading_for_current(self):
        chunks = [MarkdownChunk("A", 1, "A body", "note.md")]

        selected, label = chunks_for_combo_index(chunks, 0, current_only=True)

        self.assertEqual(selected, [])
        self.assertEqual(label, "")

    def test_cap_cards(self):
        self.assertEqual(cap_cards(["a", "b", "c", "d", "e"], 3), ["a", "b", "c"])

    def test_cap_cards_per_chunk_caps_each_batch(self):
        capped = cap_cards_per_chunk(
            [
                ["a1", "a2", "a3", "a4", "a5"],
                ["b1", "b2", "b3", "b4"],
            ],
            3,
        )

        self.assertEqual(capped, ["a1", "a2", "a3", "b1", "b2", "b3"])

    def test_summarize_text_collapses_whitespace_and_truncates(self):
        self.assertEqual(summarize_text("A\n  B\tC", 20), "A B C")
        self.assertEqual(summarize_text("abcdefghij", 7), "abcd...")

    def test_tags_text_roundtrip_helpers(self):
        self.assertEqual(tags_to_text(["ai", "", "ml"]), "ai ml")
        self.assertEqual(
            tags_from_text("ai, ml；机器学习\nai"),
            ["ai", "ml", "机器学习"],
        )

    def test_invert_flags(self):
        self.assertEqual(invert_flags([True, False, True]), [False, True, False])

    def test_remove_items_by_flags(self):
        remaining, removed = remove_items_by_flags(["a", "b", "c"], [True, False, True])

        self.assertEqual(remaining, ["b"])
        self.assertEqual(removed, 2)

    def test_keep_items_by_flags(self):
        remaining, removed = keep_items_by_flags(["a", "b", "c"], [True, False, True])

        self.assertEqual(remaining, ["a", "c"])
        self.assertEqual(removed, 1)


if __name__ == "__main__":
    unittest.main()
