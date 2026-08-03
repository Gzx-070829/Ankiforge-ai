"""Pure state transitions for the disposable workbench session."""

from __future__ import annotations

from dataclasses import replace

from ..pipeline.write_traceability import SourceType
from .models import (
    GenerationState,
    MaterialState,
    ReviewDecisionRecord,
    ReviewState,
    WorkbenchArtifactStatus,
    WorkbenchSessionState,
    WriteState,
)


def _require_open(state: WorkbenchSessionState) -> None:
    if not isinstance(state, WorkbenchSessionState):
        raise TypeError("state must be a WorkbenchSessionState")
    if state.closed:
        raise RuntimeError("closed workbench sessions cannot be reused")


def _invalidated_write_state(state: WorkbenchSessionState) -> WriteState:
    return WriteState(
        target_revision=state.write.target_revision,
        mapping_revision=state.write.mapping_revision,
        status=WorkbenchArtifactStatus.STALE,
    )


def update_material(
    state: WorkbenchSessionState,
    *,
    char_count: int,
    source_type: SourceType,
) -> WorkbenchSessionState:
    """Replace material metadata and invalidate generated artifacts."""

    _require_open(state)
    material = MaterialState(
        revision=state.material.revision + 1,
        has_material=char_count > 0,
        char_count=char_count,
        source_type=source_type,
    )
    return replace(
        state,
        material=material,
        generation=GenerationState(
            candidate_revision=state.generation.candidate_revision,
        ),
        review=ReviewState(),
        write=_invalidated_write_state(state),
    )


def start_generation(
    state: WorkbenchSessionState,
    *,
    request_id: int,
) -> WorkbenchSessionState:
    """Begin one explicit generation request and clear older results."""

    _require_open(state)
    if not state.material.has_material:
        raise ValueError("material is required before generation")
    generation = GenerationState(
        request_id=request_id,
        status=WorkbenchArtifactStatus.RUNNING,
        candidate_revision=state.generation.candidate_revision,
    )
    return replace(
        state,
        generation=generation,
        review=ReviewState(),
        write=_invalidated_write_state(state),
    )


def complete_generation(
    state: WorkbenchSessionState,
    *,
    request_id: int,
    candidate_ids: tuple[str, ...],
) -> WorkbenchSessionState:
    """Apply a current request result or ignore a stale completion."""

    _require_open(state)
    if request_id != state.generation.request_id:
        return state
    candidate_revision = state.generation.candidate_revision + 1
    generation = GenerationState(
        request_id=request_id,
        status=WorkbenchArtifactStatus.COMPLETE,
        candidate_revision=candidate_revision,
        candidate_ids=candidate_ids,
    )
    return replace(
        state,
        generation=generation,
        review=ReviewState(
            candidate_revision=candidate_revision,
            status=WorkbenchArtifactStatus.CURRENT,
        ),
        write=_invalidated_write_state(state),
    )


def fail_generation(
    state: WorkbenchSessionState,
    *,
    request_id: int,
    error_code: str,
) -> WorkbenchSessionState:
    """Apply a current request failure or ignore a stale failure."""

    _require_open(state)
    if request_id != state.generation.request_id:
        return state
    return replace(
        state,
        generation=GenerationState(
            request_id=request_id,
            status=WorkbenchArtifactStatus.FAILED,
            candidate_revision=state.generation.candidate_revision,
            error_code=error_code,
        ),
        review=ReviewState(),
        write=_invalidated_write_state(state),
    )


def record_review_decision(
    state: WorkbenchSessionState,
    candidate_id: str,
    decision: str,
) -> WorkbenchSessionState:
    """Record one review choice and invalidate duplicate readiness."""

    _require_open(state)
    if candidate_id not in state.generation.candidate_ids:
        raise ValueError("candidate_id is not part of the current generation")
    decisions = {item.candidate_id: item for item in state.review.decisions}
    decisions[candidate_id] = ReviewDecisionRecord(candidate_id, decision)
    ordered = tuple(
        decisions[item]
        for item in state.generation.candidate_ids
        if item in decisions
    )
    review_status = (
        WorkbenchArtifactStatus.COMPLETE
        if len(ordered) == len(state.generation.candidate_ids)
        else WorkbenchArtifactStatus.CURRENT
    )
    return replace(
        state,
        review=ReviewState(
            candidate_revision=state.generation.candidate_revision,
            revision=state.review.revision + 1,
            status=review_status,
            decisions=ordered,
        ),
        write=_invalidated_write_state(state),
    )


def change_target(state: WorkbenchSessionState) -> WorkbenchSessionState:
    """Advance the target revision and invalidate duplicate readiness."""

    _require_open(state)
    return replace(
        state,
        write=WriteState(
            target_revision=state.write.target_revision + 1,
            mapping_revision=state.write.mapping_revision,
            status=WorkbenchArtifactStatus.STALE,
        ),
    )


def change_mapping(state: WorkbenchSessionState) -> WorkbenchSessionState:
    """Advance the mapping revision and invalidate duplicate readiness."""

    _require_open(state)
    return replace(
        state,
        write=WriteState(
            target_revision=state.write.target_revision,
            mapping_revision=state.write.mapping_revision + 1,
            status=WorkbenchArtifactStatus.STALE,
        ),
    )


def mark_duplicate_check_current(
    state: WorkbenchSessionState,
) -> WorkbenchSessionState:
    """Snapshot the candidate, target, and mapping revisions after a check."""

    _require_open(state)
    if state.review.status is not WorkbenchArtifactStatus.COMPLETE:
        raise ValueError("review must be complete before duplicate checking")
    return replace(
        state,
        write=WriteState(
            target_revision=state.write.target_revision,
            mapping_revision=state.write.mapping_revision,
            duplicate_candidate_revision=state.generation.candidate_revision,
            duplicate_target_revision=state.write.target_revision,
            duplicate_mapping_revision=state.write.mapping_revision,
            status=WorkbenchArtifactStatus.CURRENT,
        ),
    )


def write_is_ready(state: WorkbenchSessionState) -> bool:
    """Return whether immutable state satisfies the pre-write readiness gate."""

    if not isinstance(state, WorkbenchSessionState) or state.closed:
        return False
    decisions = {item.decision for item in state.review.decisions}
    return (
        state.generation.status is WorkbenchArtifactStatus.COMPLETE
        and state.review.status is WorkbenchArtifactStatus.COMPLETE
        and "keep" in decisions
        and state.write.status is WorkbenchArtifactStatus.CURRENT
        and state.write.duplicate_candidate_revision
        == state.generation.candidate_revision
        and state.write.duplicate_target_revision == state.write.target_revision
        and state.write.duplicate_mapping_revision == state.write.mapping_revision
    )


def close_session(state: WorkbenchSessionState) -> WorkbenchSessionState:
    """Discard all disposable state and permanently close the snapshot."""

    _require_open(state)
    return WorkbenchSessionState(closed=True)
