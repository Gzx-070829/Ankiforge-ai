from dataclasses import replace
import unittest

from ankiforge_ai.intelligence.call_budget import CallPurpose
from ankiforge_ai.intelligence.generation_run import (
    ChunkGenerationState,
    GenerationStage,
    complete_run,
    create_generation_run,
    fail_chunk,
    reserve_run_call,
    start_chunk,
    succeed_chunk,
    transition_run,
)
from ankiforge_ai.intelligence.models import IntelligenceLevel
from ankiforge_ai.intelligence.recovery import (
    FailedChunkRetry,
    apply_failed_chunk_retry,
    create_failed_chunk_retry,
    start_failed_chunk_retry,
    succeed_failed_chunk_retry,
)


class PartialFailureRecoveryTests(unittest.TestCase):
    def failed_run(self):
        run = create_generation_run(
            run_id="run-recovery",
            request_id=1,
            document_id="doc-recovery",
            document_hash="b" * 64,
            document_snapshot={"text": "private source"},
            settings_snapshot={"card_mode": "concept"},
            level=IntelligenceLevel.FAST,
            chunk_ids=(
                "chunk-0000000000000001",
                "chunk-0000000000000002",
            ),
        )
        run = transition_run(
            transition_run(run, GenerationStage.PLANNING),
            GenerationStage.GENERATING,
        )
        run = reserve_run_call(run, CallPurpose.GENERATE)
        run = start_chunk(run, "chunk-0000000000000001")
        run = succeed_chunk(
            run,
            "chunk-0000000000000001",
            (
                {
                    "candidate_id": "card-sibling",
                    "front": "private sibling front",
                    "back": "private sibling back",
                },
            ),
        )
        run = start_chunk(run, "chunk-0000000000000002")
        return fail_chunk(
            run,
            "chunk-0000000000000002",
            reason_code="generation_call_failed",
        )

    def test_explicit_retry_contains_failed_chunks_only_and_is_safe(self):
        retry = create_failed_chunk_retry(
            self.failed_run(),
            retry_id="retry-001",
        )

        self.assertIsInstance(retry, FailedChunkRetry)
        self.assertEqual(
            retry.chunk_ids,
            ("chunk-0000000000000002",),
        )
        self.assertNotIn("private source", repr(retry))
        self.assertNotIn("private sibling", repr(retry))

    def test_applying_retry_retains_siblings_and_does_not_bill_until_dispatch(self):
        failed = self.failed_run()
        retry = create_failed_chunk_retry(failed, retry_id="retry-001")

        prepared = apply_failed_chunk_retry(failed, retry)

        self.assertEqual(prepared.cards, failed.cards)
        self.assertEqual(prepared.call_budget.call_count, failed.call_budget.call_count)
        self.assertEqual(
            prepared.chunks[0].state,
            ChunkGenerationState.SUCCEEDED,
        )
        self.assertEqual(
            prepared.chunks[1].state,
            ChunkGenerationState.PENDING,
        )
        self.assertEqual(
            prepared.retry_scheduled_chunk_ids,
            ("chunk-0000000000000002",),
        )

    def test_retry_dispatch_reserves_once_and_duplicate_dispatch_cannot_bill(self):
        failed = self.failed_run()
        retry = create_failed_chunk_retry(failed, retry_id="retry-001")
        prepared = apply_failed_chunk_retry(failed, retry)

        running = start_failed_chunk_retry(
            prepared,
            retry,
            "chunk-0000000000000002",
        )
        billed_count = running.call_budget.call_count

        self.assertEqual(billed_count, prepared.call_budget.call_count + 1)
        self.assertEqual(
            running.retry_dispatch_call_counts,
            (("chunk-0000000000000002", billed_count),),
        )
        with self.assertRaisesRegex(ValueError, "retry_chunk_not_pending"):
            start_failed_chunk_retry(
                running,
                retry,
                "chunk-0000000000000002",
            )
        self.assertEqual(running.call_budget.call_count, billed_count)

    def test_retry_accounting_rejects_stale_token_and_unrelated_phase_calls(self):
        failed = self.failed_run()
        retry = create_failed_chunk_retry(failed, retry_id="retry-001")

        for source_count in (0, 2):
            with self.subTest(source_count=source_count):
                with self.assertRaisesRegex(ValueError, "retry_call_accounting"):
                    apply_failed_chunk_retry(
                        failed,
                        replace(retry, source_call_count=source_count),
                    )

        prepared = apply_failed_chunk_retry(failed, retry)
        unrelated = reserve_run_call(prepared, CallPurpose.GENERATE)
        with self.assertRaisesRegex(ValueError, "retry_dispatch_accounting"):
            start_failed_chunk_retry(
                unrelated,
                retry,
                "chunk-0000000000000002",
            )

        running = start_failed_chunk_retry(
            prepared,
            retry,
            "chunk-0000000000000002",
        )
        post_dispatch_call = reserve_run_call(running, CallPurpose.GENERATE)
        with self.assertRaisesRegex(ValueError, "retry_completion_accounting"):
            succeed_failed_chunk_retry(
                post_dispatch_call,
                retry,
                "chunk-0000000000000002",
                (),
            )

    def test_retry_source_call_count_is_bounded_by_global_budget(self):
        failed = self.failed_run()
        retry = create_failed_chunk_retry(failed, retry_id="retry-001")

        for count in (True, -1, 13, 1.5):
            with self.subTest(count=count):
                with self.assertRaises((TypeError, ValueError)):
                    replace(retry, source_call_count=count)

    def test_retry_success_adds_only_new_cards_without_duplicating_sibling(self):
        failed = self.failed_run()
        retry = create_failed_chunk_retry(failed, retry_id="retry-001")
        running = start_failed_chunk_retry(
            apply_failed_chunk_retry(failed, retry),
            retry,
            "chunk-0000000000000002",
        )
        recovered = succeed_failed_chunk_retry(
            running,
            retry,
            "chunk-0000000000000002",
            (
                {
                    "candidate_id": "card-recovered",
                    "front": "recovered front",
                    "back": "recovered back",
                },
            ),
        )

        self.assertEqual(
            tuple(card["candidate_id"] for card in recovered.cards),
            ("card-sibling", "card-recovered"),
        )
        with self.assertRaisesRegex(ValueError, "retry_chunk_not_running"):
            succeed_failed_chunk_retry(
                recovered,
                retry,
                "chunk-0000000000000002",
                (),
            )

    def test_retry_cannot_be_scheduled_twice_or_for_a_foreign_run(self):
        failed = self.failed_run()
        retry = create_failed_chunk_retry(failed, retry_id="retry-001")
        prepared = apply_failed_chunk_retry(failed, retry)

        with self.assertRaisesRegex(ValueError, "retry_already_scheduled"):
            apply_failed_chunk_retry(prepared, retry)
        foreign = create_generation_run(
            run_id="run-foreign",
            request_id=2,
            document_id="doc-recovery",
            document_hash="b" * 64,
            document_snapshot={},
            settings_snapshot={},
            chunk_ids=("chunk-0000000000000002",),
        )
        with self.assertRaisesRegex(ValueError, "retry_run_mismatch"):
            apply_failed_chunk_retry(foreign, retry)

    def test_no_failure_means_no_retry_and_there_is_no_recursive_api(self):
        failed = self.failed_run()
        retry = create_failed_chunk_retry(failed, retry_id="retry-001")
        running = start_failed_chunk_retry(
            apply_failed_chunk_retry(failed, retry),
            retry,
            "chunk-0000000000000002",
        )
        recovered = succeed_failed_chunk_retry(
            running,
            retry,
            "chunk-0000000000000002",
            (),
        )

        with self.assertRaisesRegex(ValueError, "no_failed_chunks"):
            create_failed_chunk_retry(recovered, retry_id="retry-002")
        self.assertFalse(hasattr(retry, "retry"))
        self.assertFalse(hasattr(retry, "run_automatically"))

    def test_explicit_click_can_reopen_only_failures_from_a_completed_partial_run(self):
        partial = self.failed_run()
        partial = transition_run(partial, GenerationStage.REVIEWING)
        partial = transition_run(partial, GenerationStage.CHECKING_COVERAGE)
        partial = complete_run(
            transition_run(partial, GenerationStage.DEDUPLICATING)
        )

        retry = create_failed_chunk_retry(partial, retry_id="retry-completed")
        prepared = apply_failed_chunk_retry(partial, retry)

        self.assertEqual(prepared.stage, GenerationStage.GENERATING)
        self.assertEqual(
            prepared.chunks[0].state,
            ChunkGenerationState.SUCCEEDED,
        )
        self.assertEqual(
            prepared.chunks[1].state,
            ChunkGenerationState.PENDING,
        )
        self.assertEqual(prepared.cards, partial.cards)


if __name__ == "__main__":
    unittest.main()
