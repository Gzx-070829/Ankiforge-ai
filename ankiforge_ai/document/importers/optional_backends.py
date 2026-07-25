from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Mapping, Optional, Union

from ..backends.base import BackendResult, DocumentBackend
from ..backends.output_validation import validate_safe_output_text
from ..errors import DocumentImportError
from ..limits import DEFAULT_DOCUMENT_LIMITS, DocumentLimits
from ..models import BlockKind, DocumentIR, DocumentSection
from ..source_labels import get_safe_source_label
from .base import DocumentImporter, ImportInspection
from .text import block, location, make_document


_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_LIST = re.compile(r"^\s*(?:[-+*]|\d+[.)])\s+(.+?)\s*$")
_TABLE_SEPARATOR = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*$")
_URI = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")


def backend_error(
    code: str,
    action: str = "check_backend",
) -> DocumentImportError:
    return DocumentImportError(
        code=code,
        message_key=f"document.error.{code}",
        action_key=f"document.action.{action}",
    )


def validate_local_backend_path(
    path: Union[str, Path],
    supported_extensions,
    limits: DocumentLimits,
) -> Path:
    if not isinstance(path, (str, Path)):
        raise backend_error("invalid_local_file", "reselect_file")
    raw = str(path)
    if not raw or "\x00" in raw or _URI.match(raw):
        raise backend_error("invalid_local_file", "reselect_file")
    source = Path(raw)
    try:
        if not source.is_absolute() or source.is_symlink():
            raise OSError
        source = source.resolve(strict=True)
        if not source.is_file():
            raise OSError
        size = source.stat().st_size
    except OSError:
        raise backend_error("invalid_local_file", "reselect_file") from None
    if size == 0:
        raise backend_error("empty_file")
    if size > limits.max_source_file_bytes:
        raise backend_error("file_too_large")
    if source.suffix.casefold() not in frozenset(supported_extensions):
        raise backend_error("backend_format_unsupported", "choose_importer")
    return source


def validated_backend_text(
    result: BackendResult,
    limits: DocumentLimits,
) -> str:
    if (
        not isinstance(result, BackendResult)
        or result.returncode != 0
        or not isinstance(result.stdout, str)
    ):
        raise backend_error("backend_failed")
    text = result.stdout.replace("\r\n", "\n").replace("\r", "\n")
    try:
        encoded_length = len(text.encode("utf-8"))
        validate_safe_output_text(text)
    except UnicodeEncodeError:
        raise backend_error("backend_invalid_output") from None
    except ValueError:
        raise backend_error("backend_invalid_output") from None
    if (
        not text.strip()
        or len(text) > limits.max_text_chars
        or encoded_length > limits.max_text_chars * 4
    ):
        raise backend_error("backend_invalid_output")
    return text


def document_from_backend_markdown(
    path: Path,
    source_type: str,
    markdown: str,
    limits: DocumentLimits,
    *,
    title: Optional[str] = None,
) -> DocumentIR:
    text = _validate_markdown_text(markdown, limits)
    label = get_safe_source_label(path)
    lines = text.splitlines()
    sections = []
    current_blocks = []
    current_heading = None
    heading_path = []
    current_path = ()
    block_index = 0

    def flush_section():
        nonlocal current_blocks
        if not current_blocks:
            return
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

    index = 0
    while index < len(lines):
        raw = lines[index]
        line_number = index + 1
        heading = _HEADING.match(raw)
        if heading:
            flush_section()
            level = len(heading.group(1))
            value = heading.group(2).strip()
            heading_path[level - 1 :] = []
            while len(heading_path) < level - 1:
                heading_path.append("")
            heading_path.append(value)
            current_heading = value
            current_path = tuple(part for part in heading_path if part)
            block_index += 1
            current_blocks.append(
                block(
                    block_index,
                    BlockKind.HEADING,
                    value,
                    label,
                    line_start=line_number,
                    line_end=line_number,
                    metadata={"level": level},
                )
            )
            index += 1
            continue
        if raw.lstrip().startswith(("```", "~~~")):
            marker = raw.lstrip()[:3]
            language = raw.lstrip()[3:].strip()[:64]
            start = line_number
            values = []
            index += 1
            while index < len(lines) and not lines[index].lstrip().startswith(marker):
                values.append(lines[index])
                index += 1
            if index < len(lines):
                index += 1
            block_index += 1
            current_blocks.append(
                block(
                    block_index,
                    BlockKind.CODE,
                    "\n".join(values),
                    label,
                    line_start=start,
                    line_end=index,
                    metadata={"language": language},
                )
            )
            continue
        list_match = _LIST.match(raw)
        if list_match:
            start = line_number
            values = []
            while index < len(lines):
                match = _LIST.match(lines[index])
                if match is None:
                    break
                values.append(match.group(1))
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
            start = line_number
            values = [raw]
            index += 2
            while index < len(lines) and "|" in lines[index] and lines[index].strip():
                values.append(lines[index])
                index += 1
            if len(values) > limits.max_table_rows:
                raise backend_error("backend_invalid_output")
            for value in values:
                cells = _table_cells(value)
                if (
                    len(cells) > limits.max_table_columns
                    or any(len(cell) > limits.max_cell_chars for cell in cells)
                ):
                    raise backend_error("backend_invalid_output")
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
            start = line_number
            values = [raw.rstrip()]
            index += 1
            while index < len(lines) and lines[index].strip():
                if (
                    _HEADING.match(lines[index])
                    or _LIST.match(lines[index])
                    or lines[index].lstrip().startswith(("```", "~~~"))
                ):
                    break
                if (
                    "|" in lines[index]
                    and index + 1 < len(lines)
                    and _TABLE_SEPARATOR.match(lines[index + 1])
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
                heading_path=(),
                location=location(label, line_start=1),
                blocks=(),
            )
        )
    selected_title = _safe_title(title)
    if selected_title is None:
        selected_title = next(
            (section.heading for section in sections if section.heading),
            None,
        )
    try:
        return make_document(
            path,
            source_type,
            text,
            tuple(sections),
            title=selected_title,
            limits=limits,
        )
    except (TypeError, ValueError, DocumentImportError):
        raise backend_error("backend_invalid_output") from None


def parse_docling_output(
    path: Path,
    output: str,
    limits: DocumentLimits,
    *,
    schema: str = "markdown",
) -> DocumentIR:
    if schema == "markdown":
        return document_from_backend_markdown(
            path,
            "docling",
            output,
            limits,
        )
    if schema != "docling_json_v1":
        raise backend_error("backend_invalid_output")
    try:
        value = json.loads(
            output,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_finite,
        )
    except (json.JSONDecodeError, RecursionError, ValueError):
        raise backend_error("backend_invalid_output") from None
    if not isinstance(value, dict) or frozenset(value) not in {
        frozenset({"markdown"}),
        frozenset({"markdown", "title"}),
    }:
        raise backend_error("backend_invalid_output")
    markdown = value.get("markdown")
    title = value.get("title")
    if not isinstance(markdown, str) or (
        title is not None and not isinstance(title, str)
    ):
        raise backend_error("backend_invalid_output")
    return document_from_backend_markdown(
        path,
        "docling",
        markdown,
        limits,
        title=title,
    )


class OptionalBackendImporter(DocumentImporter):
    def __init__(self, backend: DocumentBackend, *, explicitly_enabled: bool) -> None:
        if not isinstance(backend, DocumentBackend):
            raise TypeError("backend must implement DocumentBackend")
        self._backend = backend
        self._explicitly_enabled = explicitly_enabled is True
        capability = backend.capabilities()
        self.importer_id = capability.backend_id
        self.supported_extensions = capability.supported_extensions

    def availability(self) -> bool:
        return self._explicitly_enabled and self._backend.probe().available

    def inspect(
        self,
        path: Union[str, Path],
        limits: DocumentLimits = DEFAULT_DOCUMENT_LIMITS,
    ) -> ImportInspection:
        source = validate_local_backend_path(path, self.supported_extensions, limits)
        if not self._explicitly_enabled:
            raise backend_error("backend_disabled", "enable_backend")
        return ImportInspection(
            importer_id=self.importer_id,
            source_label=get_safe_source_label(source),
            detected_file_type=source.suffix.casefold().lstrip("."),
            warnings=("optional_local_backend",),
        )

    def import_document(
        self,
        path: Union[str, Path],
        limits: DocumentLimits = DEFAULT_DOCUMENT_LIMITS,
    ) -> DocumentIR:
        if not self._explicitly_enabled:
            raise backend_error("backend_disabled", "enable_backend")
        return self._backend.convert_local_file(path, limits)


def create_optional_backend_importers(
    enabled_backend_ids=(),
    *,
    pandoc_executable=None,
    runners: Optional[Mapping[str, object]] = None,
):
    enabled = tuple(enabled_backend_ids)
    if not enabled:
        return ()
    if len(set(enabled)) != len(enabled) or not all(
        backend_id in {"docling", "markitdown", "pandoc"}
        for backend_id in enabled
    ):
        raise ValueError("enabled_backend_ids contains an unknown backend")
    supplied_runners = {} if runners is None else dict(runners)
    if set(supplied_runners) - set(enabled):
        raise ValueError("runner supplied for a backend that is not enabled")
    from ..backends.docling_adapter import DoclingBackend
    from ..backends.markitdown_adapter import MarkItDownBackend
    from ..backends.pandoc_adapter import PandocBackend

    factories = {
        "docling": lambda: DoclingBackend(runner=supplied_runners.get("docling")),
        "markitdown": lambda: MarkItDownBackend(
            runner=supplied_runners.get("markitdown")
        ),
        "pandoc": lambda: PandocBackend(
            executable=pandoc_executable,
            runner=supplied_runners.get("pandoc"),
        ),
    }
    return tuple(
        OptionalBackendImporter(
            factories[backend_id](),
            explicitly_enabled=True,
        )
        for backend_id in enabled
    )


def _validate_markdown_text(text: str, limits: DocumentLimits) -> str:
    if not isinstance(text, str):
        raise backend_error("backend_invalid_output")
    try:
        encoded_length = len(text.encode("utf-8"))
        validate_safe_output_text(text)
    except UnicodeEncodeError:
        raise backend_error("backend_invalid_output") from None
    except ValueError:
        raise backend_error("backend_invalid_output") from None
    if (
        not text.strip()
        or len(text) > limits.max_text_chars
        or encoded_length > limits.max_text_chars * 4
    ):
        raise backend_error("backend_invalid_output")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _safe_title(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    candidate = value.strip()
    try:
        validate_safe_output_text(candidate)
    except ValueError:
        raise backend_error("backend_invalid_output") from None
    if (
        not candidate
        or len(candidate) > 120
        or any(character in candidate for character in "\r\n/\\")
    ):
        raise backend_error("backend_invalid_output")
    return candidate


def _table_cells(value: str):
    stripped = value.strip().strip("|")
    return [cell.strip() for cell in stripped.split("|")]


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _reject_non_finite(value):
    raise ValueError("non-finite JSON number")
