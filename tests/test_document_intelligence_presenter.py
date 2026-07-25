import unittest
from dataclasses import replace

from ankiforge_ai.document import (
    BlockKind,
    DocumentBlock,
    DocumentIR,
    DocumentSection,
)
from ankiforge_ai.intelligence import (
    GenerationStage,
    IntelligenceLevel,
    analyze_document,
    chunk_document,
    create_generation_run,
    estimate_generation,
    fail_chunk,
    start_chunk,
    transition_run,
)
from ankiforge_ai.ui.document_intelligence_presenter import (
    present_auto_recommendation,
    present_batch_intelligence_estimate,
    present_document_summary,
    present_generation_progress,
    present_intelligence_estimate,
    stage_label,
)


def _fixture():
    blocks = (
        DocumentBlock(
            "block-heading",
            BlockKind.HEADING,
            "Join strategies",
        ),
        DocumentBlock(
            "block-code",
            BlockKind.CODE,
            "SELECT * FROM users JOIN orders ON users.id = orders.user_id;",
        ),
        DocumentBlock(
            "block-table",
            BlockKind.TABLE,
            "Join | Use\nINNER | matches\nLEFT | all left rows",
        ),
    )
    document = DocumentIR(
        schema_version=1,
        document_id="doc-presenter",
        title="SQL notes",
        language_hint="en",
        source_type="markdown",
        source_label="sql-notes.md",
        sections=(
            DocumentSection(
                "section-joins",
                "Joins",
                blocks=blocks,
            ),
        ),
        original_char_count=sum(len(block.text) for block in blocks),
        extracted_char_count=sum(len(block.text) for block in blocks),
    )
    analysis = analyze_document(document)
    chunks = chunk_document(document)
    return document, analysis, chunks


class DocumentIntelligencePresenterTests(unittest.TestCase):
    def test_document_summary_is_bilingual_bounded_and_path_free(self):
        document, analysis, _chunks = _fixture()

        zh = present_document_summary(document, analysis, language="zh")
        en = present_document_summary(document, analysis, language="en")

        self.assertEqual(zh.title, "sql-notes.md")
        self.assertIn("1 个章节", zh.detail)
        self.assertIn("3 个内容块", zh.detail)
        self.assertIn("1 section", en.detail)
        self.assertIn("3 blocks", en.detail)
        rendered = repr(zh) + repr(en)
        self.assertNotIn("C:\\", rendered)
        self.assertNotIn("doc-presenter", rendered)
        self.assertNotIn("DocumentAnalysis", rendered)

    def test_auto_recommendation_localizes_recommended_modes(self):
        document, analysis, _chunks = _fixture()
        zh = present_auto_recommendation(analysis, language="zh")
        en = present_auto_recommendation(analysis, language="en")

        self.assertEqual(zh.label, "Auto 推荐")
        self.assertEqual(en.label, "Auto recommendation")
        self.assertTrue(zh.modes)
        self.assertTrue(en.modes)
        self.assertNotIn("code_understanding", repr(zh))
        self.assertNotIn("table_relationship", repr(en))

    def test_fast_standard_and_deep_estimates_show_calls_cards_and_confirmation(self):
        _document, analysis, chunks = _fixture()
        views = []
        for level in IntelligenceLevel:
            estimate = estimate_generation(analysis, chunks, level=level)
            views.append(
                present_intelligence_estimate(estimate, language="en")
            )

        self.assertEqual(
            tuple(view.level_label for view in views),
            ("Fast", "Standard", "Deep"),
        )
        self.assertEqual(
            tuple(view.call_range for view in views),
            (
                "2 planned · up to 3 calls",
                "3 planned · up to 8 calls",
                "4 planned · up to 12 calls",
            ),
        )
        self.assertFalse(views[0].requires_confirmation)
        self.assertTrue(views[1].requires_confirmation)
        self.assertTrue(views[2].requires_confirmation)
        self.assertIn("planner", views[1].confirmation_text)
        self.assertIn("grouped generation", views[1].confirmation_text)
        self.assertIn("critic", views[2].confirmation_text)
        self.assertIn("only if needed", views[2].confirmation_text)
        one_chunk_standard = present_intelligence_estimate(
            replace(
                estimate_generation(
                    analysis,
                    chunks,
                    level=IntelligenceLevel.STANDARD,
                ),
                chunk_count=1,
            ),
            language="en",
        )
        one_chunk_deep = present_intelligence_estimate(
            replace(
                estimate_generation(
                    analysis,
                    chunks,
                    level=IntelligenceLevel.DEEP,
                ),
                chunk_count=1,
            ),
            language="en",
        )
        self.assertEqual(
            one_chunk_standard.call_range,
            "2 planned · up to 8 calls",
        )
        self.assertEqual(
            one_chunk_deep.call_range,
            "3 planned · up to 12 calls",
        )
        for view in views:
            self.assertIn("chunks", view.detail)
            self.assertIn("cards", view.detail)
            self.assertNotIn("$", view.detail)

    def test_card_estimates_are_capped_by_the_actual_full_run_card_limit(self):
        _document, analysis, chunks = _fixture()
        limits = {
            IntelligenceLevel.FAST: 3,
            IntelligenceLevel.STANDARD: 5,
            IntelligenceLevel.DEEP: 8,
        }
        for level, card_limit in limits.items():
            with self.subTest(level=level.value):
                estimate = replace(
                    estimate_generation(analysis, chunks, level=level),
                    estimated_card_min=10,
                    estimated_card_max=25,
                )
                view = present_intelligence_estimate(
                    estimate,
                    language="en",
                    card_limit=card_limit,
                )
                self.assertIn(
                    f"{card_limit}–{card_limit} cards",
                    view.detail,
                )

    def test_batch_estimate_keeps_overflow_visible_while_capping_cards(self):
        _document, analysis, chunks = _fixture()
        estimate = replace(
            estimate_generation(
                analysis,
                chunks,
                level=IntelligenceLevel.STANDARD,
            ),
            chunk_count=30,
            estimated_card_min=10,
            estimated_card_max=25,
        )

        view = present_batch_intelligence_estimate(
            (estimate, estimate),
            language="en",
            card_limit=5,
        )

        self.assertIn("60 chunks", view.detail)
        self.assertIn("5–5 cards", view.detail)

    def test_every_generation_stage_has_a_bilingual_user_label(self):
        for stage in GenerationStage:
            with self.subTest(stage=stage.value):
                zh = stage_label(stage, language="zh")
                en = stage_label(stage, language="en")
                self.assertTrue(zh)
                self.assertTrue(en)
                self.assertNotEqual(zh, stage.value)
                self.assertNotEqual(en, stage.value)
                self.assertNotIn("_", en)

    def test_partial_progress_retains_cards_and_exposes_explicit_failed_only_retry(self):
        document, _analysis, chunks = _fixture()
        if len(chunks) == 1:
            chunks = chunks + (replace(chunks[0], chunk_id="chunk-0123456789abcdef"),)
        run = create_generation_run(
            run_id="run-presenter",
            request_id=1,
            document_id=document.document_id,
            document_hash="a" * 64,
            document_snapshot=document,
            settings_snapshot={"level": "standard"},
            level=IntelligenceLevel.STANDARD,
            chunk_ids=tuple(chunk.chunk_id for chunk in chunks[:2]),
        )
        run = transition_run(run, GenerationStage.PLANNING)
        run = transition_run(run, GenerationStage.GENERATING)
        run = start_chunk(run, chunks[0].chunk_id)
        run = fail_chunk(
            run,
            chunks[0].chunk_id,
            reason_code="chunk_generation_failed",
        )

        view = present_generation_progress(run, language="en")

        self.assertEqual(view.stage_label, "Generating cards")
        self.assertEqual(view.failed_chunks, 1)
        self.assertTrue(view.show_retry_failed)
        self.assertEqual(view.retry_label, "Retry failed files only")
        for forbidden in (
            "chunk_generation_failed",
            chunks[0].chunk_id,
            "GenerationRun",
            "CallBudget",
        ):
            self.assertNotIn(forbidden, repr(view))


if __name__ == "__main__":
    unittest.main()
