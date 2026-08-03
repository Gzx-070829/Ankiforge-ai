import unittest

from ankiforge_ai.document import (
    BlockKind,
    DocumentBlock,
    DocumentIR,
    DocumentSection,
    SourceLocation,
    SourceSpan,
)
from ankiforge_ai.document.source_spans import source_span_from_chunk
from ankiforge_ai.intelligence import (
    GenerationStage,
    IntelligenceLevel,
    analyze_document,
    start_chunk,
    succeed_chunk,
    transition_run,
)
from ankiforge_ai.intelligence.chunking import chunk_document
from ankiforge_ai.intelligence.chunking.models import DocumentChunk
from ankiforge_ai.pipeline.generation_settings import GenerationSettings
from ankiforge_ai.ui.beginner_flow_models import BeginnerFlowSession
from ankiforge_ai.ui.document_import_queue import DocumentImportWorkerResult
from ankiforge_ai.ui.source_location_presenter import present_source_location
from ankiforge_ai.ui.universal_document_generation_adapter import (
    build_imported_generation_run,
    drafts_from_generation_run,
)


class SourceSpanTests(unittest.TestCase):
    def test_single_location_chunk_keeps_only_honest_safe_precision(self):
        chunk = DocumentChunk(
            chunk_id="chunk-0000000000000001",
            document_id="doc-lecture",
            sequence=0,
            section_id="section-energy",
            heading_path=("Energy",),
            text="ATP stores immediately usable cellular energy.",
            block_ids=("block-atp",),
            block_kinds=(BlockKind.PARAGRAPH,),
            source_locations=(
                SourceLocation(
                    file_label="lecture.pdf",
                    page=6,
                ),
            ),
        )

        span = source_span_from_chunk(
            chunk,
            source_label="C:\\Users\\private\\lecture.pdf",
        )

        self.assertEqual(span.document_id, "doc-lecture")
        self.assertEqual(span.source_label, "lecture.pdf")
        self.assertEqual(span.locator_kind, "page")
        self.assertEqual(span.locator_value, "6")
        self.assertEqual(span.block_id, "block-atp")
        self.assertEqual(span.display_label, "lecture.pdf · page 6")
        self.assertNotIn("Users", repr(span))
        self.assertNotIn(chunk.text, repr(span))

    def test_multiple_locations_degrade_without_inventing_a_page_or_block(self):
        chunk = DocumentChunk(
            chunk_id="chunk-0000000000000002",
            document_id="doc-notes",
            sequence=0,
            section_id="section-combined",
            heading_path=("Combined",),
            text="Combined source text.",
            block_ids=("block-one", "block-two"),
            block_kinds=(BlockKind.PARAGRAPH, BlockKind.PARAGRAPH),
            source_locations=(
                SourceLocation(page=2),
                SourceLocation(page=3),
            ),
        )

        span = source_span_from_chunk(chunk, source_label="notes.pdf")

        self.assertEqual(span.locator_kind, "document")
        self.assertEqual(span.locator_value, "doc-notes")
        self.assertIsNone(span.block_id)
        self.assertNotIn("page", span.display_label)

    def test_safe_dict_round_trip_and_localized_presenter(self):
        span = SourceSpan(
            document_id="doc-sheet",
            source_label="table.xlsx",
            locator_kind="row",
            locator_value="2-4",
            block_id="block-table",
            char_start=10,
            char_end=24,
            display_label="table.xlsx · rows 2–4",
        )

        restored = SourceSpan.from_safe_dict(span.to_safe_dict())
        view = present_source_location(restored, "bounded evidence", language="zh")

        self.assertEqual(restored, span)
        self.assertEqual(view.chip, "table.xlsx · 第 2–4 行")
        self.assertEqual(view.snippet, "bounded evidence")

    def test_invalid_identifiers_offsets_and_locator_values_are_rejected(self):
        cases = (
            {"document_id": "../private", "source_label": "notes.md"},
            {
                "document_id": "doc-safe",
                "source_label": "notes.md",
                "locator_kind": "page",
                "locator_value": "C:\\Users\\private\\notes.md",
            },
            {
                "document_id": "doc-safe",
                "source_label": "notes.md",
                "char_start": 20,
                "char_end": 10,
            },
        )
        for values in cases:
            with self.subTest(values=values):
                with self.assertRaises((TypeError, ValueError)):
                    SourceSpan(**values)

    def test_universal_generation_carries_span_through_edit_copy_and_restore(self):
        location = SourceLocation(file_label="lecture.pdf", page=4)
        document = DocumentIR(
            schema_version=1,
            document_id="doc-source-span",
            title="Energy",
            language_hint="en",
            source_type="pdf",
            source_label="lecture.pdf",
            sections=(
                DocumentSection(
                    section_id="section-energy",
                    heading="Energy",
                    location=location,
                    blocks=(
                        DocumentBlock(
                            block_id="block-atp",
                            kind=BlockKind.PARAGRAPH,
                            text="ATP stores immediately usable cellular energy.",
                            location=location,
                        ),
                    ),
                ),
            ),
            original_char_count=45,
            extracted_char_count=45,
        )
        analysis = analyze_document(document)
        chunks = chunk_document(document)
        imported = DocumentImportWorkerResult(
            document=document,
            file_type="pdf",
            importer_name="PDF fallback fixture",
            analysis=analysis,
            chunks=chunks,
        )
        run = build_imported_generation_run(
            (imported,),
            generation_settings=GenerationSettings(),
            level=IntelligenceLevel.STANDARD,
            request_id=1,
        )
        run = transition_run(run, GenerationStage.PLANNING)
        run = transition_run(run, GenerationStage.GENERATING)
        chunk_id = run.chunks[0].chunk_id
        point_id = run.plan.points[0].point_id
        run = succeed_chunk(
            start_chunk(run, chunk_id),
            chunk_id,
            (
                {
                    "candidate_id": "card-source-span",
                    "point_id": point_id,
                    "chunk_id": chunk_id,
                    "front": "What does ATP store?",
                    "back": "Immediately usable cellular energy.",
                    "source_excerpt": "ATP stores immediately usable cellular energy.",
                },
            ),
        )

        drafts = drafts_from_generation_run(run)

        self.assertEqual(len(drafts), 1)
        self.assertIsInstance(drafts[0].source_span, SourceSpan)
        self.assertEqual(drafts[0].source_span.document_id, "doc-source-span")
        self.assertEqual(drafts[0].source_span.locator_kind, "page")
        session = BeginnerFlowSession()
        session.update_material("ATP stores energy.")
        session.begin_ai_candidate_generation()
        session.apply_ai_candidate_card_drafts(drafts)
        candidate_id = session.candidate_card_previews[0].id
        original_span = session.candidate_card_previews[0].source_span
        session.replace_candidate_content(candidate_id, "ATP stores what?", "Energy.")
        self.assertEqual(session.candidate_card_previews[0].source_span, original_span)
        copied_id = session.copy_candidate(candidate_id)
        copied = next(item for item in session.candidate_card_previews if item.id == copied_id)
        self.assertEqual(copied.source_span, original_span)
        session.restore_candidate_content(candidate_id)
        self.assertEqual(session.candidate_card_previews[0].source_span, original_span)


if __name__ == "__main__":
    unittest.main()
