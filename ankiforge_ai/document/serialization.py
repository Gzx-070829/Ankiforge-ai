import json
from typing import Dict, List, Optional

from .models import (
    BlockKind,
    DocumentBlock,
    DocumentIR,
    DocumentSection,
    DocumentWarning,
    SourceLocation,
    count_blocks_by_kind,
    validate_document_ir,
)
from .limits import DEFAULT_DOCUMENT_LIMITS
from .models import MAX_METADATA_ITEMS


_ROOT_KEYS = frozenset(
    {
        "schema_version",
        "document_id",
        "title",
        "language_hint",
        "source_type",
        "source_label",
        "metadata",
        "sections",
        "warnings",
        "original_char_count",
        "extracted_char_count",
    }
)
_SECTION_KEYS = frozenset(
    {"section_id", "heading", "heading_path", "location", "blocks"}
)
_BLOCK_KEYS = frozenset({"block_id", "kind", "text", "location", "metadata"})
_WARNING_KEYS = frozenset(
    {"code", "severity", "message_key", "action_key", "location"}
)
_LOCATION_KEYS = frozenset(
    {
        "file_label",
        "page",
        "slide",
        "sheet",
        "row_start",
        "row_end",
        "cell_range",
        "section",
        "timestamp_start",
        "timestamp_end",
        "notebook_cell",
        "line_start",
        "line_end",
    }
)
_MAX_SAFE_JSON_SCALARS = DEFAULT_DOCUMENT_LIMITS.max_document_blocks * (
    MAX_METADATA_ITEMS + 32
)


def document_to_plain_text(document: DocumentIR) -> str:
    validate_document_ir(document)
    sections = []
    for section in document.sections:
        lines = []
        for block in section.blocks:
            if (
                block.kind is BlockKind.HEADING
                and section.heading
                and block.text == section.heading
            ):
                if not lines:
                    lines.append(block.text)
                continue
            lines.append(block.text)
        if lines:
            sections.append("\n".join(lines))
    return "\n\n".join(sections)


def document_to_safe_markdown(document: DocumentIR) -> str:
    validate_document_ir(document)
    rendered_sections: List[str] = []
    for section in document.sections:
        parts: List[str] = []
        if section.heading:
            level = min(max(len(section.heading_path), 1), 6)
            parts.append(f"{'#' * level} {section.heading}")
        for block in section.blocks:
            if (
                block.kind is BlockKind.HEADING
                and section.heading
                and block.text == section.heading
            ):
                continue
            if block.kind is BlockKind.CODE:
                language = block.metadata.get("language", "")
                fence_language = language if isinstance(language, str) else ""
                parts.append(f"```{fence_language}\n{block.text}\n```")
            elif block.kind is BlockKind.QUOTE:
                parts.append(
                    "\n".join(f"> {line}" for line in block.text.splitlines())
                )
            elif block.kind is BlockKind.LIST_ITEM:
                parts.append(f"- {block.text}")
            elif block.kind is BlockKind.FORMULA:
                parts.append(f"$$\n{block.text}\n$$")
            elif block.kind is BlockKind.HEADING:
                parts.append(f"## {block.text}")
            else:
                parts.append(block.text)
        if parts:
            rendered_sections.append("\n\n".join(parts))
    return "\n\n".join(rendered_sections)


def document_summary(document: DocumentIR) -> Dict[str, object]:
    validate_document_ir(document)
    return {
        "document_id": document.document_id,
        "title": document.title,
        "source_type": document.source_type,
        "source_label": document.source_label,
        "section_count": len(document.sections),
        "block_count": sum(len(section.blocks) for section in document.sections),
        "warning_count": len(document.warnings),
        "original_char_count": document.original_char_count,
        "extracted_char_count": document.extracted_char_count,
        "blocks_by_kind": count_blocks_by_kind(document),
    }


def document_to_safe_json(document: DocumentIR) -> str:
    validate_document_ir(document)
    return json.dumps(
        document.to_safe_dict(),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _location_from_dict(value: Optional[Dict[str, object]]) -> Optional[SourceLocation]:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("location must be an object or null")
    return SourceLocation(**value)


def document_from_safe_json(payload: str) -> DocumentIR:
    if not isinstance(payload, str):
        raise TypeError("payload must be a string")
    if len(payload) > DEFAULT_DOCUMENT_LIMITS.max_archive_uncompressed_bytes:
        raise ValueError("DocumentIR JSON exceeds MAX_ARCHIVE_UNCOMPRESSED_BYTES")
    try:
        payload_bytes = len(payload.encode("utf-8"))
    except UnicodeEncodeError:
        raise ValueError("DocumentIR JSON contains invalid Unicode") from None
    if payload_bytes > DEFAULT_DOCUMENT_LIMITS.max_archive_uncompressed_bytes:
        raise ValueError("DocumentIR JSON exceeds MAX_ARCHIVE_UNCOMPRESSED_BYTES")
    try:
        value = json.loads(payload, object_pairs_hook=_reject_duplicate_keys)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("invalid DocumentIR JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("DocumentIR JSON root must be an object")
    depth, scalar_count, scalar_chars = _json_metrics(value)
    if depth > DEFAULT_DOCUMENT_LIMITS.max_json_depth:
        raise ValueError("DocumentIR JSON exceeds MAX_JSON_DEPTH")
    if scalar_count > _MAX_SAFE_JSON_SCALARS:
        raise ValueError("DocumentIR JSON exceeds MAX_SAFE_JSON_SCALARS")
    if scalar_chars > DEFAULT_DOCUMENT_LIMITS.max_text_chars:
        raise ValueError("DocumentIR JSON exceeds MAX_TEXT_CHARS")
    _validate_safe_document_shape(value)
    try:
        sections = []
        for section_value in value["sections"]:
            blocks = []
            for block_value in section_value["blocks"]:
                blocks.append(
                    DocumentBlock(
                        block_id=block_value["block_id"],
                        kind=block_value["kind"],
                        text=block_value["text"],
                        location=_location_from_dict(block_value["location"]),
                        metadata=block_value["metadata"],
                    )
                )
            sections.append(
                DocumentSection(
                    section_id=section_value["section_id"],
                    heading=section_value["heading"],
                    heading_path=section_value["heading_path"],
                    location=_location_from_dict(section_value["location"]),
                    blocks=blocks,
                )
            )
        warnings = [
            DocumentWarning(
                code=warning["code"],
                severity=warning["severity"],
                message_key=warning["message_key"],
                action_key=warning["action_key"],
                location=_location_from_dict(warning["location"]),
            )
            for warning in value["warnings"]
        ]
        return DocumentIR(
            schema_version=value["schema_version"],
            document_id=value["document_id"],
            title=value["title"],
            language_hint=value["language_hint"],
            source_type=value["source_type"],
            source_label=value["source_label"],
            metadata=value["metadata"],
            sections=sections,
            warnings=warnings,
            original_char_count=value["original_char_count"],
            extracted_char_count=value["extracted_char_count"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("invalid DocumentIR JSON shape") from exc


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _require_exact_keys(value, expected, label):
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    actual = frozenset(value)
    extra = actual - expected
    if extra:
        raise ValueError(f"{label} has unexpected keys")
    missing = expected - actual
    if missing:
        raise ValueError(f"{label} is missing required keys")


def _validate_location_shape(value, label):
    if value is None:
        return
    _require_exact_keys(value, _LOCATION_KEYS, label)


def _validate_safe_document_shape(value):
    _require_exact_keys(value, _ROOT_KEYS, "document")
    if not isinstance(value["metadata"], dict):
        raise ValueError("document metadata must be an object")
    if not isinstance(value["sections"], list):
        raise ValueError("document sections must be an array")
    if not isinstance(value["warnings"], list):
        raise ValueError("document warnings must be an array")
    for section_index, section in enumerate(value["sections"]):
        label = f"section[{section_index}]"
        _require_exact_keys(section, _SECTION_KEYS, label)
        _validate_location_shape(section["location"], f"{label}.location")
        if not isinstance(section["blocks"], list):
            raise ValueError(f"{label}.blocks must be an array")
        for block_index, block in enumerate(section["blocks"]):
            block_label = f"{label}.block[{block_index}]"
            _require_exact_keys(block, _BLOCK_KEYS, block_label)
            _validate_location_shape(
                block["location"],
                f"{block_label}.location",
            )
            if not isinstance(block["metadata"], dict):
                raise ValueError(f"{block_label}.metadata must be an object")
    for warning_index, warning in enumerate(value["warnings"]):
        label = f"warning[{warning_index}]"
        _require_exact_keys(warning, _WARNING_KEYS, label)
        _validate_location_shape(warning["location"], f"{label}.location")


def _json_metrics(value: object):
    maximum = 0
    scalar_count = 0
    scalar_chars = 0
    stack = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        maximum = max(maximum, depth)
        if isinstance(current, dict):
            scalar_count += len(current)
            scalar_chars += sum(len(key) for key in current)
            stack.extend((item, depth + 1) for item in current.values())
        elif isinstance(current, list):
            stack.extend((item, depth + 1) for item in current)
        else:
            scalar_count += 1
            if isinstance(current, str):
                scalar_chars += len(current)
            elif current is not None:
                scalar_chars += len(str(current))
    return maximum, scalar_count, scalar_chars
