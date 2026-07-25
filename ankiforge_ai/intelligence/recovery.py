"""Explicit failed-only retry preparation for immutable generation runs."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from itertools import islice

from .call_budget import CallPurpose
from .generation_run import (
    ChunkGenerationSnapshot,
    ChunkGenerationState,
    GenerationRun,
    GenerationRunStatus,
    GenerationStage,
    fail_chunk,
    reserve_run_call,
    start_chunk,
    succeed_chunk,
)


MAX_RETRY_CHUNKS = 48
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_SAFE_CHUNK_ID = re.compile(r"^chunk-[a-f0-9]{16}$")


@dataclass(frozen=True, repr=False)
class FailedChunkRetry:
    retry_id: str
    source_run_id: str
    source_request_id: int
    chunk_ids: tuple[str, ...]
    source_call_count: int

    def __post_init__(self) -> None:
        for value, name in (
            (self.retry_id, "retry_id"),
            (self.source_run_id, "source_run_id"),
        ):
            if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
                raise ValueError(f"{name} must be a safe stable identifier")
        for value, name in (
            (self.source_request_id, "source_request_id"),
            (self.source_call_count, "source_call_count"),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.source_request_id < 1:
            raise ValueError("source_request_id must be positive")
        if self.source_call_count > 12:
            raise ValueError("source_call_count exceeds the global call budget")
        chunks = _bounded_tuple(
            self.chunk_ids,
            MAX_RETRY_CHUNKS,
            "chunk_ids",
        )
        if not chunks:
            raise ValueError("retry must contain failed chunks")
        if len(set(chunks)) != len(chunks) or not all(
            isinstance(item, str) and _SAFE_CHUNK_ID.fullmatch(item)
            for item in chunks
        ):
            raise ValueError("retry chunk_ids must be unique safe IDs")
        object.__setattr__(self, "chunk_ids", chunks)

    def __repr__(self) -> str:
        return (
            "FailedChunkRetry("
            f"retry_id={self.retry_id!r}, source_run_id={self.source_run_id!r}, "
            f"source_request_id={self.source_request_id}, "
            f"chunks={len(self.chunk_ids)}, "
            f"source_calls={self.source_call_count})"
        )


def create_failed_chunk_retry(
    run: GenerationRun,
    *,
    retry_id: str,
) -> FailedChunkRetry:
    _validate_run(run)
    failed_ids = _unscheduled_failed_chunk_ids(run)
    if not failed_ids:
        if run.failed_chunk_ids:
            raise ValueError("retry_already_scheduled")
        raise ValueError("no_failed_chunks")
    if run.call_budget.remaining_calls < len(failed_ids):
        raise ValueError("retry_call_budget_insufficient")
    return FailedChunkRetry(
        retry_id=retry_id,
        source_run_id=run.run_id,
        source_request_id=run.request_id,
        chunk_ids=failed_ids,
        source_call_count=run.call_budget.call_count,
    )


def failed_chunk_retry_is_available(run: GenerationRun) -> bool:
    try:
        _validate_run(run)
    except (TypeError, ValueError):
        return False
    failed_ids = _unscheduled_failed_chunk_ids(run)
    return bool(
        failed_ids
        and run.call_budget.remaining_calls >= len(failed_ids)
    )


def _unscheduled_failed_chunk_ids(run: GenerationRun) -> tuple[str, ...]:
    return tuple(
        item
        for item in run.failed_chunk_ids
        if item not in run.retry_scheduled_chunk_ids
    )


def apply_failed_chunk_retry(
    run: GenerationRun,
    retry: FailedChunkRetry,
) -> GenerationRun:
    _validate_retry_for_run(run, retry)
    if set(retry.chunk_ids) & set(run.retry_scheduled_chunk_ids):
        raise ValueError("retry_already_scheduled")
    if tuple(
        item.chunk_id
        for item in run.chunks
        if item.state is ChunkGenerationState.FAILED
        and item.chunk_id in retry.chunk_ids
    ) != retry.chunk_ids:
        raise ValueError("retry_chunk_not_failed")
    chunks = tuple(
        ChunkGenerationSnapshot(item.chunk_id)
        if item.chunk_id in retry.chunk_ids
        else item
        for item in run.chunks
    )
    return replace(
        run,
        stage=GenerationStage.GENERATING,
        chunks=chunks,
        status=GenerationRunStatus.RUNNING,
        retry_scheduled_chunk_ids=(
            *run.retry_scheduled_chunk_ids,
            *retry.chunk_ids,
        ),
    )


def start_failed_chunk_retry(
    run: GenerationRun,
    retry: FailedChunkRetry,
    chunk_id: str,
) -> GenerationRun:
    _validate_retry_identity(run, retry)
    _validate_retry_chunk(retry, chunk_id)
    chunk = _chunk(run, chunk_id)
    if chunk.state is not ChunkGenerationState.PENDING:
        raise ValueError("retry_chunk_not_pending")
    if (
        run.call_budget.call_count
        != retry.source_call_count + len(run.retry_dispatch_call_counts)
    ):
        raise ValueError("retry_dispatch_accounting_mismatch")
    reserved = reserve_run_call(run, CallPurpose.GENERATE)
    reserved = replace(
        reserved,
        retry_dispatch_call_counts=(
            *reserved.retry_dispatch_call_counts,
            (chunk_id, reserved.call_budget.call_count),
        ),
    )
    return start_chunk(reserved, chunk_id)


def succeed_failed_chunk_retry(
    run: GenerationRun,
    retry: FailedChunkRetry,
    chunk_id: str,
    cards,
) -> GenerationRun:
    _validate_retry_identity(run, retry)
    _validate_retry_chunk(retry, chunk_id)
    if _chunk(run, chunk_id).state is not ChunkGenerationState.RUNNING:
        raise ValueError("retry_chunk_not_running")
    dispatch_count = _retry_dispatch_count(run, chunk_id)
    if run.call_budget.call_count != dispatch_count:
        raise ValueError("retry_completion_accounting_mismatch")
    return succeed_chunk(run, chunk_id, cards)


def fail_failed_chunk_retry(
    run: GenerationRun,
    retry: FailedChunkRetry,
    chunk_id: str,
    *,
    reason_code: str = "retry_generation_failed",
) -> GenerationRun:
    _validate_retry_identity(run, retry)
    _validate_retry_chunk(retry, chunk_id)
    if _chunk(run, chunk_id).state is not ChunkGenerationState.RUNNING:
        raise ValueError("retry_chunk_not_running")
    dispatch_count = _retry_dispatch_count(run, chunk_id)
    if run.call_budget.call_count != dispatch_count:
        raise ValueError("retry_completion_accounting_mismatch")
    return fail_chunk(run, chunk_id, reason_code=reason_code)


def _validate_run(run: GenerationRun) -> None:
    if not isinstance(run, GenerationRun):
        raise TypeError("run must be a GenerationRun")
    if run.stage is GenerationStage.GENERATING:
        return
    if (
        run.stage is GenerationStage.COMPLETED
        and run.status is GenerationRunStatus.PARTIAL
        and run.failed_chunk_ids
    ):
        return
    else:
        raise ValueError("retry_requires_generating_stage")


def _validate_retry_for_run(
    run: GenerationRun,
    retry: FailedChunkRetry,
) -> None:
    if not isinstance(run, GenerationRun):
        raise TypeError("run must be a GenerationRun")
    if not isinstance(retry, FailedChunkRetry):
        raise TypeError("retry must be a FailedChunkRetry")
    _validate_retry_identity(run, retry)
    if retry.source_call_count != run.call_budget.call_count:
        raise ValueError("retry_call_accounting_mismatch")


def _validate_retry_identity(
    run: GenerationRun,
    retry: FailedChunkRetry,
) -> None:
    if not isinstance(run, GenerationRun):
        raise TypeError("run must be a GenerationRun")
    if not isinstance(retry, FailedChunkRetry):
        raise TypeError("retry must be a FailedChunkRetry")
    if (
        retry.source_run_id != run.run_id
        or retry.source_request_id != run.request_id
    ):
        raise ValueError("retry_run_mismatch")
    _validate_run(run)


def _validate_retry_chunk(retry: FailedChunkRetry, chunk_id: str) -> None:
    if chunk_id not in retry.chunk_ids:
        raise ValueError("retry_contains_failed_chunks_only")


def _chunk(run: GenerationRun, chunk_id: str) -> ChunkGenerationSnapshot:
    for item in run.chunks:
        if item.chunk_id == chunk_id:
            return item
    raise ValueError("unknown_retry_chunk")


def _retry_dispatch_count(run: GenerationRun, chunk_id: str) -> int:
    for dispatched_chunk_id, call_count in run.retry_dispatch_call_counts:
        if dispatched_chunk_id == chunk_id:
            return call_count
    raise ValueError("retry_dispatch_accounting_missing")


def _bounded_tuple(value, limit: int, name: str) -> tuple:
    if isinstance(value, (str, bytes)):
        raise TypeError(f"{name} must be a sequence")
    try:
        result = tuple(islice(iter(value), limit + 1))
    except TypeError:
        raise TypeError(f"{name} must be iterable") from None
    if len(result) > limit:
        raise ValueError(f"{name} exceeds its approved limit")
    return result
