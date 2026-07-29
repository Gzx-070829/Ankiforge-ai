"""Immutable knowledge-plan and coverage models."""

import re
from dataclasses import dataclass
from itertools import islice

from ...document import DEFAULT_DOCUMENT_LIMITS, SourceLocation


_SAFE_PLAN_ID = re.compile(r"^plan-[a-f0-9]{16}$")
_SAFE_POINT_ID = re.compile(r"^point-[a-f0-9]{16}$")
_SAFE_CHUNK_ID = re.compile(r"^chunk-[a-f0-9]{16}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_PRIORITIES = {"high", "medium", "low"}
MAX_DOCUMENT_CHUNKS = 48
MAX_PLAN_POINTS = 96
MAX_POINT_SOURCE_CHUNKS = 4
SUPPORTED_POINT_TYPES = frozenset(
    {
        "concept",
        "definition",
        "comparison",
        "process",
        "formula",
        "code",
        "table",
        "transcript",
        "mistake",
        "exam",
        "fact",
    }
)
SUPPORTED_TEMPLATES = frozenset(
    {
        "concept",
        "definition",
        "exam_answer",
        "quick_review",
        "compare_contrast",
        "process_steps",
        "formula_rule",
        "mistake_trap",
    }
)


@dataclass(frozen=True, repr=False)
class KnowledgePointPlan:
    point_id: str
    title: str
    point_type: str
    priority: str
    section_id: str
    source_chunk_ids: tuple[str, ...]
    source_locations: tuple[SourceLocation, ...]
    recommended_template: str
    rationale: str

    def __post_init__(self) -> None:
        if not isinstance(self.point_id, str) or not _SAFE_POINT_ID.fullmatch(
            self.point_id
        ):
            raise ValueError("point_id must be a safe stable identifier")
        _validate_id(self.section_id, "section_id")
        for value, name, limit in (
            (self.title, "title", 240),
            (self.point_type, "point_type", 40),
            (self.section_id, "section_id", 128),
            (self.recommended_template, "recommended_template", 64),
            (self.rationale, "rationale", 240),
        ):
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                raise ValueError(f"{name} must be a bounded non-empty string")
        if self.priority not in _PRIORITIES:
            raise ValueError("priority must be high, medium, or low")
        if self.point_type not in SUPPORTED_POINT_TYPES:
            raise ValueError("point_type is unsupported")
        if self.recommended_template not in SUPPORTED_TEMPLATES:
            raise ValueError("recommended_template is unsupported")
        chunk_ids = _bounded_tuple(
            self.source_chunk_ids,
            MAX_POINT_SOURCE_CHUNKS,
            "source_chunk_ids",
        )
        if not chunk_ids or len(set(chunk_ids)) != len(chunk_ids):
            raise ValueError("source_chunk_ids must contain unique chunks")
        if not all(
            isinstance(chunk_id, str) and _SAFE_CHUNK_ID.fullmatch(chunk_id)
            for chunk_id in chunk_ids
        ):
            raise ValueError("source_chunk_ids must contain safe chunk IDs")
        locations = _bounded_tuple(
            self.source_locations,
            DEFAULT_DOCUMENT_LIMITS.max_document_blocks,
            "source_locations",
        )
        if not all(isinstance(location, SourceLocation) for location in locations):
            raise TypeError("source_locations must contain SourceLocation instances")
        if len(set(locations)) != len(locations):
            raise ValueError("source_locations must be unique")
        object.__setattr__(self, "source_chunk_ids", chunk_ids)
        object.__setattr__(self, "source_locations", locations)

    def __repr__(self) -> str:
        return (
            "KnowledgePointPlan("
            f"point_id={self.point_id!r}, type={self.point_type!r}, "
            f"priority={self.priority!r}, section_id={self.section_id!r}, "
            f"source_chunks={len(self.source_chunk_ids)})"
        )


@dataclass(frozen=True, repr=False)
class KnowledgePlan:
    plan_id: str
    document_id: str
    source: str
    chunk_ids: tuple[str, ...]
    points: tuple[KnowledgePointPlan, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.plan_id, str) or not _SAFE_PLAN_ID.fullmatch(
            self.plan_id
        ):
            raise ValueError("plan_id must be a safe stable identifier")
        _validate_id(self.document_id, "document_id")
        if self.source not in {"local", "llm"}:
            raise ValueError("plan source must be local or llm")
        chunk_ids = _bounded_tuple(
            self.chunk_ids,
            MAX_DOCUMENT_CHUNKS,
            "chunk_ids",
        )
        points = _bounded_tuple(self.points, MAX_PLAN_POINTS, "points")
        if (
            not all(isinstance(chunk_id, str) for chunk_id in chunk_ids)
            or len(set(chunk_ids)) != len(chunk_ids)
            or not all(_SAFE_CHUNK_ID.fullmatch(chunk_id) for chunk_id in chunk_ids)
        ):
            raise ValueError("plan chunk_ids must be unique and bounded")
        if not all(isinstance(point, KnowledgePointPlan) for point in points):
            raise ValueError("plan points must be valid and bounded")
        if len({point.point_id for point in points}) != len(points):
            raise ValueError("plan point IDs must be unique")
        chunk_id_set = set(chunk_ids)
        if any(
            not set(point.source_chunk_ids).issubset(chunk_id_set)
            for point in points
        ):
            raise ValueError("plan point reference is absent from plan chunk_ids")
        object.__setattr__(self, "chunk_ids", chunk_ids)
        object.__setattr__(self, "points", points)

    def __repr__(self) -> str:
        return (
            "KnowledgePlan("
            f"plan_id={self.plan_id!r}, document_id={self.document_id!r}, "
            f"source={self.source!r}, chunks={len(self.chunk_ids)}, "
            f"points={len(self.points)})"
        )


@dataclass(frozen=True, repr=False)
class PlanCoverage:
    covered_chunk_ids: tuple[str, ...]
    uncovered_chunk_ids: tuple[str, ...]
    covered_section_ids: tuple[str, ...]
    uncovered_section_ids: tuple[str, ...]
    duplicate_point_ids: tuple[str, ...]
    invalid_point_ids: tuple[str, ...]
    is_grounded: bool

    def __post_init__(self) -> None:
        covered_chunks = _validated_ids(
            self.covered_chunk_ids,
            MAX_DOCUMENT_CHUNKS,
            _SAFE_CHUNK_ID,
            "covered_chunk_ids",
        )
        uncovered_chunks = _validated_ids(
            self.uncovered_chunk_ids,
            MAX_DOCUMENT_CHUNKS,
            _SAFE_CHUNK_ID,
            "uncovered_chunk_ids",
        )
        if set(covered_chunks) & set(uncovered_chunks):
            raise ValueError("covered and uncovered chunk IDs overlap")
        if len(covered_chunks) + len(uncovered_chunks) > MAX_DOCUMENT_CHUNKS:
            raise ValueError("coverage chunk IDs exceed the approved limit")
        covered_sections = _validated_ids(
            self.covered_section_ids,
            DEFAULT_DOCUMENT_LIMITS.max_document_blocks,
            _SAFE_ID,
            "covered_section_ids",
        )
        uncovered_sections = _validated_ids(
            self.uncovered_section_ids,
            DEFAULT_DOCUMENT_LIMITS.max_document_blocks,
            _SAFE_ID,
            "uncovered_section_ids",
        )
        if set(covered_sections) & set(uncovered_sections):
            raise ValueError("covered and uncovered section IDs overlap")
        duplicate_points = _validated_ids(
            self.duplicate_point_ids,
            MAX_PLAN_POINTS,
            _SAFE_POINT_ID,
            "duplicate_point_ids",
        )
        invalid_points = _validated_ids(
            self.invalid_point_ids,
            MAX_PLAN_POINTS,
            _SAFE_POINT_ID,
            "invalid_point_ids",
        )
        if not isinstance(self.is_grounded, bool):
            raise TypeError("is_grounded must be a boolean")
        if self.is_grounded and invalid_points:
            raise ValueError("grounded coverage cannot contain invalid points")
        object.__setattr__(self, "covered_chunk_ids", covered_chunks)
        object.__setattr__(self, "uncovered_chunk_ids", uncovered_chunks)
        object.__setattr__(self, "covered_section_ids", covered_sections)
        object.__setattr__(self, "uncovered_section_ids", uncovered_sections)
        object.__setattr__(self, "duplicate_point_ids", duplicate_points)
        object.__setattr__(self, "invalid_point_ids", invalid_points)

    def __repr__(self) -> str:
        return (
            "PlanCoverage("
            f"covered_chunks={len(self.covered_chunk_ids)}, "
            f"uncovered_chunks={len(self.uncovered_chunk_ids)}, "
            f"duplicate_points={len(self.duplicate_point_ids)}, "
            f"invalid_points={len(self.invalid_point_ids)}, "
            f"is_grounded={self.is_grounded})"
        )


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


def _validated_ids(value, limit: int, pattern, name: str) -> tuple[str, ...]:
    result = _bounded_tuple(value, limit, name)
    if not all(isinstance(item, str) for item in result):
        raise ValueError(f"{name} must contain unique safe IDs")
    if len(set(result)) != len(result) or not all(
        pattern.fullmatch(item) for item in result
    ):
        raise ValueError(f"{name} must contain unique safe IDs")
    return result


def _validate_id(value, name: str) -> None:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise ValueError(f"{name} must be a safe stable identifier")
