import unittest

from ankiforge_ai.pipeline.generation_settings import GenerationSettings
from ankiforge_ai.pipeline.write_traceability import (
    LastWriteBatchRecord,
    SourceType,
    build_default_tags,
    build_write_result_summary,
    build_write_summary,
    normalize_tag,
    safe_source_label,
    source_type_from_path,
)


class WriteTraceabilityTests(unittest.TestCase):
    def test_source_types_map_to_short_bilingual_labels(self):
        expected = {
            SourceType.PASTE: ("粘贴文本", "Pasted text"),
            SourceType.MARKDOWN: ("Markdown 导入", "Markdown import"),
            SourceType.TXT: ("TXT 导入", "TXT import"),
            SourceType.DOCX: ("DOCX 导入", "Imported from DOCX"),
            SourceType.PDF_FALLBACK: ("PDF fallback", "PDF fallback"),
            SourceType.UNKNOWN: ("导入材料", "Imported material"),
        }

        for source_type, (zh, en) in expected.items():
            with self.subTest(source_type=source_type):
                self.assertEqual(safe_source_label(source_type, "zh"), zh)
                self.assertEqual(safe_source_label(source_type, "en"), en)

    def test_path_detection_returns_type_without_retaining_private_path(self):
        windows = r"C:\Users\someone\private\notes.docx"
        posix = "/home/someone/private/topic.md"

        self.assertEqual(source_type_from_path(windows), SourceType.DOCX)
        self.assertEqual(source_type_from_path(posix), SourceType.MARKDOWN)
        rendered = repr(source_type_from_path(windows)) + safe_source_label(
            source_type_from_path(posix), "en"
        )
        self.assertNotIn("someone", rendered)
        self.assertNotIn("private", rendered)

    def test_normalize_tag_removes_dangerous_characters_and_limits_length(self):
        self.assertEqual(normalize_tag(" Mode: Exam / Final "), "mode-exam-final")
        self.assertEqual(normalize_tag("a" * 100), "a" * 48)
        self.assertEqual(normalize_tag("../private"), "private")
        self.assertEqual(normalize_tag(""), "")

    def test_default_tags_include_mode_and_source(self):
        tags = build_default_tags(
            GenerationSettings(card_mode="quick_review"),
            SourceType.DOCX,
        )

        self.assertEqual(
            tags,
            (
                "ankiforge",
                "ankiforge-ai",
                "mode-quick-review",
                "source-docx",
            ),
        )

    def test_prewrite_summary_contains_required_explainable_fields(self):
        summary = build_write_summary(
            target_deck="Test Deck",
            note_type="Basic",
            field_mapping=("Front → Front", "Back → Back", "Source → Extra"),
            source_label="Imported from DOCX",
            cards_to_write=3,
            warning_count=2,
            blocking_count=0,
            duplicate_behavior="skip_possible_duplicates",
            tags=("ankiforge", "mode-concept"),
        )

        self.assertEqual(summary.cards_to_write, 3)
        self.assertEqual(summary.warning_count, 2)
        self.assertEqual(summary.blocking_count, 0)
        self.assertEqual(summary.source_label, "Imported from DOCX")
        self.assertIn("ankiforge", summary.tags)
        self.assertNotIn("Test Deck", repr(summary))

    def test_postwrite_summary_and_batch_record_counts_are_safe(self):
        result = build_write_result_summary(
            written_count=2,
            skipped_duplicate_count=1,
            failed_count=0,
            target_deck="Test Deck",
            tags=("ankiforge", "mode-concept"),
        )
        batch = LastWriteBatchRecord(
            snapshot_id="snapshot-1",
            created_note_ids=(101, 102),
            requested_count=3,
            skipped_count=1,
            failed_count=0,
            target_deck="Test Deck",
            tags=result.tags,
            source_type=SourceType.PASTE,
        )

        self.assertEqual(result.written_count, 2)
        self.assertEqual(batch.created_note_ids, (101, 102))
        self.assertEqual(batch.written_count, 2)
        self.assertNotIn("Test Deck", repr(batch))
        self.assertEqual(batch.to_safe_dict()["created_note_count"], 2)

    def test_traceability_models_reject_paths_and_secret_markers(self):
        for source_label in (
            r"C:\Users\someone\notes.docx",
            "/home/someone/notes.md",
            "Bearer abcdef",
            "sk-real-looking-value",
        ):
            with self.subTest(source_label=source_label):
                with self.assertRaises(ValueError):
                    build_write_summary(
                        target_deck="Test",
                        note_type="Basic",
                        field_mapping=("Front → Front", "Back → Back"),
                        source_label=source_label,
                        cards_to_write=1,
                        warning_count=0,
                        blocking_count=0,
                        duplicate_behavior="skip_possible_duplicates",
                        tags=("ankiforge",),
                    )

    def test_batch_record_requires_unique_positive_note_ids(self):
        common = dict(
            snapshot_id="snapshot",
            requested_count=2,
            skipped_count=0,
            failed_count=0,
            target_deck="Test",
            tags=("ankiforge",),
            source_type=SourceType.PASTE,
        )
        for note_ids in ((1, 1), (0,), (-1,), (True,)):
            with self.subTest(note_ids=note_ids):
                with self.assertRaises(ValueError):
                    LastWriteBatchRecord(created_note_ids=note_ids, **common)


if __name__ == "__main__":
    unittest.main()
