from __future__ import annotations

import re

from ..limits import DEFAULT_DOCUMENT_LIMITS
from ..models import BlockKind, DocumentSection
from ..source_labels import get_safe_source_label
from .base import DocumentImporter, ImportInspection
from .text import block, location, make_document, read_text_bounded


_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_LIST = re.compile(r"^\s*(?:[-+*]|\d+[.)])\s+")
_TABLE_SEPARATOR = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*$")


def _table_cells(value):
    stripped = value.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def _validate_table_row(value, row_count, limits):
    cells = _table_cells(value)
    if (
        row_count > limits.max_table_rows
        or len(cells) > limits.max_table_columns
        or any(len(cell) > limits.max_cell_chars for cell in cells)
    ):
        from .text import import_error

        raise import_error("table_too_large")


def _frontmatter(lines):
    if not lines or lines[0].strip() != "---":
        return 0, None, ()
    closing = next(
        (number for number, value in enumerate(lines[1:51], 1) if value.strip() == "---"),
        None,
    )
    if closing is None:
        return 0, None, ()
    title = None
    tags = ()
    for value in lines[1:closing]:
        key, marker, raw = value.partition(":")
        if not marker:
            continue
        candidate = raw.strip().strip("'\"")
        if key.strip().casefold() == "title":
            if (
                candidate
                and len(candidate) <= 120
                and not any(char in candidate for char in "/\\\r\n")
                and not any(
                    secret in candidate.casefold()
                    for secret in ("api_key", "authorization", "bearer ")
                )
            ):
                title = candidate
        elif key.strip().casefold() == "tags":
            raw_tags = candidate.strip("[]")
            tags = tuple(
                tag.strip().strip("'\"")
                for tag in raw_tags.split(",")
                if tag.strip()
            )[:20]
    return closing + 1, title, tags


class MarkdownImporter(DocumentImporter):
    importer_id = "markdown"
    supported_extensions = (".md", ".markdown")

    def availability(self):
        return True

    def inspect(self, path, limits=DEFAULT_DOCUMENT_LIMITS):
        read_text_bounded(path, limits)
        return ImportInspection(
            importer_id=self.importer_id,
            source_label=get_safe_source_label(path),
            detected_file_type="markdown",
        )

    def import_document(self, path, limits=DEFAULT_DOCUMENT_LIMITS):
        text, _ = read_text_bounded(path, limits)
        label = get_safe_source_label(path)
        lines = text.splitlines()
        body_start, title, tags = _frontmatter(lines)
        sections = []
        current_blocks = []
        heading_levels = []
        current_heading = None
        current_path = ()
        block_index = 0

        def flush_section():
            nonlocal current_blocks
            if current_blocks:
                sections.append(
                    DocumentSection(
                        section_id=f"section-{len(sections) + 1:05d}",
                        heading=current_heading,
                        heading_path=current_path,
                        location=current_blocks[0].location,
                        blocks=tuple(current_blocks),
                    )
                )
                current_blocks = []

        index = body_start
        while index < len(lines):
            raw = lines[index]
            number = index + 1
            heading = _HEADING.match(raw)
            if heading:
                flush_section()
                level, value = len(heading.group(1)), heading.group(2).strip()
                heading_levels[level - 1 :] = []
                while len(heading_levels) < level - 1:
                    heading_levels.append("")
                heading_levels.append(value)
                current_heading = value
                current_path = tuple(part for part in heading_levels if part)
                block_index += 1
                current_blocks.append(
                    block(
                        block_index,
                        BlockKind.HEADING,
                        value,
                        label,
                        line_start=number,
                        line_end=number,
                        metadata={"level": level},
                    )
                )
                index += 1
                continue
            if raw.lstrip().startswith("```") or raw.lstrip().startswith("~~~"):
                marker = raw.lstrip()[:3]
                language = raw.lstrip()[3:].strip()
                start = number
                content = []
                index += 1
                while index < len(lines) and not lines[index].lstrip().startswith(marker):
                    content.append(lines[index])
                    index += 1
                end = min(index + 1, len(lines))
                if index < len(lines):
                    index += 1
                block_index += 1
                current_blocks.append(
                    block(
                        block_index,
                        BlockKind.CODE,
                        "\n".join(content),
                        label,
                        line_start=start,
                        line_end=end,
                        metadata={"language": language[:64]},
                    )
                )
                continue
            if _LIST.match(raw):
                start = number
                values = []
                while index < len(lines) and _LIST.match(lines[index]):
                    values.append(_LIST.sub("", lines[index], count=1).strip())
                    index += 1
                block_index += 1
                current_blocks.append(
                    block(
                        block_index,
                        BlockKind.LIST,
                        "\n".join(values),
                        label,
                        line_start=start,
                        line_end=index,
                    )
                )
                continue
            if (
                "|" in raw
                and index + 1 < len(lines)
                and _TABLE_SEPARATOR.match(lines[index + 1])
            ):
                start = number
                values = [raw]
                _validate_table_row(raw, 1, limits)
                index += 2
                while index < len(lines) and "|" in lines[index] and lines[index].strip():
                    _validate_table_row(lines[index], len(values) + 1, limits)
                    values.append(lines[index])
                    index += 1
                block_index += 1
                current_blocks.append(
                    block(
                        block_index,
                        BlockKind.TABLE,
                        "\n".join(values),
                        label,
                        line_start=start,
                        line_end=index,
                    )
                )
                continue
            if raw.strip():
                start = number
                values = [raw.rstrip()]
                index += 1
                while index < len(lines) and lines[index].strip():
                    if (
                        _HEADING.match(lines[index])
                        or _LIST.match(lines[index])
                        or lines[index].lstrip().startswith(("```", "~~~"))
                    ):
                        break
                    values.append(lines[index].rstrip())
                    index += 1
                block_index += 1
                current_blocks.append(
                    block(
                        block_index,
                        BlockKind.PARAGRAPH,
                        "\n".join(values),
                        label,
                        line_start=start,
                        line_end=start + len(values) - 1,
                    )
                )
                continue
            index += 1
        flush_section()
        if not sections:
            sections.append(
                DocumentSection(
                    section_id="section-00001",
                    heading=None,
                    location=location(label, line_start=body_start + 1),
                    blocks=(),
                )
            )
        metadata = {"tags": ", ".join(tags)} if tags else {}
        return make_document(
            path,
            "markdown",
            text,
            sections,
            title=title,
            metadata=metadata,
            limits=limits,
        )
