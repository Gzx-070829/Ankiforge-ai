"""Offline, UI-independent source file import for AnkiForge AI."""

from __future__ import annotations

import locale
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree


TEXT_FILE_SIZE_LIMIT = 5 * 1024 * 1024
DOCUMENT_FILE_SIZE_LIMIT = 10 * 1024 * 1024
DOCX_XML_SIZE_LIMIT = 20 * 1024 * 1024
DOCX_MAX_ARCHIVE_ENTRIES = 2048
DOCX_ELEMENT_LIMIT = 100_000
DOCX_TEXT_CHARACTER_LIMIT = 5_000_000

SUPPORTED_SUFFIXES = frozenset({".md", ".markdown", ".txt", ".docx", ".pdf"})


@dataclass(frozen=True)
class ImportedSource:
    """One imported source, ready to place in the material text box."""

    filename: str
    suffix: str
    text: str
    char_count: int
    warnings: tuple[str, ...]
    source_label: str


class SourceImportError(ValueError):
    """A safe, stable import failure that the UI can translate."""

    def __init__(self, code: str, filename: str = "") -> None:
        self.code = code
        self.filename = filename
        super().__init__(code)


def import_source_file(path: Path) -> ImportedSource:
    """Import one supported local file without Anki, UI, or network access."""

    source_path = Path(path)
    _ensure_regular_file(source_path)
    suffix = source_path.suffix.casefold()
    if suffix == ".doc":
        raise SourceImportError("legacy_doc", source_path.name)
    if suffix not in SUPPORTED_SUFFIXES:
        raise SourceImportError("unsupported_type", source_path.name)
    if suffix == ".txt":
        return import_text_file(source_path)
    if suffix in {".md", ".markdown"}:
        return import_markdown_file(source_path)
    if suffix == ".docx":
        return import_docx_file(source_path)
    return import_pdf_file(source_path)


def import_text_file(path: Path) -> ImportedSource:
    """Import a UTF-8 text file, with an explicit local-encoding fallback."""

    return _import_utf8_text(Path(path), expected_suffixes={".txt"})


def import_markdown_file(path: Path) -> ImportedSource:
    """Import Markdown as text while preserving its original structure."""

    return _import_utf8_text(Path(path), expected_suffixes={".md", ".markdown"})


def import_docx_file(path: Path) -> ImportedSource:
    """Extract paragraphs and simple table text from a DOCX zip container."""

    source_path = Path(path)
    _ensure_suffix(source_path, {".docx"})
    _ensure_size(source_path, DOCUMENT_FILE_SIZE_LIMIT)
    try:
        with zipfile.ZipFile(source_path, mode="r") as archive:
            if len(archive.infolist()) > DOCX_MAX_ARCHIVE_ENTRIES:
                raise SourceImportError("docx_invalid", source_path.name)
            try:
                document_info = archive.getinfo("word/document.xml")
            except KeyError as error:
                raise SourceImportError(
                    "docx_missing_document",
                    source_path.name,
                ) from error
            if document_info.flag_bits & 0x1:
                raise SourceImportError("docx_invalid", source_path.name)
            if document_info.file_size > DOCX_XML_SIZE_LIMIT:
                raise SourceImportError("file_too_large", source_path.name)
            document_xml = archive.read(document_info)
    except SourceImportError:
        raise
    except (OSError, RuntimeError, zipfile.BadZipFile) as error:
        raise SourceImportError("docx_invalid", source_path.name) from error

    try:
        root = _parse_docx_xml(document_xml)
    except _DocxComplexityError as error:
        raise SourceImportError("file_too_large", source_path.name) from error
    except (ElementTree.ParseError, LookupError, UnicodeError, ValueError) as error:
        raise SourceImportError("docx_invalid", source_path.name) from error

    text = _extract_docx_text(root).strip()
    if not text:
        raise SourceImportError("empty_file", source_path.name)
    return _build_imported_source(
        source_path,
        text,
        warnings=("docx_text_only",),
    )


def import_pdf_file(path: Path) -> ImportedSource:
    """Fail safely because the public package does not bundle a PDF parser."""

    source_path = Path(path)
    _ensure_suffix(source_path, {".pdf"})
    _ensure_size(source_path, DOCUMENT_FILE_SIZE_LIMIT)
    raise SourceImportError("pdf_unavailable", source_path.name)


def _import_utf8_text(
    path: Path,
    *,
    expected_suffixes: set[str],
) -> ImportedSource:
    _ensure_suffix(path, expected_suffixes)
    _ensure_size(path, TEXT_FILE_SIZE_LIMIT)
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise SourceImportError("read_failed", path.name) from error
    if not raw:
        raise SourceImportError("empty_file", path.name)

    warnings: tuple[str, ...] = ()
    try:
        text = raw.decode("utf-8")
        if text.startswith("\ufeff"):
            text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            encoding = locale.getpreferredencoding(False) or "utf-8"
            if encoding.casefold().replace("_", "-") in {"utf-8", "utf8"}:
                raise SourceImportError("read_failed", path.name)
            try:
                text = raw.decode(encoding)
            except (LookupError, UnicodeDecodeError) as error:
                raise SourceImportError("read_failed", path.name) from error
            warnings = ("system_encoding_fallback",)

    if not text.strip():
        raise SourceImportError("empty_file", path.name)
    return _build_imported_source(path, text, warnings=warnings)


def _build_imported_source(
    path: Path,
    text: str,
    *,
    warnings: tuple[str, ...],
) -> ImportedSource:
    suffix = path.suffix.casefold()
    safe_label = path.name.replace("\r", " ").replace("\n", " ")
    return ImportedSource(
        filename=path.name,
        suffix=suffix,
        text=text,
        char_count=len(text),
        warnings=warnings,
        source_label=safe_label,
    )


def merge_imported_source_text(
    existing_text: str,
    imported: ImportedSource,
) -> tuple[str, bool]:
    """Append safely when material exists; never overwrite it silently."""

    if not existing_text.strip():
        return imported.text, False
    combined = (
        existing_text
        + f"\n\n--- {imported.source_label} ---\n\n"
        + imported.text
    )
    return combined, True


def _ensure_regular_file(path: Path) -> None:
    if not path.exists() or not path.is_file():
        raise SourceImportError("file_not_found", path.name)


def _ensure_suffix(path: Path, expected_suffixes: set[str]) -> None:
    _ensure_regular_file(path)
    if path.suffix.casefold() not in expected_suffixes:
        if path.suffix.casefold() == ".doc":
            raise SourceImportError("legacy_doc", path.name)
        raise SourceImportError("unsupported_type", path.name)


def _ensure_size(path: Path, limit: int) -> None:
    try:
        size = path.stat().st_size
    except OSError as error:
        raise SourceImportError("read_failed", path.name) from error
    if size > limit:
        raise SourceImportError("file_too_large", path.name)


def _extract_docx_text(root: ElementTree.Element) -> str:
    body = next((node for node in root.iter() if _local_name(node) == "body"), None)
    if body is None:
        return ""

    blocks: list[str] = []
    for child in body:
        name = _local_name(child)
        if name == "p":
            blocks.append(_paragraph_text(child))
        elif name == "tbl":
            table_text = _table_text(child)
            if table_text:
                blocks.append(table_text)
    return "\n".join(blocks)


class _DocxComplexityError(ValueError):
    pass


class _LimitedTreeBuilder(ElementTree.TreeBuilder):
    def __init__(self):
        super().__init__()
        self.element_count = 0
        self.text_character_count = 0

    def start(self, tag, attrs):
        self.element_count += 1
        if self.element_count > DOCX_ELEMENT_LIMIT:
            raise _DocxComplexityError("too many XML elements")
        return super().start(tag, attrs)

    def data(self, data):
        self.text_character_count += len(data)
        if self.text_character_count > DOCX_TEXT_CHARACTER_LIMIT:
            raise _DocxComplexityError("too much XML text")
        return super().data(data)


def _parse_docx_xml(document_xml: bytes) -> ElementTree.Element:
    security_scan = b"".join(document_xml.replace(b"\x00", b"").upper().split())
    if b"<!DOCTYPE" in security_scan or b"<!ENTITY" in security_scan:
        raise ElementTree.ParseError("document type declarations are not allowed")
    parser = ElementTree.XMLParser(target=_LimitedTreeBuilder())
    parser.feed(document_xml)
    return parser.close()


def _paragraph_text(paragraph: ElementTree.Element) -> str:
    parts: list[str] = []
    for node in paragraph.iter():
        name = _local_name(node)
        if name == "t" and node.text:
            parts.append(node.text)
        elif name == "tab":
            parts.append("\t")
        elif name in {"br", "cr"}:
            parts.append("\n")
    return "".join(parts)


def _table_text(table: ElementTree.Element) -> str:
    rows: list[str] = []
    for row in (node for node in table if _local_name(node) == "tr"):
        cells: list[str] = []
        for cell in (node for node in row if _local_name(node) == "tc"):
            paragraphs = [
                _paragraph_text(node).strip()
                for node in cell.iter()
                if _local_name(node) == "p"
            ]
            cells.append("\n".join(part for part in paragraphs if part))
        if cells:
            rows.append("\t".join(cells))
    return "\n".join(rows)


def _local_name(element: ElementTree.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]
