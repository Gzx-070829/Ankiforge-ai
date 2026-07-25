from collections.abc import Mapping
from dataclasses import FrozenInstanceError, dataclass, replace
import unittest

from ankiforge_ai.intelligence.call_budget import CallPurpose
from ankiforge_ai.intelligence.generation_run import (
    ChunkGenerationSnapshot,
    ChunkGenerationState,
    GenerationRunStatus,
    GenerationStage,
    MAX_SNAPSHOT_BYTES,
    MAX_SNAPSHOT_DEPTH,
    MAX_SNAPSHOT_MAPPING_KEYS,
    MAX_SNAPSHOT_SEQUENCE_ITEMS,
    MAX_SNAPSHOT_TEXT_CHARS,
    complete_run,
    create_generation_run,
    fail_chunk,
    reserve_run_call,
    start_chunk,
    succeed_chunk,
    supersede_run,
    transition_run,
)
from ankiforge_ai.intelligence.models import IntelligenceLevel


class CountingMapping(Mapping):
    def __init__(self, count):
        self.count = count
        self.yield_count = 0

    def __len__(self):
        return 0

    def __iter__(self):
        for index in range(self.count):
            self.yield_count += 1
            yield f"key-{index}"

    def __getitem__(self, key):
        return key


class CountingList(list):
    def __init__(self, count):
        super().__init__(range(count))
        self.yield_count = 0

    def __iter__(self):
        for item in super().__iter__():
            self.yield_count += 1
            yield item


class GenerationRunV014Tests(unittest.TestCase):
    def make_run(self, *, level=IntelligenceLevel.STANDARD):
        return create_generation_run(
            run_id="run-001",
            request_id=7,
            document_id="doc-001",
            document_hash="a" * 64,
            document_snapshot={
                "document_id": "doc-001",
                "blocks": [{"text": "private material"}],
            },
            settings_snapshot={
                "card_mode": "concept",
                "private_hint": "private setting",
            },
            level=level,
            chunk_ids=("chunk-0123456789abcdef", "chunk-fedcba9876543210"),
        )

    def test_factory_copies_nested_snapshots_and_exposes_no_mutable_sequences(self):
        document = {
            "document_id": "doc-001",
            "blocks": [{"text": "private material"}],
        }
        settings = {"card_mode": "concept", "tags": ["alpha"]}

        run = create_generation_run(
            run_id="run-001",
            request_id=7,
            document_id="doc-001",
            document_hash="a" * 64,
            document_snapshot=document,
            settings_snapshot=settings,
            chunk_ids=["chunk-0123456789abcdef"],
        )
        document["blocks"][0]["text"] = "changed"
        settings["tags"].append("changed")

        self.assertEqual(
            run.document_snapshot["blocks"][0]["text"],
            "private material",
        )
        self.assertEqual(run.settings_snapshot["tags"], ("alpha",))
        self.assertIsInstance(run.chunks, tuple)
        with self.assertRaises(TypeError):
            run.settings_snapshot["card_mode"] = "exam"
        with self.assertRaises(FrozenInstanceError):
            run.stage = GenerationStage.GENERATING

    def test_stage_graph_rejects_skips_and_terminal_transitions(self):
        run = self.make_run(level=IntelligenceLevel.FAST)

        with self.assertRaisesRegex(ValueError, "illegal_stage_transition"):
            transition_run(run, GenerationStage.GENERATING)
        planning = transition_run(run, GenerationStage.PLANNING)
        generating = transition_run(planning, GenerationStage.GENERATING)
        generating = reserve_run_call(generating, CallPurpose.GENERATE)
        for chunk in generating.chunks:
            generating = succeed_chunk(
                start_chunk(generating, chunk.chunk_id),
                chunk.chunk_id,
                (),
            )
        reviewing = transition_run(generating, GenerationStage.REVIEWING)
        coverage = transition_run(reviewing, GenerationStage.CHECKING_COVERAGE)
        deduplicating = transition_run(coverage, GenerationStage.DEDUPLICATING)
        completed = complete_run(deduplicating)

        self.assertEqual(completed.status, GenerationRunStatus.COMPLETED)
        with self.assertRaisesRegex(ValueError, "terminal_run"):
            transition_run(completed, GenerationStage.FAILED)

    def test_fast_locally_plans_without_a_planner_call_or_repair_stage(self):
        run = self.make_run(level=IntelligenceLevel.FAST)
        planning = transition_run(run, GenerationStage.PLANNING)
        generating = transition_run(planning, GenerationStage.GENERATING)

        self.assertEqual(planning.call_budget.call_count, 0)
        with self.assertRaisesRegex(ValueError, "call_not_allowed"):
            reserve_run_call(planning, CallPurpose.PLANNER)
        with self.assertRaisesRegex(ValueError, "stage_not_allowed"):
            transition_run(generating, GenerationStage.REPAIRING)

    def test_chunk_failure_retains_successful_sibling_cards_and_safe_reason(self):
        run = transition_run(
            transition_run(self.make_run(), GenerationStage.PLANNING),
            GenerationStage.GENERATING,
        )
        first_id, second_id = (item.chunk_id for item in run.chunks)
        run = start_chunk(run, first_id)
        run = succeed_chunk(
            run,
            first_id,
            ({"candidate_id": "card-1", "front": "private front"},),
        )
        run = start_chunk(run, second_id)
        run = fail_chunk(run, second_id, reason_code="provider_call_failed")

        self.assertEqual(run.chunks[0].state, ChunkGenerationState.SUCCEEDED)
        self.assertEqual(run.chunks[1].state, ChunkGenerationState.FAILED)
        self.assertEqual(run.cards[0]["candidate_id"], "card-1")
        self.assertEqual(run.failed_chunk_ids, (second_id,))
        self.assertEqual(run.status, GenerationRunStatus.PARTIAL)
        self.assertNotIn("private front", repr(run))
        self.assertIn("provider_call_failed", repr(run))

    def test_chunk_transition_rejects_duplicate_completion(self):
        run = transition_run(
            transition_run(self.make_run(), GenerationStage.PLANNING),
            GenerationStage.GENERATING,
        )
        chunk_id = run.chunks[0].chunk_id
        succeeded = succeed_chunk(start_chunk(run, chunk_id), chunk_id, ())

        with self.assertRaisesRegex(ValueError, "chunk_not_running"):
            succeed_chunk(succeeded, chunk_id, ())
        with self.assertRaisesRegex(ValueError, "chunk_not_running"):
            fail_chunk(succeeded, chunk_id, reason_code="late_failure")

    def test_repair_and_supplement_reservations_are_atomic_and_single_use(self):
        run = transition_run(
            transition_run(
                self.make_run(level=IntelligenceLevel.DEEP),
                GenerationStage.PLANNING,
            ),
            GenerationStage.GENERATING,
        )
        for chunk in run.chunks:
            run = succeed_chunk(start_chunk(run, chunk.chunk_id), chunk.chunk_id, ())
        repairing = transition_run(
            transition_run(run, GenerationStage.REVIEWING),
            GenerationStage.REPAIRING,
        )
        repaired = reserve_run_call(
            repairing,
            CallPurpose.REPAIR,
            point_id="point-0123456789abcdef",
        )

        self.assertEqual(repaired.call_budget.call_count, 1)
        self.assertEqual(
            repaired.repaired_point_ids,
            ("point-0123456789abcdef",),
        )
        with self.assertRaisesRegex(ValueError, "repair_already_used"):
            reserve_run_call(
                repaired,
                CallPurpose.REPAIR,
                point_id="point-0123456789abcdef",
            )

        coverage = transition_run(repaired, GenerationStage.CHECKING_COVERAGE)
        supplemented = reserve_run_call(
            coverage,
            CallPurpose.SUPPLEMENT,
        )
        self.assertTrue(supplemented.supplement_used)
        self.assertEqual(supplemented.call_budget.call_count, 2)
        with self.assertRaisesRegex(ValueError, "supplement_already_used"):
            reserve_run_call(supplemented, CallPurpose.SUPPLEMENT)

    def test_completion_requires_deduplication_and_no_unfinished_chunks(self):
        run = transition_run(
            transition_run(
                self.make_run(level=IntelligenceLevel.FAST),
                GenerationStage.PLANNING,
            ),
            GenerationStage.GENERATING,
        )
        run = reserve_run_call(run, CallPurpose.GENERATE)
        for chunk in run.chunks:
            run = succeed_chunk(start_chunk(run, chunk.chunk_id), chunk.chunk_id, ())
        run = transition_run(run, GenerationStage.REVIEWING)
        run = transition_run(run, GenerationStage.CHECKING_COVERAGE)

        with self.assertRaisesRegex(ValueError, "completion_stage"):
            complete_run(run)
        completed = complete_run(
            transition_run(run, GenerationStage.DEDUPLICATING)
        )
        self.assertEqual(completed.stage, GenerationStage.COMPLETED)
        self.assertEqual(completed.status, GenerationRunStatus.COMPLETED)

    def test_completion_enforces_minimum_actual_calls_without_reserving_for_caller(self):
        run = transition_run(
            transition_run(
                self.make_run(level=IntelligenceLevel.FAST),
                GenerationStage.PLANNING,
            ),
            GenerationStage.GENERATING,
        )
        for chunk in run.chunks:
            run = succeed_chunk(start_chunk(run, chunk.chunk_id), chunk.chunk_id, ())
        run = transition_run(run, GenerationStage.REVIEWING)
        run = transition_run(run, GenerationStage.CHECKING_COVERAGE)
        run = transition_run(run, GenerationStage.DEDUPLICATING)

        with self.assertRaisesRegex(ValueError, "minimum_call_policy_not_met"):
            complete_run(run)
        self.assertEqual(run.call_budget.call_count, 0)

    def test_superseded_run_is_terminal_and_preserves_safe_counts(self):
        run = self.make_run()
        superseded = supersede_run(run)

        self.assertEqual(superseded.stage, GenerationStage.SUPERSEDED)
        self.assertEqual(superseded.status, GenerationRunStatus.SUPERSEDED)
        self.assertIn("chunks=2", repr(superseded))
        self.assertNotIn("private material", repr(superseded))
        self.assertNotIn("private setting", repr(superseded))
        with self.assertRaisesRegex(ValueError, "terminal_run"):
            start_chunk(superseded, superseded.chunks[0].chunk_id)

    def test_partial_completion_is_terminal_to_ordinary_stage_transitions(self):
        run = transition_run(
            transition_run(
                self.make_run(level=IntelligenceLevel.FAST),
                GenerationStage.PLANNING,
            ),
            GenerationStage.GENERATING,
        )
        run = reserve_run_call(run, CallPurpose.GENERATE)
        first_id, second_id = (item.chunk_id for item in run.chunks)
        run = succeed_chunk(start_chunk(run, first_id), first_id, ())
        run = fail_chunk(
            start_chunk(run, second_id),
            second_id,
            reason_code="generation_call_failed",
        )
        run = transition_run(run, GenerationStage.REVIEWING)
        run = transition_run(run, GenerationStage.CHECKING_COVERAGE)
        run = complete_run(
            transition_run(run, GenerationStage.DEDUPLICATING)
        )

        self.assertEqual(run.status, GenerationRunStatus.PARTIAL)
        with self.assertRaisesRegex(ValueError, "terminal_run"):
            transition_run(run, GenerationStage.GENERATING)

    def test_direct_run_construction_enforces_global_card_cap_across_chunks(self):
        run = self.make_run()
        private_cards = tuple(
            {"candidate_id": f"card-{index}", "front": "private", "back": "private"}
            for index in range(49)
        )

        with self.assertRaisesRegex(ValueError, "run cards"):
            run.__class__(
                **{
                    **run.__dict__,
                    "chunks": (
                        ChunkGenerationSnapshot(
                            run.chunks[0].chunk_id,
                            ChunkGenerationState.SUCCEEDED,
                            private_cards,
                        ),
                        ChunkGenerationSnapshot(
                            run.chunks[1].chunk_id,
                            ChunkGenerationState.SUCCEEDED,
                            private_cards,
                        ),
                    ),
                }
            )

    def test_identifiers_counts_and_reason_codes_are_strictly_validated(self):
        base = dict(
            run_id="run-001",
            request_id=1,
            document_id="doc-001",
            document_hash="a" * 64,
            document_snapshot={},
            settings_snapshot={},
            chunk_ids=("chunk-0123456789abcdef",),
        )
        invalid_overrides = (
            {"request_id": True},
            {"request_id": 1.5},
            {"run_id": "../private"},
            {"document_hash": "not-a-hash"},
            {"chunk_ids": ("../private",)},
        )

        for override in invalid_overrides:
            with self.subTest(override=override):
                with self.assertRaises((TypeError, ValueError)):
                    create_generation_run(**{**base, **override})

    def test_direct_constructor_rejects_incoherent_stage_status_and_chunk_state(self):
        run = self.make_run()
        failed_chunk = ChunkGenerationSnapshot(
            run.chunks[0].chunk_id,
            ChunkGenerationState.FAILED,
            (),
            "generation_call_failed",
        )
        succeeded_chunk = ChunkGenerationSnapshot(
            run.chunks[0].chunk_id,
            ChunkGenerationState.SUCCEEDED,
            (),
        )
        adversarial = (
            {"status": GenerationRunStatus.PARTIAL},
            {
                "chunks": (failed_chunk, run.chunks[1]),
                "status": GenerationRunStatus.RUNNING,
            },
            {
                "stage": GenerationStage.COMPLETED,
                "status": GenerationRunStatus.COMPLETED,
            },
            {
                "stage": GenerationStage.REVIEWING,
                "chunks": (succeeded_chunk, run.chunks[1]),
            },
        )

        for updates in adversarial:
            with self.subTest(updates=updates):
                with self.assertRaises(ValueError):
                    replace(run, **updates)

        fast = self.make_run(level=IntelligenceLevel.FAST)
        with self.assertRaisesRegex(ValueError, "Fast"):
            replace(fast, stage=GenerationStage.REPAIRING)

    def test_snapshot_freezer_caps_mapping_sequence_depth_text_bytes_and_cycles(self):
        mapping = CountingMapping(MAX_SNAPSHOT_MAPPING_KEYS + 1)
        with self.assertRaisesRegex(ValueError, "snapshot_mapping_limit"):
            create_generation_run(
                run_id="run-mapping",
                request_id=1,
                document_id="doc-mapping",
                document_hash="e" * 64,
                document_snapshot=mapping,
                settings_snapshot={},
                chunk_ids=("chunk-0000000000000001",),
            )
        self.assertEqual(mapping.yield_count, MAX_SNAPSHOT_MAPPING_KEYS + 1)

        sequence = CountingList(MAX_SNAPSHOT_SEQUENCE_ITEMS + 1)
        with self.assertRaisesRegex(ValueError, "snapshot_sequence_limit"):
            create_generation_run(
                run_id="run-sequence",
                request_id=1,
                document_id="doc-sequence",
                document_hash="e" * 64,
                document_snapshot={"items": sequence},
                settings_snapshot={},
                chunk_ids=("chunk-0000000000000001",),
            )
        self.assertEqual(sequence.yield_count, MAX_SNAPSHOT_SEQUENCE_ITEMS + 1)

        cycle = {}
        cycle["self"] = cycle
        with self.assertRaisesRegex(ValueError, "snapshot_cycle"):
            create_generation_run(
                run_id="run-cycle",
                request_id=1,
                document_id="doc-cycle",
                document_hash="e" * 64,
                document_snapshot=cycle,
                settings_snapshot={},
                chunk_ids=("chunk-0000000000000001",),
            )

        nested = "leaf"
        for _index in range(MAX_SNAPSHOT_DEPTH + 1):
            nested = [nested]
        with self.assertRaisesRegex(ValueError, "snapshot_depth_limit"):
            create_generation_run(
                run_id="run-depth",
                request_id=1,
                document_id="doc-depth",
                document_hash="e" * 64,
                document_snapshot=nested,
                settings_snapshot={},
                chunk_ids=("chunk-0000000000000001",),
            )

        for value, code in (
            ("x" * (MAX_SNAPSHOT_TEXT_CHARS + 1), "snapshot_text_limit"),
            (b"x" * (MAX_SNAPSHOT_BYTES + 1), "snapshot_bytes_limit"),
        ):
            with self.subTest(code=code):
                with self.assertRaisesRegex(ValueError, code):
                    create_generation_run(
                        run_id="run-scalar",
                        request_id=1,
                        document_id="doc-scalar",
                        document_hash="e" * 64,
                        document_snapshot={"value": value},
                        settings_snapshot={},
                        chunk_ids=("chunk-0000000000000001",),
                    )

    def test_snapshot_freezer_rejects_hostile_custom_iterable_without_consuming(self):
        class HostileIterable:
            consumed = False

            def __iter__(self):
                self.consumed = True
                raise AssertionError("custom iterable must not be consumed")

        hostile = HostileIterable()
        with self.assertRaisesRegex(TypeError, "snapshot"):
            create_generation_run(
                run_id="run-hostile",
                request_id=1,
                document_id="doc-hostile",
                document_hash="e" * 64,
                document_snapshot={"value": hostile},
                settings_snapshot={},
                chunk_ids=("chunk-0000000000000001",),
            )
        self.assertFalse(hostile.consumed)

    def test_snapshot_freezer_recursively_captures_frozen_dataclass_aliases(self):
        @dataclass(frozen=True)
        class FrozenAlias:
            values: object

        aliased_values = ["captured"]
        snapshot_value = FrozenAlias(aliased_values)
        run = create_generation_run(
            run_id="run-dataclass-alias",
            request_id=1,
            document_id="doc-dataclass-alias",
            document_hash="e" * 64,
            document_snapshot={"payload": snapshot_value},
            settings_snapshot={},
            chunk_ids=("chunk-0000000000000001",),
        )

        aliased_values.append("mutated")
        captured = run.document_snapshot["payload"]
        self.assertIsInstance(captured, FrozenAlias)
        self.assertIsNot(captured, snapshot_value)
        self.assertEqual(captured.values, ("captured",))

    def test_required_task_models_are_public_intelligence_exports(self):
        import ankiforge_ai.intelligence as intelligence

        required = (
            "GenerationRun",
            "GenerationStage",
            "GenerationRunStatus",
            "ChunkGenerationState",
            "CallBudget",
            "CriticDecision",
            "CoverageReport",
            "DeduplicationResult",
            "FailedChunkRetry",
            "DeckStyleProfile",
        )

        for name in required:
            with self.subTest(name=name):
                self.assertTrue(hasattr(intelligence, name))


if __name__ == "__main__":
    unittest.main()
