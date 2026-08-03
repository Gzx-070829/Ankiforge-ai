"""Safe short source chips and bounded extracted-text snippets."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Optional, Union

from ..document import SourceLocation, SourceSpan


_WHITESPACE = re.compile(r"\s+")
_WINDOWS_PATH = re.compile(
    r"(?<![\w])(?:[A-Za-z]:[\\/])(?:[^\s\"'<>|]+[\\/]?)+"
)
_POSIX_PATH = re.compile(r"(?<![\w])/(?:[^\s\"'<>/]+/)+[^\s\"'<>/]*")
_MAX_CHIP_CHARS = 96


@dataclass(frozen=True)
class SourceLocationView:
    chip: str
    action_label: str
    snippet: str


def present_source_location(
    location: Optional[Union[SourceLocation, SourceSpan]],
    block_text: str,
    *,
    language: str = "en",
    max_snippet_chars: int = 240,
) -> SourceLocationView:
    if location is not None and not isinstance(location, (SourceLocation, SourceSpan)):
        raise TypeError("location must be source evidence or None")
    if not isinstance(block_text, str):
        raise TypeError("block_text must be a string")
    if language not in {"zh", "en"}:
        raise ValueError("language must be zh or en")
    if (
        isinstance(max_snippet_chars, bool)
        or not isinstance(max_snippet_chars, int)
        or not 40 <= max_snippet_chars <= 500
    ):
        raise ValueError("max_snippet_chars must be between 40 and 500")
    return SourceLocationView(
        chip=_chip(location, language),
        action_label=(
            "查看来源片段" if language == "zh" else "View source snippet"
        ),
        snippet=_bounded_snippet(block_text, max_snippet_chars),
    )


def _chip(
    location: Optional[Union[SourceLocation, SourceSpan]],
    language: str,
) -> str:
    if location is None:
        return "来源" if language == "zh" else "Source"
    if isinstance(location, SourceSpan):
        return _source_span_chip(location, language)
    file_label = (
        _safe_chip_text(location.file_label)
        if location.file_label is not None
        else ""
    )
    fallback = "来源" if language == "zh" else "Source"
    if location.page is not None:
        value = f"第 {location.page} 页" if language == "zh" else f"Page {location.page}"
    elif location.slide is not None:
        value = (
            f"第 {location.slide} 张幻灯片"
            if language == "zh"
            else f"Slide {location.slide}"
        )
    elif location.sheet is not None:
        sheet = _safe_chip_text(location.sheet)
        value = (
            f"工作表“{sheet}”"
            if language == "zh"
            else f'Sheet "{sheet}"'
        )
        if location.row_start is not None:
            if (
                location.row_end is not None
                and location.row_end != location.row_start
            ):
                row = f"{location.row_start}–{location.row_end}"
                value += (
                    f"，第 {row} 行"
                    if language == "zh"
                    else f", Rows {row}"
                )
            else:
                value += (
                    f"，第 {location.row_start} 行"
                    if language == "zh"
                    else f", Row {location.row_start}"
                )
    elif location.notebook_cell is not None:
        value = (
            f"第 {location.notebook_cell} 个单元格"
            if language == "zh"
            else f"Cell {location.notebook_cell}"
        )
    elif location.timestamp_start is not None:
        value = _format_timestamp(location.timestamp_start)
    elif location.line_start is not None:
        if (
            location.line_end is not None
            and location.line_end != location.line_start
        ):
            lines = f"{location.line_start}–{location.line_end}"
            value = f"第 {lines} 行" if language == "zh" else f"Lines {lines}"
        else:
            value = (
                f"第 {location.line_start} 行"
                if language == "zh"
                else f"Line {location.line_start}"
            )
    elif location.section:
        value = _safe_chip_text(location.section)
    else:
        value = fallback
    if file_label:
        value = (
            file_label
            if value == fallback
            else f"{file_label} · {value}"
        )
    if len(value) > _MAX_CHIP_CHARS:
        return value[: _MAX_CHIP_CHARS - 1].rstrip() + "…"
    return value


def _source_span_chip(span: SourceSpan, language: str) -> str:
    label = _safe_chip_text(span.source_label)
    kind = span.locator_kind
    raw_value = span.locator_value
    value = raw_value.replace("-", "–") if kind in {"row", "line"} else raw_value
    if kind in {"document", "block"}:
        detail = ""
    elif kind == "page":
        detail = f"第 {value} 页" if language == "zh" else f"Page {value}"
    elif kind == "slide":
        detail = f"第 {value} 张幻灯片" if language == "zh" else f"Slide {value}"
    elif kind == "row":
        detail = f"第 {value} 行" if language == "zh" else f"Rows {value}"
        if "–" not in value and language == "en":
            detail = f"Row {value}"
    elif kind == "line":
        detail = f"第 {value} 行" if language == "zh" else f"Lines {value}"
        if "–" not in value and language == "en":
            detail = f"Line {value}"
    elif kind == "cell":
        detail = f"单元格 {value}" if language == "zh" else f"Cell {value}"
    elif kind == "sheet":
        detail = f"工作表“{value}”" if language == "zh" else f'Sheet "{value}"'
    elif kind == "section":
        detail = value
    else:
        detail = value
    rendered = label if not detail else f"{label} · {detail}"
    if len(rendered) > _MAX_CHIP_CHARS:
        return rendered[: _MAX_CHIP_CHARS - 1].rstrip() + "…"
    return rendered


def _safe_chip_text(value: str) -> str:
    normalized = _WHITESPACE.sub(" ", value).strip()
    normalized = (
        normalized.replace('"', "”")
        .replace("\\", " ")
        .replace("/", " ")
    )
    return normalized or "Source"


def _format_timestamp(value: float) -> str:
    seconds = max(0, int(math.floor(value)))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    return f"{minutes:02}:{seconds:02}"


def _bounded_snippet(text: str, limit: int) -> str:
    redacted = _WINDOWS_PATH.sub("[local file]", text)
    redacted = _POSIX_PATH.sub("[local file]", redacted)
    normalized = _WHITESPACE.sub(" ", redacted).strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


__all__ = ["SourceLocationView", "present_source_location"]
