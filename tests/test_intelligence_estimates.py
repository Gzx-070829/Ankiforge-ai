import unittest
from dataclasses import replace

from ankiforge_ai.document import BlockKind, DocumentBlock, DocumentIR, DocumentSection
from ankiforge_ai.intelligence import (
    IntelligenceLevel,
    analyze_document,
    chunk_document,
    estimate_generation,
)
from ankiforge_ai.intelligence.planning import build_local_knowledge_plan


class _GuardedInfiniteChunks:
    def __init__(self, item):
        self.item = item
        self.yield_count = 0

    def __iter__(self):
        while True:
            self.yield_count += 1
            if self.yield_count > 49:
                raise AssertionError("consumer read beyond cap+1")
            yield self.item


def _estimate_fixture(section_count=5):
    sections = tuple(
        DocumentSection(
            section_id=f"estimate-{index}",
            heading=f"Topic {index}",
            blocks=(
                DocumentBlock(
                    f"estimate-block-{index}",
                    BlockKind.PARAGRAPH,
                    f"Concept {index} is supported by explicit source evidence.",
                ),
            ),
        )
        for index in range(section_count)
    )
    char_count = sum(len(section.blocks[0].text) for section in sections)
    document = DocumentIR(
        schema_version=1,
        document_id="doc-estimate",
        title="Estimate fixture",
        language_hint="en",
        source_type="text",
        source_label="estimate.txt",
        sections=sections,
        original_char_count=char_count,
        extracted_char_count=char_count,
    )
    analysis = analyze_document(document)
    chunks = chunk_document(document)
    plan = build_local_knowledge_plan(document, chunks, analysis)
    return analysis, chunks, plan


class IntelligenceEstimateTests(unittest.TestCase):
    def test_standard_is_default_with_exact_policy_range(self):
        analysis, chunks, plan = _estimate_fixture()

        estimate = estimate_generation(analysis, chunks, plan=plan)

        self.assertEqual(estimate.level, IntelligenceLevel.STANDARD)
        self.assertEqual(
            (estimate.estimated_call_min, estimate.estimated_call_max),
            (3, 8),
        )
        self.assertTrue(estimate.requires_confirmation)
        self.assertEqual(estimate.chunk_count, 5)
        self.assertLessEqual(
            estimate.estimated_card_min, len(plan.points)
        )
        self.assertGreaterEqual(
            estimate.estimated_card_max, len(plan.points)
        )

    def test_each_level_respects_exact_call_bounds_and_card_ordering(self):
        analysis, chunks, plan = _estimate_fixture()
        fast = estimate_generation(
            analysis, chunks, level="fast", plan=plan
        )
        standard = estimate_generation(
            analysis, chunks, level=IntelligenceLevel.STANDARD, plan=plan
        )
        deep = estimate_generation(
            analysis, chunks, level="deep", plan=plan
        )

        self.assertEqual(
            (fast.estimated_call_min, fast.estimated_call_max), (1, 3)
        )
        self.assertEqual(
            (standard.estimated_call_min, standard.estimated_call_max), (3, 8)
        )
        self.assertEqual(
            (deep.estimated_call_min, deep.estimated_call_max), (4, 12)
        )
        self.assertFalse(fast.requires_confirmation)
        self.assertLessEqual(
            fast.estimated_card_max, standard.estimated_card_max
        )
        self.assertLessEqual(
            standard.estimated_card_max, deep.estimated_card_max
        )
        self.assertEqual(fast.max_calls, 12)
        self.assertEqual(standard.max_calls, 12)
        self.assertEqual(deep.max_calls, 12)

    def test_deep_estimate_at_48_chunks_never_exceeds_12_calls(self):
        analysis, chunks, plan = _estimate_fixture(section_count=48)

        estimate = estimate_generation(
            analysis,
            chunks,
            level=IntelligenceLevel.DEEP,
            plan=plan,
        )

        self.assertEqual(estimate.chunk_count, 48)
        self.assertEqual(estimate.estimated_call_max, 12)

    def test_more_than_48_chunks_and_unknown_level_fail_before_arithmetic(self):
        analysis, chunks, plan = _estimate_fixture()

        with self.assertRaisesRegex(ValueError, "MAX_DOCUMENT_CHUNKS"):
            estimate_generation(analysis, chunks * 10, plan=plan)
        with self.assertRaisesRegex(ValueError, "level"):
            estimate_generation(analysis, chunks, level="unbounded", plan=plan)

    def test_estimate_consumes_only_chunk_cap_plus_one_from_iterable(self):
        analysis, chunks, plan = _estimate_fixture()
        guarded = _GuardedInfiniteChunks(chunks[0])

        with self.assertRaisesRegex(ValueError, "MAX_DOCUMENT_CHUNKS"):
            estimate_generation(analysis, guarded, plan=plan)

        self.assertEqual(guarded.yield_count, 49)

    def test_empty_document_estimates_no_cards_but_keeps_bounded_call_policy(self):
        document = DocumentIR(
            schema_version=1,
            document_id="empty-estimate",
            title="Empty",
            language_hint=None,
            source_type="text",
            source_label="empty.txt",
        )
        analysis = analyze_document(document)

        estimate = estimate_generation(
            analysis, (), level=IntelligenceLevel.FAST
        )

        self.assertEqual(
            (estimate.estimated_card_min, estimate.estimated_card_max), (0, 0)
        )
        self.assertEqual(
            (estimate.estimated_call_min, estimate.estimated_call_max), (1, 3)
        )

    def test_estimate_constructor_enforces_public_limits_and_exact_policy(self):
        analysis, chunks, plan = _estimate_fixture()
        standard = estimate_generation(analysis, chunks, plan=plan)
        fast = estimate_generation(
            analysis,
            chunks,
            level=IntelligenceLevel.FAST,
            plan=plan,
        )
        invalid_estimates = (
            (standard, {"max_calls": 13}),
            (standard, {"estimated_card_min": standard.estimated_card_max + 1}),
            (standard, {"estimated_call_min": standard.estimated_call_max + 1}),
            (standard, {"chunk_count": 49}),
            (standard, {"estimated_card_max": 97}),
            (standard, {"estimated_card_min": True}),
            (standard, {"chunk_count": 1.5}),
            (standard, {"estimated_call_min": 2}),
            (fast, {"requires_confirmation": True}),
        )

        for estimate, changes in invalid_estimates:
            with self.subTest(level=estimate.level.value, changes=tuple(changes)):
                with self.assertRaises((TypeError, ValueError)):
                    replace(estimate, **changes)


if __name__ == "__main__":
    unittest.main()
