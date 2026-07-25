from concurrent.futures import Future
from dataclasses import replace
import unittest
from unittest.mock import patch

from ankiforge_ai.intelligence.critic import (
    CriticAction,
    CriticDecision,
    repair_and_revalidate as real_repair_and_revalidate,
)
from ankiforge_ai.intelligence.call_budget import CallBudget
from ankiforge_ai.intelligence.call_budget import CallPurpose
from ankiforge_ai.intelligence.coverage import assess_generation_coverage
from ankiforge_ai.intelligence.planning import KnowledgePlan, KnowledgePointPlan
from ankiforge_ai.intelligence.generation_run import (
    GenerationRunStatus,
    GenerationStage,
    create_generation_run,
    reserve_run_call,
    start_chunk,
    succeed_chunk,
    transition_run,
)
from ankiforge_ai.intelligence.models import IntelligenceLevel
from ankiforge_ai.pipeline.generation_settings import GenerationSettings
from ankiforge_ai.ui.intelligent_generation_task_controller import (
    IntelligentGenerationTaskController,
    IntelligentGenerationTaskCompletion,
    _apply_coverage_supplement,
    _execute_lifecycle,
)


class DeferredTaskman:
    def __init__(self):
        self.pending = []

    def run_in_background(self, task, on_done, *, uses_collection=True):
        future = Future()
        self.pending.append((task, on_done, future, uses_collection))
        return future

    def complete(self, index=0):
        task, on_done, future, _uses_collection = self.pending[index]
        try:
            future.set_result(task())
        except Exception as error:
            future.set_exception(error)
        on_done(future)


class IntelligentGenerationTaskControllerTests(unittest.TestCase):
    @staticmethod
    def make_plan(*, include_missing_high=False):
        points = [
            KnowledgePointPlan(
                point_id="point-0000000000000001",
                title="ATP carries cellular energy",
                point_type="concept",
                priority="high",
                section_id="section-one",
                source_chunk_ids=("chunk-0000000000000001",),
                source_locations=(),
                recommended_template="concept",
                rationale="Core concept",
            )
        ]
        if include_missing_high:
            points.append(
                KnowledgePointPlan(
                    point_id="point-0000000000000002",
                    title="ATP powers cellular work",
                    point_type="concept",
                    priority="high",
                    section_id="section-two",
                    source_chunk_ids=("chunk-0000000000000001",),
                    source_locations=(),
                    recommended_template="concept",
                    rationale="Second source section",
                )
            )
        return KnowledgePlan(
            plan_id="plan-0000000000000001",
            document_id="doc-controller",
            source="local",
            chunk_ids=("chunk-0000000000000001",),
            points=tuple(points),
        )

    def make_run(self, request_id=1, *, level=IntelligenceLevel.DEEP):
        run = create_generation_run(
            run_id=f"run-{request_id}",
            request_id=request_id,
            document_id="doc-controller",
            document_hash="c" * 64,
            document_snapshot={
                "document_id": "doc-controller",
                "material": (
                    "ATP is the immediate energy carrier in cells. "
                    "ATP carries energy for cellular work."
                ),
            },
            settings_snapshot={
                "card_mode": "concept",
                "secret_hint": "private settings",
            },
            level=level,
            chunk_ids=("chunk-0000000000000001",),
        )
        return replace(run, plan=self.make_plan())

    @staticmethod
    def generator(run):
        return {
            run.chunks[0].chunk_id: (
                {
                    "candidate_id": "card-1",
                    "point_id": "point-0000000000000001",
                    "section_id": "section-one",
                    "front": "What role does ATP have?",
                    "back": "ATP carries energy.",
                },
            )
        }

    def test_worker_callbacks_receive_reserved_immutable_snapshots_off_collection(self):
        taskman = DeferredTaskman()
        callback_observations = []
        completions = []

        def planner(run):
            callback_observations.append(
                ("planner", run.stage, run.call_budget.call_count)
            )
            with self.assertRaises(TypeError):
                run.settings_snapshot["card_mode"] = "exam"
            return self.make_plan()

        def generator(run):
            callback_observations.append(
                ("generator", run.stage, run.call_budget.call_count)
            )
            return self.generator(run)

        def critic(run):
            callback_observations.append(
                ("critic", run.stage, run.call_budget.call_count)
            )
            return {"action": "pass", "reasoning": "private critic output"}

        controller = IntelligentGenerationTaskController(taskman)
        request_id = controller.submit(
            run_snapshot=self.make_run(),
            planner_callback=planner,
            generator_callback=generator,
            critic_callback=critic,
            on_complete=completions.append,
        )

        self.assertEqual(request_id, 1)
        self.assertEqual(callback_observations, [])
        self.assertFalse(taskman.pending[0][3])
        taskman.complete()

        self.assertEqual(
            callback_observations,
            [
                ("planner", GenerationStage.PLANNING, 1),
                ("generator", GenerationStage.GENERATING, 2),
                ("critic", GenerationStage.REVIEWING, 3),
            ],
        )
        completed = completions[0].run
        self.assertEqual(completed.stage, GenerationStage.COMPLETED)
        self.assertEqual(completed.status, GenerationRunStatus.COMPLETED)
        self.assertIsNone(completions[0].error_code)
        self.assertEqual(completed.call_budget.call_count, 3)
        self.assertEqual(completed.cards[0]["candidate_id"], "card-1")
        self.assertNotIn("planner output", repr(completed))
        self.assertNotIn("critic output", repr(completions[0]))

    def test_local_reject_overrides_callback_accept_and_removes_card(self):
        taskman = DeferredTaskman()
        critic_calls = []
        completions = []

        def ungrounded_generator(run):
            return {
                run.chunks[0].chunk_id: (
                    {
                        "candidate_id": "card-ungrounded",
                        "point_id": "point-0000000000000001",
                        "section_id": "section-one",
                        "front": "Which planet is closest to the Sun?",
                        "back": "Mercury is closest to the Sun.",
                    },
                )
            }

        def accepting_critic(run):
            critic_calls.append(run.call_budget.call_count)
            return {"action": "pass", "reasoning": "waive all local rules"}

        controller = IntelligentGenerationTaskController(taskman)
        controller.submit(
            run_snapshot=self.make_run(),
            planner_callback=lambda _run: self.make_plan(),
            generator_callback=ungrounded_generator,
            critic_callback=accepting_critic,
            on_complete=completions.append,
        )
        taskman.complete()

        self.assertEqual(critic_calls, [3])
        self.assertEqual(completions[0].run.cards, ())
        self.assertEqual(completions[0].run.call_budget.call_count, 3)
        self.assertIsNone(completions[0].error_code)

    def test_callback_reject_removes_locally_grounded_card(self):
        taskman = DeferredTaskman()
        completions = []
        controller = IntelligentGenerationTaskController(taskman)
        controller.submit(
            run_snapshot=self.make_run(),
            planner_callback=lambda _run: self.make_plan(),
            generator_callback=self.generator,
            critic_callback=lambda _run: {"action": "reject"},
            on_complete=completions.append,
        )
        taskman.complete()

        self.assertEqual(completions[0].run.cards, ())
        self.assertEqual(completions[0].run.call_budget.call_count, 3)

    def test_fast_local_quality_dedup_and_coverage_run_before_completion(self):
        taskman = DeferredTaskman()
        completions = []

        def duplicate_generator(run):
            card = {
                "candidate_id": "card-1",
                "point_id": "point-0000000000000001",
                "section_id": "section-one",
                "front": "What role does ATP have?",
                "back": "ATP carries energy.",
            }
            duplicate = {**card, "candidate_id": "card-2"}
            return {run.chunks[0].chunk_id: (card, duplicate)}

        controller = IntelligentGenerationTaskController(taskman)
        controller.submit(
            run_snapshot=self.make_run(level=IntelligenceLevel.FAST),
            generator_callback=duplicate_generator,
            on_complete=completions.append,
        )
        taskman.complete()

        completed = completions[0].run
        self.assertEqual(completed.status, GenerationRunStatus.COMPLETED)
        self.assertEqual(
            tuple(card["candidate_id"] for card in completed.cards),
            ("card-1",),
        )
        self.assertEqual(completed.deduplication_result.duplicate_candidate_ids, ("card-2",))
        self.assertEqual(completed.coverage_report.card_count, 1)

    def test_coverage_uses_plan_universe_and_reports_missing_high_priority(self):
        taskman = DeferredTaskman()
        completions = []
        run = replace(
            self.make_run(level=IntelligenceLevel.FAST),
            plan=self.make_plan(include_missing_high=True),
        )
        controller = IntelligentGenerationTaskController(taskman)
        controller.submit(
            run_snapshot=run,
            generator_callback=self.generator,
            on_complete=completions.append,
        )
        taskman.complete()

        completion = completions[0]
        report = completion.run.coverage_report
        self.assertEqual(completion.error_code, None)
        self.assertEqual(
            report.missing_high_priority_point_ids,
            ("point-0000000000000002",),
        )
        self.assertEqual(report.uncovered_section_ids, ("section-two",))
        self.assertTrue(report.supplement_recommended)
        self.assertIsInstance(completion.run.plan, KnowledgePlan)
        self.assertEqual(
            completion.run.plan.points[1].source_chunk_ids,
            ("chunk-0000000000000001",),
        )

    def test_missing_coverage_source_fails_with_safe_reason(self):
        taskman = DeferredTaskman()
        completions = []
        controller = IntelligentGenerationTaskController(taskman)
        controller.submit(
            run_snapshot=replace(
                self.make_run(level=IntelligenceLevel.FAST),
                plan=None,
            ),
            generator_callback=self.generator,
            on_complete=completions.append,
        )
        taskman.complete()

        completion = completions[0]
        self.assertEqual(completion.error_code, "coverage_source_unavailable")
        self.assertEqual(completion.run.status, GenerationRunStatus.FAILED)
        self.assertIsNone(completion.run.coverage_report)

    def test_new_submission_supersedes_and_discards_stale_completion(self):
        taskman = DeferredTaskman()
        completions = []
        controller = IntelligentGenerationTaskController(taskman)

        controller.submit(
            run_snapshot=self.make_run(1),
            generator_callback=self.generator,
            on_complete=completions.append,
        )
        controller.submit(
            run_snapshot=self.make_run(2),
            generator_callback=self.generator,
            on_complete=completions.append,
        )

        taskman.complete(0)
        self.assertEqual(completions, [])
        self.assertTrue(controller.running)
        taskman.complete(1)
        self.assertEqual([item.request_id for item in completions], [2])
        self.assertFalse(controller.running)

    def test_supersession_during_worker_stops_all_later_old_callbacks(self):
        taskman = DeferredTaskman()
        completions = []
        old_generator_calls = []
        controller = IntelligentGenerationTaskController(taskman)

        def superseding_planner(_old_run):
            controller.submit(
                run_snapshot=self.make_run(2),
                generator_callback=self.generator,
                on_complete=completions.append,
            )
            return {"plan_id": "old-plan"}

        def old_generator(_run):
            old_generator_calls.append("called")
            return {}

        controller.submit(
            run_snapshot=self.make_run(1),
            planner_callback=superseding_planner,
            generator_callback=old_generator,
            critic_callback=lambda _run: None,
            on_complete=completions.append,
        )

        taskman.complete(0)
        self.assertEqual(old_generator_calls, [])
        self.assertEqual(completions, [])
        taskman.complete(1)
        self.assertEqual([item.request_id for item in completions], [2])

    def test_close_makes_late_success_failure_and_callbacks_noops(self):
        taskman = DeferredTaskman()
        completions = []
        controller = IntelligentGenerationTaskController(taskman)
        controller.submit(
            run_snapshot=self.make_run(),
            generator_callback=self.generator,
            on_complete=completions.append,
        )

        controller.close()
        taskman.complete()

        self.assertFalse(controller.alive)
        self.assertFalse(controller.running)
        self.assertEqual(completions, [])
        self.assertIsNone(
            controller.submit(
                run_snapshot=self.make_run(2),
                generator_callback=self.generator,
                on_complete=completions.append,
            )
        )

    def test_worker_exception_is_safe_billed_once_and_never_retried(self):
        taskman = DeferredTaskman()
        calls = []
        completions = []
        secret = "C:\\Users\\private\\provider-output"

        def failing_generator(run):
            calls.append(run.call_budget.call_count)
            raise RuntimeError(secret)

        controller = IntelligentGenerationTaskController(taskman)
        controller.submit(
            run_snapshot=self.make_run(level=IntelligenceLevel.FAST),
            generator_callback=failing_generator,
            on_complete=completions.append,
        )
        taskman.complete()

        self.assertEqual(calls, [1])
        completion = completions[0]
        self.assertEqual(completion.error_code, "generator_call_failed")
        self.assertEqual(completion.run.call_budget.call_count, 1)
        self.assertEqual(completion.run.status, GenerationRunStatus.FAILED)
        self.assertNotIn(secret, repr(completion))

    def test_exploding_generator_iterator_keeps_generation_call_billed(self):
        class ExplodingCards:
            def __iter__(self):
                yield {
                    "candidate_id": "card-1",
                    "point_id": "point-0000000000000001",
                    "section_id": "section-one",
                    "front": "What role does ATP have?",
                    "back": "ATP carries energy.",
                }
                raise RuntimeError("private iterator output")

        taskman = DeferredTaskman()
        completions = []
        controller = IntelligentGenerationTaskController(taskman)
        controller.submit(
            run_snapshot=self.make_run(level=IntelligenceLevel.FAST),
            generator_callback=lambda _run: ExplodingCards(),
            on_complete=completions.append,
        )
        taskman.complete()

        completion = completions[0]
        self.assertEqual(completion.run.call_budget.call_count, 1)
        self.assertEqual(completion.run.status, GenerationRunStatus.FAILED)
        self.assertEqual(completion.error_code, "generation_materialization_failed")

    def test_generator_materialization_supersession_prevents_critic_reservation(self):
        taskman = DeferredTaskman()
        completions = []
        critic_calls = []
        controller = IntelligentGenerationTaskController(taskman)

        class SupersedingCards:
            def __iter__(_self):
                controller.submit(
                    run_snapshot=self.make_run(
                        2,
                        level=IntelligenceLevel.FAST,
                    ),
                    generator_callback=self.generator,
                    on_complete=completions.append,
                )
                yield {
                    "candidate_id": "old-card",
                    "point_id": "point-0000000000000001",
                    "section_id": "section-one",
                    "front": "What role does ATP have?",
                    "back": "ATP carries energy.",
                }

        controller.submit(
            run_snapshot=self.make_run(1),
            planner_callback=lambda _run: {"plan_id": "old-plan"},
            generator_callback=lambda _run: SupersedingCards(),
            critic_callback=lambda run: critic_calls.append(
                run.call_budget.call_count
            ),
            on_complete=completions.append,
        )

        taskman.complete(0)
        self.assertEqual(critic_calls, [])
        self.assertEqual(completions, [])
        taskman.complete(1)
        self.assertEqual([item.request_id for item in completions], [2])

    def test_optional_stages_can_complete_below_estimate_without_dummy_calls(self):
        cases = (
            (IntelligenceLevel.FAST, None, None, 1, None),
            (
                IntelligenceLevel.STANDARD,
                lambda _run: self.make_plan(),
                None,
                2,
                None,
            ),
            (
                IntelligenceLevel.DEEP,
                lambda _run: self.make_plan(),
                lambda _run: {"action": "pass"},
                3,
                None,
            ),
        )
        for index, (level, planner, critic, count, error_code) in enumerate(
            cases,
            start=1,
        ):
            with self.subTest(level=level):
                taskman = DeferredTaskman()
                completions = []
                controller = IntelligentGenerationTaskController(taskman)
                controller.submit(
                    run_snapshot=self.make_run(index, level=level),
                    planner_callback=planner,
                    generator_callback=self.generator,
                    critic_callback=critic,
                    on_complete=completions.append,
                )
                taskman.complete()

                self.assertEqual(
                    completions[0].run.call_budget.call_count,
                    count,
                )
                self.assertEqual(completions[0].error_code, error_code)
                self.assertEqual(
                    completions[0].run.status,
                    GenerationRunStatus.COMPLETED,
                )

    def test_deep_skips_critic_reservation_when_generation_produced_no_cards(self):
        taskman = DeferredTaskman()
        critic_calls = []
        completions = []
        controller = IntelligentGenerationTaskController(taskman)
        controller.submit(
            run_snapshot=self.make_run(level=IntelligenceLevel.DEEP),
            planner_callback=lambda _run: self.make_plan(),
            generator_callback=lambda run: {
                run.chunks[0].chunk_id: {
                    "error_code": "generation_call_failed"
                }
            },
            critic_callback=lambda _run: critic_calls.append("called"),
            on_complete=completions.append,
        )
        taskman.complete()

        completed = completions[0].run
        self.assertEqual(critic_calls, [])
        self.assertEqual(
            [
                reservation.purpose.value
                for reservation in completed.call_budget.reservations
            ],
            ["planner", "generate"],
        )
        self.assertEqual(completed.status, GenerationRunStatus.PARTIAL)

    def test_completion_callback_exception_is_isolated_and_releases_state(self):
        taskman = DeferredTaskman()

        def broken_ui_callback(_completion):
            raise ValueError("deleted wrapper with private data")

        controller = IntelligentGenerationTaskController(taskman)
        controller.submit(
            run_snapshot=self.make_run(),
            generator_callback=self.generator,
            on_complete=broken_ui_callback,
        )

        taskman.complete()

        self.assertFalse(controller.running)
        self.assertIsNone(controller.current_request_id)

    def test_partial_run_retries_failed_generation_chunks_only_after_explicit_submit(self):
        plan = KnowledgePlan(
            plan_id="plan-0000000000000099",
            document_id="doc-retry-controller",
            source="local",
            chunk_ids=(
                "chunk-0000000000000001",
                "chunk-0000000000000002",
            ),
            points=(
                KnowledgePointPlan(
                    point_id="point-0000000000000001",
                    title="ATP carries energy",
                    point_type="concept",
                    priority="high",
                    section_id="section-one",
                    source_chunk_ids=("chunk-0000000000000001",),
                    source_locations=(),
                    recommended_template="concept",
                    rationale="Core concept",
                ),
                KnowledgePointPlan(
                    point_id="point-0000000000000002",
                    title="ATP powers work",
                    point_type="concept",
                    priority="high",
                    section_id="section-two",
                    source_chunk_ids=("chunk-0000000000000002",),
                    source_locations=(),
                    recommended_template="concept",
                    rationale="Second concept",
                ),
            ),
        )
        run = create_generation_run(
            run_id="run-retry-controller",
            request_id=1,
            document_id=plan.document_id,
            document_hash="e" * 64,
            document_snapshot={
                "chunk_text_by_id": {
                    "chunk-0000000000000001": "ATP carries cellular energy.",
                    "chunk-0000000000000002": "ATP powers cellular work.",
                }
            },
            settings_snapshot={"card_mode": "concept"},
            level=IntelligenceLevel.FAST,
            chunk_ids=plan.chunk_ids,
        )
        run = replace(run, plan=plan)
        taskman = DeferredTaskman()
        first_completions = []
        controller = IntelligentGenerationTaskController(taskman)
        controller.submit(
            run_snapshot=run,
            generator_callback=lambda _run: {
                plan.chunk_ids[0]: (
                    {
                        "candidate_id": "card-first",
                        "point_id": plan.points[0].point_id,
                        "section_id": "section-one",
                        "front": "What does ATP carry?",
                        "back": "ATP carries cellular energy.",
                    },
                ),
                plan.chunk_ids[1]: {"error_code": "generation_call_failed"},
            },
            on_complete=first_completions.append,
        )
        taskman.complete()
        partial = first_completions[0].run

        self.assertEqual(partial.status, GenerationRunStatus.PARTIAL)
        self.assertEqual(partial.failed_chunk_ids, (plan.chunk_ids[1],))
        self.assertEqual(len(taskman.pending), 1)

        retry_calls = []
        retry_completions = []
        controller.retry_failed(
            run_snapshot=partial,
            retry_generator_callback=lambda retry_run, chunk_id: (
                retry_calls.append(
                    (chunk_id, retry_run.call_budget.call_count)
                )
                or (
                    {
                        "candidate_id": "card-recovered",
                        "point_id": plan.points[1].point_id,
                        "section_id": "section-two",
                        "front": "What cellular work does ATP power?",
                        "back": "ATP powers cellular work.",
                    },
                )
            ),
            on_complete=retry_completions.append,
        )
        self.assertEqual(len(taskman.pending), 2)
        self.assertEqual(retry_calls, [])
        taskman.complete(1)

        recovered = retry_completions[0].run
        self.assertEqual(recovered.status, GenerationRunStatus.COMPLETED)
        self.assertEqual(recovered.call_budget.call_count, 2)
        self.assertEqual(
            tuple(card["candidate_id"] for card in recovered.cards),
            ("card-first", "card-recovered"),
        )
        self.assertEqual(retry_calls, [(plan.chunk_ids[1], 2)])

    def test_failed_retry_cannot_be_scheduled_twice_after_first_retry_fails(self):
        taskman = DeferredTaskman()
        initial = []
        retries = []
        controller = IntelligentGenerationTaskController(taskman)
        controller.submit(
            run_snapshot=self.make_run(level=IntelligenceLevel.FAST),
            generator_callback=lambda run: {
                run.chunks[0].chunk_id: {
                    "error_code": "generation_call_failed"
                }
            },
            on_complete=initial.append,
        )
        taskman.complete()

        controller.retry_failed(
            run_snapshot=initial[0].run,
            retry_generator_callback=lambda _run, _chunk_id: {
                "error_code": "retry_generation_failed"
            },
            on_complete=retries.append,
        )
        taskman.complete(1)
        failed_retry = retries[0].run
        pending_count = len(taskman.pending)

        second = controller.retry_failed(
            run_snapshot=failed_retry,
            retry_generator_callback=lambda _run, _chunk_id: (
                self.fail("a second retry must not dispatch")
            ),
            on_complete=retries.append,
        )

        self.assertIsNone(second)
        self.assertEqual(len(taskman.pending), pending_count)
        self.assertEqual(
            failed_retry.retry_scheduled_chunk_ids,
            failed_retry.failed_chunk_ids,
        )

    def test_taskman_submit_exception_becomes_safe_current_completion(self):
        class BrokenTaskman:
            def run_in_background(self, *_args, **_kwargs):
                raise RuntimeError("private taskman output")

        completions = []
        controller = IntelligentGenerationTaskController(BrokenTaskman())
        request_id = controller.submit(
            run_snapshot=self.make_run(),
            generator_callback=self.generator,
            on_complete=completions.append,
        )

        self.assertEqual(request_id, 1)
        self.assertEqual(completions[0].error_code, "background_task_submit_failed")
        self.assertFalse(controller.running)
        self.assertNotIn("private taskman output", repr(completions[0]))

    def test_grouped_generator_reserves_each_batch_and_keeps_sibling_batch_success(self):
        plan = KnowledgePlan(
            plan_id="plan-0000000000000088",
            document_id="doc-grouped-controller",
            source="local",
            chunk_ids=(
                "chunk-0000000000000001",
                "chunk-0000000000000002",
            ),
            points=(
                KnowledgePointPlan(
                    point_id="point-0000000000000001",
                    title="ATP carries energy",
                    point_type="concept",
                    priority="high",
                    section_id="section-one",
                    source_chunk_ids=("chunk-0000000000000001",),
                    source_locations=(),
                    recommended_template="concept",
                    rationale="Core concept",
                ),
                KnowledgePointPlan(
                    point_id="point-0000000000000002",
                    title="ATP powers work",
                    point_type="concept",
                    priority="high",
                    section_id="section-two",
                    source_chunk_ids=("chunk-0000000000000002",),
                    source_locations=(),
                    recommended_template="concept",
                    rationale="Second concept",
                ),
            ),
        )
        run = replace(
            create_generation_run(
                run_id="run-grouped-controller",
                request_id=1,
                document_id=plan.document_id,
                document_hash="f" * 64,
                document_snapshot={
                    "chunk_text_by_id": {
                        plan.chunk_ids[0]: "ATP carries cellular energy.",
                        plan.chunk_ids[1]: "ATP powers cellular work.",
                    }
                },
                settings_snapshot={"card_mode": "concept"},
                level=IntelligenceLevel.FAST,
                chunk_ids=plan.chunk_ids,
            ),
            plan=plan,
        )
        observations = []

        class GroupedGenerator:
            def generation_batches(self, _run):
                return tuple((chunk_id,) for chunk_id in plan.chunk_ids)

            def generate_batch(self, reserved_run, chunk_ids):
                observations.append(
                    (chunk_ids, reserved_run.call_budget.call_count)
                )
                if chunk_ids == (plan.chunk_ids[1],):
                    raise RuntimeError("private provider failure")
                return {
                    plan.chunk_ids[0]: (
                        {
                            "candidate_id": "card-grouped",
                            "point_id": plan.points[0].point_id,
                            "section_id": "section-one",
                            "front": "What does ATP carry?",
                            "back": "ATP carries cellular energy.",
                        },
                    )
                }

        taskman = DeferredTaskman()
        completions = []
        IntelligentGenerationTaskController(taskman).submit(
            run_snapshot=run,
            generator_callback=GroupedGenerator(),
            on_complete=completions.append,
        )
        taskman.complete()

        self.assertEqual(
            observations,
            [
                ((plan.chunk_ids[0],), 1),
                ((plan.chunk_ids[1],), 2),
            ],
        )
        completed = completions[0].run
        self.assertEqual(completed.call_budget.call_count, 2)
        self.assertEqual(completed.status, GenerationRunStatus.PARTIAL)
        self.assertEqual(completed.failed_chunk_ids, (plan.chunk_ids[1],))
        self.assertEqual(
            tuple(card["candidate_id"] for card in completed.cards),
            ("card-grouped",),
        )

    def test_standard_repairs_one_locally_blocking_card_with_reserved_call(self):
        taskman = DeferredTaskman()
        completions = []
        repair_observations = []

        def ungrounded_generator(run):
            return {
                run.chunks[0].chunk_id: (
                    {
                        "candidate_id": "card-repair",
                        "point_id": "point-0000000000000001",
                        "section_id": "section-one",
                        "front": "Which planet is closest to the Sun?",
                        "back": "Mercury is closest to the Sun.",
                    },
                )
            }

        def repair(card, source_text):
            repair_observations.append(
                (card["candidate_id"], "ATP" in source_text)
            )
            return {
                **dict(card),
                "front": "What role does ATP have?",
                "back": "ATP carries energy for cellular work.",
                "source_excerpt": "ATP carries energy",
            }

        IntelligentGenerationTaskController(taskman).submit(
            run_snapshot=self.make_run(level=IntelligenceLevel.STANDARD),
            generator_callback=ungrounded_generator,
            repair_callback=repair,
            on_complete=completions.append,
        )
        taskman.complete()

        completed = completions[0].run
        self.assertEqual(repair_observations, [("card-repair", True)])
        self.assertEqual(
            [
                reservation.purpose.value
                for reservation in completed.call_budget.reservations
            ],
            ["generate", "repair"],
        )
        self.assertEqual(completed.status, GenerationRunStatus.COMPLETED)
        self.assertEqual(completed.cards[0]["candidate_id"], "card-repair")
        self.assertEqual(
            completed.cards[0]["back"],
            "ATP carries energy for cellular work.",
        )

    def test_standard_repairs_at_most_one_blocking_card_for_the_whole_run(self):
        taskman = DeferredTaskman()
        completions = []
        repair_calls = []
        plan = self.make_plan(include_missing_high=True)
        run = replace(
            self.make_run(level=IntelligenceLevel.STANDARD),
            plan=plan,
        )

        def generator(current):
            return {
                current.chunks[0].chunk_id: tuple(
                    {
                        "candidate_id": f"card-broken-{index}",
                        "point_id": point.point_id,
                        "section_id": point.section_id,
                        "front": "Which planet is closest to the Sun?",
                        "back": "Mercury is closest to the Sun.",
                    }
                    for index, point in enumerate(plan.points, start=1)
                )
            }

        def repair(card, _source_text):
            repair_calls.append(card["candidate_id"])
            return {
                **dict(card),
                "front": "What role does ATP have?",
                "back": "ATP carries energy for cellular work.",
            }

        IntelligentGenerationTaskController(taskman).submit(
            run_snapshot=run,
            generator_callback=generator,
            repair_callback=repair,
            on_complete=completions.append,
        )
        taskman.complete()

        completed = completions[0].run
        self.assertEqual(repair_calls, ["card-broken-1"])
        self.assertEqual(
            [
                reservation.purpose.value
                for reservation in completed.call_budget.reservations
            ],
            ["generate", "repair"],
        )
        self.assertEqual(
            tuple(card["candidate_id"] for card in completed.cards),
            ("card-broken-1",),
        )

    def test_deep_repairs_at_most_once_per_point_when_budget_remains(self):
        taskman = DeferredTaskman()
        completions = []
        repair_calls = []
        plan = self.make_plan(include_missing_high=True)
        run = replace(
            self.make_run(level=IntelligenceLevel.DEEP),
            plan=plan,
        )

        def generator(current):
            return {
                current.chunks[0].chunk_id: (
                    {
                        "candidate_id": "card-point-one-a",
                        "point_id": plan.points[0].point_id,
                        "section_id": plan.points[0].section_id,
                        "front": "Which planet is closest to the Sun?",
                        "back": "Mercury is closest to the Sun.",
                    },
                    {
                        "candidate_id": "card-point-one-b",
                        "point_id": plan.points[0].point_id,
                        "section_id": plan.points[0].section_id,
                        "front": "Which planet is nearest the Sun?",
                        "back": "Mercury is nearest the Sun.",
                    },
                    {
                        "candidate_id": "card-point-two",
                        "point_id": plan.points[1].point_id,
                        "section_id": plan.points[1].section_id,
                        "front": "Which planet starts the alphabet?",
                        "back": "Venus starts the alphabet.",
                    },
                )
            }

        def repair(card, _source_text):
            repair_calls.append(card["point_id"])
            return {
                **dict(card),
                "front": "What role does ATP have?",
                "back": "ATP carries energy for cellular work.",
            }

        IntelligentGenerationTaskController(taskman).submit(
            run_snapshot=run,
            generator_callback=generator,
            repair_callback=repair,
            on_complete=completions.append,
        )
        taskman.complete()

        self.assertEqual(
            repair_calls,
            [plan.points[0].point_id, plan.points[1].point_id],
        )
        self.assertEqual(
            [
                reservation.purpose.value
                for reservation in completions[0].run.call_budget.reservations
            ],
            ["generate", "repair", "repair"],
        )

    def test_local_review_and_repair_revalidation_receive_routed_user_settings(self):
        taskman = DeferredTaskman()
        completions = []
        observed_decide_settings = []
        plan = self.make_plan()
        plan = replace(
            plan,
            points=(
                replace(
                    plan.points[0],
                    recommended_template="quick_review",
                ),
            ),
        )
        run = replace(
            self.make_run(level=IntelligenceLevel.FAST),
            plan=plan,
            settings_snapshot={
                "card_mode": "auto",
                "card_count": "fewer",
                "answer_length": "medium",
                "language": "zh",
                "intelligence_level": "fast",
            },
        )

        def observe_decision(**kwargs):
            observed_decide_settings.append(kwargs.get("settings"))
            return CriticDecision(CriticAction.PASS)

        with patch(
            "ankiforge_ai.ui.intelligent_generation_task_controller.decide_card",
            side_effect=observe_decision,
        ):
            IntelligentGenerationTaskController(taskman).submit(
                run_snapshot=run,
                generator_callback=self.generator,
                on_complete=completions.append,
            )
            taskman.complete()

        self.assertEqual(len(completions[0].run.cards), 1)
        self.assertEqual(
            observed_decide_settings,
            [
                GenerationSettings(
                    card_mode="quick_review",
                    card_count="fewer",
                    answer_length="medium",
                    language="zh",
                )
            ],
        )

        repair_taskman = DeferredTaskman()
        repair_completions = []
        observed_repair_settings = []

        def capture_repair(**kwargs):
            observed_repair_settings.append(kwargs.get("settings"))
            return real_repair_and_revalidate(**kwargs)

        def ungrounded_generator(current):
            return {
                current.chunks[0].chunk_id: (
                    {
                        "candidate_id": "card-settings-repair",
                        "point_id": plan.points[0].point_id,
                        "section_id": plan.points[0].section_id,
                        "front": "Which planet is closest to the Sun?",
                        "back": "Mercury is closest to the Sun.",
                    },
                )
            }

        with patch(
            "ankiforge_ai.ui.intelligent_generation_task_controller.repair_and_revalidate",
            side_effect=capture_repair,
        ):
            IntelligentGenerationTaskController(repair_taskman).submit(
                run_snapshot=replace(
                    run,
                    level=IntelligenceLevel.STANDARD,
                    call_budget=CallBudget.for_level(
                        IntelligenceLevel.STANDARD
                    ),
                ),
                generator_callback=ungrounded_generator,
                repair_callback=lambda card, _source: {
                    **dict(card),
                    "front": "What role does ATP have?",
                    "back": "ATP carries energy for cellular work.",
                },
                on_complete=repair_completions.append,
            )
            repair_taskman.complete()

        self.assertEqual(
            observed_repair_settings,
            [
                GenerationSettings(
                    card_mode="quick_review",
                    card_count="fewer",
                    answer_length="medium",
                    language="zh",
                )
            ],
        )

    def test_deep_supplements_missing_high_priority_point_once_after_coverage(self):
        taskman = DeferredTaskman()
        completions = []
        supplement_observations = []
        plan = self.make_plan(include_missing_high=True)
        run = replace(
            self.make_run(level=IntelligenceLevel.DEEP),
            plan=plan,
        )

        def supplement(reserved_run, point_ids):
            supplement_observations.append(
                (point_ids, reserved_run.call_budget.call_count)
            )
            return {
                plan.chunk_ids[0]: (
                    {
                        "candidate_id": "card-supplement",
                        "point_id": plan.points[1].point_id,
                        "section_id": plan.points[1].section_id,
                        "front": "What work does ATP power?",
                        "back": "ATP powers cellular work.",
                    },
                )
            }

        IntelligentGenerationTaskController(taskman).submit(
            run_snapshot=run,
            planner_callback=lambda _run: plan,
            generator_callback=self.generator,
            critic_callback=lambda _run: {"action": "pass"},
            supplement_callback=supplement,
            on_complete=completions.append,
        )
        taskman.complete()

        completed = completions[0].run
        self.assertEqual(
            supplement_observations,
            [((plan.points[1].point_id,), 4)],
        )
        self.assertTrue(completed.supplement_used)
        self.assertEqual(
            [
                reservation.purpose.value
                for reservation in completed.call_budget.reservations
            ],
            ["planner", "generate", "critic", "supplement"],
        )
        self.assertEqual(completed.status, GenerationRunStatus.COMPLETED)
        self.assertEqual(
            tuple(card["candidate_id"] for card in completed.cards),
            ("card-1", "card-supplement"),
        )
        self.assertFalse(
            completed.coverage_report.supplement_recommended
        )

    def test_deep_skips_supplement_when_missing_points_only_use_failed_chunks(self):
        taskman = DeferredTaskman()
        completions = []
        supplement_calls = []
        plan = self.make_plan(include_missing_high=True)
        run = replace(
            self.make_run(level=IntelligenceLevel.DEEP),
            plan=plan,
        )

        IntelligentGenerationTaskController(taskman).submit(
            run_snapshot=run,
            planner_callback=lambda _run: plan,
            generator_callback=lambda current: {
                current.chunks[0].chunk_id: {
                    "error_code": "generation_call_failed"
                }
            },
            supplement_callback=lambda _run, point_ids: (
                supplement_calls.append(point_ids) or {}
            ),
            on_complete=completions.append,
        )
        taskman.complete()

        completed = completions[0].run
        self.assertEqual(supplement_calls, [])
        self.assertFalse(completed.supplement_used)
        self.assertEqual(
            [
                reservation.purpose.value
                for reservation in completed.call_budget.reservations
            ],
            ["planner", "generate"],
        )

    def test_deep_skips_supplement_reservation_when_card_limit_is_full(self):
        plan = self.make_plan(include_missing_high=True)
        run = replace(
            self.make_run(level=IntelligenceLevel.DEEP),
            plan=plan,
            settings_snapshot={
                "card_mode": "concept",
                "card_count": "fewer",
                "answer_length": "short",
                "language": "en",
            },
        )
        run = transition_run(run, GenerationStage.PLANNING)
        run = transition_run(run, GenerationStage.GENERATING)
        run = reserve_run_call(run, CallPurpose.GENERATE)
        run = start_chunk(run, run.chunks[0].chunk_id)
        run = succeed_chunk(
            run,
            run.chunks[0].chunk_id,
            (
                {
                    "candidate_id": "card-limit-1",
                    "point_id": plan.points[0].point_id,
                    "section_id": plan.points[0].section_id,
                    "front": "What is ATP in cells?",
                    "back": "ATP is the immediate energy carrier in cells.",
                },
                {
                    "candidate_id": "card-limit-2",
                    "point_id": plan.points[0].point_id,
                    "section_id": plan.points[0].section_id,
                    "front": "What does ATP carry?",
                    "back": "ATP carries energy.",
                },
                {
                    "candidate_id": "card-limit-3",
                    "point_id": plan.points[0].point_id,
                    "section_id": plan.points[0].section_id,
                    "front": "What work does ATP support?",
                    "back": "ATP carries energy for cellular work.",
                },
            ),
        )
        run = transition_run(run, GenerationStage.REVIEWING)
        run = transition_run(run, GenerationStage.CHECKING_COVERAGE)
        coverage = assess_generation_coverage(
            plan.points,
            run.cards,
            section_ids=tuple(
                dict.fromkeys(point.section_id for point in plan.points)
            ),
        )
        self.assertTrue(coverage.supplement_recommended)
        run = replace(run, coverage_report=coverage)
        supplement_calls = []

        completed = _apply_coverage_supplement(
            run,
            supplement_callback=lambda _run, point_ids: (
                supplement_calls.append(point_ids) or {}
            ),
            continue_if_current=lambda: True,
        )

        self.assertEqual(supplement_calls, [])
        self.assertFalse(completed.supplement_used)
        self.assertEqual(completed.call_budget.call_count, 1)

    def test_deep_supplement_filters_missing_points_to_succeeded_chunks(self):
        chunk_ids = (
            "chunk-0000000000000001",
            "chunk-0000000000000002",
        )
        points = (
            KnowledgePointPlan(
                point_id="point-0000000000000001",
                title="ATP carries energy",
                point_type="concept",
                priority="high",
                section_id="section-one",
                source_chunk_ids=(chunk_ids[0],),
                source_locations=(),
                recommended_template="concept",
                rationale="covered",
            ),
            KnowledgePointPlan(
                point_id="point-0000000000000002",
                title="ATP powers work",
                point_type="concept",
                priority="high",
                section_id="section-two",
                source_chunk_ids=(chunk_ids[0],),
                source_locations=(),
                recommended_template="concept",
                rationale="eligible missing",
            ),
            KnowledgePointPlan(
                point_id="point-0000000000000003",
                title="Mitochondria make ATP",
                point_type="concept",
                priority="high",
                section_id="section-three",
                source_chunk_ids=(chunk_ids[1],),
                source_locations=(),
                recommended_template="concept",
                rationale="failed missing",
            ),
        )
        plan = KnowledgePlan(
            plan_id="plan-0000000000000099",
            document_id="doc-mixed-supplement",
            source="local",
            chunk_ids=chunk_ids,
            points=points,
        )
        run = replace(
            create_generation_run(
                run_id="run-mixed-supplement",
                request_id=1,
                document_id=plan.document_id,
                document_hash="9" * 64,
                document_snapshot={
                    "chunk_text_by_id": {
                        chunk_ids[0]: "ATP carries energy and powers work.",
                        chunk_ids[1]: "Mitochondria make ATP.",
                    }
                },
                settings_snapshot={"card_mode": "concept"},
                level=IntelligenceLevel.DEEP,
                chunk_ids=chunk_ids,
            ),
            plan=plan,
        )
        taskman = DeferredTaskman()
        completions = []
        supplement_calls = []

        def generator(_run):
            return {
                chunk_ids[0]: (
                    {
                        "candidate_id": "card-covered",
                        "point_id": points[0].point_id,
                        "section_id": points[0].section_id,
                        "front": "What does ATP carry?",
                        "back": "ATP carries energy.",
                    },
                ),
                chunk_ids[1]: {"error_code": "generation_call_failed"},
            }

        IntelligentGenerationTaskController(taskman).submit(
            run_snapshot=run,
            planner_callback=lambda _run: plan,
            generator_callback=generator,
            critic_callback=lambda _run: {"decisions": []},
            supplement_callback=lambda _run, point_ids: (
                supplement_calls.append(point_ids) or {}
            ),
            on_complete=completions.append,
        )
        taskman.complete()

        self.assertEqual(
            supplement_calls,
            [(points[1].point_id,)],
        )
        self.assertTrue(completions[0].run.supplement_used)

    def test_hostile_grouped_mapping_is_billed_and_becomes_partial(self):
        class HostileMapping(dict):
            def __iter__(self):
                yield "chunk-0000000000000001"
                raise RuntimeError("private mapping iterator")

        class GroupedGenerator:
            def generation_batches(self, run):
                return ((run.chunks[0].chunk_id,),)

            def generate_batch(self, _run, _batch):
                return HostileMapping()

        taskman = DeferredTaskman()
        completions = []
        IntelligentGenerationTaskController(taskman).submit(
            run_snapshot=self.make_run(level=IntelligenceLevel.FAST),
            generator_callback=GroupedGenerator(),
            on_complete=completions.append,
        )
        taskman.complete()

        completed = completions[0].run
        self.assertEqual(completed.call_budget.call_count, 1)
        self.assertEqual(completed.status, GenerationRunStatus.PARTIAL)
        self.assertEqual(
            completed.failed_chunk_ids,
            ("chunk-0000000000000001",),
        )
        self.assertIsNone(completions[0].error_code)

    def test_hostile_supplement_mapping_stays_billed_without_accepting_cards(self):
        class HostileMapping(dict):
            def __iter__(self):
                yield "chunk-0000000000000001"
                raise RuntimeError("private supplement iterator")

        taskman = DeferredTaskman()
        completions = []
        plan = self.make_plan(include_missing_high=True)
        run = replace(
            self.make_run(level=IntelligenceLevel.DEEP),
            plan=plan,
        )
        IntelligentGenerationTaskController(taskman).submit(
            run_snapshot=run,
            planner_callback=lambda _run: plan,
            generator_callback=self.generator,
            critic_callback=lambda _run: {"action": "pass"},
            supplement_callback=lambda _run, _point_ids: HostileMapping(),
            on_complete=completions.append,
        )
        taskman.complete()

        completed = completions[0].run
        self.assertEqual(completed.call_budget.call_count, 4)
        self.assertTrue(completed.supplement_used)
        self.assertEqual(
            tuple(card["candidate_id"] for card in completed.cards),
            ("card-1",),
        )
        self.assertTrue(completed.coverage_report.supplement_recommended)

    def test_hostile_batch_iterable_is_preflight_bounded_before_any_dispatch(self):
        observations = []

        class TooManyBatches:
            def __iter__(self):
                for index in range(100):
                    observations.append(index)
                    yield ("chunk-0000000000000001",)

        class GroupedGenerator:
            def generation_batches(self, _run):
                return TooManyBatches()

            def generate_batch(self, _run, _batch):
                raise AssertionError("preflight must reject before dispatch")

        taskman = DeferredTaskman()
        completions = []
        IntelligentGenerationTaskController(taskman).submit(
            run_snapshot=self.make_run(level=IntelligenceLevel.FAST),
            generator_callback=GroupedGenerator(),
            on_complete=completions.append,
        )
        taskman.complete()

        self.assertEqual(observations, [0, 1, 2, 3])
        self.assertEqual(completions[0].run.call_budget.call_count, 0)
        self.assertEqual(completions[0].error_code, "generator_call_failed")

    def test_ungrounded_supplement_is_billed_but_rejected_by_local_gate(self):
        taskman = DeferredTaskman()
        completions = []
        plan = self.make_plan(include_missing_high=True)
        run = replace(
            self.make_run(level=IntelligenceLevel.DEEP),
            plan=plan,
        )
        IntelligentGenerationTaskController(taskman).submit(
            run_snapshot=run,
            planner_callback=lambda _run: plan,
            generator_callback=self.generator,
            critic_callback=lambda _run: {"action": "pass"},
            supplement_callback=lambda _run, _point_ids: {
                plan.chunk_ids[0]: (
                    {
                        "candidate_id": "card-ungrounded-supplement",
                        "point_id": plan.points[1].point_id,
                        "section_id": plan.points[1].section_id,
                        "front": "Which planet is closest to the Sun?",
                        "back": "Mercury is closest to the Sun.",
                    },
                )
            },
            on_complete=completions.append,
        )
        taskman.complete()

        completed = completions[0].run
        self.assertEqual(completed.call_budget.call_count, 4)
        self.assertTrue(completed.supplement_used)
        self.assertEqual(
            tuple(card["candidate_id"] for card in completed.cards),
            ("card-1",),
        )
        self.assertTrue(completed.coverage_report.supplement_recommended)

    def test_stale_after_repair_and_supplement_preserves_charged_superseded_runs(self):
        repair_current = [True]

        def ungrounded_generator(run):
            return {
                run.chunks[0].chunk_id: (
                    {
                        "candidate_id": "card-stale-repair",
                        "point_id": "point-0000000000000001",
                        "section_id": "section-one",
                        "front": "Which planet is closest to the Sun?",
                        "back": "Mercury is closest to the Sun.",
                    },
                )
            }

        def repair(card, _source):
            repair_current[0] = False
            return {
                **dict(card),
                "front": "What role does ATP have?",
                "back": "ATP carries energy for cellular work.",
            }

        repaired = _execute_lifecycle(
            self.make_run(level=IntelligenceLevel.STANDARD),
            planner_callback=None,
            generator_callback=ungrounded_generator,
            critic_callback=None,
            repair_callback=repair,
            continue_if_current=lambda: repair_current[0],
        )

        self.assertEqual(repaired.error_code, "request_superseded")
        self.assertEqual(repaired.run.stage, GenerationStage.SUPERSEDED)
        self.assertEqual(repaired.run.call_budget.call_count, 2)

        supplement_current = [True]
        plan = self.make_plan(include_missing_high=True)

        def supplement(_run, _point_ids):
            supplement_current[0] = False
            return {}

        supplemented = _execute_lifecycle(
            replace(
                self.make_run(level=IntelligenceLevel.DEEP),
                plan=plan,
            ),
            planner_callback=lambda _run: plan,
            generator_callback=self.generator,
            critic_callback=lambda _run: {"action": "pass"},
            supplement_callback=supplement,
            continue_if_current=lambda: supplement_current[0],
        )

        self.assertEqual(supplemented.error_code, "request_superseded")
        self.assertEqual(
            supplemented.run.stage,
            GenerationStage.SUPERSEDED,
        )
        self.assertEqual(supplemented.run.call_budget.call_count, 4)

    def test_callbacks_and_request_ids_are_strictly_validated(self):
        taskman = DeferredTaskman()
        controller = IntelligentGenerationTaskController(taskman)

        with self.assertRaisesRegex(TypeError, "run_snapshot"):
            controller.submit(
                run_snapshot={},
                generator_callback=self.generator,
                on_complete=lambda _result: None,
            )
        with self.assertRaisesRegex(TypeError, "generator_callback"):
            controller.submit(
                run_snapshot=self.make_run(),
                generator_callback=None,
                on_complete=lambda _result: None,
            )
        controller.submit(
            run_snapshot=self.make_run(2),
            generator_callback=self.generator,
            on_complete=lambda _result: None,
        )
        with self.assertRaisesRegex(ValueError, "request_id"):
            controller.submit(
                run_snapshot=self.make_run(1),
                generator_callback=self.generator,
                on_complete=lambda _result: None,
            )

    def test_completion_model_rejects_unsafe_codes_and_identity_mismatch(self):
        run = self.make_run(1, level=IntelligenceLevel.FAST)

        with self.assertRaisesRegex(ValueError, "request_id"):
            IntelligentGenerationTaskCompletion(request_id=2, run=run)
        for error_code in (
            "../private",
            "C:\\Users\\private\\key",
            "raw provider body",
            "UPPER",
        ):
            with self.subTest(error_code=error_code):
                with self.assertRaisesRegex(ValueError, "error_code"):
                    IntelligentGenerationTaskCompletion(
                        request_id=1,
                        run=run,
                        error_code=error_code,
                    )
        with self.assertRaisesRegex(TypeError, "run"):
            IntelligentGenerationTaskCompletion(
                request_id=1,
                run={},
                error_code="background_task_failed",
            )


if __name__ == "__main__":
    unittest.main()
