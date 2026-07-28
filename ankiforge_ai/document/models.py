import math
import re
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Dict, Mapping, Optional, Tuple, Union

from .limits import DEFAULT_DOCUMENT_LIMITS
from .source_labels import get_safe_source_label


SafeScalar = Union[str, int, float, bool, None]
MAX_METADATA_KEY_CHARS = 120
MAX_METADATA_VALUE_CHARS = 2_000
MAX_METADATA_ITEMS = 128
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_SENSITIVE_METADATA_KEY = re.compile(
    r"(?:api.?key|password|secret|credential|access.?token|private.?key)",
    re.IGNORECASE,
)
_SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b", re.IGNORECASE),
    re.compile(
        r"\bbearer\s+[A-Za-z0-9._~+/=-]{12,}\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
)
_ABSOLUTE_WINDOWS_PATH = re.compile(r"^[A-Za-z]:[\\/]")


class BlockKind(str, Enum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    LIST_ITEM = "list_item"
    TABLE = "table"
    CODE = "code"
    FORMULA = "formula"
    QUOTE = "quote"
    CAPTION = "caption"
    TRANSCRIPT = "transcript"
    METADATA = "metadata"


def _is_absolute_or_traversal(value: str) -> bool:
    normalized = value.replace("\\", "/")
    return (
        normalized.startswith("/")
        or bool(_ABSOLUTE_WINDOWS_PATH.match(value))
        or any(part == ".." for part in normalized.split("/"))
    )


def _contains_sensitive_value(value: str) -> bool:
    return any(pattern.search(value) for pattern in _SENSITIVE_VALUE_PATTERNS)


def _validate_unicode(value: str) -> None:
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise ValueError("invalid Unicode in document string")


def _validate_identifier(value: str, name: str) -> None:
    if isinstance(value, str):
        _validate_unicode(value)
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise ValueError(f"{name} must be a safe stable identifier")


def _freeze_metadata(
    metadata: Optional[Mapping[str, SafeScalar]],
) -> Mapping[str, SafeScalar]:
    if metadata is None:
        return MappingProxyType({})
    if not isinstance(metadata, Mapping):
        raise TypeError("metadata must be a mapping")
    if len(metadata) > MAX_METADATA_ITEMS:
        raise ValueError("metadata has too many items")
    result: Dict[str, SafeScalar] = {}
    for key, value in metadata.items():
        if not isinstance(key, str):
            raise TypeError("metadata keys must be strings")
        _validate_unicode(key)
        if not key or len(key) > MAX_METADATA_KEY_CHARS:
            raise ValueError(
                f"metadata keys must be 1..{MAX_METADATA_KEY_CHARS} characters"
            )
        if _SENSITIVE_METADATA_KEY.search(key):
            raise ValueError("sensitive metadata keys are not allowed")
        if value is not None and not isinstance(value, (str, int, float, bool)):
            raise TypeError("metadata values must be safe scalars")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("metadata floats must be finite")
        if isinstance(value, str):
            _validate_unicode(value)
            if len(value) > MAX_METADATA_VALUE_CHARS:
                raise ValueError(
                    f"metadata strings must not exceed {MAX_METADATA_VALUE_CHARS}"
                )
            if _is_absolute_or_traversal(value):
                raise ValueError("absolute paths are not allowed in metadata")
            if _contains_sensitive_value(value):
                raise ValueError("credential-like metadata values are not allowed")
        elif value is not None:
            try:
                scalar_length = len(str(value))
            except ValueError as exc:
                raise ValueError("metadata scalar is too large") from exc
            if scalar_length > MAX_METADATA_VALUE_CHARS:
                raise ValueError(
                    f"metadata scalars must not exceed {MAX_METADATA_VALUE_CHARS}"
                )
        result[key] = value
    return MappingProxyType(result)


def _validate_label(value: Optional[str], name: str) -> None:
    if value is None:
        return
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")
    _validate_unicode(value)
    if value != get_safe_source_label(value):
        raise ValueError(f"{name} must be a safe source label")


@dataclass(frozen=True)
class SourceLocation:
    file_label: Optional[str] = None
    page: Optional[int] = None
    slide: Optional[int] = None
    sheet: Optional[str] = None
    row_start: Optional[int] = None
    row_end: Optional[int] = None
    cell_range: Optional[str] = None
    section: Optional[str] = None
    timestamp_start: Optional[float] = None
    timestamp_end: Optional[float] = None
    notebook_cell: Optional[int] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None

    def __post_init__(self) -> None:
        _validate_label(self.file_label, "file_label")
        for name in ("sheet", "cell_range", "section"):
            value = getattr(self, name)
            if value is not None:
                if not isinstance(value, str):
                    raise TypeError(f"{name} must be a string or None")
                _validate_unicode(value)
                if len(value) > MAX_METADATA_VALUE_CHARS:
                    raise ValueError(f"{name} is too long")
                if _is_absolute_or_traversal(value):
                    raise ValueError(f"{name} must not contain an absolute path")
        for name in (
            "page",
            "slide",
            "row_start",
            "row_end",
            "notebook_cell",
            "line_start",
            "line_end",
        ):
            value = getattr(self, name)
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value < 1
            ):
                raise ValueError(f"{name} must be a positive integer")
            if (
                value is not None
                and value > DEFAULT_DOCUMENT_LIMITS.max_text_chars
            ):
                raise ValueError(f"{name} exceeds MAX_TEXT_CHARS")
        for name in ("timestamp_start", "timestamp_end"):
            value = getattr(self, name)
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value < 0
            ):
                raise ValueError(f"{name} must be a non-negative finite number")
        for start_name, end_name, label in (
            ("row_start", "row_end", "row"),
            ("line_start", "line_end", "line"),
            ("timestamp_start", "timestamp_end", "timestamp"),
        ):
            start = getattr(self, start_name)
            end = getattr(self, end_name)
            if start is not None and end is not None and end < start:
                raise ValueError(f"{label} end must not precede start")

    def to_safe_dict(self) -> Dict[str, object]:
        return {
            "file_label": self.file_label,
            "page": self.page,
            "slide": self.slide,
            "sheet": self.sheet,
            "row_start": self.row_start,
            "row_end": self.row_end,
            "cell_range": self.cell_range,
            "section": self.section,
            "timestamp_start": self.timestamp_start,
            "timestamp_end": self.timestamp_end,
            "notebook_cell": self.notebook_cell,
            "line_start": self.line_start,
            "line_end": self.line_end,
        }


@dataclass(frozen=True)
class DocumentWarning:
    code: str
    severity: str
    message_key: str
    action_key: str
    location: Optional[SourceLocation] = None

    def __post_init__(self) -> None:
        _validate_identifier(self.code, "warning code")
        if self.severity not in {"info", "warning", "error"}:
            raise ValueError("warning severity must be info, warning, or error")
        for name in ("message_key", "action_key"):
            _validate_identifier(getattr(self, name), name)
        if self.location is not None and not isinstance(
            self.location, SourceLocation
        ):
            raise TypeError("warning location must be a SourceLocation or None")

    def to_safe_dict(self) -> Dict[str, object]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message_key": self.message_key,
            "action_key": self.action_key,
            "location": None if self.location is None else self.location.to_safe_dict(),
        }


@dataclass(frozen=True, repr=False)
class DocumentBlock:
    block_id: str
    kind: BlockKind
    text: str
    location: Optional[SourceLocation] = None
    metadata: Mapping[str, SafeScalar] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_identifier(self.block_id, "block_id")
        try:
            normalized_kind = BlockKind(self.kind)
        except (TypeError, ValueError) as exc:
            raise ValueError("kind must be a known BlockKind") from exc
        if not isinstance(self.text, str):
            raise TypeError("block text must be a string")
        _validate_unicode(self.text)
        if self.location is not None and not isinstance(
            self.location, SourceLocation
        ):
            raise TypeError("block location must be a SourceLocation or None")
        object.__setattr__(self, "kind", normalized_kind)
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))

    def __repr__(self) -> str:
        return (
            f"DocumentBlock(block_id={self.block_id!r}, kind={self.kind.value!r}, "
            f"char_count={len(self.text)})"
        )

    def to_safe_dict(self) -> Dict[str, object]:
        return {
            "block_id": self.block_id,
            "kind": self.kind.value,
            "text": self.text,
            "location": None if self.location is None else self.location.to_safe_dict(),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, repr=False)
class DocumentSection:
    section_id: str
    heading: Optional[str]
    heading_path: Tuple[str, ...] = ()
    location: Optional[SourceLocation] = None
    blocks: Tuple[DocumentBlock, ...] = ()

    def __post_init__(self) -> None:
        _validate_identifier(self.section_id, "section_id")
        if self.heading is not None and not isinstance(self.heading, str):
            raise TypeError("section heading must be a string or None")
        if self.heading is not None:
            _validate_unicode(self.heading)
        if self.location is not None and not isinstance(
            self.location, SourceLocation
        ):
            raise TypeError("section location must be a SourceLocation or None")
        heading_path = tuple(self.heading_path)
        if not all(isinstance(part, str) for part in heading_path):
            raise TypeError("heading_path entries must be strings")
        for part in heading_path:
            _validate_unicode(part)
        blocks = tuple(self.blocks)
        if not all(isinstance(block, DocumentBlock) for block in blocks):
            raise TypeError("section blocks must be DocumentBlock instances")
        object.__setattr__(self, "heading_path", heading_path)
        object.__setattr__(self, "blocks", blocks)

    def __repr__(self) -> str:
        return (
            f"DocumentSection(section_id={self.section_id!r}, "
            f"blocks={len(self.blocks)})"
        )

    def to_safe_dict(self) -> Dict[str, object]:
        return {
            "section_id": self.section_id,
            "heading": self.heading,
            "heading_path": list(self.heading_path),
            "location": None if self.location is None else self.location.to_safe_dict(),
            "blocks": [block.to_safe_dict() for block in self.blocks],
        }


@dataclass(frozen=True, repr=False)
class DocumentIR:
    schema_version: int
    document_id: str
    title: str
    language_hint: Optional[str]
    source_type: str
    source_label: str
    metadata: Mapping[str, SafeScalar] = field(default_factory=dict)
    sections: Tuple[DocumentSection, ...] = ()
    warnings: Tuple[DocumentWarning, ...] = ()
    original_char_count: int = 0
    extracted_char_count: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))
        object.__setattr__(self, "sections", tuple(self.sections))
        object.__setattr__(self, "warnings", tuple(self.warnings))
        validate_document_ir(self)

    def __repr__(self) -> str:
        kinds = ",".join(sorted(count_blocks_by_kind(self)))
        return (
            f"DocumentIR(document_id={self.document_id!r}, "
            f"source_label={self.source_label!r}, sections={len(self.sections)}, "
            f"blocks={sum(len(section.blocks) for section in self.sections)}, "
            f"kinds={kinds!r}, warnings={len(self.warnings)})"
        )

    def to_safe_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "document_id": self.document_id,
            "title": self.title,
            "language_hint": self.language_hint,
            "source_type": self.source_type,
            "source_label": self.source_label,
            "metadata": dict(self.metadata),
            "sections": [section.to_safe_dict() for section in self.sections],
            "warnings": [warning.to_safe_dict() for warning in self.warnings],
            "original_char_count": self.original_char_count,
            "extracted_char_count": self.extracted_char_count,
        }


def validate_document_ir(
    document: DocumentIR,
    *,
    max_text_chars: int = DEFAULT_DOCUMENT_LIMITS.max_text_chars,
    max_document_blocks: int = DEFAULT_DOCUMENT_LIMITS.max_document_blocks,
) -> None:
    if not isinstance(document, DocumentIR):
        raise TypeError("document must be a DocumentIR")
    if document.schema_version != 1:
        raise ValueError("unsupported schema_version")
    _validate_identifier(document.document_id, "document_id")
    if not isinstance(document.title, str):
        raise TypeError("title must be a string")
    _validate_unicode(document.title)
    if document.language_hint is not None and not isinstance(
        document.language_hint, str
    ):
        raise TypeError("language_hint must be a string or None")
    if document.language_hint is not None:
        _validate_unicode(document.language_hint)
    _validate_identifier(document.source_type, "source_type")
    _validate_label(document.source_label, "source_label")
    if not all(isinstance(section, DocumentSection) for section in document.sections):
        raise TypeError("sections must contain DocumentSection instances")
    if not all(isinstance(warning, DocumentWarning) for warning in document.warnings):
        raise TypeError("warnings must contain DocumentWarning instances")
    for name in ("original_char_count", "extracted_char_count"):
        value = getattr(document, name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{name} must be a non-negative integer")
        if value > max_text_chars:
            raise ValueError(f"{name} exceeds MAX_TEXT_CHARS")

    section_ids = set()
    block_ids = set()
    block_count = 0
    text_chars = (
        len(document.title)
        + len(document.source_type)
        + len(document.source_label)
        + (len(document.language_hint) if document.language_hint else 0)
        + _metadata_char_count(document.metadata)
    )
    for section in document.sections:
        if section.section_id in section_ids:
            raise ValueError(f"duplicate section_id: {section.section_id}")
        section_ids.add(section.section_id)
        text_chars += len(section.heading) if section.heading else 0
        text_chars += sum(len(part) for part in section.heading_path)
        text_chars += _location_char_count(section.location)
        for block in section.blocks:
            if block.block_id in block_ids:
                raise ValueError(f"duplicate block_id: {block.block_id}")
            block_ids.add(block.block_id)
            block_count += 1
            text_chars += len(block.text)
            text_chars += _metadata_char_count(block.metadata)
            text_chars += _location_char_count(block.location)
    for warning in document.warnings:
        text_chars += (
            len(warning.code)
            + len(warning.severity)
            + len(warning.message_key)
            + len(warning.action_key)
            + _location_char_count(warning.location)
        )
    if block_count > max_document_blocks:
        raise ValueError("document exceeds MAX_DOCUMENT_BLOCKS")
    if text_chars > max_text_chars or document.extracted_char_count > max_text_chars:
        raise ValueError("document exceeds MAX_TEXT_CHARS")


def count_blocks_by_kind(document: DocumentIR) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for section in document.sections:
        for block in section.blocks:
            counts[block.kind.value] = counts.get(block.kind.value, 0) + 1
    return dict(sorted(counts.items()))


def _metadata_char_count(metadata: Mapping[str, SafeScalar]) -> int:
    total = 0
    for key, value in metadata.items():
        total += len(key)
        if value is not None:
            total += len(str(value))
    return total


def _location_char_count(location: Optional[SourceLocation]) -> int:
    if location is None:
        return 0
    return sum(
        len(value)
        for value in (
            location.file_label,
            location.sheet,
            location.cell_range,
            location.section,
        )
        if value is not None
    )
