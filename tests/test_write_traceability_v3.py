import unittest

from ankiforge_ai.pipeline.write_traceability import (
    LastWriteBatchRecord,
    SourceType,
    build_write_result_summary,
    create_last_write_batch_record,
)


class WriteTraceabilityV3Tests(unittest.TestCase):
    def test_existing_batch_constructor_remains_compatible(self):
        record = LastWriteBatchRecord(
            snapshot_id="snapshot-old",
            created_note_ids=(101,),
            requested_count=1,
            skipped_count=0,
            failed_count=0,
            target_deck="Test Deck",
            tags=("ankiforge",),
            source_type=SourceType.PASTE,
        )

        self.assertEqual(record.batch_id, "")
        self.assertEqual(record.timestamp_utc, "")
        self.assertEqual(record.note_type, "")
        self.assertEqual(record.source_label, "")

    def test_factory_creates_utc_batch_metadata_and_safe_source_label(self):
        record = create_last_write_batch_record(
            snapshot_id="snapshot-new",
            created_note_ids=(101, 102),
            requested_count=3,
            skipped_count=1,
            failed_count=0,
            target_deck="Private Test Deck",
            note_type="Basic",
            tags=("ankiforge", "mode-concept"),
            source_type=SourceType.DOCX,
        )

        self.assertRegex(record.batch_id, r"^batch-[0-9a-f]{32}$")
        self.assertRegex(
            record.timestamp_utc,
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$",
        )
        self.assertEqual(record.note_type, "Basic")
        self.assertEqual(record.source_label, "Imported from DOCX")

    def test_factory_accepts_explicit_metadata_for_deterministic_replay(self):
        record = create_last_write_batch_record(
            snapshot_id="snapshot-fixed",
            created_note_ids=(201,),
            requested_count=1,
            skipped_count=0,
            failed_count=0,
            target_deck="Test Deck",
            note_type="Basic::Review",
            tags=("ankiforge",),
            source_type=SourceType.MARKDOWN,
            source_label="Markdown import",
            batch_id="batch-test-001",
            timestamp_utc="2026-07-15T08:30:00Z",
        )

        self.assertEqual(record.batch_id, "batch-test-001")
        self.assertEqual(record.timestamp_utc, "2026-07-15T08:30:00Z")
        self.assertEqual(record.source_label, "Markdown import")

    def test_postwrite_summary_carries_trace_metadata_with_old_builder(self):
        result = build_write_result_summary(
            written_count=2,
            skipped_duplicate_count=1,
            failed_count=0,
            target_deck="Private Test Deck",
            note_type="Basic",
            source_label="Pasted text",
            timestamp_utc="2026-07-15T08:30:00Z",
            batch_id="batch-test-001",
            tags=("ankiforge",),
        )

        self.assertEqual(result.note_type, "Basic")
        self.assertEqual(result.source_label, "Pasted text")
        self.assertEqual(result.timestamp_utc, "2026-07-15T08:30:00Z")
        self.assertEqual(result.batch_id, "batch-test-001")
        self.assertEqual(result.to_safe_dict()["written_count"], 2)

    def test_raw_note_ids_never_enter_safe_repr_or_safe_dict(self):
        record = create_last_write_batch_record(
            snapshot_id="snapshot-private",
            created_note_ids=(987654321, 123456789),
            requested_count=2,
            skipped_count=0,
            failed_count=0,
            target_deck="Private Test Deck",
            note_type="Private Note Type",
            tags=("ankiforge",),
            source_type=SourceType.PASTE,
            batch_id="batch-safe",
            timestamp_utc="2026-07-15T08:30:00Z",
        )
        rendered = repr(record) + str(record.to_safe_dict())

        self.assertNotIn("987654321", rendered)
        self.assertNotIn("123456789", rendered)
        self.assertNotIn("Private Test Deck", repr(record))
        self.assertNotIn("Private Note Type", repr(record))
        self.assertEqual(record.to_safe_dict()["created_note_count"], 2)

    def test_trace_metadata_rejects_paths_secrets_and_non_utc_timestamps(self):
        common = dict(
            snapshot_id="snapshot",
            created_note_ids=(1,),
            requested_count=1,
            skipped_count=0,
            failed_count=0,
            target_deck="Test",
            note_type="Basic",
            tags=("ankiforge",),
            source_type=SourceType.PASTE,
            batch_id="batch-safe",
            timestamp_utc="2026-07-15T08:30:00Z",
        )
        invalid = (
            {"batch_id": "sk-real-looking-value"},
            {"batch_id": r"C:\private\batch"},
            {"note_type": r"C:\private\NoteType"},
            {"source_label": "/home/private/notes.md"},
            {"timestamp_utc": "2026-07-15T08:30:00+08:00"},
            {"timestamp_utc": "not-a-time"},
        )

        for override in invalid:
            with self.subTest(override=override):
                values = dict(common)
                values.update(override)
                with self.assertRaises(ValueError):
                    create_last_write_batch_record(**values)


if __name__ == "__main__":
    unittest.main()
