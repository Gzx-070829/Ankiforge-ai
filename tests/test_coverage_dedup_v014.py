import unittest

from ankiforge_ai.intelligence.coverage import (
    CoverageReport,
    assess_generation_coverage,
)
from ankiforge_ai.intelligence.deduplication import (
    DeduplicationResult,
    canonicalize_card_text,
    deduplicate_cards,
)


class CoverageV014Tests(unittest.TestCase):
    def test_reports_missing_priority_uncovered_overcovered_and_duplicates(self):
        points = (
            {"point_id": "point-0000000000000001", "priority": "high", "section_id": "alpha"},
            {"point_id": "point-0000000000000002", "priority": "high", "section_id": "beta"},
            {"point_id": "point-0000000000000003", "priority": "low", "section_id": "gamma"},
        )
        cards = (
            {"candidate_id": "card-1", "point_id": "point-0000000000000001", "section_id": "alpha"},
            {"candidate_id": "card-2", "point_id": "point-0000000000000001", "section_id": "alpha"},
            {"candidate_id": "card-3", "point_id": "point-0000000000000001", "section_id": "alpha"},
            {"candidate_id": "card-4", "point_id": "point-0000000000000001", "section_id": "alpha"},
        )

        report = assess_generation_coverage(
            points,
            cards,
            section_ids=("alpha", "beta", "gamma"),
            max_cards=6,
        )

        self.assertIsInstance(report, CoverageReport)
        self.assertEqual(
            report.missing_high_priority_point_ids,
            ("point-0000000000000002",),
        )
        self.assertEqual(report.uncovered_section_ids, ("beta", "gamma"))
        self.assertEqual(report.overcovered_section_ids, ("alpha",))
        self.assertEqual(
            report.duplicate_point_ids,
            ("point-0000000000000001",),
        )
        self.assertEqual(report.overflow_count, 0)
        self.assertTrue(report.supplement_recommended)

    def test_card_overflow_and_safe_repr_report_counts_not_bodies(self):
        cards = tuple(
            {
                "candidate_id": f"card-{index}",
                "point_id": "point-0000000000000001",
                "section_id": "alpha",
                "front": "private body",
            }
            for index in range(5)
        )
        report = assess_generation_coverage(
            (
                {
                    "point_id": "point-0000000000000001",
                    "priority": "high",
                    "section_id": "alpha",
                },
            ),
            cards,
            section_ids=("alpha",),
            max_cards=3,
        )

        self.assertEqual(report.overflow_count, 2)
        self.assertIn("cards=5/3", repr(report))
        self.assertNotIn("private body", repr(report))

    def test_overflow_never_recommends_a_supplement_even_when_priority_is_missing(self):
        report = assess_generation_coverage(
            (
                {
                    "point_id": "point-0000000000000001",
                    "priority": "high",
                    "section_id": "alpha",
                },
                {
                    "point_id": "point-0000000000000002",
                    "priority": "high",
                    "section_id": "beta",
                },
            ),
            (
                {
                    "candidate_id": "card-1",
                    "point_id": "point-0000000000000001",
                    "section_id": "alpha",
                },
                {
                    "candidate_id": "card-2",
                    "point_id": "point-0000000000000001",
                    "section_id": "alpha",
                },
            ),
            section_ids=("alpha", "beta"),
            max_cards=1,
        )

        self.assertEqual(
            report.missing_high_priority_point_ids,
            ("point-0000000000000002",),
        )
        self.assertEqual(report.overflow_count, 1)
        self.assertFalse(report.supplement_recommended)

    def test_card_limit_equality_suppresses_supplement_in_assessor_and_model(self):
        report = assess_generation_coverage(
            (
                {
                    "point_id": "point-0000000000000001",
                    "priority": "high",
                    "section_id": "alpha",
                },
                {
                    "point_id": "point-0000000000000002",
                    "priority": "high",
                    "section_id": "beta",
                },
            ),
            (
                {
                    "candidate_id": "card-1",
                    "point_id": "point-0000000000000001",
                    "section_id": "alpha",
                },
            ),
            section_ids=("alpha", "beta"),
            max_cards=1,
        )

        self.assertFalse(report.supplement_recommended)
        with self.assertRaisesRegex(ValueError, "card capacity"):
            CoverageReport(
                missing_high_priority_point_ids=("point-0000000000000002",),
                uncovered_section_ids=("beta",),
                overcovered_section_ids=(),
                duplicate_point_ids=(),
                card_count=1,
                max_cards=1,
                overflow_count=0,
                supplement_recommended=True,
            )

    def test_coverage_rejects_unbounded_or_unknown_references(self):
        point = {
            "point_id": "point-0000000000000001",
            "priority": "high",
            "section_id": "alpha",
        }
        with self.assertRaisesRegex(ValueError, "unknown point"):
            assess_generation_coverage(
                (point,),
                (
                    {
                        "candidate_id": "card-1",
                        "point_id": "point-ffffffffffffffff",
                        "section_id": "alpha",
                    },
                ),
                section_ids=("alpha",),
            )
        with self.assertRaisesRegex(ValueError, "approved limit"):
            assess_generation_coverage(
                (point,) * 97,
                (),
                section_ids=("alpha",),
            )


class DeduplicationV014Tests(unittest.TestCase):
    def test_exact_and_canonical_duplicates_across_chunks_keep_first(self):
        cards = (
            {
                "candidate_id": "card-1",
                "chunk_id": "chunk-0000000000000001",
                "front": "What is ATP?",
                "back": "ATP stores usable energy.",
            },
            {
                "candidate_id": "card-2",
                "chunk_id": "chunk-0000000000000002",
                "front": "What is ATP?",
                "back": "ATP stores usable energy.",
            },
            {
                "candidate_id": "card-3",
                "chunk_id": "chunk-0000000000000003",
                "front": "  WHAT　is ATP？！ ",
                "back": "ATP stores usable energy…",
            },
        )

        result = deduplicate_cards(cards)

        self.assertIsInstance(result, DeduplicationResult)
        self.assertEqual(
            tuple(card["candidate_id"] for card in result.unique_cards),
            ("card-1",),
        )
        self.assertEqual(result.exact_duplicate_ids, ("card-2",))
        self.assertEqual(result.canonical_duplicate_ids, ("card-3",))
        self.assertEqual(result.similar_duplicate_ids, ())
        self.assertEqual(result.duplicate_candidate_ids, ("card-2", "card-3"))
        self.assertEqual(
            tuple(
                (item.candidate_id, item.matched_candidate_id, item.kind, item.reason_code)
                for item in result.matches
            ),
            (
                ("card-2", "card-1", "exact", "exact_text"),
                ("card-3", "card-1", "canonical", "normalized_text"),
            ),
        )

    def test_similar_duplicate_requires_safe_similarity_and_source_overlap(self):
        cards = (
            {
                "candidate_id": "card-1",
                "chunk_id": "chunk-0000000000000001",
                "point_id": "point-0000000000000001",
                "front": "How does ATP provide immediately usable cellular energy?",
                "back": "ATP provides immediately usable energy for cellular work.",
            },
            {
                "candidate_id": "card-2",
                "chunk_id": "chunk-0000000000000002",
                "point_id": "point-0000000000000001",
                "front": "How does ATP provide usable cellular energy?",
                "back": "ATP provides usable energy for cellular work.",
            },
            {
                "candidate_id": "card-3",
                "chunk_id": "chunk-0000000000000003",
                "point_id": "point-0000000000000003",
                "front": "How does ATP provide usable cellular energy?",
                "back": "ATP provides usable energy for cellular work.",
            },
        )

        result = deduplicate_cards(cards, similarity_threshold=0.75)

        self.assertEqual(result.similar_duplicate_ids, ("card-2",))
        self.assertEqual(result.matches[0].matched_candidate_id, "card-1")
        self.assertEqual(result.matches[0].kind, "similar")
        self.assertIn(
            result.matches[0].reason_code,
            {"shared_source_token_overlap", "shared_source_character_overlap"},
        )
        self.assertGreaterEqual(result.matches[0].similarity, 0.75)
        self.assertEqual(
            tuple(card["candidate_id"] for card in result.unique_cards),
            ("card-1", "card-3"),
        )
        self.assertEqual(result.comparison_count, 2)

    def test_semantic_matcher_is_protocol_only_and_default_off(self):
        calls = []

        def semantic_matcher(_left, _right):
            calls.append("called")
            raise AssertionError("semantic matcher must remain disabled")

        result = deduplicate_cards(
            (
                {
                    "candidate_id": "card-1",
                    "chunk_id": "chunk-0000000000000001",
                    "front": "What is ATP?",
                    "back": "Energy carrier.",
                },
                {
                    "candidate_id": "card-2",
                    "chunk_id": "chunk-0000000000000002",
                    "front": "What is DNA?",
                    "back": "Genetic material.",
                },
            ),
            semantic_matcher=semantic_matcher,
        )

        self.assertEqual(calls, [])
        self.assertFalse(result.semantic_dedup_used)

    def test_dedup_is_deterministic_bounded_and_repr_has_no_card_bodies(self):
        private = "C:\\Users\\private\\source body"
        cards = tuple(
            {
                "candidate_id": f"card-{index}",
                "chunk_id": f"chunk-{index:016x}",
                "front": f"Question {index} {private}",
                "back": f"Answer {index}",
            }
            for index in range(96)
        )

        first = deduplicate_cards(cards)
        second = deduplicate_cards(cards)

        self.assertEqual(first, second)
        self.assertLessEqual(first.comparison_count, 96 * 95 // 2)
        self.assertNotIn(private, repr(first))
        with self.assertRaisesRegex(ValueError, "approved limit"):
            deduplicate_cards((*cards, cards[0]))

    def test_similarity_threshold_must_be_finite_and_in_safe_range(self):
        for threshold in (True, 0.0, 0.49, 1.01, float("nan"), float("inf")):
            with self.subTest(threshold=threshold):
                with self.assertRaises((TypeError, ValueError)):
                    deduplicate_cards((), similarity_threshold=threshold)

    def test_canonicalization_preserves_meaningful_math_and_code_symbols(self):
        self.assertNotEqual(
            canonicalize_card_text("What is x+y?"),
            canonicalize_card_text("What is xy?"),
        )
        self.assertNotEqual(
            canonicalize_card_text("Use x ≤ y ± 1 → accept."),
            canonicalize_card_text("Use x y 1 accept."),
        )
        result = deduplicate_cards(
            (
                {
                    "candidate_id": "card-symbol",
                    "chunk_id": "chunk-0000000000000001",
                    "front": "What is x+y?",
                    "back": "Add x and y.",
                },
                {
                    "candidate_id": "card-plain",
                    "chunk_id": "chunk-0000000000000002",
                    "front": "What is xy?",
                    "back": "Use the variable xy.",
                },
            )
        )

        self.assertEqual(
            tuple(card["candidate_id"] for card in result.unique_cards),
            ("card-symbol", "card-plain"),
        )

    def test_character_ngrams_catch_small_typo_with_shared_source(self):
        result = deduplicate_cards(
            (
                {
                    "candidate_id": "card-original",
                    "point_id": "point-0000000000000001",
                    "front": "What is photosynthesiss?",
                    "back": "Photosynthesiss converts light energy into chemical energy.",
                },
                {
                    "candidate_id": "card-corrected",
                    "point_id": "point-0000000000000001",
                    "front": "What is photosynthesis?",
                    "back": "Photosynthesis converts light energy into chemical energy.",
                },
            ),
            similarity_threshold=0.86,
        )

        self.assertEqual(result.similar_duplicate_ids, ("card-corrected",))
        self.assertEqual(
            result.matches[0].reason_code,
            "shared_source_character_overlap",
        )
        self.assertNotIn("photosynthesis", repr(result).casefold())


if __name__ == "__main__":
    unittest.main()
