"""Safe, honest source evidence carried through the review workflow."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Mapping, Optional

from .limits import DEFAULT_DOCUMENT_LIMITS
from .models import SourceLocation
from .source_labels import get_safe_source_label


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_SAFE_RANGE = re.compile(r"^[1-9]\d*(?:-[1-9]\d*)?$")
_ABSOLUTE_WINDOWS_PATH = re.compile(r"^[A-Za-z]:[\\/]")
_WHITESPACE = re.compile(r"\s+")
_LOCATOR_KINDS = frozenset(
    {
        "document",
        "section",
        "page",
        "slide",
        "sheet",
        "row",
        "line",
        "cell",
        "block",
        "timestamp",
    }
)
MAX_LOCATOR_VALUE_CHARS = 160
MAX_DISPLAY_LABEL_CHARS = 200


@dataclass(frozen=True, repr=False)
class SourceSpan:
    """Content-free source identity with only importer-supported precision."""

    document_id: str
    source_label: str
    locator_kind: str = "document"
    locator_value: Optional[str] = None
    block_id: Optional[str] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    display_label: Optional[str] = None

    def __post_init__(self) -> None:
        _validate_id(self.document_id, "document_id")
        safe_label = get_safe_source_label(self.source_label)
        if not isinstance(self.source_label, str):
            raise TypeError("source_label must be a string")
        if self.locator_kind not in _LOCATOR_KINDS:
            raise ValueError("locator_kind is unsupported")
        locator_value = self.locator_value
        if locator_value is None:
            if self.locator_kind != "document":
                raise ValueError("non-document source spans require a locator value")
            locator_value = self.document_id
        locator_value = _safe_bounded_text(
            locator_value,
            "locator_value",
            MAX_LOCATOR_VALUE_CHARS,
        )
        _validate_locator_value(self.locator_kind, locator_value)
        if self.block_id is not None:
            _validate_id(self.block_id, "block_id")
        _validate_offsets(self.char_start, self.char_end)
        display_label = self.display_label
        if display_label is None:
            display_label = _default_display_label(
                safe_label,
                self.locator_kind,
                locator_value,
            )
        display_label = _safe_bounded_text(
            display_label,
            "display_label",
            MAX_DISPLAY_LABEL_CHARS,
        )
        object.__setattr__(self, "source_label", safe_label)
        object.__setattr__(self, "locator_value", locator_value)
        object.__setattr__(self, "display_label", display_label)

    def __repr__(self) -> str:
        return (
            "SourceSpan("
            f"document_id={self.document_id!r}, locator_kind={self.locator_kind!r}, "
            f"block_id={self.block_id!r}, offsets={self.has_offsets})"
        )

    @property
    def has_offsets(self) -> bool:
        return self.char_start is not None

    def to_safe_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "source_label": self.source_label,
            "locator_kind": self.locator_kind,
            "locator_value": self.locator_value,
            "block_id": self.block_id,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "display_label": self.display_label,
        }

    @classmethod
    def from_safe_dict(cls, value: Mapping[str, object]) -> "SourceSpan":
        if not isinstance(value, Mapping):
            raise TypeError("source span payload must be a mapping")
        expected = {
            "document_id",
            "source_label",
            "locator_kind",
            "locator_value",
            "block_id",
            "char_start",
            "char_end",
            "display_label",
        }
        if set(value) != expected:
            raise ValueError("source span payload fields are incomplete or unknown")
        return cls(**{name: value[name] for name in expected})


def source_span_from_chunk(
    chunk,
    *,
    source_label: str,
    char_start: Optional[int] = None,
    char_end: Optional[int] = None,
) -> SourceSpan:
    """Normalize one chunk without fabricating precision across its boundaries."""

    document_id = getattr(chunk, "document_id", None)
    block_ids = tuple(getattr(chunk, "block_ids", ()))
    locations = tuple(getattr(chunk, "source_locations", ()))
    _validate_id(document_id, "document_id")
    if not block_ids or not all(
        isinstance(item, str) and _SAFE_ID.fullmatch(item) for item in block_ids
    ):
        raise ValueError("chunk must contain safe block IDs")
    if not all(isinstance(item, SourceLocation) for item in locations):
        raise TypeError("chunk source locations must contain SourceLocation values")
    block_id = block_ids[0] if len(block_ids) == 1 else None
    if len(locations) == 1:
        locator_kind, locator_value = _locator_from_location(locations[0])
        if locator_kind == "document":
            locator_value = document_id
    elif not locations and block_id is not None:
        locator_kind, locator_value = "block", block_id
    else:
        locator_kind, locator_value = "document", document_id
    return SourceSpan(
        document_id=document_id,
        source_label=source_label,
        locator_kind=locator_kind,
        locator_value=locator_value,
        block_id=block_id,
        char_start=char_start,
        char_end=char_end,
    )


def _locator_from_location(location: SourceLocation) -> tuple[str, str]:
    if location.page is not None:
        return "page", str(location.page)
    if location.slide is not None:
        return "slide", str(location.slide)
    if location.sheet is not None:
        if location.cell_range:
            return "cell", location.cell_range
        if location.row_start is not None:
            return "row", _range_value(location.row_start, location.row_end)
        return "sheet", location.sheet
    if location.notebook_cell is not None:
        return "cell", str(location.notebook_cell)
    if location.timestamp_start is not None:
        return "timestamp", _timestamp_value(location.timestamp_start)
    if location.line_start is not None:
        return "line", _range_value(location.line_start, location.line_end)
    if location.section:
        return "section", location.section
    return "document", "document"


def _range_value(start: int, end: Optional[int]) -> str:
    return str(start) if end is None or end == start else f"{start}-{end}"


def _timestamp_value(value: float) -> str:
    seconds = max(0, int(math.floor(value)))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    return f"{minutes:02}:{seconds:02}"


def _validate_id(value, name: str) -> None:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise ValueError(f"{name} must be a safe stable identifier")


def _safe_bounded_text(value, name: str, limit: int) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    normalized = _WHITESPACE.sub(" ", value).strip()
    if not normalized or len(normalized) > limit or _looks_like_path(normalized):
        raise ValueError(f"{name} must be safe and bounded")
    if any(0xD800 <= ord(character) <= 0xDFFF for character in normalized):
        raise ValueError(f"{name} contains invalid Unicode")
    return normalized


def _looks_like_path(value: str) -> bool:
    normalized = value.replace("\\", "/")
    return (
        normalized.startswith("/")
        or bool(_ABSOLUTE_WINDOWS_PATH.match(value))
        or any(part == ".." for part in normalized.split("/"))
    )


def _validate_locator_value(kind: str, value: str) -> None:
    if kind in {"page", "slide"}:
        if not value.isdigit() or int(value) < 1:
            raise ValueError(f"{kind} locator must be a positive integer")
    elif kind in {"row", "line"}:
        match = _SAFE_RANGE.fullmatch(value)
        if match is None:
            raise ValueError(f"{kind} locator must be a positive range")
        parts = tuple(int(item) for item in value.split("-"))
        if len(parts) == 2 and parts[1] < parts[0]:
            raise ValueError(f"{kind} locator end must not precede start")


def _validate_offsets(start: Optional[int], end: Optional[int]) -> None:
    if (start is None) != (end is None):
        raise ValueError("character offsets must be provided together")
    if start is None:
        return
    if (
        isinstance(start, bool)
        or not isinstance(start, int)
        or isinstance(end, bool)
        or not isinstance(end, int)
        or start < 0
        or end <= start
        or end > DEFAULT_DOCUMENT_LIMITS.max_text_chars
    ):
        raise ValueError("character offsets are invalid")


def _default_display_label(source_label: str, kind: str, value: str) -> str:
    if kind in {"document", "block"}:
        return source_label
    labels = {
        "page": "page",
        "slide": "slide",
        "sheet": "sheet",
        "row": "rows" if "-" in value else "row",
        "line": "lines" if "-" in value else "line",
        "cell": "cell",
        "section": "section",
        "timestamp": "time",
    }
    rendered = value.replace("-", "–") if kind in {"row", "line"} else value
    return f"{source_label} · {labels[kind]} {rendered}"


__all__ = ["SourceSpan", "source_span_from_chunk"]
