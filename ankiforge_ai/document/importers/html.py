from __future__ import annotations

from html.parser import HTMLParser

from ..limits import DEFAULT_DOCUMENT_LIMITS
from ..models import BlockKind, DocumentSection
from ..source_labels import get_safe_source_label
from .base import DocumentImporter, ImportInspection
from .text import (
    block,
    import_error,
    location,
    make_document,
    read_text_bounded,
)


class _SafeHTMLParser(HTMLParser):
    ACTIVE = {"script", "style", "iframe", "object", "embed", "svg"}
    BLOCKS = {
        "p": BlockKind.PARAGRAPH,
        "li": BlockKind.LIST,
        "blockquote": BlockKind.QUOTE,
        "pre": BlockKind.CODE,
    }

    def __init__(self, limits=DEFAULT_DOCUMENT_LIMITS):
        super().__init__(convert_charrefs=True)
        self.limits = limits
        self.title = ""
        self._title_depth = 0
        self._ignored = 0
        self._current = None
        self._pieces = []
        self._start_line = 1
        self.items = []
        self._table_rows = None
        self._table_row = None
        self._cell_parts = None
        self._cell_chars = 0
        self._table_start_line = 1
        self._table_columns = 0
        self._table_row_count = 0
        self._table_stack = []
        self._table_depth = 0
        self._table_output_chars = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.casefold()
        if tag in self.ACTIVE:
            self._ignored += 1
            return
        if self._ignored:
            return
        if tag == "title":
            self._title_depth += 1
        if tag == "table":
            self._begin_table()
            return
        if self._table_rows is not None:
            if tag == "tr":
                self._finish_table_row()
                self._begin_table_row()
            elif tag in {"td", "th"}:
                if self._table_row is None:
                    self._begin_table_row()
                self._finish_table_cell()
                attributes = dict(attrs)
                colspan = attributes.get("colspan", "1")
                rowspan = attributes.get("rowspan", "1")
                if (
                    not colspan.isdigit()
                    or not rowspan.isdigit()
                    or int(colspan) < 1
                    or int(rowspan) < 1
                ):
                    raise import_error("malformed_file")
                self._table_columns += int(colspan)
                if (
                    self._table_columns > self.limits.max_table_columns
                    or self._table_row_count - 1 + int(rowspan)
                    > self.limits.max_table_rows
                ):
                    raise import_error("table_too_large")
                self._cell_parts = []
                self._cell_chars = 0
            return
        if tag in {f"h{level}" for level in range(1, 7)}:
            self._begin(BlockKind.HEADING)
        elif tag in self.BLOCKS:
            self._begin(self.BLOCKS[tag])
        elif tag == "img":
            alt = dict(attrs).get("alt", "").strip()
            if alt:
                self.items.append((BlockKind.CAPTION, alt, self.getpos()[0], self.getpos()[0]))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        tag = tag.casefold()
        if tag in self.ACTIVE:
            if self._ignored:
                self._ignored -= 1
            return
        if self._ignored:
            return
        if tag == "title" and self._title_depth:
            self._title_depth -= 1
        if self._table_rows is not None:
            if tag in {"td", "th"} and self._cell_parts is not None:
                self._finish_table_cell()
            elif tag == "tr" and self._table_row is not None:
                self._finish_table_row()
            elif tag == "table":
                self._finish_table()
            return
        if (
            tag in self.BLOCKS
            or tag in {f"h{level}" for level in range(1, 7)}
        ):
            self._finish()

    def handle_data(self, data):
        if self._ignored:
            return
        if self._title_depth:
            self.title += data
        if self._cell_parts is not None:
            if self._cell_chars + len(data) > self.limits.max_cell_chars:
                raise import_error("table_too_large")
            self._cell_chars += len(data)
            self._cell_parts.append(data)
            return
        if self._current is not None:
            self._pieces.append(data)

    def _begin(self, kind):
        self._finish()
        self._current = kind
        self._pieces = []
        self._start_line = self.getpos()[0]

    def _finish(self):
        if self._current is not None:
            text = " ".join("".join(self._pieces).split())
            if self._current is BlockKind.CODE:
                text = "".join(self._pieces).strip()
            if text:
                self.items.append(
                    (self._current, text, self._start_line, self.getpos()[0])
                )
        self._current = None
        self._pieces = []

    def _finish_table_cell(self):
        if self._cell_parts is None:
            return
        value = " ".join("".join(self._cell_parts).split())
        if len(value) > self.limits.max_cell_chars:
            raise import_error("table_too_large")
        if self._table_row is not None:
            self._table_row.append(value)
        self._cell_parts = None
        self._cell_chars = 0

    def _begin_table_row(self):
        self._table_row_count += 1
        if self._table_row_count > self.limits.max_table_rows:
            raise import_error("table_too_large")
        self._table_row = []
        self._table_columns = 0

    def _finish_table_row(self):
        self._finish_table_cell()
        if self._table_row is None:
            return
        if len(self._table_row) > self.limits.max_table_columns:
            raise import_error("table_too_large")
        if self._table_row:
            self._table_rows.append(self._table_row)
        self._table_row = None
        self._table_columns = 0

    def _begin_table(self):
        if self._table_depth >= self.limits.max_xml_depth:
            raise import_error("document_too_complex")
        self._table_depth += 1
        if self._table_rows is None:
            self._finish()
        else:
            self._table_stack.append(
                (
                    self._table_rows,
                    self._table_row,
                    self._cell_parts,
                    self._cell_chars,
                    self._table_start_line,
                    self._table_columns,
                    self._table_row_count,
                )
            )
        self._table_rows = []
        self._table_row = None
        self._cell_parts = None
        self._cell_chars = 0
        self._table_start_line = self.getpos()[0]
        self._table_columns = 0
        self._table_row_count = 0

    def _finish_table(self):
        self._finish_table_cell()
        self._finish_table_row()
        value = "\n".join(
            "\t".join(row) for row in self._table_rows if row
        )
        start_line = self._table_start_line
        if value:
            output_chars = self._table_output_chars + len(value)
            if output_chars > self.limits.max_text_chars:
                raise import_error("document_too_complex")
            self._table_output_chars = output_chars
            self.items.append(
                (
                    BlockKind.TABLE,
                    value,
                    start_line,
                    self.getpos()[0],
                )
            )
        self._table_depth -= 1
        if self._table_stack:
            (
                self._table_rows,
                self._table_row,
                self._cell_parts,
                self._cell_chars,
                self._table_start_line,
                self._table_columns,
                self._table_row_count,
            ) = self._table_stack.pop()
            return
        self._table_rows = None

    def close(self):
        super().close()
        self._finish()


class HtmlImporter(DocumentImporter):
    importer_id = "html"
    supported_extensions = (".html", ".htm", ".xhtml")

    def availability(self):
        return True

    def inspect(self, path, limits=DEFAULT_DOCUMENT_LIMITS):
        read_text_bounded(path, limits)
        return ImportInspection(
            importer_id=self.importer_id,
            source_label=get_safe_source_label(path),
            detected_file_type="html",
        )

    def import_document(self, path, limits=DEFAULT_DOCUMENT_LIMITS):
        text, _ = read_text_bounded(path, limits)
        label = get_safe_source_label(path)
        parser = _SafeHTMLParser(limits)
        try:
            parser.feed(text)
            parser.close()
        except (ValueError, AssertionError):
            from .text import import_error

            raise import_error("malformed_file") from None
        blocks = tuple(
            block(
                index,
                kind,
                value,
                label,
                line_start=start,
                line_end=end,
            )
            for index, (kind, value, start, end) in enumerate(parser.items, 1)
        )
        section = DocumentSection(
            section_id="section-00001",
            heading=next(
                (value for kind, value, _, _ in parser.items if kind is BlockKind.HEADING),
                None,
            ),
            location=blocks[0].location if blocks else location(label, line_start=1),
            blocks=blocks,
        )
        return make_document(
            path,
            "html",
            text,
            (section,),
            title=" ".join(parser.title.split()) or None,
            limits=limits,
        )
