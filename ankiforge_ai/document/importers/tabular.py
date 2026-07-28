from __future__ import annotations

import csv
from pathlib import Path

from ..limits import DEFAULT_DOCUMENT_LIMITS
from ..models import BlockKind, DocumentSection
from ..source_labels import get_safe_source_label
from .base import DocumentImporter, ImportInspection
from .text import (
    DocumentParseBudget,
    block,
    import_error,
    location,
    make_document,
    read_text_bounded,
)


class TabularImporter(DocumentImporter):
    _TYPES = {".csv": ("csv", ","), ".tsv": ("tsv", "\t")}
    supported_extensions = tuple(_TYPES)

    def __init__(self, source_type="csv", delimiter=","):
        self.source_type = source_type
        self.delimiter = delimiter
        self.importer_id = source_type

    @classmethod
    def for_path(cls, path):
        source_type, delimiter = cls._TYPES.get(
            Path(path).suffix.casefold(), ("csv", ",")
        )
        return cls(source_type, delimiter)

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
        try:
            rows = []
            reader = csv.reader(text.splitlines(), delimiter=self.delimiter)
            for row_number, row in enumerate(reader, 1):
                if (
                    row_number > limits.max_table_rows + 1
                    or len(row) > limits.max_table_columns
                    or any(len(value) > limits.max_cell_chars for value in row)
                ):
                    raise import_error("table_too_large")
                rows.append(row)
        except (csv.Error, UnicodeError):
            raise import_error("malformed_file") from None
        if not rows or not any(value.strip() for row in rows for value in row):
            raise import_error("empty_file")
        header = "\t".join(rows[0])
        data = rows[1:]
        blocks = ()
        if data:
            value = "\n".join([header] + ["\t".join(row) for row in data])
            blocks = (
                block(
                    1,
                    BlockKind.TABLE,
                    value,
                    label,
                    line_start=1,
                    line_end=len(rows),
                    row_start=2,
                    row_end=len(rows),
                    metadata={"column_count": len(rows[0])},
                    budget=budget,
                ),
            )
        section = DocumentSection(
            section_id="section-00001",
            heading=header,
            location=location(label, row_start=1, row_end=len(rows)),
            blocks=blocks,
        )
        return make_document(path, self.source_type, text, (section,), limits=limits)
