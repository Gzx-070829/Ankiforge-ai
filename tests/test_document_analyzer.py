import unittest
from dataclasses import replace

from ankiforge_ai.document import (
    BlockKind,
    DocumentBlock,
    DocumentIR,
    DocumentSection,
    SourceLocation,
)
from ankiforge_ai.intelligence import analyze_document


def _document(*blocks, language_hint=None):
    return DocumentIR(
        schema_version=1,
        document_id="doc-analysis",
        title="Mixed study notes",
        language_hint=language_hint,
        source_type="markdown",
        source_label="study.md",
        sections=(
            DocumentSection(
                section_id="section-main",
                heading="Review",
                heading_path=("Review",),
                location=SourceLocation(file_label="study.md", section="Review"),
                blocks=tuple(blocks),
            ),
        ),
        original_char_count=sum(len(block.text) for block in blocks),
        extracted_char_count=sum(len(block.text) for block in blocks),
    )


class DocumentAnalyzerTests(unittest.TestCase):
    def test_reports_hand_derived_structural_and_semantic_signals(self):
        document = _document(
            DocumentBlock(
                "definition",
                BlockKind.PARAGRAPH,
                "Mitosis is a type of cell division that produces two daughter cells.",
            ),
            DocumentBlock(
                "comparison",
                BlockKind.PARAGRAPH,
                "Unlike meiosis, mitosis preserves chromosome number.",
            ),
            DocumentBlock(
                "process",
                BlockKind.LIST,
                "First copy DNA.\nThen align chromosomes.\nFinally divide the cell.",
            ),
            DocumentBlock(
                "formula",
                BlockKind.FORMULA,
                "density = mass / volume",
            ),
            DocumentBlock(
                "code",
                BlockKind.CODE,
                "def area(radius):\n    return 3.14 * radius ** 2",
            ),
            DocumentBlock(
                "table",
                BlockKind.TABLE,
                "Phase | Event\nG1 | Growth\nS | DNA replication",
            ),
            DocumentBlock(
                "transcript",
                BlockKind.TRANSCRIPT,
                "Welcome to today's review of cell division.",
                location=SourceLocation(
                    file_label="study.md",
                    timestamp_start=0.0,
                    timestamp_end=4.0,
                ),
            ),
            DocumentBlock(
                "bilingual",
                BlockKind.PARAGRAPH,
                "光合作用是指植物把光能转成化学能的过程。 Photosynthesis stores light energy.",
            ),
        )

        analysis = analyze_document(document)

        self.assertEqual(analysis.document_id, "doc-analysis")
        self.assertEqual(analysis.dominant_language, "mixed")
        self.assertEqual(analysis.document_kind, "mixed")
        self.assertEqual(analysis.section_count, 1)
        self.assertEqual(analysis.block_count, 8)
        self.assertEqual(analysis.definition_count, 2)
        self.assertEqual(analysis.comparison_count, 1)
        self.assertEqual(analysis.process_count, 1)
        self.assertEqual(analysis.formula_count, 1)
        self.assertEqual(analysis.code_block_count, 1)
        self.assertEqual(analysis.table_block_count, 1)
        self.assertEqual(analysis.transcript_block_count, 1)
        self.assertEqual(analysis.estimated_knowledge_points, 8)
        self.assertEqual(
            analysis.recommended_modes,
            (
                "code_understanding",
                "table_relationship",
                "transcript_summary_candidate",
                "formula_rule",
                "compare_contrast",
                "process_steps",
                "definition",
                "concept",
            ),
        )
        self.assertEqual(analysis.confidence, 0.98)

    def test_empty_document_is_bounded_and_has_a_conservative_fallback(self):
        analysis = analyze_document(_document())

        self.assertEqual(analysis.dominant_language, "unknown")
        self.assertEqual(analysis.document_kind, "empty")
        self.assertEqual(analysis.estimated_knowledge_points, 0)
        self.assertEqual(analysis.recommended_modes, ("concept",))
        self.assertEqual(analysis.confidence, 0.25)
        self.assertIn("analysis.empty_document", analysis.warnings)

    def test_empty_blocks_are_counted_without_becoming_knowledge_points(self):
        analysis = analyze_document(
            _document(DocumentBlock("empty", BlockKind.METADATA, ""))
        )

        self.assertEqual(analysis.block_count, 1)
        self.assertEqual(analysis.estimated_knowledge_points, 0)
        self.assertEqual(analysis.document_kind, "empty")
        self.assertIn("analysis.empty_document", analysis.warnings)

    def test_calendar_copula_and_single_next_are_not_learning_signals(self):
        analysis = analyze_document(
            _document(
                DocumentBlock(
                    "calendar",
                    BlockKind.PARAGRAPH,
                    "The meeting is Tuesday.",
                ),
                DocumentBlock(
                    "single-next",
                    BlockKind.PARAGRAPH,
                    "Next review the appendix.",
                ),
                DocumentBlock(
                    "zh-calendar",
                    BlockKind.PARAGRAPH,
                    "会议是在星期二举行。",
                ),
            )
        )

        self.assertEqual(analysis.definition_count, 0)
        self.assertEqual(analysis.process_count, 0)
        self.assertEqual(analysis.recommended_modes, ("concept",))

    def test_analysis_repr_contains_counts_but_not_source_text(self):
        source_body = "A private lesson body is a concise definition."
        analysis = analyze_document(
            _document(DocumentBlock("body", BlockKind.PARAGRAPH, source_body))
        )

        rendered = repr(analysis)
        self.assertIn("document_id='doc-analysis'", rendered)
        self.assertIn("blocks=1", rendered)
        self.assertNotIn(source_body, rendered)
        self.assertNotIn("C:\\Users\\", rendered)

    def test_analysis_constructor_rejects_unsafe_and_incoherent_values(self):
        analysis = analyze_document(
            _document(
                DocumentBlock(
                    "definition",
                    BlockKind.PARAGRAPH,
                    "Mitosis is a type of cell division.",
                )
            )
        )
        invalid_changes = (
            {"document_id": "C:\\Users\\private\\notes.md"},
            {"estimated_knowledge_points": 97},
            {"definition_count": analysis.block_count + 1},
            {"content_density": float("nan")},
            {"confidence": float("inf")},
            {"block_count": True},
            {"section_count": "1"},
        )

        for changes in invalid_changes:
            with self.subTest(changes=tuple(changes)):
                with self.assertRaises((TypeError, ValueError)):
                    replace(analysis, **changes)


if __name__ == "__main__":
    unittest.main()
