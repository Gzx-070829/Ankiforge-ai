from __future__ import annotations

import re
from dataclasses import dataclass

from ..limits import DEFAULT_DOCUMENT_LIMITS
from ..models import BlockKind, DocumentSection
from ..source_labels import get_safe_source_label
from .base import DocumentImporter, ImportInspection
from .text import (
    DocumentParseBudget,
    block,
    location,
    make_document,
    read_text_bounded,
)


_TIMING = re.compile(
    r"(?P<start>\d{1,2}:\d{2}(?::\d{2})?[,.]\d{3})\s*-->\s*"
    r"(?P<end>\d{1,2}:\d{2}(?::\d{2})?[,.]\d{3})"
)


def _seconds(value):
    parts = value.replace(",", ".").split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])


@dataclass
class _Caption:
    start: float
    end: float
    text: str
    line_start: int
    line_end: int


class SubtitleImporter(DocumentImporter):
    _TYPES = {".srt": "srt", ".vtt": "vtt"}
    supported_extensions = tuple(_TYPES)

    def __init__(self, source_type="srt"):
        self.source_type = source_type
        self.importer_id = source_type

    @classmethod
    def for_path(cls, path):
        from pathlib import Path

        return cls(cls._TYPES.get(Path(path).suffix.casefold(), "srt"))

    def availability(self):
        return True

    def inspect(self, path, limits=DEFAULT_DOCUMENT_LIMITS):
        read_text_bounded(path, limits)
        return ImportInspection(
            importer_id=self.importer_id,
            source_label=get_safe_source_label(path),
            detected_file_type=self.source_type,
        )

    def import_document(self, path, limits=DEFAULT_DOCUMENT_LIMITS):
        text, _ = read_text_bounded(path, limits)
        label = get_safe_source_label(path)
        budget = DocumentParseBudget(limits)
        budget.consume_section()
        lines = text.splitlines()
        captions = []
        index = 0
        while index < len(lines):
            timing = _TIMING.search(lines[index])
            if timing is None:
                index += 1
                continue
            start_line = index + 1
            index += 1
            content = []
            while index < len(lines) and lines[index].strip():
                content.append(lines[index].strip())
                index += 1
            if content:
                budget.ensure_blocks(len(captions) + 1)
                captions.append(
                    _Caption(
                        _seconds(timing.group("start")),
                        _seconds(timing.group("end")),
                        "\n".join(content),
                        start_line,
                        index,
                    )
                )
        groups = []
        for caption in captions:
            if groups and caption.start - groups[-1][-1].end <= 1.0:
                groups[-1].append(caption)
            else:
                groups.append([caption])
        blocks = tuple(
            block(
                number,
                BlockKind.TRANSCRIPT,
                "\n".join(item.text for item in group),
                label,
                line_start=group[0].line_start,
                line_end=group[-1].line_end,
                timestamp_start=group[0].start,
                timestamp_end=group[-1].end,
                budget=budget,
            )
            for number, group in enumerate(groups, 1)
        )
        section = DocumentSection(
            section_id="section-00001",
            heading=None,
            location=blocks[0].location if blocks else location(label, line_start=1),
            blocks=blocks,
        )
        return make_document(path, self.source_type, text, (section,), limits=limits)
