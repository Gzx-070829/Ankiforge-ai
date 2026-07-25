from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterable, Optional, Sequence, Tuple, Union

from ..errors import DocumentImportError
from ..limits import DEFAULT_DOCUMENT_LIMITS, DocumentLimits
from ..models import (
    BlockKind,
    DocumentBlock,
    DocumentIR,
    DocumentSection,
    DocumentWarning,
    SourceLocation,
    validate_document_ir,
)
from ..source_labels import get_safe_source_label
from .base import DocumentImporter, ImportInspection


def import_error(code: str, action: str = "choose_another_file") -> DocumentImportError:
    return DocumentImportError(
        code=code,
        message_key=f"document.error.{code}",
        action_key=f"document.action.{action}",
    )


def read_text_bounded(
    path: Union[str, Path],
    limits: DocumentLimits = DEFAULT_DOCUMENT_LIMITS,
) -> tuple[str, str]:
    source = Path(path)
    try:
        size = source.stat().st_size
        if not source.is_file():
            raise OSError
    except OSError:
        raise import_error("file_unavailable", "reselect_file") from None
    if size == 0:
        raise import_error("empty_file")
    if size > limits.max_text_file_bytes:
        raise import_error("file_too_large")
    try:
        payload = source.read_bytes()
    except OSError:
        raise import_error("file_unavailable", "reselect_file") from None
    if payload.startswith(b"\xff\xfe\x00\x00"):
        encoding = "utf-32-le"
    elif payload.startswith(b"\x00\x00\xfe\xff"):
        encoding = "utf-32-be"
    elif payload.startswith(b"\xef\xbb\xbf"):
        encoding = "utf-8-sig"
    elif payload.startswith(b"\xff\xfe"):
        encoding = "utf-16-le"
    elif payload.startswith(b"\xfe\xff"):
        encoding = "utf-16-be"
    else:
        encoding = "utf-8"
    try:
        text = payload.decode(encoding)
    except (LookupError, UnicodeDecodeError):
        raise import_error("binary_file") from None
    if text.startswith("\ufeff"):
        text = text[1:]
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        raise import_error("empty_file")
    if len(text) > limits.max_text_chars:
        raise import_error("document_too_complex")
    return text, encoding


def location(
    label: str,
    *,
    line_start: Optional[int] = None,
    line_end: Optional[int] = None,
    **kwargs,
) -> SourceLocation:
    return SourceLocation(
        file_label=label,
        line_start=line_start,
        line_end=line_end,
        **kwargs,
    )


def block(
    index: int,
    kind: BlockKind,
    text: str,
    label: str,
    *,
    line_start: Optional[int] = None,
    line_end: Optional[int] = None,
    metadata=None,
    **location_kwargs,
) -> DocumentBlock:
    return DocumentBlock(
        block_id=f"block-{index:05d}",
        kind=kind,
        text=text,
        location=location(
            label,
            line_start=line_start,
            line_end=line_end,
            **location_kwargs,
        ),
        metadata={} if metadata is None else metadata,
    )


def warning(code: str, label: str, **location_kwargs) -> DocumentWarning:
    return DocumentWarning(
        code=code,
        severity="warning",
        message_key=f"document.warning.{code}",
        action_key="document.action.review_import",
        location=location(label, **location_kwargs),
    )


def make_document(
    path: Union[str, Path],
    source_type: str,
    text: str,
    sections: Sequence[DocumentSection],
    *,
    title: Optional[str] = None,
    warnings: Iterable[DocumentWarning] = (),
    metadata=None,
    limits: DocumentLimits = DEFAULT_DOCUMENT_LIMITS,
) -> DocumentIR:
    label = get_safe_source_label(path)
    identity = hashlib.sha256(
        f"{source_type}\0{label}\0{text}".encode("utf-8")
    ).hexdigest()[:24]
    extracted = sum(
        len(item.text) for section in sections for item in section.blocks
    )
    document = DocumentIR(
        schema_version=1,
        document_id=f"document-{identity}",
        title=title or Path(label).stem or label,
        language_hint=None,
        source_type=source_type,
        source_label=label,
        metadata={} if metadata is None else metadata,
        sections=tuple(sections),
        warnings=tuple(warnings),
        original_char_count=len(text),
        extracted_char_count=extracted,
    )
    try:
        validate_document_ir(
            document,
            max_text_chars=limits.max_text_chars,
            max_document_blocks=limits.max_document_blocks,
        )
    except ValueError:
        raise import_error("document_too_complex") from None
    return document


def paragraph_blocks(text: str, label: str) -> tuple[DocumentBlock, ...]:
    lines = text.splitlines()
    result = []
    start = None
    collected = []
    for number, line in enumerate(lines + [""], start=1):
        if line.strip():
            if start is None:
                start = number
            collected.append(line.rstrip())
        elif collected:
            result.append(
                block(
                    len(result) + 1,
                    BlockKind.PARAGRAPH,
                    "\n".join(collected),
                    label,
                    line_start=start,
                    line_end=number - 1,
                )
            )
            start = None
            collected = []
    return tuple(result)


class TextImporter(DocumentImporter):
    importer_id = "text"
    supported_extensions = (".txt", ".log")

    def availability(self) -> bool:
        return True

    def inspect(self, path, limits=DEFAULT_DOCUMENT_LIMITS) -> ImportInspection:
        _, encoding = read_text_bounded(path, limits)
        return ImportInspection(
            importer_id=self.importer_id,
            source_label=get_safe_source_label(path),
            detected_file_type="text",
            warnings=(f"encoding:{encoding}",),
        )

    def import_document(self, path, limits=DEFAULT_DOCUMENT_LIMITS) -> DocumentIR:
        text, _ = read_text_bounded(path, limits)
        label = get_safe_source_label(path)
        section = DocumentSection(
            section_id="section-00001",
            heading=None,
            heading_path=(),
            location=location(label, line_start=1),
            blocks=paragraph_blocks(text, label),
        )
        return make_document(path, "text", text, (section,), limits=limits)


class TextMarkupImporter(TextImporter):
    _TYPES = {
        ".yaml": "yaml",
        ".yml": "yaml",
        ".rst": "rst",
        ".org": "org",
        ".tex": "latex",
        ".latex": "latex",
        ".log": "text",
    }
    supported_extensions = tuple(_TYPES)

    def __init__(self, source_type: str = "text") -> None:
        self.source_type = source_type
        self.importer_id = source_type

    @classmethod
    def for_path(cls, path: Union[str, Path]) -> "TextMarkupImporter":
        return cls(cls._TYPES.get(Path(path).suffix.casefold(), "text"))

    def import_document(self, path, limits=DEFAULT_DOCUMENT_LIMITS) -> DocumentIR:
        text, _ = read_text_bounded(path, limits)
        label = get_safe_source_label(path)
        lines = text.splitlines()
        heading = None
        heading_end = 0
        if self.source_type == "yaml" and lines:
            match = re.match(r"^\s*title\s*:\s*(.+?)\s*$", lines[0], re.I)
            if match:
                heading, heading_end = match.group(1).strip("'\""), 1
        elif self.source_type == "rst" and len(lines) > 1:
            if re.fullmatch(r"[=~-]{3,}", lines[1].strip()):
                heading, heading_end = lines[0].strip(), 2
        elif self.source_type == "org" and lines:
            match = re.match(r"^\*+\s+(.+?)\s*$", lines[0])
            if match:
                heading, heading_end = match.group(1), 1
        elif self.source_type == "latex" and lines:
            match = re.match(
                r"^\s*\\(?:part|chapter|section|subsection)\{([^{}]+)\}",
                lines[0],
            )
            if match:
                heading, heading_end = match.group(1), 1
        parsed_blocks = []
        if heading:
            parsed_blocks.append(
                block(
                    1,
                    BlockKind.HEADING,
                    heading,
                    label,
                    line_start=1,
                    line_end=heading_end,
                )
            )
        remainder = "\n".join(lines[heading_end:])
        for item in paragraph_blocks(remainder, label):
            parsed_blocks.append(
                block(
                    len(parsed_blocks) + 1,
                    item.kind,
                    item.text,
                    label,
                    line_start=(
                        item.location.line_start + heading_end
                        if item.location.line_start is not None
                        else None
                    ),
                    line_end=(
                        item.location.line_end + heading_end
                        if item.location.line_end is not None
                        else None
                    ),
                )
            )
        blocks = tuple(parsed_blocks)
        section = DocumentSection(
            section_id="section-00001",
            heading=heading,
            heading_path=(heading,) if heading else (),
            location=location(label, line_start=1),
            blocks=blocks,
        )
        return make_document(path, self.source_type, text, (section,), limits=limits)
