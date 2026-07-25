from __future__ import annotations

import json
from pathlib import Path

from ..limits import DEFAULT_DOCUMENT_LIMITS
from ..models import BlockKind, DocumentSection
from ..source_labels import get_safe_source_label
from .base import DocumentImporter, ImportInspection
from .text import block, import_error, location, make_document, read_text_bounded


def _load_json(value: str):
    def reject_constant(_value):
        raise ValueError("non-finite number")

    try:
        return json.loads(value, parse_constant=reject_constant)
    except (json.JSONDecodeError, RecursionError, ValueError):
        raise import_error("malformed_file") from None


def _scalar_text(value):
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value)


def _walk_scalars(value, max_depth):
    result = []
    stack = [("$", value, 1)]
    while stack:
        path, current, depth = stack.pop()
        if depth > max_depth:
            raise import_error("document_too_complex")
        if isinstance(current, dict):
            items = list(current.items())
            for key, child in reversed(items):
                segment = str(key).replace("\\", "\\\\").replace(".", "\\.")
                stack.append((f"{path}.{segment}", child, depth + 1))
        elif isinstance(current, list):
            for index in range(len(current) - 1, -1, -1):
                stack.append((f"{path}[{index}]", current[index], depth + 1))
        else:
            result.append((path, _scalar_text(current)))
    return result


class JsonDataImporter(DocumentImporter):
    _TYPES = {".json": "json", ".jsonl": "jsonl"}
    supported_extensions = tuple(_TYPES)

    def __init__(self, source_type="json"):
        self.source_type = source_type
        self.importer_id = source_type

    @classmethod
    def for_path(cls, path):
        return cls(cls._TYPES.get(Path(path).suffix.casefold(), "json"))

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
        if self.source_type == "jsonl":
            records = []
            for line_number, raw in enumerate(text.splitlines(), 1):
                if raw.strip():
                    records.append((line_number, _load_json(raw)))
        else:
            records = [(1, _load_json(text))]
        sections = []
        block_index = 0
        for record_number, (line_number, value) in enumerate(records, 1):
            values = _walk_scalars(value, limits.max_json_depth)
            blocks = []
            for path_value, scalar in values:
                block_index += 1
                blocks.append(
                    block(
                        block_index,
                        BlockKind.METADATA,
                        f"{path_value} = {scalar}",
                        label,
                        line_start=line_number,
                        line_end=line_number if self.source_type == "jsonl" else None,
                        section=path_value.rsplit(".", 1)[0],
                    )
                )
            heading = f"Record {record_number}" if self.source_type == "jsonl" else None
            sections.append(
                DocumentSection(
                    section_id=f"section-{record_number:05d}",
                    heading=heading,
                    heading_path=(heading,) if heading else (),
                    location=location(label, line_start=line_number),
                    blocks=tuple(blocks),
                )
            )
        return make_document(path, self.source_type, text, sections, limits=limits)
