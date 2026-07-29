"""Immutable structural chunk models."""

import re
from dataclasses import dataclass
from itertools import islice

from ...document import (
    BlockKind,
    DEFAULT_DOCUMENT_LIMITS,
    SourceLocation,
)


_SAFE_CHUNK_ID = re.compile(r"^chunk-[a-f0-9]{16}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_ABSOLUTE_WINDOWS_PATH = re.compile(r"^[A-Za-z]:[\\/]")
MAX_CHUNK_CHARS = 12_000
MAX_HEADING_CHARS = 2_000


@dataclass(frozen=True, repr=False)
class DocumentChunk:
    chunk_id: str
    document_id: str
    sequence: int
    section_id: str
    heading_path: tuple[str, ...]
    text: str
    block_ids: tuple[str, ...]
    block_kinds: tuple[BlockKind, ...]
    source_locations: tuple[SourceLocation, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.chunk_id, str) or not _SAFE_CHUNK_ID.fullmatch(
            self.chunk_id
        ):
            raise ValueError("chunk_id must be a safe stable identifier")
        _validate_id(self.document_id, "document_id")
        _validate_id(self.section_id, "section_id")
        if (
            isinstance(self.sequence, bool)
            or not isinstance(self.sequence, int)
            or self.sequence < 0
        ):
            raise ValueError("chunk sequence must be a non-negative integer")
        if not isinstance(self.text, str):
            raise TypeError("chunk text must be a string")
        _validate_unicode(self.text)
        if len(self.text) > MAX_CHUNK_CHARS:
            raise ValueError("chunk text exceeds MAX_CHUNK_CHARS")
        heading_path = _bounded_tuple(
            self.heading_path,
            DEFAULT_DOCUMENT_LIMITS.max_document_blocks,
            "heading_path",
        )
        for part in heading_path:
            if (
                not isinstance(part, str)
                or not part
                or len(part) > MAX_HEADING_CHARS
                or _looks_like_path(part)
            ):
                raise ValueError("heading_path must contain safe bounded labels")
            _validate_unicode(part)
        block_ids = _bounded_tuple(
            self.block_ids,
            DEFAULT_DOCUMENT_LIMITS.max_document_blocks,
            "block_ids",
        )
        if not block_ids:
            raise ValueError("block_ids must not be empty")
        for block_id in block_ids:
            _validate_id(block_id, "block_id")
        raw_kinds = _bounded_tuple(
            self.block_kinds,
            DEFAULT_DOCUMENT_LIMITS.max_document_blocks,
            "block_kinds",
        )
        try:
            block_kinds = tuple(BlockKind(kind) for kind in raw_kinds)
        except (TypeError, ValueError):
            raise ValueError("block_kinds must contain known block kinds") from None
        if len(block_kinds) != len(block_ids):
            raise ValueError("block_kinds must align with block_ids")
        locations = _bounded_tuple(
            self.source_locations,
            DEFAULT_DOCUMENT_LIMITS.max_document_blocks,
            "source_locations",
        )
        if not all(isinstance(location, SourceLocation) for location in locations):
            raise TypeError("source_locations must contain SourceLocation instances")
        if len(set(locations)) != len(locations):
            raise ValueError("source_locations must be unique")
        object.__setattr__(self, "heading_path", heading_path)
        object.__setattr__(self, "block_ids", block_ids)
        object.__setattr__(self, "block_kinds", block_kinds)
        object.__setattr__(self, "source_locations", locations)

    @property
    def char_count(self) -> int:
        return len(self.text)

    def __repr__(self) -> str:
        return (
            "DocumentChunk("
            f"chunk_id={self.chunk_id!r}, document_id={self.document_id!r}, "
            f"sequence={self.sequence}, section_id={self.section_id!r}, "
            f"blocks={len(self.block_ids)}, chars={self.char_count})"
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


def _validate_id(value, name: str) -> None:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise ValueError(f"{name} must be a safe stable identifier")
    _validate_unicode(value)


def _validate_unicode(value: str) -> None:
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise ValueError("invalid Unicode in chunk value")


def _looks_like_path(value: str) -> bool:
    normalized = value.replace("\\", "/")
    return (
        normalized.startswith("/")
        or bool(_ABSOLUTE_WINDOWS_PATH.match(value))
        or any(part == ".." for part in normalized.split("/"))
    )
