"""Pure bounded generation lifecycle without Qt or Anki dependencies."""

from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import islice
from typing import Mapping, Optional

from ..intelligence.call_budget import CallPurpose
from ..intelligence.coverage import CoverageReport, assess_generation_coverage
from ..intelligence.critic import (
    CriticAction,
    CriticDecision,
    decide_card,
    repair_and_revalidate,
)
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
from ..intelligence.recovery import (
    apply_failed_chunk_retry,
    fail_failed_chunk_retry,
    failed_chunk_retry_is_available,
    start_failed_chunk_retry,
    succeed_failed_chunk_retry,
)
from ..pipeline.generation_settings import (
    GenerationSettings,
    card_limit_for_settings,
)


class _CoverageSourceUnavailable(ValueError):
    pass


def failed_generation_retry_is_available(run: GenerationRun) -> bool:
    """Return whether one failed-only retry can still add a card safely."""

    if not failed_chunk_retry_is_available(run):
        return False
    return _remaining_card_slots(run) > 0


@dataclass(frozen=True)
class GenerationLifecycleResult:
    run: GenerationRun
    error_code: Optional[str] = None


@dataclass(frozen=True, repr=False)
class IntelligentGenerationProgress:
    request_id: int
    run: GenerationRun
    completed_groups: int = 0
    total_groups: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.run, GenerationRun):
            raise TypeError("run must be a GenerationRun")
        if self.request_id != self.run.request_id:
            raise ValueError("request_id must match the run")
        for value, name in (
            (self.completed_groups, "completed_groups"),
            (self.total_groups, "total_groups"),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.completed_groups > self.total_groups:
            raise ValueError("completed_groups must not exceed total_groups")

    def __repr__(self) -> str:
        return (
            "IntelligentGenerationProgress("
            f"request_id={self.request_id}, stage={self.run.stage.value!r}, "
            f"groups={self.completed_groups}/{self.total_groups})"
        )


def execute_generation_lifecycle(
    run: GenerationRun,
    *,
    planner_callback,
    generator_callback,
    critic_callback,
    repair_callback=None,
    supplement_callback=None,
    progress_callback=None,
    continue_if_current=lambda: True,
) -> GenerationLifecycleResult:
    current = transition_run(run, GenerationStage.PLANNING)
    _emit_worker_progress(progress_callback, current)
    if (
        planner_callback is not None
        and current.level in {IntelligenceLevel.STANDARD, IntelligenceLevel.DEEP}
    ):
        if not continue_if_current():
            return GenerationLifecycleResult(
                supersede_run(current),
                "request_superseded",
            )
        current = reserve_run_call(current, CallPurpose.PLANNER)
        if not continue_if_current():
            return GenerationLifecycleResult(
                supersede_run(current),
                "request_superseded",
            )
        try:
            plan = planner_callback(current)
            current = replace(current, plan=plan)
        except Exception:
            return GenerationLifecycleResult(
                failed_generation_run(current, "planner_call_failed"),
                "planner_call_failed",
            )
        if not continue_if_current():
            return GenerationLifecycleResult(
                supersede_run(current),
                "request_superseded",
            )
    current = transition_run(current, GenerationStage.GENERATING)
    _emit_worker_progress(progress_callback, current)
    if not continue_if_current():
        return GenerationLifecycleResult(
            supersede_run(current),
            "request_superseded",
        )
    try:
        current, generated = _dispatch_generation_calls(
            current,
            generator_callback,
            continue_if_current=continue_if_current,
            progress_callback=progress_callback,
        )
    except _GenerationSuperseded as error:
        return GenerationLifecycleResult(
            supersede_run(error.run),
            "request_superseded",
        )
    except _GenerationDispatchFailed as error:
        return GenerationLifecycleResult(
            failed_generation_run(error.run, "generator_call_failed"),
            "generator_call_failed",
        )
    if not continue_if_current():
        return GenerationLifecycleResult(
            supersede_run(current),
            "request_superseded",
        )
    try:
        current = _apply_generated_chunks(current, generated)
    except Exception:
        return GenerationLifecycleResult(
            failed_generation_run(current, "generation_materialization_failed"),
            "generation_materialization_failed",
        )
    if not continue_if_current():
        return GenerationLifecycleResult(
            supersede_run(current),
            "request_superseded",
        )
    current = transition_run(current, GenerationStage.REVIEWING)
    _emit_worker_progress(progress_callback, current)
    critic_output = None
    if (
        critic_callback is not None
        and current.level is IntelligenceLevel.DEEP
        and bool(current.cards)
    ):
        if not continue_if_current():
            return GenerationLifecycleResult(
                supersede_run(current),
                "request_superseded",
            )
        current = reserve_run_call(current, CallPurpose.CRITIC)
        if not continue_if_current():
            return GenerationLifecycleResult(
                supersede_run(current),
                "request_superseded",
            )
        try:
            critic_output = critic_callback(current)
        except Exception:
            return GenerationLifecycleResult(
                failed_generation_run(current, "critic_call_failed"),
                "critic_call_failed",
            )
        if not continue_if_current():
            return GenerationLifecycleResult(
                supersede_run(current),
                "request_superseded",
            )
    try:
        current = _apply_review_and_repairs(
            current,
            critic_output,
            repair_callback=repair_callback,
            continue_if_current=continue_if_current,
            progress_callback=progress_callback,
        )
    except _LifecycleSuperseded as error:
        return GenerationLifecycleResult(
            supersede_run(error.run),
            "request_superseded",
        )
    except Exception:
        return GenerationLifecycleResult(
            failed_generation_run(current, "critic_result_invalid"),
            "critic_result_invalid",
        )
    if not continue_if_current():
        return GenerationLifecycleResult(
            supersede_run(current),
            "request_superseded",
        )
    current = transition_run(current, GenerationStage.CHECKING_COVERAGE)
    _emit_worker_progress(progress_callback, current)
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
        return GenerationLifecycleResult(
            failed_generation_run(current, "postprocessing_failed"),
            "postprocessing_failed",
        )
    try:
        coverage = _assess_run_coverage(current)
    except _CoverageSourceUnavailable:
        return GenerationLifecycleResult(
            failed_generation_run(current, "coverage_source_unavailable"),
            "coverage_source_unavailable",
        )
    except Exception:
        return GenerationLifecycleResult(
            failed_generation_run(current, "coverage_assessment_failed"),
            "coverage_assessment_failed",
        )
    try:
        current = replace(
            current,
            coverage_report=coverage,
            deduplication_result=deduplication,
        )
        current = apply_coverage_supplement(
            current,
            supplement_callback=supplement_callback,
            continue_if_current=continue_if_current,
        )
    except _LifecycleSuperseded as error:
        return GenerationLifecycleResult(
            supersede_run(error.run),
            "request_superseded",
        )
    except Exception:
        return GenerationLifecycleResult(
            failed_generation_run(current, "postprocessing_failed"),
            "postprocessing_failed",
        )
    current = transition_run(current, GenerationStage.DEDUPLICATING)
    _emit_worker_progress(progress_callback, current)
    current = complete_run(current)
    _emit_worker_progress(progress_callback, current)
    return GenerationLifecycleResult(current)


class _GenerationDispatchFailed(RuntimeError):
    def __init__(self, run: GenerationRun):
        self.run = run
        super().__init__("generator_call_failed")


class _GenerationSuperseded(_GenerationDispatchFailed):
    pass


class _LifecycleSuperseded(RuntimeError):
    def __init__(self, run: GenerationRun):
        self.run = run
        super().__init__("request_superseded")


def generation_callback_is_grouped(callback: object) -> bool:
    return callable(getattr(callback, "generation_batches", None)) and callable(
        getattr(callback, "generate_batch", None)
    )


def _dispatch_generation_calls(
    run: GenerationRun,
    generator_callback,
    *,
    continue_if_current,
    progress_callback=None,
) -> tuple[GenerationRun, object]:
    if not generation_callback_is_grouped(generator_callback):
        current = reserve_run_call(run, CallPurpose.GENERATE)
        if not continue_if_current():
            raise _GenerationSuperseded(current)
        try:
            generated = generator_callback(current)
            _emit_worker_progress(
                progress_callback,
                current,
                completed_groups=1,
                total_groups=1,
            )
            return current, generated
        except Exception:
            raise _GenerationDispatchFailed(current) from None
    try:
        batches = _validated_generation_batches(
            run,
            generator_callback.generation_batches(run),
        )
    except Exception:
        raise _GenerationDispatchFailed(run) from None
    current = run
    generated = {}
    _emit_worker_progress(
        progress_callback,
        current,
        completed_groups=0,
        total_groups=len(batches),
    )
    for batch_index, batch in enumerate(batches, 1):
        if not continue_if_current():
            raise _GenerationSuperseded(current)
        current = reserve_run_call(current, CallPurpose.GENERATE)
        if not continue_if_current():
            raise _GenerationSuperseded(current)
        try:
            outcome = generator_callback.generate_batch(current, batch)
        except Exception:
            generated.update(
                {
                    chunk_id: {"error_code": "generation_call_failed"}
                    for chunk_id in batch
                }
            )
            _emit_worker_progress(
                progress_callback,
                current,
                completed_groups=batch_index,
                total_groups=len(batches),
            )
            continue
        try:
            outcome_by_chunk = _bounded_mapping_for_ids(outcome, batch)
        except (TypeError, ValueError):
            generated.update(
                {
                    chunk_id: {"error_code": "generation_output_invalid"}
                    for chunk_id in batch
                }
            )
            _emit_worker_progress(
                progress_callback,
                current,
                completed_groups=batch_index,
                total_groups=len(batches),
            )
            continue
        for chunk_id in batch:
            generated[chunk_id] = outcome_by_chunk.get(
                chunk_id,
                {"error_code": "generation_result_missing"},
            )
        _emit_worker_progress(
            progress_callback,
            current,
            completed_groups=batch_index,
            total_groups=len(batches),
        )
    return current, generated


def _emit_worker_progress(
    callback,
    run: GenerationRun,
    *,
    completed_groups: int = 0,
    total_groups: int = 0,
) -> None:
    if callback is None:
        return
    try:
        callback(run, completed_groups, total_groups)
    except Exception:
        return


def _validated_generation_batches(
    run: GenerationRun,
    value,
) -> tuple[tuple[str, ...], ...]:
    if isinstance(value, (str, bytes)):
        raise TypeError("generation batches must be a sequence")
    remaining = run.call_budget.remaining_calls
    try:
        raw_batches = tuple(islice(iter(value), remaining + 1))
    except TypeError:
        raise TypeError("generation batches must be a sequence") from None
    if len(raw_batches) > remaining:
        raise ValueError("generation batches exceed the remaining call budget")
    batches = []
    for raw_batch in raw_batches:
        if isinstance(raw_batch, (str, bytes)):
            raise TypeError("one generation batch must be a sequence")
        try:
            batch = tuple(islice(iter(raw_batch), len(run.chunks) + 1))
        except TypeError:
            raise TypeError("one generation batch must be a sequence") from None
        if len(batch) > len(run.chunks):
            raise ValueError("one generation batch exceeds run chunks")
        batches.append(batch)
    batches = tuple(batches)
    if not batches:
        raise ValueError("generation batches cannot be empty")
    flattened = tuple(chunk_id for batch in batches for chunk_id in batch)
    expected = tuple(chunk.chunk_id for chunk in run.chunks)
    if any(not batch for batch in batches) or flattened != expected:
        raise ValueError("generation batches must partition run chunks in order")
    return batches


def _bounded_mapping_for_ids(value, allowed_ids) -> dict:
    if not isinstance(value, Mapping):
        raise TypeError("value must be a mapping")
    allowed = tuple(allowed_ids)
    try:
        keys = tuple(islice(iter(value), len(allowed) + 1))
    except Exception:
        raise ValueError("mapping keys are invalid") from None
    if (
        len(keys) > len(allowed)
        or len(set(keys)) != len(keys)
        or not set(keys).issubset(set(allowed))
    ):
        raise ValueError("mapping keys are invalid")
    copied = {}
    for key in keys:
        try:
            copied[key] = value[key]
        except Exception:
            raise ValueError("mapping values are invalid") from None
    return copied


def execute_failed_retry_lifecycle(
    run: GenerationRun,
    retry,
    *,
    retry_generator_callback,
    progress_callback=None,
    continue_if_current=lambda: True,
) -> GenerationLifecycleResult:
    current = apply_failed_chunk_retry(run, retry)
    total_groups = len(retry.chunk_ids)
    _emit_worker_progress(
        progress_callback,
        current,
        completed_groups=0,
        total_groups=total_groups,
    )
    for completed_groups, chunk_id in enumerate(retry.chunk_ids, 1):
        if not continue_if_current():
            return GenerationLifecycleResult(
                supersede_run(current),
                "request_superseded",
            )
        remaining_card_slots = _remaining_card_slots(current)
        if remaining_card_slots < 1:
            current = start_chunk(current, chunk_id)
            current = fail_chunk(
                current,
                chunk_id,
                reason_code="card_limit_reached",
            )
            _emit_worker_progress(
                progress_callback,
                current,
                completed_groups=completed_groups,
                total_groups=total_groups,
            )
            continue
        current = start_failed_chunk_retry(current, retry, chunk_id)
        if not continue_if_current():
            return GenerationLifecycleResult(
                supersede_run(current),
                "request_superseded",
            )
        try:
            outcome = retry_generator_callback(current, chunk_id)
        except Exception:
            current = fail_failed_chunk_retry(
                current,
                retry,
                chunk_id,
            )
            _emit_worker_progress(
                progress_callback,
                current,
                completed_groups=completed_groups,
                total_groups=total_groups,
            )
            continue
        if isinstance(outcome, Mapping) and set(outcome).issubset(
            {"cards", "error_code"}
        ):
            error_code = outcome.get("error_code")
            if error_code is not None:
                current = fail_failed_chunk_retry(
                    current,
                    retry,
                    chunk_id,
                    reason_code=error_code,
                )
                _emit_worker_progress(
                    progress_callback,
                    current,
                    completed_groups=completed_groups,
                    total_groups=total_groups,
                )
                continue
            outcome = outcome.get("cards", ())
        try:
            outcome = _bounded_retry_cards(
                outcome,
                remaining_card_slots,
            )
            current = succeed_failed_chunk_retry(
                current,
                retry,
                chunk_id,
                outcome,
            )
        except (TypeError, ValueError):
            current = fail_failed_chunk_retry(
                current,
                retry,
                chunk_id,
                reason_code="generation_output_invalid",
            )
        _emit_worker_progress(
            progress_callback,
            current,
            completed_groups=completed_groups,
            total_groups=total_groups,
        )
    current = transition_run(current, GenerationStage.REVIEWING)
    _emit_worker_progress(progress_callback, current)
    current = _apply_critic_decisions(current, None)
    current = transition_run(current, GenerationStage.CHECKING_COVERAGE)
    _emit_worker_progress(progress_callback, current)
    try:
        deduplication = deduplicate_cards(current.cards)
        current = _retain_candidate_ids(
            current,
            {
                _card_value(card, "candidate_id")
                for card in deduplication.unique_cards
            },
        )
        coverage = _assess_run_coverage(current)
        current = replace(
            current,
            coverage_report=coverage,
            deduplication_result=deduplication,
        )
    except Exception:
        failed = failed_generation_run(current, "postprocessing_failed")
        _emit_worker_progress(progress_callback, failed)
        return GenerationLifecycleResult(
            failed,
            "postprocessing_failed",
        )
    current = transition_run(current, GenerationStage.DEDUPLICATING)
    _emit_worker_progress(progress_callback, current)
    current = complete_run(current)
    _emit_worker_progress(progress_callback, current)
    return GenerationLifecycleResult(current)


def _bounded_retry_cards(cards, remaining_card_slots: int) -> tuple:
    if (
        isinstance(remaining_card_slots, bool)
        or not isinstance(remaining_card_slots, int)
        or remaining_card_slots < 1
    ):
        raise ValueError("remaining_card_slots must be positive")
    if isinstance(cards, (str, bytes, bytearray, Mapping)):
        raise TypeError("retry cards must be an iterable of card values")
    try:
        bounded = tuple(islice(iter(cards), remaining_card_slots + 1))
    except TypeError:
        raise TypeError("retry cards must be iterable") from None
    return bounded[:remaining_card_slots]


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
                        settings=_generation_settings_for_card(run, card),
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


def _apply_review_and_repairs(
    run: GenerationRun,
    critic_output: object,
    *,
    repair_callback,
    continue_if_current,
    progress_callback=None,
) -> GenerationRun:
    cards = run.cards
    per_candidate = _critic_output_by_candidate(cards, critic_output)
    accepted_ids = set()
    repair_items = []
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
                        settings=_generation_settings_for_card(run, card),
                    )
                except (TypeError, ValueError):
                    decision = CriticDecision(
                        CriticAction.REJECT,
                        ("local_validation_failed",),
                        local_blocking=True,
                    )
            if decision.action in {CriticAction.PASS, CriticAction.FLAG}:
                accepted_ids.add(candidate_id)
            elif (
                decision.action is CriticAction.REPAIR
                and callable(repair_callback)
                and run.level
                in {IntelligenceLevel.STANDARD, IntelligenceLevel.DEEP}
            ):
                repair_items.append(
                    (
                        card,
                        _card_value(card, "point_id"),
                        source_text,
                        _generation_settings_for_card(run, card),
                    )
                )
    if not repair_items:
        return _retain_candidate_ids(run, accepted_ids)
    if run.level is IntelligenceLevel.STANDARD:
        repair_items = repair_items[:1]
    current = transition_run(run, GenerationStage.REPAIRING)
    _emit_worker_progress(progress_callback, current)
    replacements = {}
    for card, point_id, source_text, generation_settings in repair_items:
        if not continue_if_current():
            raise _LifecycleSuperseded(current)
        if point_id in current.repaired_point_ids:
            continue
        if current.call_budget.remaining_calls < 1:
            break
        try:
            result = repair_and_revalidate(
                run=current,
                point_id=point_id,
                card=card,
                source_text=source_text,
                repair_callback=repair_callback,
                settings=generation_settings,
            )
        except Exception:
            continue
        current = result.run
        if not continue_if_current():
            raise _LifecycleSuperseded(current)
        if result.accepted:
            candidate_id = _card_value(result.card, "candidate_id")
            accepted_ids.add(candidate_id)
            replacements[candidate_id] = result.card
    current = _retain_and_replace_cards(
        current,
        accepted_ids,
        replacements,
    )
    return transition_run(current, GenerationStage.REVIEWING)


def apply_coverage_supplement(
    run: GenerationRun,
    *,
    supplement_callback,
    continue_if_current,
) -> GenerationRun:
    coverage = run.coverage_report
    if (
        run.level is not IntelligenceLevel.DEEP
        or not callable(supplement_callback)
        or not isinstance(coverage, CoverageReport)
        or not coverage.supplement_recommended
    ):
        return run
    eligible_point_ids = _eligible_supplement_point_ids(
        run,
        coverage.missing_high_priority_point_ids,
    )
    if (
        not eligible_point_ids
        or run.call_budget.remaining_calls < 1
        or len(run.cards)
        >= card_limit_for_settings(_generation_settings_from_run(run))
    ):
        return run
    if not continue_if_current():
        raise _LifecycleSuperseded(run)
    try:
        current = reserve_run_call(run, CallPurpose.SUPPLEMENT)
    except Exception:
        return run
    try:
        generated = supplement_callback(
            current,
            eligible_point_ids,
        )
        if not continue_if_current():
            raise _LifecycleSuperseded(current)
        current = _append_supplement_cards(current, generated)
        deduplication = deduplicate_cards(current.cards)
        current = _retain_candidate_ids(
            current,
            {
                _card_value(card, "candidate_id")
                for card in deduplication.unique_cards
            },
        )
        return replace(
            current,
            coverage_report=_assess_run_coverage(current),
            deduplication_result=deduplication,
        )
    except _LifecycleSuperseded:
        raise
    except Exception:
        return current


def _append_supplement_cards(
    run: GenerationRun,
    generated: object,
) -> GenerationRun:
    by_chunk = {chunk.chunk_id: chunk for chunk in run.chunks}
    try:
        generated_by_chunk = _bounded_mapping_for_ids(
            generated,
            tuple(by_chunk),
        )
    except (TypeError, ValueError):
        raise ValueError("supplement output is invalid")
    remaining_card_slots = max(
        0,
        card_limit_for_settings(_generation_settings_from_run(run))
        - len(run.cards),
    )
    chunks = []
    for chunk in run.chunks:
        additions = generated_by_chunk.get(chunk.chunk_id, ())
        if chunk.state is not ChunkGenerationState.SUCCEEDED:
            additions = ()
        try:
            candidates = tuple(additions)
        except TypeError:
            raise ValueError("supplement output is invalid") from None
        source_text = _source_text_for_chunk(run, chunk.chunk_id)
        accepted_additions = []
        for card in candidates:
            try:
                decision = decide_card(
                    card=card,
                    source_text=source_text,
                    model_decision=CriticDecision(CriticAction.PASS),
                    settings=_generation_settings_for_card(run, card),
                )
            except (TypeError, ValueError):
                continue
            if decision.action in {CriticAction.PASS, CriticAction.FLAG}:
                if remaining_card_slots < 1:
                    break
                accepted_additions.append(card)
                remaining_card_slots -= 1
        cards = (*chunk.cards, *accepted_additions)
        chunks.append(
            ChunkGenerationSnapshot(
                chunk_id=chunk.chunk_id,
                state=chunk.state,
                cards=cards,
                reason_code=chunk.reason_code,
            )
        )
    return replace(run, chunks=tuple(chunks))


def _retain_and_replace_cards(
    run: GenerationRun,
    candidate_ids: set,
    replacements: Mapping,
) -> GenerationRun:
    chunks = tuple(
        ChunkGenerationSnapshot(
            chunk_id=chunk.chunk_id,
            state=chunk.state,
            cards=tuple(
                replacements.get(
                    _card_value(card, "candidate_id"),
                    card,
                )
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


def _eligible_supplement_point_ids(
    run: GenerationRun,
    missing_point_ids,
) -> tuple[str, ...]:
    if not isinstance(run.plan, KnowledgePlan):
        return ()
    succeeded_chunk_ids = {
        chunk.chunk_id
        for chunk in run.chunks
        if chunk.state is ChunkGenerationState.SUCCEEDED
    }
    point_by_id = {
        point.point_id: point for point in run.plan.points
    }
    return tuple(
        point_id
        for point_id in missing_point_ids
        if point_id in point_by_id
        and bool(
            set(point_by_id[point_id].source_chunk_ids)
            & succeeded_chunk_ids
        )
    )


def _generation_settings_for_card(
    run: GenerationRun,
    card: object,
) -> GenerationSettings:
    settings = _generation_settings_from_run(run)
    if settings.card_mode != "auto" or not isinstance(run.plan, KnowledgePlan):
        return settings
    point_id = _card_value(card, "point_id")
    recommended_template = next(
        (
            point.recommended_template
            for point in run.plan.points
            if point.point_id == point_id
        ),
        None,
    )
    if not isinstance(recommended_template, str):
        return replace(settings, card_mode="concept")
    try:
        return replace(settings, card_mode=recommended_template)
    except ValueError:
        return replace(settings, card_mode="concept")


def _generation_settings_from_run(run: GenerationRun) -> GenerationSettings:
    snapshot = run.settings_snapshot
    values = {}
    defaults = GenerationSettings()
    for name in ("card_mode", "card_count", "answer_length", "language"):
        value = snapshot.get(name) if isinstance(snapshot, Mapping) else None
        values[name] = value if isinstance(value, str) else getattr(defaults, name)
    try:
        return GenerationSettings(**values)
    except ValueError:
        return defaults


def _remaining_card_slots(run: GenerationRun) -> int:
    return max(
        0,
        card_limit_for_settings(_generation_settings_from_run(run))
        - len(run.cards),
    )


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


def failed_generation_run(run: GenerationRun, error_code: str) -> GenerationRun:
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

__all__ = [
    "GenerationLifecycleResult",
    "IntelligentGenerationProgress",
    "apply_coverage_supplement",
    "execute_failed_retry_lifecycle",
    "execute_generation_lifecycle",
    "failed_generation_retry_is_available",
    "failed_generation_run",
    "generation_callback_is_grouped",
]
