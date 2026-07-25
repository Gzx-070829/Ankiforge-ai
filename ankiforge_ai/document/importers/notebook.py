from __future__ import annotations

from ..limits import DEFAULT_DOCUMENT_LIMITS
from ..models import BlockKind, DocumentSection
from ..source_labels import get_safe_source_label
from .base import DocumentImporter, ImportInspection
from .json_data import _load_json, _walk_scalars
from .text import (
    block,
    import_error,
    location,
    make_document,
    read_text_bounded,
    warning,
)


def _source_text(value):
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return "".join(value)
    if isinstance(value, str):
        return value
    return ""


class NotebookImporter(DocumentImporter):
    importer_id = "ipynb"
    supported_extensions = (".ipynb",)

    def availability(self):
        return True

    def inspect(self, path, limits=DEFAULT_DOCUMENT_LIMITS):
        read_text_bounded(path, limits)
        return ImportInspection(
            importer_id=self.importer_id,
            source_label=get_safe_source_label(path),
            detected_file_type="ipynb",
        )

    def import_document(self, path, limits=DEFAULT_DOCUMENT_LIMITS):
        text, _ = read_text_bounded(path, limits)
        label = get_safe_source_label(path)
        value = _load_json(text)
        _walk_scalars(value, limits.max_json_depth)
        if not isinstance(value, dict) or not isinstance(value.get("cells"), list):
            raise import_error("malformed_file")
        sections = []
        warnings = []
        warning_codes = set()
        block_index = 0
        output_chars = 0
        for cell_number, cell in enumerate(value["cells"], 1):
            if not isinstance(cell, dict):
                raise import_error("malformed_file")
            kind = cell.get("cell_type")
            source = _source_text(cell.get("source")).strip()
            blocks = []
            if source and kind in {"markdown", "raw", "code"}:
                block_index += 1
                blocks.append(
                    block(
                        block_index,
                        BlockKind.CODE if kind == "code" else BlockKind.PARAGRAPH,
                        source,
                        label,
                        notebook_cell=cell_number,
                    )
                )
            if kind == "code":
                for output in cell.get("outputs", ()):
                    if not isinstance(output, dict):
                        continue
                    if output.get("output_type") == "stream":
                        output_text = _source_text(output.get("text")).strip()
                        if not output_text:
                            continue
                        if output_chars + len(output_text) > limits.max_notebook_output_chars:
                            if "notebook_output_too_large" not in warning_codes:
                                warnings.append(
                                    warning(
                                        "notebook_output_too_large",
                                        label,
                                        notebook_cell=cell_number,
                                    )
                                )
                                warning_codes.add("notebook_output_too_large")
                            continue
                        output_chars += len(output_text)
                        block_index += 1
                        blocks.append(
                            block(
                                block_index,
                                BlockKind.TRANSCRIPT,
                                output_text,
                                label,
                                notebook_cell=cell_number,
                            )
                        )
                    elif "data" in output:
                        if "notebook_binary_output_skipped" not in warning_codes:
                            warnings.append(
                                warning(
                                    "notebook_binary_output_skipped",
                                    label,
                                    notebook_cell=cell_number,
                                )
                            )
                            warning_codes.add("notebook_binary_output_skipped")
            sections.append(
                DocumentSection(
                    section_id=f"section-{cell_number:05d}",
                    heading=f"Cell {cell_number}",
                    heading_path=(f"Cell {cell_number}",),
                    location=location(label, notebook_cell=cell_number),
                    blocks=tuple(blocks),
                )
            )
        return make_document(
            path,
            "ipynb",
            text,
            sections,
            warnings=warnings,
            limits=limits,
        )
