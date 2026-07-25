"""Pure immutable state transitions for one bounded intelligence run."""

from __future__ import annotations

import re
import math
from dataclasses import dataclass, fields, is_dataclass, replace
from enum import Enum
from itertools import islice
from types import MappingProxyType
from typing import Mapping, Optional

from .call_budget import CallBudget, CallPurpose
from .models import IntelligenceLevel


MAX_RUN_CHUNKS = 48
MAX_RUN_CARDS = 96
MAX_REPAIRED_POINTS = 96
MAX_SNAPSHOT_DEPTH = 16
MAX_SNAPSHOT_NODES = 4_096
MAX_SNAPSHOT_MAPPING_KEYS = 256
MAX_SNAPSHOT_SEQUENCE_ITEMS = 256
MAX_SNAPSHOT_TEXT_CHARS = 5_000_000
MAX_SNAPSHOT_BYTES = 256_000
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_SAFE_CHUNK_ID = re.compile(r"^chunk-[a-f0-9]{16}$")
_SAFE_POINT_ID = re.compile(r"^point-[a-f0-9]{16}$")
_SAFE_HASH = re.compile(r"^[a-f0-9]{64}$")
_SAFE_REASON = re.compile(r"^[a-z][a-z0-9_]{0,119}$")


class GenerationStage(str, Enum):
    ANALYZING = "analyzing"
    PLANNING = "planning"
    GENERATING = "generating"
    REVIEWING = "reviewing"
    REPAIRING = "repairing"
    CHECKING_COVERAGE = "checking_coverage"
    DEDUPLICATING = "deduplicating"
    COMPLETED = "completed"
    FAILED = "failed"
    SUPERSEDED = "superseded"


class GenerationRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PARTIAL = "partial"
    COMPLETED = "completed"
    FAILED = "failed"
    SUPERSEDED = "superseded"


class ChunkGenerationState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True, repr=False)
class ChunkGenerationSnapshot:
    chunk_id: str
    state: ChunkGenerationState = ChunkGenerationState.PENDING
    cards: tuple[object, ...] = ()
    reason_code: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.chunk_id, str) or not _SAFE_CHUNK_ID.fullmatch(
            self.chunk_id
        ):
            raise ValueError("chunk_id must be a safe stable identifier")
        try:
            state = ChunkGenerationState(self.state)
        except (TypeError, ValueError):
            raise ValueError("chunk state is unsupported") from None
        cards = _bounded_tuple(self.cards, MAX_RUN_CARDS, "chunk cards")
        frozen_cards = tuple(_freeze_snapshot(card) for card in cards)
        if state is not ChunkGenerationState.SUCCEEDED and frozen_cards:
            raise ValueError("only a succeeded chunk may contain cards")
        if self.reason_code is not None and (
            not isinstance(self.reason_code, str)
            or not _SAFE_REASON.fullmatch(self.reason_code)
        ):
            raise ValueError("chunk reason_code must be a safe code")
        if state is ChunkGenerationState.FAILED and self.reason_code is None:
            raise ValueError("failed chunk requires a reason_code")
        if state is not ChunkGenerationState.FAILED and self.reason_code is not None:
            raise ValueError("only a failed chunk may contain a reason_code")
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "cards", frozen_cards)

    def __repr__(self) -> str:
        return (
            "ChunkGenerationSnapshot("
            f"chunk_id={self.chunk_id!r}, state={self.state.value!r}, "
            f"cards={len(self.cards)}, reason_code={self.reason_code!r})"
        )


@dataclass(frozen=True, repr=False)
class GenerationRun:
    run_id: str
    request_id: int
    document_id: str
    document_hash: str
    document_snapshot: object
    settings_snapshot: object
    level: IntelligenceLevel
    stage: GenerationStage
    status: GenerationRunStatus
    chunks: tuple[ChunkGenerationSnapshot, ...]
    call_budget: CallBudget
    plan: object = None
    repaired_point_ids: tuple[str, ...] = ()
    supplement_used: bool = False
    retry_scheduled_chunk_ids: tuple[str, ...] = ()
    retry_dispatch_call_counts: tuple[tuple[str, int], ...] = ()
    coverage_report: object = None
    deduplication_result: object = None
    error_code: Optional[str] = None

    def __post_init__(self) -> None:
        _validate_id(self.run_id, "run_id")
        _validate_id(self.document_id, "document_id")
        if (
            isinstance(self.request_id, bool)
            or not isinstance(self.request_id, int)
            or self.request_id < 1
        ):
            raise ValueError("request_id must be a positive integer")
        if not isinstance(self.document_hash, str) or not _SAFE_HASH.fullmatch(
            self.document_hash
        ):
            raise ValueError("document_hash must be a lowercase SHA-256 digest")
        try:
            level = IntelligenceLevel(self.level)
            stage = GenerationStage(self.stage)
            status = GenerationRunStatus(self.status)
        except (TypeError, ValueError):
            raise ValueError("run level, stage, or status is unsupported") from None
        chunks = _bounded_tuple(self.chunks, MAX_RUN_CHUNKS, "chunks")
        if not chunks or not all(
            isinstance(item, ChunkGenerationSnapshot) for item in chunks
        ):
            raise ValueError("chunks must contain bounded chunk snapshots")
        if len({item.chunk_id for item in chunks}) != len(chunks):
            raise ValueError("chunk IDs must be unique")
        if sum(len(item.cards) for item in chunks) > MAX_RUN_CARDS:
            raise ValueError("run cards exceed the approved limit")
        if not isinstance(self.call_budget, CallBudget):
            raise TypeError("call_budget must be a CallBudget")
        if self.call_budget.level is not level:
            raise ValueError("call budget level must match the run level")
        repaired = _bounded_tuple(
            self.repaired_point_ids,
            MAX_REPAIRED_POINTS,
            "repaired_point_ids",
        )
        if len(set(repaired)) != len(repaired) or not all(
            isinstance(item, str) and _SAFE_POINT_ID.fullmatch(item)
            for item in repaired
        ):
            raise ValueError("repaired_point_ids must contain unique safe IDs")
        retry_ids = _bounded_tuple(
            self.retry_scheduled_chunk_ids,
            MAX_RUN_CHUNKS,
            "retry_scheduled_chunk_ids",
        )
        known_chunk_ids = {item.chunk_id for item in chunks}
        if len(set(retry_ids)) != len(retry_ids) or not set(retry_ids).issubset(
            known_chunk_ids
        ):
            raise ValueError("retry chunk IDs must be unique run chunk IDs")
        dispatch_counts = _bounded_tuple(
            self.retry_dispatch_call_counts,
            MAX_RUN_CHUNKS,
            "retry_dispatch_call_counts",
        )
        normalized_dispatch_counts = []
        dispatch_chunk_ids = set()
        for item in dispatch_counts:
            if (
                not isinstance(item, tuple)
                or len(item) != 2
                or not isinstance(item[0], str)
                or not _SAFE_CHUNK_ID.fullmatch(item[0])
                or isinstance(item[1], bool)
                or not isinstance(item[1], int)
                or not 1 <= item[1] <= self.call_budget.call_count
            ):
                raise ValueError("retry dispatch counts must be bounded reservations")
            if item[0] in dispatch_chunk_ids or item[0] not in retry_ids:
                raise ValueError("retry dispatch chunks must be unique scheduled chunks")
            if (
                self.call_budget.reservations[item[1] - 1].purpose
                is not CallPurpose.GENERATE
            ):
                raise ValueError("retry dispatch must reference generation reservation")
            dispatch_chunk_ids.add(item[0])
            normalized_dispatch_counts.append(item)
        if not isinstance(self.supplement_used, bool):
            raise TypeError("supplement_used must be a boolean")
        if self.error_code is not None and (
            not isinstance(self.error_code, str)
            or not _SAFE_REASON.fullmatch(self.error_code)
        ):
            raise ValueError("error_code must be a safe reason code")
        _validate_status_stage(stage, status)
        _validate_run_coherence(
            level=level,
            stage=stage,
            status=status,
            chunks=chunks,
            call_budget=self.call_budget,
            error_code=self.error_code,
        )
        frozen_document = _freeze_snapshot(self.document_snapshot)
        frozen_settings = _freeze_snapshot(self.settings_snapshot)
        frozen_plan = _freeze_snapshot(self.plan)
        object.__setattr__(self, "document_snapshot", frozen_document)
        object.__setattr__(self, "settings_snapshot", frozen_settings)
        object.__setattr__(self, "plan", frozen_plan)
        object.__setattr__(
            self,
            "coverage_report",
            _freeze_snapshot(self.coverage_report),
        )
        object.__setattr__(
            self,
            "deduplication_result",
            _freeze_snapshot(self.deduplication_result),
        )
        object.__setattr__(self, "level", level)
        object.__setattr__(self, "stage", stage)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "chunks", chunks)
        object.__setattr__(self, "repaired_point_ids", repaired)
        object.__setattr__(self, "retry_scheduled_chunk_ids", retry_ids)
        object.__setattr__(
            self,
            "retry_dispatch_call_counts",
            tuple(normalized_dispatch_counts),
        )

    @property
    def cards(self) -> tuple[object, ...]:
        return tuple(card for chunk in self.chunks for card in chunk.cards)

    @property
    def failed_chunk_ids(self) -> tuple[str, ...]:
        return tuple(
            chunk.chunk_id
            for chunk in self.chunks
            if chunk.state is ChunkGenerationState.FAILED
        )

    def __repr__(self) -> str:
        reasons = tuple(
            chunk.reason_code
            for chunk in self.chunks
            if chunk.reason_code is not None
        )
        return (
            "GenerationRun("
            f"run_id={self.run_id!r}, request_id={self.request_id}, "
            f"document_id={self.document_id!r}, level={self.level.value!r}, "
            f"stage={self.stage.value!r}, status={self.status.value!r}, "
            f"chunks={len(self.chunks)}, cards={len(self.cards)}, "
            f"failed_chunks={len(self.failed_chunk_ids)}, "
            f"calls={self.call_budget.call_count}/{self.call_budget.call_limit}, "
            f"reason_codes={reasons!r})"
        )


_LEGAL_STAGE_TRANSITIONS = {
    GenerationStage.ANALYZING: frozenset(
        {GenerationStage.PLANNING, GenerationStage.FAILED, GenerationStage.SUPERSEDED}
    ),
    GenerationStage.PLANNING: frozenset(
        {GenerationStage.GENERATING, GenerationStage.FAILED, GenerationStage.SUPERSEDED}
    ),
    GenerationStage.GENERATING: frozenset(
        {GenerationStage.REVIEWING, GenerationStage.FAILED, GenerationStage.SUPERSEDED}
    ),
    GenerationStage.REVIEWING: frozenset(
        {
            GenerationStage.REPAIRING,
            GenerationStage.CHECKING_COVERAGE,
            GenerationStage.FAILED,
            GenerationStage.SUPERSEDED,
        }
    ),
    GenerationStage.REPAIRING: frozenset(
        {
            GenerationStage.REVIEWING,
            GenerationStage.CHECKING_COVERAGE,
            GenerationStage.FAILED,
            GenerationStage.SUPERSEDED,
        }
    ),
    GenerationStage.CHECKING_COVERAGE: frozenset(
        {
            GenerationStage.DEDUPLICATING,
            GenerationStage.FAILED,
            GenerationStage.SUPERSEDED,
        }
    ),
    GenerationStage.DEDUPLICATING: frozenset(
        {GenerationStage.COMPLETED, GenerationStage.FAILED, GenerationStage.SUPERSEDED}
    ),
    GenerationStage.COMPLETED: frozenset(),
    GenerationStage.FAILED: frozenset(),
    GenerationStage.SUPERSEDED: frozenset(),
}
_TERMINAL_STATUSES = {
    GenerationRunStatus.COMPLETED,
    GenerationRunStatus.FAILED,
    GenerationRunStatus.SUPERSEDED,
}


def create_generation_run(
    *,
    run_id: str,
    request_id: int,
    document_id: str,
    document_hash: str,
    document_snapshot: object,
    settings_snapshot: object,
    chunk_ids,
    level: IntelligenceLevel = IntelligenceLevel.STANDARD,
) -> GenerationRun:
    try:
        normalized_level = IntelligenceLevel(level)
    except (TypeError, ValueError):
        raise ValueError("level must be fast, standard, or deep") from None
    raw_ids = _bounded_tuple(chunk_ids, MAX_RUN_CHUNKS, "chunk_ids")
    chunks = tuple(ChunkGenerationSnapshot(chunk_id=item) for item in raw_ids)
    return GenerationRun(
        run_id=run_id,
        request_id=request_id,
        document_id=document_id,
        document_hash=document_hash,
        document_snapshot=document_snapshot,
        settings_snapshot=settings_snapshot,
        level=normalized_level,
        stage=GenerationStage.ANALYZING,
        status=GenerationRunStatus.RUNNING,
        chunks=chunks,
        call_budget=CallBudget.for_level(normalized_level),
    )


def transition_run(run: GenerationRun, stage: GenerationStage) -> GenerationRun:
    _require_active(run)
    try:
        target = GenerationStage(stage)
    except (TypeError, ValueError):
        raise ValueError("stage is unsupported") from None
    if run.level is IntelligenceLevel.FAST and target is GenerationStage.REPAIRING:
        raise ValueError("stage_not_allowed")
    if target not in _LEGAL_STAGE_TRANSITIONS[run.stage]:
        raise ValueError("illegal_stage_transition")
    if target is GenerationStage.COMPLETED:
        status = GenerationRunStatus.COMPLETED
    elif target is GenerationStage.FAILED:
        status = GenerationRunStatus.FAILED
    elif target is GenerationStage.SUPERSEDED:
        status = GenerationRunStatus.SUPERSEDED
    elif run.failed_chunk_ids:
        status = GenerationRunStatus.PARTIAL
    else:
        status = GenerationRunStatus.RUNNING
    return replace(run, stage=target, status=status)


def reserve_run_call(
    run: GenerationRun,
    purpose: CallPurpose,
    *,
    point_id: Optional[str] = None,
) -> GenerationRun:
    _require_active(run)
    try:
        normalized = CallPurpose(purpose)
    except (TypeError, ValueError):
        return replace(run, call_budget=run.call_budget.reserve(purpose))
    expected_stage = {
        CallPurpose.PLANNER: GenerationStage.PLANNING,
        CallPurpose.GENERATE: GenerationStage.GENERATING,
        CallPurpose.CRITIC: GenerationStage.REVIEWING,
        CallPurpose.REPAIR: GenerationStage.REPAIRING,
        CallPurpose.SUPPLEMENT: GenerationStage.CHECKING_COVERAGE,
    }[normalized]
    if run.stage is not expected_stage:
        raise ValueError("call_stage_mismatch")
    if normalized is CallPurpose.REPAIR:
        if not isinstance(point_id, str) or not _SAFE_POINT_ID.fullmatch(point_id):
            raise ValueError("repair requires a safe point_id")
        if point_id in run.repaired_point_ids:
            raise ValueError("repair_already_used")
    elif point_id is not None:
        raise ValueError("point_id is only valid for a repair")
    if normalized is CallPurpose.SUPPLEMENT and run.supplement_used:
        raise ValueError("supplement_already_used")
    reserved_budget = run.call_budget.reserve(normalized)
    updates = {"call_budget": reserved_budget}
    if normalized is CallPurpose.REPAIR:
        updates["repaired_point_ids"] = (*run.repaired_point_ids, point_id)
    if normalized is CallPurpose.SUPPLEMENT:
        updates["supplement_used"] = True
    return replace(run, **updates)


def start_chunk(run: GenerationRun, chunk_id: str) -> GenerationRun:
    _require_active(run)
    if run.stage is not GenerationStage.GENERATING:
        raise ValueError("chunk_stage_mismatch")
    index, chunk = _chunk_by_id(run, chunk_id)
    if chunk.state is not ChunkGenerationState.PENDING:
        raise ValueError("chunk_not_pending")
    return _replace_chunk(
        run,
        index,
        replace(chunk, state=ChunkGenerationState.RUNNING),
    )


def succeed_chunk(run: GenerationRun, chunk_id: str, cards) -> GenerationRun:
    _require_active(run)
    if run.stage is not GenerationStage.GENERATING:
        raise ValueError("chunk_stage_mismatch")
    index, chunk = _chunk_by_id(run, chunk_id)
    if chunk.state is not ChunkGenerationState.RUNNING:
        raise ValueError("chunk_not_running")
    new_chunk = ChunkGenerationSnapshot(
        chunk_id=chunk.chunk_id,
        state=ChunkGenerationState.SUCCEEDED,
        cards=_bounded_tuple(cards, MAX_RUN_CARDS, "cards"),
    )
    if len(run.cards) + len(new_chunk.cards) > MAX_RUN_CARDS:
        raise ValueError("run cards exceed the approved limit")
    return _replace_chunk(run, index, new_chunk)


def fail_chunk(
    run: GenerationRun,
    chunk_id: str,
    *,
    reason_code: str,
) -> GenerationRun:
    _require_active(run)
    if run.stage is not GenerationStage.GENERATING:
        raise ValueError("chunk_stage_mismatch")
    index, chunk = _chunk_by_id(run, chunk_id)
    if chunk.state is not ChunkGenerationState.RUNNING:
        raise ValueError("chunk_not_running")
    new_chunk = ChunkGenerationSnapshot(
        chunk_id=chunk.chunk_id,
        state=ChunkGenerationState.FAILED,
        reason_code=reason_code,
    )
    chunks = list(run.chunks)
    chunks[index] = new_chunk
    return replace(
        run,
        chunks=tuple(chunks),
        status=GenerationRunStatus.PARTIAL,
    )


def complete_run(run: GenerationRun) -> GenerationRun:
    _require_active(run)
    if run.stage is not GenerationStage.DEDUPLICATING:
        raise ValueError("completion_stage_mismatch")
    if any(
        chunk.state in {ChunkGenerationState.PENDING, ChunkGenerationState.RUNNING}
        for chunk in run.chunks
    ):
        raise ValueError("unfinished_chunks")
    if not any(
        reservation.purpose is CallPurpose.GENERATE
        for reservation in run.call_budget.reservations
    ):
        raise ValueError("generation_call_not_reserved")
    status = (
        GenerationRunStatus.PARTIAL
        if run.failed_chunk_ids
        else GenerationRunStatus.COMPLETED
    )
    return replace(run, stage=GenerationStage.COMPLETED, status=status)


def supersede_run(run: GenerationRun) -> GenerationRun:
    _require_active(run)
    return replace(
        run,
        stage=GenerationStage.SUPERSEDED,
        status=GenerationRunStatus.SUPERSEDED,
    )


def _chunk_by_id(
    run: GenerationRun,
    chunk_id: str,
) -> tuple[int, ChunkGenerationSnapshot]:
    for index, chunk in enumerate(run.chunks):
        if chunk.chunk_id == chunk_id:
            return index, chunk
    raise ValueError("unknown_chunk_id")


def _replace_chunk(
    run: GenerationRun,
    index: int,
    chunk: ChunkGenerationSnapshot,
) -> GenerationRun:
    chunks = list(run.chunks)
    chunks[index] = chunk
    return replace(run, chunks=tuple(chunks))


def _require_active(run: GenerationRun) -> None:
    if not isinstance(run, GenerationRun):
        raise TypeError("run must be a GenerationRun")
    if run.stage in {
        GenerationStage.COMPLETED,
        GenerationStage.FAILED,
        GenerationStage.SUPERSEDED,
    } or run.status in _TERMINAL_STATUSES:
        raise ValueError("terminal_run")


def _validate_id(value: object, name: str) -> None:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise ValueError(f"{name} must be a safe stable identifier")


def _validate_status_stage(
    stage: GenerationStage,
    status: GenerationRunStatus,
) -> None:
    expected = {
        GenerationStage.COMPLETED: {
            GenerationRunStatus.COMPLETED,
            GenerationRunStatus.PARTIAL,
        },
        GenerationStage.FAILED: {GenerationRunStatus.FAILED},
        GenerationStage.SUPERSEDED: {GenerationRunStatus.SUPERSEDED},
    }
    if stage in expected and status not in expected[stage]:
        raise ValueError("terminal stage and status do not match")
    if stage not in expected and status in _TERMINAL_STATUSES:
        raise ValueError("active stage cannot have a terminal status")


def _validate_run_coherence(
    *,
    level: IntelligenceLevel,
    stage: GenerationStage,
    status: GenerationRunStatus,
    chunks: tuple[ChunkGenerationSnapshot, ...],
    call_budget: CallBudget,
    error_code: Optional[str],
) -> None:
    failed = any(
        chunk.state is ChunkGenerationState.FAILED for chunk in chunks
    )
    unfinished = any(
        chunk.state in {
            ChunkGenerationState.PENDING,
            ChunkGenerationState.RUNNING,
        }
        for chunk in chunks
    )
    if level is IntelligenceLevel.FAST and stage is GenerationStage.REPAIRING:
        raise ValueError("Fast runs cannot enter the repairing stage")
    if status is GenerationRunStatus.PARTIAL and not failed:
        raise ValueError("PARTIAL status requires failed chunks")
    if failed and status in {
        GenerationRunStatus.PENDING,
        GenerationRunStatus.RUNNING,
        GenerationRunStatus.COMPLETED,
    }:
        raise ValueError("failed chunks require PARTIAL or terminal failure status")
    if stage is GenerationStage.COMPLETED:
        if unfinished:
            raise ValueError("completed run cannot contain unfinished chunks")
        if failed != (status is GenerationRunStatus.PARTIAL):
            raise ValueError("completed status must match failed chunk state")
        if not any(
            reservation.purpose is CallPurpose.GENERATE
            for reservation in call_budget.reservations
        ):
            raise ValueError("generation_call_not_reserved")
    if stage in {
        GenerationStage.REVIEWING,
        GenerationStage.REPAIRING,
        GenerationStage.CHECKING_COVERAGE,
        GenerationStage.DEDUPLICATING,
    } and unfinished:
        raise ValueError("post-generation stage cannot contain unfinished chunks")
    if stage in {
        GenerationStage.ANALYZING,
        GenerationStage.PLANNING,
    } and any(chunk.state is not ChunkGenerationState.PENDING for chunk in chunks):
        raise ValueError("pre-generation stage requires pending chunks")
    if status is GenerationRunStatus.PENDING and (
        stage is not GenerationStage.ANALYZING
        or call_budget.call_count
        or any(chunk.state is not ChunkGenerationState.PENDING for chunk in chunks)
    ):
        raise ValueError("PENDING status requires an untouched analyzing run")
    if error_code is not None and status is not GenerationRunStatus.FAILED:
        raise ValueError("run error_code requires FAILED status")
    allowed_purposes = {
        GenerationStage.ANALYZING: frozenset(),
        GenerationStage.PLANNING: frozenset({CallPurpose.PLANNER}),
        GenerationStage.GENERATING: frozenset(
            {CallPurpose.PLANNER, CallPurpose.GENERATE}
        ),
        GenerationStage.REVIEWING: frozenset(
            {
                CallPurpose.PLANNER,
                CallPurpose.GENERATE,
                CallPurpose.CRITIC,
                CallPurpose.REPAIR,
            }
        ),
        GenerationStage.REPAIRING: frozenset(
            {
                CallPurpose.PLANNER,
                CallPurpose.GENERATE,
                CallPurpose.CRITIC,
                CallPurpose.REPAIR,
            }
        ),
        GenerationStage.CHECKING_COVERAGE: frozenset(CallPurpose),
        GenerationStage.DEDUPLICATING: frozenset(CallPurpose),
        GenerationStage.COMPLETED: frozenset(CallPurpose),
        GenerationStage.FAILED: frozenset(CallPurpose),
        GenerationStage.SUPERSEDED: frozenset(CallPurpose),
    }[stage]
    if any(
        reservation.purpose not in allowed_purposes
        for reservation in call_budget.reservations
    ):
        raise ValueError("call reservation is incoherent with the run stage")


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


def _freeze_snapshot(value):
    state = {"nodes": 0, "active": set()}
    return _freeze_snapshot_value(value, depth=0, state=state)


def _freeze_snapshot_value(value, *, depth: int, state):
    if depth > MAX_SNAPSHOT_DEPTH:
        raise ValueError("snapshot_depth_limit")
    state["nodes"] += 1
    if state["nodes"] > MAX_SNAPSHOT_NODES:
        raise ValueError("snapshot_node_limit")
    if value is None or isinstance(value, (bool, int, Enum)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("snapshot_number_invalid")
        return value
    if isinstance(value, str):
        if len(value) > MAX_SNAPSHOT_TEXT_CHARS:
            raise ValueError("snapshot_text_limit")
        return value
    if isinstance(value, bytes):
        if len(value) > MAX_SNAPSHOT_BYTES:
            raise ValueError("snapshot_bytes_limit")
        return value
    if isinstance(value, Mapping):
        identity = id(value)
        if identity in state["active"]:
            raise ValueError("snapshot_cycle")
        state["active"].add(identity)
        try:
            try:
                keys = tuple(
                    islice(iter(value), MAX_SNAPSHOT_MAPPING_KEYS + 1)
                )
            except Exception:
                raise ValueError("snapshot_mapping_invalid") from None
            if len(keys) > MAX_SNAPSHOT_MAPPING_KEYS:
                raise ValueError("snapshot_mapping_limit")
            copied = {}
            for key in keys:
                frozen_key = _freeze_snapshot_value(
                    key,
                    depth=depth + 1,
                    state=state,
                )
                if not isinstance(frozen_key, (str, int, bool, Enum)):
                    raise TypeError("snapshot_mapping_key_invalid")
                try:
                    item = value[key]
                except Exception:
                    raise ValueError("snapshot_mapping_invalid") from None
                copied[frozen_key] = _freeze_snapshot_value(
                    item,
                    depth=depth + 1,
                    state=state,
                )
            return MappingProxyType(copied)
        finally:
            state["active"].discard(identity)
    if isinstance(value, (list, tuple, set, frozenset)):
        identity = id(value)
        if identity in state["active"]:
            raise ValueError("snapshot_cycle")
        state["active"].add(identity)
        try:
            try:
                items = tuple(
                    islice(iter(value), MAX_SNAPSHOT_SEQUENCE_ITEMS + 1)
                )
            except Exception:
                raise ValueError("snapshot_sequence_invalid") from None
            if len(items) > MAX_SNAPSHOT_SEQUENCE_ITEMS:
                raise ValueError("snapshot_sequence_limit")
            frozen = tuple(
                _freeze_snapshot_value(
                    item,
                    depth=depth + 1,
                    state=state,
                )
                for item in items
            )
            return frozenset(frozen) if isinstance(value, (set, frozenset)) else frozen
        finally:
            state["active"].discard(identity)
    if is_dataclass(value):
        if isinstance(value, type):
            raise TypeError("snapshot dataclass instances are required")
        identity = id(value)
        if identity in state["active"]:
            raise ValueError("snapshot_cycle")
        state["active"].add(identity)
        try:
            captured = {}
            for item in fields(value):
                try:
                    field_value = getattr(value, item.name)
                except Exception:
                    raise ValueError("snapshot_dataclass_invalid") from None
                captured[item.name] = _freeze_snapshot_value(
                    field_value,
                    depth=depth + 1,
                    state=state,
                )
            parameters = getattr(type(value), "__dataclass_params__", None)
            if parameters is not None and parameters.frozen:
                try:
                    frozen_copy = object.__new__(type(value))
                    for item in fields(value):
                        object.__setattr__(
                            frozen_copy,
                            item.name,
                            captured[item.name],
                        )
                    return frozen_copy
                except Exception:
                    raise ValueError("snapshot_dataclass_invalid") from None
            return MappingProxyType(captured)
        finally:
            state["active"].discard(identity)
    raise TypeError("snapshot values must be immutable or plain data")
