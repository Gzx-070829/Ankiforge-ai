import unittest

from ankiforge_ai.document import SourceLocation
from ankiforge_ai.ui.source_location_presenter import present_source_location


class SourceLocationPresenterTests(unittest.TestCase):
    def test_short_english_chips_cover_native_location_types(self):
        cases = (
            (SourceLocation(page=6), "Page 6"),
            (SourceLocation(slide=4), "Slide 4"),
            (
                SourceLocation(sheet="Results", row_start=2),
                'Sheet "Results", Row 2',
            ),
            (SourceLocation(section="Chapter 3"), "Chapter 3"),
            (SourceLocation(notebook_cell=7), "Cell 7"),
            (SourceLocation(timestamp_start=62.5), "01:02"),
            (SourceLocation(line_start=10, line_end=14), "Lines 10–14"),
        )
        for location, expected in cases:
            with self.subTest(expected=expected):
                view = present_source_location(
                    location,
                    "A bounded source block.",
                    language="en",
                )
                self.assertEqual(view.chip, expected)

    def test_short_chinese_chips_are_localized(self):
        cases = (
            (SourceLocation(page=6), "第 6 页"),
            (SourceLocation(slide=4), "第 4 张幻灯片"),
            (
                SourceLocation(sheet="Results", row_start=2),
                "工作表“Results”，第 2 行",
            ),
            (SourceLocation(notebook_cell=7), "第 7 个单元格"),
            (SourceLocation(timestamp_start=62.5), "01:02"),
        )
        for location, expected in cases:
            with self.subTest(expected=expected):
                view = present_source_location(
                    location,
                    "受限的来源片段。",
                    language="zh",
                )
                self.assertEqual(view.chip, expected)

    def test_file_label_is_included_before_location_without_exposing_paths(self):
        en = present_source_location(
            SourceLocation(file_label="lecture.pdf", page=6),
            "Evidence",
            language="en",
        )
        zh = present_source_location(
            SourceLocation(file_label="讲义.pdf", slide=4),
            "证据",
            language="zh",
        )
        file_only = present_source_location(
            SourceLocation(file_label="notes.md"),
            "Evidence",
            language="en",
        )

        self.assertEqual(en.chip, "lecture.pdf · Page 6")
        self.assertEqual(zh.chip, "讲义.pdf · 第 4 张幻灯片")
        self.assertEqual(file_only.chip, "notes.md")
        for chip in (en.chip, zh.chip, file_only.chip):
            self.assertNotIn("/", chip)
            self.assertNotIn("\\", chip)

    def test_snippet_is_whitespace_normalized_bounded_and_never_reads_a_file(self):
        private_path = "C:/Users/private/Documents/secret.txt"
        text = "  First line.\n\n" + ("evidence " * 80) + private_path

        view = present_source_location(
            SourceLocation(page=1),
            text,
            language="en",
            max_snippet_chars=120,
        )

        self.assertLessEqual(len(view.snippet), 120)
        self.assertNotIn("\n", view.snippet)
        self.assertTrue(view.snippet.endswith("…"))
        self.assertNotIn(private_path, view.snippet)
        self.assertEqual(view.action_label, "View source snippet")

    def test_unknown_location_uses_bilingual_safe_fallback(self):
        en = present_source_location(None, "Evidence", language="en")
        zh = present_source_location(None, "证据", language="zh")

        self.assertEqual(en.chip, "Source")
        self.assertEqual(zh.chip, "来源")

    def test_presenter_rejects_unbounded_or_invalid_inputs(self):
        with self.assertRaisesRegex(ValueError, "max_snippet_chars"):
            present_source_location(None, "text", max_snippet_chars=10)
        with self.assertRaisesRegex(ValueError, "language"):
            present_source_location(None, "text", language="fr")
        with self.assertRaisesRegex(TypeError, "block_text"):
            present_source_location(None, object())


if __name__ == "__main__":
    unittest.main()
