from concurrent.futures import Future
from dataclasses import replace
import unittest

from ankiforge_ai.intelligence.planning import KnowledgePlan, KnowledgePointPlan
from ankiforge_ai.intelligence.generation_run import (
    GenerationRunStatus,
    GenerationStage,
    create_generation_run,
)
from ankiforge_ai.intelligence.models import IntelligenceLevel
from ankiforge_ai.ui.intelligent_generation_task_controller import (
    IntelligentGenerationTaskController,
    IntelligentGenerationTaskCompletion,
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
        incomplete = completions[0].run
        self.assertEqual(incomplete.stage, GenerationStage.FAILED)
        self.assertEqual(incomplete.status, GenerationRunStatus.FAILED)
        self.assertEqual(completions[0].error_code, "minimum_call_policy_not_met")
        self.assertEqual(incomplete.call_budget.call_count, 3)
        self.assertEqual(incomplete.cards[0]["candidate_id"], "card-1")
        self.assertNotIn("planner output", repr(incomplete))
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
        self.assertEqual(completions[0].error_code, "minimum_call_policy_not_met")

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

    def test_controller_enforces_level_minimum_without_dummy_calls(self):
        cases = (
            (IntelligenceLevel.FAST, None, None, 1, None),
            (
                IntelligenceLevel.STANDARD,
                lambda _run: self.make_plan(),
                None,
                2,
                "minimum_call_policy_not_met",
            ),
            (
                IntelligenceLevel.DEEP,
                lambda _run: self.make_plan(),
                lambda _run: {"action": "pass"},
                3,
                "minimum_call_policy_not_met",
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
                expected_status = (
                    GenerationRunStatus.COMPLETED
                    if error_code is None
                    else GenerationRunStatus.FAILED
                )
                self.assertEqual(completions[0].run.status, expected_status)

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
