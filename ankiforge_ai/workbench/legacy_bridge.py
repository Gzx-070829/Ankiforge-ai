"""Content-free projection from the legacy mutable UI session."""

from __future__ import annotations

from typing import Optional

from ..pipeline.write_traceability import SourceType, coerce_source_type
from .models import (
    GenerationState,
    MaterialState,
    ReviewDecisionRecord,
    ReviewState,
    WorkbenchArtifactStatus,
    WorkbenchSessionState,
    WriteState,
)


_FAILED_GENERATION_STATES = frozenset(
    {
        "provider_error",
        "timeout",
        "invalid_json",
        "empty_output",
        "empty_cards",
        "material_too_long",
    }
)
_REVIEW_DECISION_MAP = {
    "looks_good": "keep",
    "needs_revision": "needs_edit",
    "skip_for_now": "discard",
}


def _enum_value(value: object, default: str = "") -> str:
    resolved = getattr(value, "value", value)
    return resolved if isinstance(resolved, str) else default


def _candidate_ids(session: object) -> tuple[str, ...]:
    previews = tuple(getattr(session, "candidate_card_previews", ()) or ())
    if previews:
        return tuple(str(getattr(item, "id")) for item in previews)
    drafts = tuple(getattr(session, "ai_candidate_card_drafts", ()) or ())
    return tuple(f"candidate-{getattr(item, 'id')}" for item in drafts)


def _generation_state(
    session: object,
    candidate_ids: tuple[str, ...],
    active_request_id: Optional[int],
) -> GenerationState:
    state_value = _enum_value(getattr(session, "ai_generation_state", None), "idle")
    candidate_revision = int(getattr(session, "candidate_revision", 0))
    if state_value == "running":
        return GenerationState(
            request_id=active_request_id,
            status=WorkbenchArtifactStatus.RUNNING,
            candidate_revision=candidate_revision,
        )
    if state_value in _FAILED_GENERATION_STATES:
        error_value = _enum_value(
            getattr(session, "ai_draft_error_code", None),
            state_value,
        )
        return GenerationState(
            status=WorkbenchArtifactStatus.FAILED,
            candidate_revision=candidate_revision,
            error_code=error_value or state_value,
        )
    candidate_state = _enum_value(
        getattr(session, "candidate_cards_state", None),
        "empty",
    )
    if candidate_ids and (state_value == "success" or candidate_state == "current"):
        return GenerationState(
            status=WorkbenchArtifactStatus.COMPLETE,
            candidate_revision=candidate_revision,
            candidate_ids=candidate_ids,
        )
    return GenerationState(candidate_revision=candidate_revision)


def _review_state(
    session: object,
    generation: GenerationState,
) -> ReviewState:
    if not generation.candidate_ids:
        return ReviewState()
    raw_decisions = getattr(session, "candidate_review_decisions", {}) or {}
    decisions = []
    for candidate_id in generation.candidate_ids:
        raw = raw_decisions.get(candidate_id)
        mapped = _REVIEW_DECISION_MAP.get(_enum_value(raw))
        if mapped is not None:
            decisions.append(ReviewDecisionRecord(candidate_id, mapped))
    status = (
        WorkbenchArtifactStatus.COMPLETE
        if len(decisions) == len(generation.candidate_ids)
        else WorkbenchArtifactStatus.CURRENT
    )
    return ReviewState(
        candidate_revision=generation.candidate_revision,
        revision=int(getattr(session, "review_revision", 0)),
        status=status,
        decisions=tuple(decisions),
    )


def _write_state(
    session: object,
    generation: GenerationState,
    *,
    target_revision: int,
    mapping_revision: int,
) -> WriteState:
    duplicate_state = _enum_value(
        getattr(session, "duplicate_check_preview_state", None),
        "empty",
    )
    if duplicate_state == "current":
        return WriteState(
            target_revision=target_revision,
            mapping_revision=mapping_revision,
            duplicate_candidate_revision=generation.candidate_revision,
            duplicate_target_revision=target_revision,
            duplicate_mapping_revision=mapping_revision,
            status=WorkbenchArtifactStatus.CURRENT,
        )
    return WriteState(
        target_revision=target_revision,
        mapping_revision=mapping_revision,
        status=(
            WorkbenchArtifactStatus.STALE
            if duplicate_state == "cleared"
            else WorkbenchArtifactStatus.EMPTY
        ),
    )


def project_legacy_session(
    session: object,
    active_request_id: Optional[int] = None,
    *,
    target_revision: int = 0,
    mapping_revision: int = 0,
) -> WorkbenchSessionState:
    """Project structural state without copying user or credential content."""

    if session is None or not hasattr(session, "material_text"):
        raise TypeError("session must expose the legacy workbench state")
    material_text = getattr(session, "material_text", "")
    if not isinstance(material_text, str):
        raise TypeError("legacy material_text must be a string")
    source_type = getattr(session, "source_type", SourceType.PASTE)
    if not isinstance(source_type, SourceType):
        source_type = coerce_source_type(source_type)
    material = MaterialState(
        revision=int(getattr(session, "material_revision", 0)),
        has_material=bool(material_text),
        char_count=len(material_text),
        source_type=source_type,
    )
    candidate_ids = _candidate_ids(session)
    generation = _generation_state(session, candidate_ids, active_request_id)
    review = _review_state(session, generation)
    write = _write_state(
        session,
        generation,
        target_revision=target_revision,
        mapping_revision=mapping_revision,
    )
    return WorkbenchSessionState(
        material=material,
        generation=generation,
        review=review,
        write=write,
        closed=bool(getattr(session, "closed", False)),
    )
