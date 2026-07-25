"""Taskman lifecycle adapter for bounded immutable intelligence runs."""

from __future__ import annotations

from dataclasses import dataclass, replace
from threading import Lock
import re
from typing import Callable, Mapping, Optional

from ..intelligence.call_budget import CallPurpose
from ..intelligence.coverage import CoverageReport, assess_generation_coverage
from ..intelligence.critic import CriticAction, CriticDecision, decide_card
from ..intelligence.deduplication import deduplicate_cards
from ..intelligence.generation_run import (
    ChunkGenerationSnapshot,
    ChunkGenerationState,
    GenerationRun,
    GenerationStage,
    complete_run,
    fail_chunk,
    reserve_run_call,
    start_chunk,
    succeed_chunk,
    supersede_run,
    transition_run,
)
from ..intelligence.models import IntelligenceLevel
from ..intelligence.planning import KnowledgePlan


_SAFE_REASON = re.compile(r"^[a-z][a-z0-9_]{0,119}$")


class _CoverageSourceUnavailable(ValueError):
    pass


@dataclass(frozen=True, repr=False)
class IntelligentGenerationRequestSnapshot:
    request_id: int
    run: GenerationRun

    def __post_init__(self) -> None:
        if not isinstance(self.run, GenerationRun):
            raise TypeError("run must be a GenerationRun")
        if self.request_id != self.run.request_id:
            raise ValueError("request_id must match the run")

    def __repr__(self) -> str:
        return (
            "IntelligentGenerationRequestSnapshot("
            f"request_id={self.request_id}, run_id={self.run.run_id!r}, "
            f"chunks={len(self.run.chunks)})"
        )


@dataclass(frozen=True, repr=False)
class IntelligentGenerationTaskCompletion:
    request_id: int
    run: GenerationRun
    error_code: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.run, GenerationRun):
            raise TypeError("run must be a GenerationRun")
        if (
            isinstance(self.request_id, bool)
            or not isinstance(self.request_id, int)
            or self.request_id < 1
            or self.request_id != self.run.request_id
        ):
            raise ValueError("request_id must match the run identity")
        if self.error_code is not None and (
            not isinstance(self.error_code, str)
            or not _SAFE_REASON.fullmatch(self.error_code)
        ):
            raise ValueError("error_code must be a safe bounded code")

    @property
    def result(self) -> GenerationRun:
        return self.run

    def __repr__(self) -> str:
        return (
            "IntelligentGenerationTaskCompletion("
            f"request_id={self.request_id}, run_id={self.run.run_id!r}, "
            f"stage={self.run.stage.value!r}, status={self.run.status.value!r}, "
            f"cards={len(self.run.cards)}, calls={self.run.call_budget.call_count}, "
            f"error_code={self.error_code!r})"
        )


@dataclass(frozen=True)
class _WorkerResult:
    run: GenerationRun
    error_code: Optional[str] = None


class IntelligentGenerationTaskController:
    """Execute only injected callbacks and silently discard stale UI delivery."""

    def __init__(
        self,
        taskman,
        *,
        planner_callback=None,
        generator_callback=None,
        critic_callback=None,
    ):
        run_in_background = getattr(taskman, "run_in_background", None)
        if not callable(run_in_background):
            raise TypeError("taskman must provide run_in_background")
        for callback, name in (
            (planner_callback, "planner_callback"),
            (generator_callback, "generator_callback"),
            (critic_callback, "critic_callback"),
        ):
            if callback is not None and not callable(callback):
                raise TypeError(f"{name} must be callable")
        self._taskman = taskman
        self._default_planner = planner_callback
        self._default_generator = generator_callback
        self._default_critic = critic_callback
        self._lock = Lock()
        self._current_request_id = None
        self._highest_request_id = 0
        self._running = False
        self._alive = True

    @property
    def running(self) -> bool:
        with self._lock:
            return self._running

    @property
    def alive(self) -> bool:
        with self._lock:
            return self._alive

    @property
    def current_request_id(self):
        with self._lock:
            return self._current_request_id

    def submit(
        self,
        *,
        run_snapshot: GenerationRun,
        generator_callback=None,
        on_complete: Callable[[IntelligentGenerationTaskCompletion], None],
        planner_callback=None,
        critic_callback=None,
    ):
        if not isinstance(run_snapshot, GenerationRun):
            raise TypeError("run_snapshot must be a GenerationRun")
        generator = (
            self._default_generator
            if generator_callback is None
            else generator_callback
        )
        planner = (
            self._default_planner
            if planner_callback is None
            else planner_callback
        )
        critic = (
            self._default_critic
            if critic_callback is None
            else critic_callback
        )
        if not callable(generator):
            raise TypeError("generator_callback must be callable")
        for callback, name in (
            (planner, "planner_callback"),
            (critic, "critic_callback"),
        ):
            if callback is not None and not callable(callback):
                raise TypeError(f"{name} must be callable")
        if not callable(on_complete):
            raise TypeError("on_complete must be callable")
        snapshot = IntelligentGenerationRequestSnapshot(
            request_id=run_snapshot.request_id,
            run=run_snapshot,
        )
        with self._lock:
            if not self._alive:
                return None
            if snapshot.request_id <= self._highest_request_id:
                raise ValueError("request_id must increase for each submission")
            self._highest_request_id = snapshot.request_id
            self._current_request_id = snapshot.request_id
            self._running = True

        def background_task():
            if not self._is_current(snapshot.request_id):
                return _WorkerResult(
                    supersede_run(snapshot.run),
                    "request_superseded",
                )
            return _execute_lifecycle(
                snapshot.run,
                planner_callback=planner,
                generator_callback=generator,
                critic_callback=critic,
                continue_if_current=lambda: self._is_current(
                    snapshot.request_id
                ),
            )

        def on_done(future):
            try:
                worker_result = future.result()
                completion = IntelligentGenerationTaskCompletion(
                    request_id=snapshot.request_id,
                    run=worker_result.run,
                    error_code=worker_result.error_code,
                )
            except Exception:
                completion = IntelligentGenerationTaskCompletion(
                    request_id=snapshot.request_id,
                    run=_failed_run(snapshot.run, "background_task_failed"),
                    error_code="background_task_failed",
                )
            self._finish_if_current(completion, on_complete)

        try:
            self._taskman.run_in_background(
                background_task,
                on_done,
                uses_collection=False,
            )
        except Exception:
            self._finish_if_current(
                IntelligentGenerationTaskCompletion(
                    request_id=snapshot.request_id,
                    run=_failed_run(
                        snapshot.run,
                        "background_task_submit_failed",
                    ),
                    error_code="background_task_submit_failed",
                ),
                on_complete,
            )
        return snapshot.request_id

    def invalidate(self) -> None:
        with self._lock:
            self._current_request_id = None
            self._running = False

    def close(self) -> None:
        with self._lock:
            self._alive = False
            self._current_request_id = None
            self._running = False

    def _is_current(self, request_id: int) -> bool:
        with self._lock:
            return (
                self._alive
                and self._running
                and self._current_request_id == request_id
            )

    def _finish_if_current(self, completion, on_complete) -> None:
        with self._lock:
            if (
                not self._alive
                or completion.request_id != self._current_request_id
            ):
                return
            self._current_request_id = None
            self._running = False
        try:
            on_complete(completion)
        except Exception:
            # UI wrappers may have been deleted or adapters may fail. The
            # controller owns cleanup; callback exceptions never escape.
            return


def _execute_lifecycle(
    run: GenerationRun,
    *,
    planner_callback,
    generator_callback,
    critic_callback,
    continue_if_current=lambda: True,
) -> _WorkerResult:
    current = transition_run(run, GenerationStage.PLANNING)
    if (
        planner_callback is not None
        and current.level in {IntelligenceLevel.STANDARD, IntelligenceLevel.DEEP}
    ):
        if not continue_if_current():
            return _WorkerResult(
                supersede_run(current),
                "request_superseded",
            )
        current = reserve_run_call(current, CallPurpose.PLANNER)
        if not continue_if_current():
            return _WorkerResult(
                supersede_run(current),
                "request_superseded",
            )
        try:
            plan = planner_callback(current)
            current = replace(current, plan=plan)
        except Exception:
            return _WorkerResult(
                _failed_run(current, "planner_call_failed"),
                "planner_call_failed",
            )
        if not continue_if_current():
            return _WorkerResult(
                supersede_run(current),
                "request_superseded",
            )
    current = transition_run(current, GenerationStage.GENERATING)
    if not continue_if_current():
        return _WorkerResult(
            supersede_run(current),
            "request_superseded",
        )
    current = reserve_run_call(current, CallPurpose.GENERATE)
    if not continue_if_current():
        return _WorkerResult(
            supersede_run(current),
            "request_superseded",
        )
    try:
        generated = generator_callback(current)
    except Exception:
        return _WorkerResult(
            _failed_run(current, "generator_call_failed"),
            "generator_call_failed",
        )
    if not continue_if_current():
        return _WorkerResult(
            supersede_run(current),
            "request_superseded",
        )
    try:
        current = _apply_generated_chunks(current, generated)
    except Exception:
        return _WorkerResult(
            _failed_run(current, "generation_materialization_failed"),
            "generation_materialization_failed",
        )
    if not continue_if_current():
        return _WorkerResult(
            supersede_run(current),
            "request_superseded",
        )
    current = transition_run(current, GenerationStage.REVIEWING)
    critic_output = None
    if (
        critic_callback is not None
        and current.level is IntelligenceLevel.DEEP
    ):
        if not continue_if_current():
            return _WorkerResult(
                supersede_run(current),
                "request_superseded",
            )
        current = reserve_run_call(current, CallPurpose.CRITIC)
        if not continue_if_current():
            return _WorkerResult(
                supersede_run(current),
                "request_superseded",
            )
        try:
            critic_output = critic_callback(current)
        except Exception:
            return _WorkerResult(
                _failed_run(current, "critic_call_failed"),
                "critic_call_failed",
            )
        if not continue_if_current():
            return _WorkerResult(
                supersede_run(current),
                "request_superseded",
            )
    try:
        current = _apply_critic_decisions(current, critic_output)
    except Exception:
        return _WorkerResult(
            _failed_run(current, "critic_result_invalid"),
            "critic_result_invalid",
        )
    if not continue_if_current():
        return _WorkerResult(
            supersede_run(current),
            "request_superseded",
        )
    current = transition_run(current, GenerationStage.CHECKING_COVERAGE)
    try:
        deduplication = deduplicate_cards(current.cards)
        current = _retain_candidate_ids(
            current,
            {
                _card_value(card, "candidate_id")
                for card in deduplication.unique_cards
            },
        )
    except Exception:
        return _WorkerResult(
            _failed_run(current, "postprocessing_failed"),
            "postprocessing_failed",
        )
    try:
        coverage = _assess_run_coverage(current)
    except _CoverageSourceUnavailable:
        return _WorkerResult(
            _failed_run(current, "coverage_source_unavailable"),
            "coverage_source_unavailable",
        )
    except Exception:
        return _WorkerResult(
            _failed_run(current, "coverage_assessment_failed"),
            "coverage_assessment_failed",
        )
    try:
        current = replace(
            current,
            coverage_report=coverage,
            deduplication_result=deduplication,
        )
    except Exception:
        return _WorkerResult(
            _failed_run(current, "postprocessing_failed"),
            "postprocessing_failed",
        )
    current = transition_run(current, GenerationStage.DEDUPLICATING)
    if current.call_budget.call_count < current.call_budget.minimum_calls:
        return _WorkerResult(
            _failed_run(current, "minimum_call_policy_not_met"),
            "minimum_call_policy_not_met",
        )
    current = complete_run(current)
    return _WorkerResult(current)


def _apply_generated_chunks(run: GenerationRun, generated: object) -> GenerationRun:
    if len(run.chunks) == 1 and not isinstance(generated, Mapping):
        generated_by_chunk = {run.chunks[0].chunk_id: generated}
    elif isinstance(generated, Mapping):
        generated_by_chunk = generated
    else:
        return _fail_all_pending_chunks(run, "generation_output_invalid")
    current = run
    for chunk in run.chunks:
        if chunk.state is not ChunkGenerationState.PENDING:
            continue
        current = start_chunk(current, chunk.chunk_id)
        if chunk.chunk_id not in generated_by_chunk:
            current = fail_chunk(
                current,
                chunk.chunk_id,
                reason_code="generation_result_missing",
            )
            continue
        outcome = generated_by_chunk[chunk.chunk_id]
        if isinstance(outcome, Exception):
            current = fail_chunk(
                current,
                chunk.chunk_id,
                reason_code="generation_call_failed",
            )
            continue
        if isinstance(outcome, Mapping) and set(outcome).issubset(
            {"cards", "error_code"}
        ):
            error_code = outcome.get("error_code")
            if error_code is not None:
                try:
                    current = fail_chunk(
                        current,
                        chunk.chunk_id,
                        reason_code=error_code,
                    )
                except (TypeError, ValueError):
                    current = fail_chunk(
                        current,
                        chunk.chunk_id,
                        reason_code="generation_output_invalid",
                    )
                continue
            outcome = outcome.get("cards", ())
        try:
            current = succeed_chunk(
                current,
                chunk.chunk_id,
                outcome,
            )
        except (TypeError, ValueError):
            current = fail_chunk(
                current,
                chunk.chunk_id,
                reason_code="generation_output_invalid",
            )
    return current


def _fail_all_pending_chunks(run: GenerationRun, reason_code: str) -> GenerationRun:
    current = run
    for chunk in run.chunks:
        if chunk.state is ChunkGenerationState.PENDING:
            current = fail_chunk(
                start_chunk(current, chunk.chunk_id),
                chunk.chunk_id,
                reason_code=reason_code,
            )
    return current


def _apply_critic_decisions(
    run: GenerationRun,
    critic_output: object,
) -> GenerationRun:
    cards = run.cards
    per_candidate = _critic_output_by_candidate(cards, critic_output)
    accepted_ids = set()
    for chunk in run.chunks:
        if chunk.state is not ChunkGenerationState.SUCCEEDED:
            continue
        for card in chunk.cards:
            candidate_id = _card_value(card, "candidate_id")
            source_text = _source_text_for_chunk(run, chunk.chunk_id)
            if not source_text:
                decision = CriticDecision(
                    CriticAction.REJECT,
                    ("source_unavailable",),
                    local_blocking=True,
                )
            else:
                try:
                    decision = decide_card(
                        card=card,
                        source_text=source_text,
                        model_decision=per_candidate.get(candidate_id),
                    )
                except (TypeError, ValueError):
                    decision = CriticDecision(
                        CriticAction.REJECT,
                        ("local_validation_failed",),
                        local_blocking=True,
                    )
            if decision.action in {CriticAction.PASS, CriticAction.FLAG}:
                accepted_ids.add(candidate_id)
    return _retain_candidate_ids(run, accepted_ids)


def _critic_output_by_candidate(cards, output: object) -> dict:
    candidate_ids = tuple(
        _card_value(card, "candidate_id") for card in cards
    )
    if output is None:
        return {}
    if isinstance(output, (CriticDecision, str)):
        return {candidate_id: output for candidate_id in candidate_ids}
    if isinstance(output, Mapping):
        if "action" in output:
            return {candidate_id: output for candidate_id in candidate_ids}
        return {
            candidate_id: output.get(candidate_id)
            for candidate_id in candidate_ids
            if output.get(candidate_id) is not None
        }
    if isinstance(output, (list, tuple)):
        if len(output) != len(candidate_ids):
            raise ValueError("critic result count mismatch")
        return dict(zip(candidate_ids, output))
    raise ValueError("critic result is unsupported")


def _source_text_for_chunk(run: GenerationRun, chunk_id: str) -> str:
    snapshot = run.document_snapshot
    if not isinstance(snapshot, Mapping):
        return ""
    by_id = snapshot.get("chunk_text_by_id")
    if isinstance(by_id, Mapping):
        value = by_id.get(chunk_id)
        if isinstance(value, str):
            return value
    chunks = snapshot.get("chunks")
    if isinstance(chunks, Mapping):
        value = chunks.get(chunk_id)
        if isinstance(value, str):
            return value
        if isinstance(value, Mapping) and isinstance(value.get("text"), str):
            return value["text"]
    for name in ("material", "text"):
        value = snapshot.get(name)
        if isinstance(value, str) and len(run.chunks) == 1:
            return value
    return ""


def _retain_candidate_ids(
    run: GenerationRun,
    candidate_ids: set,
) -> GenerationRun:
    chunks = tuple(
        ChunkGenerationSnapshot(
            chunk_id=chunk.chunk_id,
            state=chunk.state,
            cards=tuple(
                card
                for card in chunk.cards
                if _card_value(card, "candidate_id") in candidate_ids
            ),
            reason_code=chunk.reason_code,
        )
        if chunk.state is ChunkGenerationState.SUCCEEDED
        else chunk
        for chunk in run.chunks
    )
    return replace(run, chunks=chunks)


def _assess_run_coverage(run: GenerationRun) -> CoverageReport:
    plan = run.plan
    run_chunk_ids = tuple(chunk.chunk_id for chunk in run.chunks)
    if (
        not isinstance(plan, KnowledgePlan)
        or plan.document_id != run.document_id
        or not plan.points
        or plan.chunk_ids != run_chunk_ids
    ):
        raise _CoverageSourceUnavailable("coverage source is unavailable")
    section_ids = tuple(
        dict.fromkeys(point.section_id for point in plan.points)
    )
    return assess_generation_coverage(
        plan.points,
        run.cards,
        section_ids=section_ids,
    )


def _card_value(card: object, name: str):
    if isinstance(card, Mapping):
        return card.get(name)
    return getattr(card, name, None)


def _failed_run(run: GenerationRun, error_code: str) -> GenerationRun:
    if run.stage in {
        GenerationStage.COMPLETED,
        GenerationStage.FAILED,
        GenerationStage.SUPERSEDED,
    }:
        return run
    return replace(
        transition_run(run, GenerationStage.FAILED),
        error_code=error_code,
    )
