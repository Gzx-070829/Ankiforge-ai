"""Immutable, content-free state for the Create -> Review -> Write workbench."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Optional

from ..pipeline.write_traceability import SourceType


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_SAFE_ERROR_CODE = re.compile(r"^[a-z][a-z0-9_]{0,119}$")
_REVIEW_DECISIONS = frozenset({"keep", "discard", "needs_edit"})


class WorkbenchArtifactStatus(str, Enum):
    """Small shared vocabulary for disposable application artifacts."""

    EMPTY = "empty"
    CURRENT = "current"
    RUNNING = "running"
    FAILED = "failed"
    STALE = "stale"
    COMPLETE = "complete"


def _validate_non_negative_int(value: object, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")


def _validate_optional_revision(value: object, name: str) -> None:
    if value is not None:
        _validate_non_negative_int(value, name)


def _validate_safe_id(value: object, name: str) -> None:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise ValueError(f"{name} must be a safe bounded identifier")


@dataclass(frozen=True, repr=False)
class MaterialState:
    revision: int = 0
    has_material: bool = False
    char_count: int = 0
    source_type: SourceType = SourceType.PASTE

    def __post_init__(self) -> None:
        _validate_non_negative_int(self.revision, "revision")
        if not isinstance(self.has_material, bool):
            raise ValueError("has_material must be a boolean")
        _validate_non_negative_int(self.char_count, "char_count")
        if not isinstance(self.source_type, SourceType):
            raise ValueError("source_type must be a SourceType")
        if self.has_material != (self.char_count > 0):
            raise ValueError("material presence must match its character count")

    def __repr__(self) -> str:
        return (
            "MaterialState("
            f"revision={self.revision}, has_material={self.has_material}, "
            f"char_count={self.char_count}, source_type={self.source_type.value!r})"
        )


@dataclass(frozen=True, repr=False)
class GenerationState:
    request_id: Optional[int] = None
    status: WorkbenchArtifactStatus = WorkbenchArtifactStatus.EMPTY
    candidate_revision: int = 0
    candidate_ids: tuple[str, ...] = field(default_factory=tuple)
    error_code: Optional[str] = None

    def __post_init__(self) -> None:
        if self.request_id is not None and (
            isinstance(self.request_id, bool)
            or not isinstance(self.request_id, int)
            or self.request_id < 1
        ):
            raise ValueError("request_id must be a positive integer or None")
        if not isinstance(self.status, WorkbenchArtifactStatus):
            raise ValueError("status must be a WorkbenchArtifactStatus")
        _validate_non_negative_int(self.candidate_revision, "candidate_revision")
        if not isinstance(self.candidate_ids, tuple):
            raise ValueError("candidate_ids must be a tuple")
        for candidate_id in self.candidate_ids:
            _validate_safe_id(candidate_id, "candidate_id")
        if len(set(self.candidate_ids)) != len(self.candidate_ids):
            raise ValueError("candidate_ids must be unique")
        if self.error_code is not None and (
            not isinstance(self.error_code, str)
            or not _SAFE_ERROR_CODE.fullmatch(self.error_code)
        ):
            raise ValueError("error_code must be a safe bounded code")
        if self.status is WorkbenchArtifactStatus.RUNNING:
            if self.request_id is None or self.candidate_ids or self.error_code:
                raise ValueError("running generation state is inconsistent")
        elif self.status is WorkbenchArtifactStatus.COMPLETE:
            if not self.candidate_ids or self.error_code is not None:
                raise ValueError("complete generation requires candidates")
        elif self.status is WorkbenchArtifactStatus.FAILED:
            if self.error_code is None or self.candidate_ids:
                raise ValueError("failed generation requires only an error code")
        elif self.status is WorkbenchArtifactStatus.EMPTY:
            if self.candidate_ids or self.error_code is not None:
                raise ValueError("empty generation cannot contain results")
        else:
            raise ValueError("generation status must be empty, running, failed, or complete")

    def __repr__(self) -> str:
        return (
            "GenerationState("
            f"request_id={self.request_id!r}, status={self.status.value!r}, "
            f"candidate_revision={self.candidate_revision}, "
            f"candidate_count={len(self.candidate_ids)}, "
            f"error_code={self.error_code!r})"
        )


@dataclass(frozen=True)
class ReviewDecisionRecord:
    candidate_id: str
    decision: str

    def __post_init__(self) -> None:
        _validate_safe_id(self.candidate_id, "candidate_id")
        if self.decision not in _REVIEW_DECISIONS:
            raise ValueError("decision must be keep, discard, or needs_edit")


@dataclass(frozen=True, repr=False)
class ReviewState:
    candidate_revision: int = 0
    revision: int = 0
    status: WorkbenchArtifactStatus = WorkbenchArtifactStatus.EMPTY
    decisions: tuple[ReviewDecisionRecord, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _validate_non_negative_int(self.candidate_revision, "candidate_revision")
        _validate_non_negative_int(self.revision, "revision")
        if self.status not in {
            WorkbenchArtifactStatus.EMPTY,
            WorkbenchArtifactStatus.CURRENT,
            WorkbenchArtifactStatus.STALE,
            WorkbenchArtifactStatus.COMPLETE,
        }:
            raise ValueError("review status is not valid")
        if not isinstance(self.decisions, tuple) or not all(
            isinstance(item, ReviewDecisionRecord) for item in self.decisions
        ):
            raise ValueError("decisions must contain ReviewDecisionRecord values")
        candidate_ids = tuple(item.candidate_id for item in self.decisions)
        if len(set(candidate_ids)) != len(candidate_ids):
            raise ValueError("review decisions must have unique candidate IDs")
        if self.status is WorkbenchArtifactStatus.EMPTY and self.decisions:
            raise ValueError("empty review cannot contain decisions")

    def __repr__(self) -> str:
        counts = {decision: 0 for decision in sorted(_REVIEW_DECISIONS)}
        for item in self.decisions:
            counts[item.decision] += 1
        return (
            "ReviewState("
            f"candidate_revision={self.candidate_revision}, revision={self.revision}, "
            f"status={self.status.value!r}, decision_count={len(self.decisions)}, "
            f"kept={counts['keep']}, discarded={counts['discard']}, "
            f"needs_edit={counts['needs_edit']})"
        )


@dataclass(frozen=True, repr=False)
class WriteState:
    target_revision: int = 0
    mapping_revision: int = 0
    duplicate_candidate_revision: Optional[int] = None
    duplicate_target_revision: Optional[int] = None
    duplicate_mapping_revision: Optional[int] = None
    status: WorkbenchArtifactStatus = WorkbenchArtifactStatus.EMPTY

    def __post_init__(self) -> None:
        _validate_non_negative_int(self.target_revision, "target_revision")
        _validate_non_negative_int(self.mapping_revision, "mapping_revision")
        revisions = (
            self.duplicate_candidate_revision,
            self.duplicate_target_revision,
            self.duplicate_mapping_revision,
        )
        for value, name in zip(
            revisions,
            (
                "duplicate_candidate_revision",
                "duplicate_target_revision",
                "duplicate_mapping_revision",
            ),
        ):
            _validate_optional_revision(value, name)
        if any(value is None for value in revisions) != all(
            value is None for value in revisions
        ):
            raise ValueError("duplicate snapshot revisions must be all present or absent")
        if self.status not in {
            WorkbenchArtifactStatus.EMPTY,
            WorkbenchArtifactStatus.CURRENT,
            WorkbenchArtifactStatus.STALE,
        }:
            raise ValueError("write readiness status is not valid")
        if self.status is WorkbenchArtifactStatus.CURRENT and revisions[0] is None:
            raise ValueError("current write state requires a duplicate snapshot")
        if self.status is WorkbenchArtifactStatus.EMPTY and revisions[0] is not None:
            raise ValueError("empty write state cannot contain a duplicate snapshot")

    @property
    def has_duplicate_snapshot(self) -> bool:
        return self.duplicate_candidate_revision is not None

    def __repr__(self) -> str:
        return (
            "WriteState("
            f"target_revision={self.target_revision}, "
            f"mapping_revision={self.mapping_revision}, "
            f"status={self.status.value!r}, "
            f"has_duplicate_snapshot={self.has_duplicate_snapshot})"
        )


@dataclass(frozen=True, repr=False)
class WorkbenchSessionState:
    material: MaterialState = field(default_factory=MaterialState)
    generation: GenerationState = field(default_factory=GenerationState)
    review: ReviewState = field(default_factory=ReviewState)
    write: WriteState = field(default_factory=WriteState)
    closed: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.material, MaterialState):
            raise ValueError("material must be a MaterialState")
        if not isinstance(self.generation, GenerationState):
            raise ValueError("generation must be a GenerationState")
        if not isinstance(self.review, ReviewState):
            raise ValueError("review must be a ReviewState")
        if not isinstance(self.write, WriteState):
            raise ValueError("write must be a WriteState")
        if not isinstance(self.closed, bool):
            raise ValueError("closed must be a boolean")
        candidate_ids = set(self.generation.candidate_ids)
        review_ids = {item.candidate_id for item in self.review.decisions}
        if review_ids - candidate_ids:
            raise ValueError("review decisions must reference current candidates")
        if candidate_ids and self.review.candidate_revision != self.generation.candidate_revision:
            raise ValueError("review must reference the current candidate revision")
        if (
            self.review.status is WorkbenchArtifactStatus.COMPLETE
            and len(review_ids) != len(candidate_ids)
        ):
            raise ValueError("complete review requires one decision per candidate")
        if self.write.status is WorkbenchArtifactStatus.CURRENT and (
            self.write.duplicate_candidate_revision
            != self.generation.candidate_revision
            or self.write.duplicate_target_revision != self.write.target_revision
            or self.write.duplicate_mapping_revision != self.write.mapping_revision
        ):
            raise ValueError("current write state must match all current revisions")
        if self.closed and (
            self.material.has_material
            or self.generation.candidate_ids
            or self.review.decisions
            or self.write.has_duplicate_snapshot
        ):
            raise ValueError("closed workbench state must not retain session data")

    def __repr__(self) -> str:
        return (
            "WorkbenchSessionState("
            f"material_revision={self.material.revision}, "
            f"material_chars={self.material.char_count}, "
            f"source_type={self.material.source_type.value!r}, "
            f"generation_status={self.generation.status.value!r}, "
            f"generation_request_id={self.generation.request_id!r}, "
            f"candidate_revision={self.generation.candidate_revision}, "
            f"candidate_count={len(self.generation.candidate_ids)}, "
            f"review_revision={self.review.revision}, "
            f"review_status={self.review.status.value!r}, "
            f"review_decision_count={len(self.review.decisions)}, "
            f"target_revision={self.write.target_revision}, "
            f"mapping_revision={self.write.mapping_revision}, "
            f"duplicate_snapshot={self.write.has_duplicate_snapshot}, "
            f"closed={self.closed})"
        )


def initial_workbench_state() -> WorkbenchSessionState:
    """Return a fresh, empty, non-persistent workbench state."""

    return WorkbenchSessionState()
