"""Safe plain-text rendering and duplicate normalization for Anki HTML fields."""

from __future__ import annotations

import html
from html.parser import HTMLParser


_BLOCK_TAGS = {
    "address",
    "article",
    "blockquote",
    "div",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "li",
    "p",
    "pre",
    "section",
    "table",
    "tr",
}
_IGNORED_CONTENT_TAGS = {"script", "style"}


def normalize_plain_text_newlines(text: str) -> str:
    return str(text or "").replace("\r\n", "\n").replace("\r", "\n")


def render_plain_text_anki_html(text: str) -> str:
    """Render one raw plain-text value exactly once at the writer boundary."""

    normalized = normalize_plain_text_newlines(text)
    return html.escape(normalized, quote=True).replace("\n", "<br>")


def plain_text_from_anki_html(field_html: str) -> str:
    """Decode existing Anki HTML to inert text for comparison only."""

    parser = _AnkiFieldTextParser()
    try:
        parser.feed(str(field_html or ""))
        parser.close()
    except (ValueError, TypeError):
        return normalize_plain_text_newlines(str(field_html or ""))
    return normalize_plain_text_newlines("".join(parser.parts))


def duplicate_key_from_plain_text(text: str) -> str:
    """Preserve the existing exact/casefold/whitespace duplicate semantics."""

    return " ".join(normalize_plain_text_newlines(text).split()).casefold()


def duplicate_key_from_anki_html(field_html: str) -> str:
    return duplicate_key_from_plain_text(plain_text_from_anki_html(field_html))


class _AnkiFieldTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag, attrs):
        normalized = tag.casefold()
        if normalized in _IGNORED_CONTENT_TAGS:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
        if normalized == "br":
            self.parts.append("\n")
        elif normalized in _BLOCK_TAGS:
            self._append_boundary()

    def handle_startendtag(self, tag, attrs):
        if not self._ignored_depth and tag.casefold() == "br":
            self.parts.append("\n")

    def handle_endtag(self, tag):
        normalized = tag.casefold()
        if normalized in _IGNORED_CONTENT_TAGS:
            if self._ignored_depth:
                self._ignored_depth -= 1
            return
        if not self._ignored_depth and normalized in _BLOCK_TAGS:
            self._append_boundary()

    def handle_data(self, data):
        if not self._ignored_depth:
            self.parts.append(data)

    def _append_boundary(self):
        if self.parts and not self.parts[-1].endswith("\n"):
            self.parts.append("\n")
