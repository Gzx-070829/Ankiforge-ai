"""Structure-first grouping and bounded secondary splitting."""

import hashlib
import re
from dataclasses import dataclass

from ankiforge_ai.document import (
    BlockKind,
    DocumentBlock,
    DocumentIR,
    DocumentSection,
    SourceLocation,
)

from .models import DocumentChunk
from .table_chunker import iter_table_text
from .token_budget import _validate_budget, iter_text_to_budget
from .transcript_chunker import iter_transcript_text


TARGET_CHUNK_CHARS = 6_000
MAX_CHUNK_CHARS = 12_000
MAX_DOCUMENT_CHUNKS = 48
_ABSOLUTE_WINDOWS_PATH = re.compile(r"^[A-Za-z]:[\\/]")


@dataclass(frozen=True)
class _Unit:
    blocks: tuple[DocumentBlock, ...]
    text: str
    source_locations: tuple[SourceLocation, ...]
    boundary: tuple[object, ...]


def chunk_document(
    document: DocumentIR,
    *,
    target_chars: int = TARGET_CHUNK_CHARS,
    max_chars: int = MAX_CHUNK_CHARS,
    max_chunks: int = MAX_DOCUMENT_CHUNKS,
) -> tuple[DocumentChunk, ...]:
    if not isinstance(document, DocumentIR):
        raise TypeError("document must be a DocumentIR")
    _validate_budget(target_chars, max_chars)
    if max_chars > MAX_CHUNK_CHARS:
        raise ValueError("max_chars must not exceed MAX_CHUNK_CHARS")
    if (
        isinstance(max_chunks, bool)
        or not isinstance(max_chunks, int)
        or not 1 <= max_chunks <= MAX_DOCUMENT_CHUNKS
    ):
        raise ValueError("max_chunks must be within MAX_DOCUMENT_CHUNKS")

    chunks = []
    for section in document.sections:
        prefix, safe_heading_path = _section_prefix(section)
        if len(prefix) >= max_chars:
            raise ValueError("section heading exceeds MAX_CHUNK_CHARS")
        content_target = max(1, target_chars - len(prefix))
        content_max = max_chars - len(prefix)
        units = _section_units(section)
        grouped = _group_units(
            units,
            content_target=content_target,
            content_max=content_max,
        )
        for unit_group in grouped:
            if len(unit_group) == 1 and len(unit_group[0].text) > content_max:
                drafts = _iter_oversized_unit(
                    unit_group[0],
                    prefix=prefix,
                    heading_path=safe_heading_path,
                    section_id=section.section_id,
                    target_chars=content_target,
                    max_chars=content_max,
                )
            else:
                drafts = iter(
                    (
                        (
                            prefix
                            + "\n\n".join(unit.text for unit in unit_group),
                            tuple(
                                block
                                for unit in unit_group
                                for block in unit.blocks
                            ),
                            _unique_locations(
                                location
                                for unit in unit_group
                                for location in unit.source_locations
                            ),
                            safe_heading_path,
                            section.section_id,
                        ),
                    )
                )
            for text, blocks, locations, heading_path, section_id in drafts:
                if len(chunks) >= max_chunks:
                    raise ValueError("document exceeds MAX_DOCUMENT_CHUNKS")
                sequence = len(chunks)
                digest_input = "\x1f".join(
                    (
                        document.document_id,
                        section_id,
                        str(sequence),
                        *(block.block_id for block in blocks),
                    )
                ).encode("utf-8")
                chunk_id = "chunk-" + hashlib.sha256(digest_input).hexdigest()[:16]
                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        document_id=document.document_id,
                        sequence=sequence,
                        section_id=section_id,
                        heading_path=heading_path,
                        text=text,
                        block_ids=tuple(block.block_id for block in blocks),
                        block_kinds=tuple(block.kind for block in blocks),
                        source_locations=locations,
                    )
                )
    return tuple(chunks)


def _section_units(section: DocumentSection) -> tuple[_Unit, ...]:
    units = []
    blocks = section.blocks
    index = 0
    while index < len(blocks):
        block = blocks[index]
        if (
            block.kind is BlockKind.PARAGRAPH
            and index + 1 < len(blocks)
            and blocks[index + 1].kind in {BlockKind.CODE, BlockKind.FORMULA}
        ):
            paired = (block, blocks[index + 1])
            units.append(_unit(paired, section.location))
            index += 2
            continue
        if block.kind is BlockKind.LIST_ITEM:
            end = index + 1
            while end < len(blocks) and blocks[end].kind is BlockKind.LIST_ITEM:
                end += 1
            units.append(_unit(tuple(blocks[index:end]), section.location))
            index = end
            continue
        units.append(_unit((block,), section.location))
        index += 1
    return tuple(units)


def _unit(
    blocks: tuple[DocumentBlock, ...],
    section_location: SourceLocation | None,
) -> _Unit:
    locations = _unique_locations(
        block.location or section_location
        for block in blocks
        if block.location is not None or section_location is not None
    )
    location = locations[0] if locations else section_location
    return _Unit(
        blocks=blocks,
        text=(
            blocks[0].text
            if len(blocks) == 1
            else "\n\n".join(block.text for block in blocks)
        ),
        source_locations=locations,
        boundary=_boundary_key(location),
    )


def _group_units(
    units: tuple[_Unit, ...],
    *,
    content_target: int,
    content_max: int,
) -> tuple[tuple[_Unit, ...], ...]:
    groups = []
    current = []
    current_length = 0
    current_has_table = False
    for unit in units:
        standalone = any(block.kind is BlockKind.TABLE for block in unit.blocks)
        addition = len(unit.text) + (2 if current else 0)
        same_boundary = not current or current[-1].boundary == unit.boundary
        if (
            current
            and (
                standalone
                or current_has_table
                or not same_boundary
                or current_length + addition > content_target
                or current_length + addition > content_max
            )
        ):
            groups.append(tuple(current))
            current = []
            current_length = 0
            current_has_table = False
            addition = len(unit.text)
        current.append(unit)
        current_length += addition
        current_has_table = current_has_table or standalone
        if standalone or len(unit.text) > content_max:
            groups.append(tuple(current))
            current = []
            current_length = 0
            current_has_table = False
    if current:
        groups.append(tuple(current))
    return tuple(groups)


def _iter_oversized_unit(
    unit: _Unit,
    *,
    prefix: str,
    heading_path: tuple[str, ...],
    section_id: str,
    target_chars: int,
    max_chars: int,
):
    blocks = unit.blocks
    if len(blocks) == 1 and blocks[0].kind is BlockKind.TABLE:
        pieces = iter_table_text(
            unit.text, target_chars=target_chars, max_chars=max_chars
        )
    elif len(blocks) == 1 and blocks[0].kind is BlockKind.TRANSCRIPT:
        pieces = iter_transcript_text(
            unit.text, target_chars=target_chars, max_chars=max_chars
        )
    elif (
        len(blocks) == 2
        and blocks[0].kind is BlockKind.PARAGRAPH
        and blocks[1].kind in {BlockKind.CODE, BlockKind.FORMULA}
    ):
        context = blocks[0].text + "\n\n"
        if len(context) < max_chars:
            content_pieces = iter_text_to_budget(
                blocks[1].text,
                target_chars=max(1, target_chars - len(context)),
                max_chars=max_chars - len(context),
            )
            pieces = (context + piece for piece in content_pieces)
        else:
            pieces = iter_text_to_budget(
                unit.text, target_chars=target_chars, max_chars=max_chars
            )
    else:
        pieces = iter_text_to_budget(
            unit.text, target_chars=target_chars, max_chars=max_chars
        )
    for piece in pieces:
        yield (
            prefix + piece,
            blocks,
            unit.source_locations,
            heading_path,
            section_id,
        )


def _section_prefix(
    section: DocumentSection,
) -> tuple[str, tuple[str, ...]]:
    candidates = section.heading_path or (
        (section.heading,) if section.heading else ()
    )
    safe_parts = tuple(
        part.strip()
        for part in candidates
        if part.strip() and not _looks_like_path(part)
    )
    if not safe_parts:
        return "", ()
    return "# " + " > ".join(safe_parts) + "\n\n", safe_parts


def _looks_like_path(value: str) -> bool:
    normalized = value.replace("\\", "/")
    return (
        normalized.startswith("/")
        or bool(_ABSOLUTE_WINDOWS_PATH.match(value))
        or any(part == ".." for part in normalized.split("/"))
    )


def _boundary_key(location: SourceLocation | None) -> tuple[object, ...]:
    if location is None:
        return ()
    return (
        location.file_label,
        location.page,
        location.slide,
        location.sheet,
        location.row_start,
        location.row_end,
        location.section,
        location.cell_range,
        location.timestamp_start,
        location.timestamp_end,
        location.notebook_cell,
        location.line_start,
        location.line_end,
    )


def _unique_locations(locations) -> tuple[SourceLocation, ...]:
    result = []
    seen = set()
    for location in locations:
        if location is not None and location not in seen:
            seen.add(location)
            result.append(location)
    return tuple(result)
