"""Immutable, dependency-free models for deterministic document intelligence."""

import math
import re
from dataclasses import dataclass
from enum import Enum
from itertools import islice
from types import MappingProxyType
from typing import Mapping


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_SAFE_CODE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,119}$")
_LANGUAGES = {"unknown", "en", "zh", "mixed"}
_DOCUMENT_KINDS = {
    "empty",
    "mixed",
    "code",
    "table",
    "transcript",
    "formula",
    "structured",
    "text",
}
_RECOMMENDED_MODES = {
    "code_understanding",
    "table_relationship",
    "transcript_summary_candidate",
    "formula_rule",
    "compare_contrast",
    "process_steps",
    "definition",
    "concept",
}
_BLOCK_KINDS = {
    "heading",
    "paragraph",
    "list",
    "list_item",
    "table",
    "code",
    "formula",
    "quote",
    "caption",
    "transcript",
    "metadata",
}
_MAX_DOCUMENT_BLOCKS = 20_000
_MAX_TEXT_CHARS = 5_000_000
_MAX_DOCUMENT_CHUNKS = 48
_MAX_PLAN_POINTS = 96
_MAX_AI_CALLS = 12
_CALL_POLICY = {
    "fast": (1, 3),
    "standard": (3, 8),
    "deep": (4, 12),
}


class IntelligenceLevel(str, Enum):
    FAST = "fast"
    STANDARD = "standard"
    DEEP = "deep"


@dataclass(frozen=True, repr=False)
class DocumentAnalysis:
    document_id: str
    dominant_language: str
    document_kind: str
    section_count: int
    block_count: int
    char_count: int
    content_density: float
    definition_count: int
    comparison_count: int
    process_count: int
    formula_count: int
    code_block_count: int
    table_block_count: int
    transcript_block_count: int
    estimated_knowledge_points: int
    recommended_modes: tuple[str, ...]
    warnings: tuple[str, ...]
    confidence: float
    block_kind_counts: Mapping[str, int]

    def __post_init__(self) -> None:
        if not isinstance(self.document_id, str) or not _SAFE_ID.fullmatch(
            self.document_id
        ):
            raise ValueError("document_id must be a safe stable identifier")
        if self.dominant_language not in _LANGUAGES:
            raise ValueError("dominant_language is unsupported")
        if self.document_kind not in _DOCUMENT_KINDS:
            raise ValueError("document_kind is unsupported")
        counts = (
            self.section_count,
            self.block_count,
            self.char_count,
            self.definition_count,
            self.comparison_count,
            self.process_count,
            self.formula_count,
            self.code_block_count,
            self.table_block_count,
            self.transcript_block_count,
            self.estimated_knowledge_points,
        )
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in counts):
            raise ValueError("analysis counts must be non-negative integers")
        if (
            self.section_count > _MAX_DOCUMENT_BLOCKS
            or self.block_count > _MAX_DOCUMENT_BLOCKS
            or self.char_count > _MAX_TEXT_CHARS
        ):
            raise ValueError("analysis document counts exceed approved limits")
        if self.estimated_knowledge_points > _MAX_PLAN_POINTS:
            raise ValueError("estimated knowledge points exceed the approved limit")
        signal_counts = (
            self.definition_count,
            self.comparison_count,
            self.process_count,
            self.formula_count,
            self.code_block_count,
            self.table_block_count,
            self.transcript_block_count,
        )
        if any(value > self.block_count for value in signal_counts):
            raise ValueError("analysis signal count exceeds block count")
        if self.block_count and not self.section_count:
            raise ValueError("non-empty analysis must contain a section")
        if (
            isinstance(self.confidence, bool)
            or not isinstance(self.confidence, (int, float))
            or not math.isfinite(self.confidence)
            or not 0.0 <= self.confidence <= 1.0
        ):
            raise ValueError("analysis confidence must be between zero and one")
        if (
            isinstance(self.content_density, bool)
            or not isinstance(self.content_density, (int, float))
            or not math.isfinite(self.content_density)
            or not 0 <= self.content_density <= _MAX_TEXT_CHARS
        ):
            raise ValueError(
                "analysis content density must be finite and within bounds"
            )
        modes = _bounded_string_tuple(
            self.recommended_modes,
            len(_RECOMMENDED_MODES),
            "recommended_modes",
        )
        if len(set(modes)) != len(modes) or any(
            mode not in _RECOMMENDED_MODES for mode in modes
        ):
            raise ValueError("recommended_modes contain unsupported values")
        warnings = _bounded_string_tuple(self.warnings, 32, "warnings")
        if any(not _SAFE_CODE.fullmatch(warning) for warning in warnings):
            raise ValueError("warnings must contain bounded safe codes")
        kind_counts = _bounded_block_kind_counts(self.block_kind_counts)
        if sum(kind_counts.values()) != self.block_count:
            raise ValueError("block_kind_counts must sum to block_count")
        for name, count in (
            ("formula", self.formula_count),
            ("code", self.code_block_count),
            ("table", self.table_block_count),
            ("transcript", self.transcript_block_count),
        ):
            if count > kind_counts.get(name, 0):
                raise ValueError(
                    "specialist signal count exceeds its block kind count"
                )
        object.__setattr__(self, "recommended_modes", modes)
        object.__setattr__(self, "warnings", warnings)
        object.__setattr__(
            self,
            "block_kind_counts",
            MappingProxyType(dict(sorted(kind_counts.items()))),
        )

    @property
    def has_definitions(self) -> bool:
        return self.definition_count > 0

    @property
    def has_comparisons(self) -> bool:
        return self.comparison_count > 0

    @property
    def has_processes(self) -> bool:
        return self.process_count > 0

    @property
    def has_formulas(self) -> bool:
        return self.formula_count > 0

    @property
    def has_code(self) -> bool:
        return self.code_block_count > 0

    @property
    def has_tables(self) -> bool:
        return self.table_block_count > 0

    @property
    def has_transcript(self) -> bool:
        return self.transcript_block_count > 0

    def __repr__(self) -> str:
        return (
            "DocumentAnalysis("
            f"document_id={self.document_id!r}, kind={self.document_kind!r}, "
            f"sections={self.section_count}, blocks={self.block_count}, "
            f"estimated_points={self.estimated_knowledge_points}, "
            f"confidence={self.confidence:.2f})"
        )


@dataclass(frozen=True, repr=False)
class TemplateRoute:
    mode_id: str
    template_id: str
    confidence: float
    reason_code: str
    source_constraints: tuple[str, ...]
    overridden: bool = False

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("route confidence must be between zero and one")
        object.__setattr__(self, "source_constraints", tuple(self.source_constraints))

    def __repr__(self) -> str:
        return (
            "TemplateRoute("
            f"mode_id={self.mode_id!r}, template_id={self.template_id!r}, "
            f"confidence={self.confidence:.2f}, reason_code={self.reason_code!r}, "
            f"overridden={self.overridden})"
        )


@dataclass(frozen=True, repr=False)
class PlanEstimate:
    level: IntelligenceLevel
    chunk_count: int
    estimated_card_min: int
    estimated_card_max: int
    estimated_call_min: int
    estimated_call_max: int
    max_calls: int = 12
    requires_confirmation: bool = True

    def __post_init__(self) -> None:
        try:
            normalized_level = IntelligenceLevel(self.level)
        except (TypeError, ValueError) as exc:
            raise ValueError("level must be fast, standard, or deep") from exc
        values = (
            self.chunk_count,
            self.estimated_card_min,
            self.estimated_card_max,
            self.estimated_call_min,
            self.estimated_call_max,
            self.max_calls,
        )
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in values):
            raise ValueError("estimate counts must be non-negative integers")
        if self.estimated_card_min > self.estimated_card_max:
            raise ValueError("estimated card minimum exceeds maximum")
        if self.estimated_call_min > self.estimated_call_max:
            raise ValueError("estimated call minimum exceeds maximum")
        if self.estimated_call_max > self.max_calls:
            raise ValueError("estimated calls exceed the hard ceiling")
        if self.chunk_count > _MAX_DOCUMENT_CHUNKS:
            raise ValueError("estimate chunk count exceeds the approved limit")
        if self.estimated_card_max > _MAX_PLAN_POINTS:
            raise ValueError("estimated cards exceed the approved limit")
        if self.max_calls > _MAX_AI_CALLS:
            raise ValueError("max_calls exceeds the hard ceiling")
        if (
            self.estimated_call_min,
            self.estimated_call_max,
        ) != _CALL_POLICY[normalized_level.value]:
            raise ValueError("estimated calls do not match the level policy")
        if not isinstance(self.requires_confirmation, bool):
            raise TypeError("requires_confirmation must be a boolean")
        if self.requires_confirmation is (
            normalized_level is IntelligenceLevel.FAST
        ):
            raise ValueError(
                "requires_confirmation does not match the level policy"
            )
        object.__setattr__(self, "level", normalized_level)

    def __repr__(self) -> str:
        return (
            "PlanEstimate("
            f"level={self.level.value!r}, chunks={self.chunk_count}, "
            f"cards={self.estimated_card_min}..{self.estimated_card_max}, "
            f"calls={self.estimated_call_min}..{self.estimated_call_max})"
        )


def _bounded_string_tuple(value, limit: int, name: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)):
        raise TypeError(f"{name} must be a sequence")
    try:
        result = tuple(islice(iter(value), limit + 1))
    except TypeError:
        raise TypeError(f"{name} must be iterable") from None
    if len(result) > limit:
        raise ValueError(f"{name} exceeds its approved limit")
    if not all(isinstance(item, str) and item for item in result):
        raise ValueError(f"{name} must contain non-empty strings")
    return result


def _bounded_block_kind_counts(value) -> dict[str, int]:
    if not isinstance(value, Mapping):
        raise TypeError("block_kind_counts must be a mapping")
    if len(value) > len(_BLOCK_KINDS):
        raise ValueError("block_kind_counts exceed the approved limit")
    try:
        keys = tuple(islice(iter(value), len(_BLOCK_KINDS) + 1))
    except TypeError:
        raise TypeError("block_kind_counts must be a mapping") from None
    if len(keys) > len(_BLOCK_KINDS) or len(keys) != len(value):
        raise ValueError("block_kind_counts exceed the approved limit")
    result = {}
    for key in keys:
        try:
            count = value[key]
        except Exception:
            raise ValueError("block_kind_counts could not be read safely") from None
        if (
            key not in _BLOCK_KINDS
            or isinstance(count, bool)
            or not isinstance(count, int)
            or count < 0
        ):
            raise ValueError("block_kind_counts contain unsupported values")
        result[key] = count
    if len(result) != len(keys):
        raise ValueError("block_kind_counts must contain unique keys")
    return result
