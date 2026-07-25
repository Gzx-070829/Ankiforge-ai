from __future__ import annotations

from pathlib import Path

from ..limits import DEFAULT_DOCUMENT_LIMITS
from ..models import BlockKind, DocumentSection
from ..source_labels import get_safe_source_label
from .base import DocumentImporter, ImportInspection
from .text import block, location, make_document, read_text_bounded


_TYPES = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".rs": "rust",
    ".go": "go",
    ".sql": "sql",
    ".sh": "shell",
    ".ps1": "powershell",
}


class CodeTextImporter(DocumentImporter):
    supported_extensions = tuple(_TYPES)

    def __init__(self, source_type="python"):
        self.source_type = source_type
        self.importer_id = source_type

    @classmethod
    def for_path(cls, path):
        return cls(_TYPES.get(Path(path).suffix.casefold(), "text"))

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
        lines = text.splitlines()
        groups = []
        start = None
        content = []
        for number, value in enumerate(lines + [""], 1):
            if value.strip():
                if start is None:
                    start = number
                content.append(value)
            elif content:
                groups.append((start, number - 1, "\n".join(content)))
                start = None
                content = []
        blocks = tuple(
            block(
                index,
                BlockKind.CODE,
                value,
                label,
                line_start=start_line,
                line_end=end_line,
                metadata={"language": self.source_type},
            )
            for index, (start_line, end_line, value) in enumerate(groups, 1)
        )
        section = DocumentSection(
            section_id="section-00001",
            heading=None,
            location=blocks[0].location if blocks else location(label, line_start=1),
            blocks=blocks,
        )
        return make_document(path, self.source_type, text, (section,), limits=limits)
