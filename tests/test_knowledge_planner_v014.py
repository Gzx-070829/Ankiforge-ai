import json
import unittest
from collections.abc import Mapping
from dataclasses import replace

from ankiforge_ai.document import (
    BlockKind,
    DocumentBlock,
    DocumentIR,
    DocumentSection,
    SourceLocation,
)
from ankiforge_ai.intelligence import analyze_document, chunk_document
from ankiforge_ai.intelligence.planning import (
    KnowledgePlan,
    KnowledgePointPlan,
    PlanCoverage,
    assess_plan_coverage,
    build_local_knowledge_plan,
    parse_llm_knowledge_plan,
)
from ankiforge_ai.intelligence.chunking import DocumentChunk


class _GuardedInfiniteChunks:
    def __init__(self, item):
        self.item = item
        self.yield_count = 0

    def __iter__(self):
        while True:
            self.yield_count += 1
            if self.yield_count > 49:
                raise AssertionError("planner consumed beyond cap+1")
            yield self.item


class _WrongSizeHostileMapping(Mapping):
    def __len__(self):
        return 2

    def __iter__(self):
        raise AssertionError("wrong-sized mapping must not be copied")

    def __getitem__(self, key):
        raise AssertionError("wrong-sized mapping must not be read")


class _CountingLocation(SourceLocation):
    comparison_count = 0

    def __eq__(self, other):
        type(self).comparison_count += 1
        return super().__eq__(other)

    __hash__ = SourceLocation.__hash__


class _GuardedFiveChunkIds:
    def __init__(self, chunk_ids):
        self.chunk_ids = tuple(chunk_ids)
        self.yield_count = 0

    def __iter__(self):
        for chunk_id in self.chunk_ids:
            self.yield_count += 1
            if self.yield_count > 5:
                raise AssertionError("source references read beyond limit+1")
            yield chunk_id


def _planning_document():
    sections = (
        DocumentSection(
            section_id="alpha",
            heading="Energy",
            heading_path=("Energy",),
            blocks=(
                DocumentBlock(
                    "alpha-atp",
                    BlockKind.PARAGRAPH,
                    "ATP is the cell's immediate energy carrier.",
                    SourceLocation(file_label="plan.md", section="Energy", line_start=1),
                ),
                DocumentBlock(
                    "alpha-duplicate",
                    BlockKind.PARAGRAPH,
                    "ATP is the cell's immediate energy carrier.",
                    SourceLocation(file_label="plan.md", section="Energy", line_start=3),
                ),
                DocumentBlock(
                    "alpha-process",
                    BlockKind.LIST,
                    "First capture energy. Then synthesize ATP.",
                    SourceLocation(file_label="plan.md", section="Energy", line_start=5),
                ),
            ),
        ),
        DocumentSection(
            section_id="beta",
            heading="Mass",
            heading_path=("Mass",),
            blocks=(
                DocumentBlock(
                    "beta-formula",
                    BlockKind.FORMULA,
                    "density = mass / volume",
                    SourceLocation(file_label="plan.md", section="Mass", line_start=9),
                ),
            ),
        ),
        DocumentSection(
            section_id="gamma",
            heading="Languages",
            heading_path=("Languages",),
            blocks=(
                DocumentBlock(
                    "gamma-code",
                    BlockKind.CODE,
                    "def greet(name):\n    return 'Hello ' + name",
                    SourceLocation(
                        file_label="plan.md", section="Languages", line_start=12
                    ),
                ),
            ),
        ),
    )
    char_count = sum(
        len(block.text) for section in sections for block in section.blocks
    )
    return DocumentIR(
        schema_version=1,
        document_id="doc-plan",
        title="Planning fixture",
        language_hint="en",
        source_type="markdown",
        source_label="plan.md",
        sections=sections,
        original_char_count=char_count,
        extracted_char_count=char_count,
    )


class KnowledgePlannerV014Tests(unittest.TestCase):
    def setUp(self):
        self.document = _planning_document()
        self.analysis = analyze_document(self.document)
        self.chunks = chunk_document(
            self.document, target_chars=70, max_chars=120
        )
        self.local = build_local_knowledge_plan(
            self.document, self.chunks, self.analysis
        )

    def test_local_plan_balances_sections_prioritizes_and_deduplicates(self):
        points = self.local.points

        self.assertEqual(
            tuple(point.section_id for point in points[:3]),
            ("alpha", "beta", "gamma"),
        )
        self.assertEqual(
            tuple(point.priority for point in points[:3]),
            ("high", "high", "high"),
        )
        normalized_titles = tuple(
            "".join(character.casefold() for character in point.title if character.isalnum())
            for point in points
        )
        self.assertEqual(len(normalized_titles), len(set(normalized_titles)))
        self.assertEqual(
            sum(
                point.title == "ATP is the cell's immediate energy carrier."
                for point in points
            ),
            1,
        )

    def test_every_local_point_is_grounded_in_existing_chunk_and_location(self):
        by_id = {chunk.chunk_id: chunk for chunk in self.chunks}
        document_locations = {
            block.location
            for section in self.document.sections
            for block in section.blocks
            if block.location is not None
        }

        for point in self.local.points:
            self.assertTrue(point.source_chunk_ids)
            self.assertTrue(
                all(chunk_id in by_id for chunk_id in point.source_chunk_ids)
            )
            self.assertTrue(
                any(
                    point.title in by_id[chunk_id].text
                    for chunk_id in point.source_chunk_ids
                )
            )
            self.assertTrue(
                all(location in document_locations for location in point.source_locations)
            )
            self.assertIn(
                point.recommended_template,
                {
                    "concept",
                    "definition",
                    "process_steps",
                    "formula_rule",
                },
            )

    def test_duplicate_normalized_llm_points_invalidate_entire_supplied_plan(self):
        alpha_chunk = next(
            chunk for chunk in self.chunks if "ATP is the cell" in chunk.text
        )
        payload = json.dumps(
            {
                "points": [
                    {
                        "title": "ATP is the cell's immediate energy carrier.",
                        "point_type": "definition",
                        "priority": "high",
                        "source_chunk_ids": [alpha_chunk.chunk_id],
                        "recommended_template": "definition",
                        "rationale": "explicit_definition",
                    },
                    {
                        "title": "ATP is the cell's immediate energy carrier.",
                        "point_type": "definition",
                        "priority": "low",
                        "source_chunk_ids": [alpha_chunk.chunk_id],
                        "recommended_template": "definition",
                        "rationale": "duplicate_wording",
                    },
                ]
            }
        )

        plan = parse_llm_knowledge_plan(
            payload,
            self.document,
            self.chunks,
            fallback_plan=self.local,
        )

        self.assertIs(plan, self.local)

    def test_single_grounded_llm_point_is_validated_and_locally_identified(self):
        alpha_chunk = next(
            chunk for chunk in self.chunks if "ATP is the cell" in chunk.text
        )
        payload = {
            "points": [
                {
                    "title": "ATP is the cell's immediate energy carrier.",
                    "point_type": "definition",
                    "priority": "high",
                    "source_chunk_ids": [alpha_chunk.chunk_id],
                    "recommended_template": "definition",
                    "rationale": "explicit_definition",
                }
            ]
        }

        plan = parse_llm_knowledge_plan(
            payload,
            self.document,
            self.chunks,
            fallback_plan=self.local,
        )

        self.assertEqual(plan.source, "llm")
        self.assertEqual(len(plan.points), 1)
        self.assertEqual(plan.points[0].section_id, "alpha")
        self.assertEqual(plan.points[0].source_locations, alpha_chunk.source_locations)
        self.assertTrue(plan.points[0].point_id.startswith("point-"))

    def test_malformed_ungrounded_and_over_limit_llm_results_fall_back_locally(self):
        first_chunk_id = self.chunks[0].chunk_id
        valid_point = {
            "title": next(
                point.title
                for point in self.local.points
                if first_chunk_id in point.source_chunk_ids
            ),
            "point_type": "definition",
            "priority": "high",
            "source_chunk_ids": [first_chunk_id],
            "recommended_template": "definition",
            "rationale": "explicit_definition",
        }
        invalid_payloads = (
            None,
            "{",
            '{"points":' + "[" * 1100 + "]" * 1100 + "}",
            {"points": [], "extra": "not allowed"},
            {"points": [{**valid_point, "priority": 1}]},
            {
                "points": [
                    {
                        **valid_point,
                        "source_chunk_ids": ["chunk-0000000000000000"],
                    }
                ]
            },
            {"points": [{**valid_point, "title": "Mercury is a moon."}]},
            {"points": [valid_point] * 97},
        )

        for payload in invalid_payloads:
            with self.subTest(payload_type=type(payload).__name__):
                self.assertIs(
                    parse_llm_knowledge_plan(
                        payload,
                        self.document,
                        self.chunks,
                        fallback_plan=self.local,
                    ),
                    self.local,
                )

    def test_coverage_reports_grounding_duplicates_and_uncovered_chunks(self):
        complete = assess_plan_coverage(
            self.document, self.chunks, self.local
        )
        reduced = replace(self.local, points=self.local.points[:1])
        incomplete = assess_plan_coverage(
            self.document, self.chunks, reduced
        )
        duplicated = replace(
            self.local,
            points=self.local.points
            + (
                replace(
                    self.local.points[0],
                    point_id="point-ffffffffffffffff",
                ),
            ),
        )
        duplicate_coverage = assess_plan_coverage(
            self.document, self.chunks, duplicated
        )

        self.assertTrue(complete.is_grounded)
        self.assertFalse(complete.invalid_point_ids)
        self.assertGreater(len(incomplete.uncovered_chunk_ids), 0)
        self.assertGreater(len(incomplete.uncovered_section_ids), 0)
        self.assertEqual(
            duplicate_coverage.duplicate_point_ids,
            ("point-ffffffffffffffff",),
        )

    def test_invalid_supplied_fallback_is_rebuilt_from_current_chunks(self):
        invalid_point = replace(
            self.local.points[0],
            title="Mercury is a moon.",
        )
        invalid_fallback = replace(self.local, points=(invalid_point,))

        result = parse_llm_knowledge_plan(
            None,
            self.document,
            self.chunks,
            fallback_plan=invalid_fallback,
        )

        self.assertEqual(
            result,
            build_local_knowledge_plan(
                self.document,
                self.chunks,
                self.analysis,
            ),
        )
        self.assertIsNot(result, invalid_fallback)

    def test_cross_section_multi_chunk_point_is_not_grounded_or_covered(self):
        alpha = next(chunk for chunk in self.chunks if chunk.section_id == "alpha")
        beta = next(chunk for chunk in self.chunks if chunk.section_id == "beta")
        source = self.local.points[0]
        cross_section = replace(
            source,
            point_id="point-eeeeeeeeeeeeeeee",
            source_chunk_ids=(alpha.chunk_id, beta.chunk_id),
            source_locations=alpha.source_locations + beta.source_locations,
            section_id="alpha",
            title="ATP is the cell's immediate energy carrier.",
        )
        plan = replace(self.local, points=(cross_section,))

        coverage = assess_plan_coverage(self.document, self.chunks, plan)

        self.assertFalse(coverage.is_grounded)
        self.assertEqual(
            coverage.invalid_point_ids,
            ("point-eeeeeeeeeeeeeeee",),
        )
        self.assertEqual(coverage.covered_chunk_ids, ())

    def test_plan_models_freeze_sequences_and_enforce_reference_membership(self):
        point = self.local.points[0]
        frozen_point = KnowledgePointPlan(
            point_id=point.point_id,
            title=point.title,
            point_type=point.point_type,
            priority=point.priority,
            section_id=point.section_id,
            source_chunk_ids=list(point.source_chunk_ids),
            source_locations=list(point.source_locations),
            recommended_template=point.recommended_template,
            rationale=point.rationale,
        )
        frozen_plan = KnowledgePlan(
            plan_id=self.local.plan_id,
            document_id=self.local.document_id,
            source="local",
            chunk_ids=list(self.local.chunk_ids),
            points=[frozen_point],
        )

        self.assertIsInstance(frozen_point.source_chunk_ids, tuple)
        self.assertIsInstance(frozen_point.source_locations, tuple)
        self.assertIsInstance(frozen_plan.chunk_ids, tuple)
        self.assertIsInstance(frozen_plan.points, tuple)
        with self.assertRaisesRegex(ValueError, "source_chunk"):
            replace(frozen_point, source_chunk_ids=("../chunk",))
        with self.assertRaisesRegex(ValueError, "reference"):
            replace(
                frozen_plan,
                chunk_ids=tuple(
                    chunk_id
                    for chunk_id in frozen_plan.chunk_ids
                    if chunk_id not in frozen_point.source_chunk_ids
                ),
            )

    def test_point_model_enforces_exact_type_and_template_allowlists(self):
        point = self.local.points[0]
        supported_point_types = {
            "concept",
            "definition",
            "comparison",
            "process",
            "formula",
            "code",
            "table",
            "transcript",
            "mistake",
            "exam",
            "fact",
        }
        supported_templates = {
            "concept",
            "definition",
            "exam_answer",
            "quick_review",
            "compare_contrast",
            "process_steps",
            "formula_rule",
            "mistake_trap",
        }

        for point_type in supported_point_types:
            with self.subTest(point_type=point_type):
                self.assertEqual(
                    replace(point, point_type=point_type).point_type,
                    point_type,
                )
        for template in supported_templates:
            with self.subTest(template=template):
                self.assertEqual(
                    replace(point, recommended_template=template).recommended_template,
                    template,
                )
        with self.assertRaisesRegex(ValueError, "point_type"):
            replace(point, point_type="arbitrary")
        with self.assertRaisesRegex(ValueError, "recommended_template"):
            replace(point, recommended_template="arbitrary")

    def test_point_model_accepts_one_to_four_refs_and_caps_before_materializing(self):
        point = self.local.points[0]
        reference_ids = tuple(chunk.chunk_id for chunk in self.chunks)

        for count in range(1, 5):
            with self.subTest(count=count):
                bounded_point = replace(
                    point,
                    source_chunk_ids=reference_ids[:count],
                )
                self.assertEqual(
                    bounded_point.source_chunk_ids, reference_ids[:count]
                )
                self.assertEqual(
                    replace(self.local, points=(bounded_point,)).points,
                    (bounded_point,),
                )
        with self.assertRaisesRegex(ValueError, "source_chunk_ids"):
            replace(point, source_chunk_ids=())
        with self.assertRaisesRegex(ValueError, "unique"):
            replace(
                point,
                source_chunk_ids=(reference_ids[0], reference_ids[0]),
            )
        guarded = _GuardedFiveChunkIds(reference_ids)
        with self.assertRaisesRegex(ValueError, "approved limit"):
            replace(point, source_chunk_ids=guarded)
        self.assertEqual(guarded.yield_count, 5)

    def test_llm_point_with_five_same_section_refs_falls_back(self):
        chunks = tuple(
            DocumentChunk(
                chunk_id=f"chunk-{index + 100:016x}",
                document_id=self.document.document_id,
                sequence=index,
                section_id="alpha",
                heading_path=("Energy",),
                text="ATP is the cell's immediate energy carrier.",
                block_ids=("alpha-atp",),
                block_kinds=(BlockKind.PARAGRAPH,),
                source_locations=(),
            )
            for index in range(5)
        )
        fallback = build_local_knowledge_plan(
            self.document,
            chunks,
            self.analysis,
        )
        payload = {
            "points": [
                {
                    "title": "ATP is the cell's immediate energy carrier.",
                    "point_type": "definition",
                    "priority": "high",
                    "source_chunk_ids": [chunk.chunk_id for chunk in chunks],
                    "recommended_template": "definition",
                    "rationale": "explicit_definition",
                }
            ]
        }

        plan = parse_llm_knowledge_plan(
            payload,
            self.document,
            chunks,
            fallback_plan=fallback,
        )

        self.assertIs(plan, fallback)

    def test_plan_coverage_freezes_fields_and_rejects_overlap(self):
        coverage = PlanCoverage(
            covered_chunk_ids=["chunk-0123456789abcdef"],
            uncovered_chunk_ids=["chunk-fedcba9876543210"],
            covered_section_ids=["section-one"],
            uncovered_section_ids=["section-two"],
            duplicate_point_ids=[],
            invalid_point_ids=[],
            is_grounded=True,
        )

        self.assertIsInstance(coverage.covered_chunk_ids, tuple)
        self.assertIsInstance(coverage.uncovered_section_ids, tuple)
        with self.assertRaisesRegex(ValueError, "overlap"):
            PlanCoverage(
                covered_chunk_ids=["chunk-0123456789abcdef"],
                uncovered_chunk_ids=["chunk-0123456789abcdef"],
                covered_section_ids=[],
                uncovered_section_ids=[],
                duplicate_point_ids=[],
                invalid_point_ids=[],
                is_grounded=True,
            )

    def test_local_planner_consumes_only_chunk_cap_plus_one(self):
        guarded = _GuardedInfiniteChunks(self.chunks[0])

        with self.assertRaisesRegex(ValueError, "at most 48"):
            build_local_knowledge_plan(
                self.document,
                guarded,
                self.analysis,
            )

        self.assertEqual(guarded.yield_count, 49)

    def test_wrong_sized_hostile_mapping_falls_back_without_copying(self):
        result = parse_llm_knowledge_plan(
            _WrongSizeHostileMapping(),
            self.document,
            self.chunks,
            fallback_plan=self.local,
        )

        self.assertIs(result, self.local)

    def test_llm_location_dedup_is_linear_and_preserves_order(self):
        locations = tuple(
            _CountingLocation(
                file_label="plan.md",
                section="Energy",
                line_start=index,
            )
            for index in range(1, 121)
        )
        chunks = tuple(
            DocumentChunk(
                chunk_id=f"chunk-{index:016x}",
                document_id=self.document.document_id,
                sequence=index,
                section_id="alpha",
                heading_path=("Energy",),
                text="ATP is the cell's immediate energy carrier.",
                block_ids=("alpha-atp",),
                block_kinds=(BlockKind.PARAGRAPH,),
                source_locations=locations[index * 30 : (index + 1) * 30],
            )
            for index in range(4)
        )
        fallback = build_local_knowledge_plan(
            self.document,
            chunks,
            self.analysis,
        )
        payload = {
            "points": [
                {
                    "title": "ATP is the cell's immediate energy carrier.",
                    "point_type": "definition",
                    "priority": "high",
                    "source_chunk_ids": [
                        chunk.chunk_id for chunk in chunks
                    ],
                    "recommended_template": "definition",
                    "rationale": "explicit_definition",
                }
            ]
        }
        _CountingLocation.comparison_count = 0

        plan = parse_llm_knowledge_plan(
            payload,
            self.document,
            chunks,
            fallback_plan=fallback,
        )

        self.assertEqual(plan.source, "llm")
        self.assertEqual(plan.points[0].source_locations, locations)
        self.assertLess(_CountingLocation.comparison_count, 300)

    def test_plan_repr_never_dumps_source_or_rationale(self):
        rendered = repr(self.local)

        self.assertIn("document_id='doc-plan'", rendered)
        self.assertNotIn("ATP is the cell", rendered)
        self.assertNotIn(self.local.points[0].rationale, rendered)
        self.assertNotIn("C:\\Users\\", rendered)


if __name__ == "__main__":
    unittest.main()
