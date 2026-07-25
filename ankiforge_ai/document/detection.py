import posixpath
import json
import re
import stat
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple, Union
from xml.etree import ElementTree

from .errors import DocumentImportError
from .limits import DEFAULT_DOCUMENT_LIMITS, DocumentLimits


DETECTION_PREFIX_BYTES = 64 * 1024
_XML_ROOT = re.compile(
    r"^\s*(?:<\?xml[^>]*\?>\s*)?<([A-Za-z_][A-Za-z0-9_.:-]*)",
    re.DOTALL,
)
_TEXT_EXTENSIONS: Dict[str, str] = {
    ".txt": "text",
    ".log": "text",
    ".md": "markdown",
    ".markdown": "markdown",
    ".rst": "rst",
    ".org": "org",
    ".tex": "latex",
    ".latex": "latex",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".csv": "csv",
    ".tsv": "tsv",
    ".jsonl": "jsonl",
    ".srt": "srt",
    ".vtt": "vtt",
    ".html": "html",
    ".htm": "html",
    ".xml": "xml",
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".rs": "rust",
    ".go": "go",
    ".sql": "sql",
    ".sh": "shell",
    ".ps1": "powershell",
}
_EXPECTED_EXTENSIONS: Dict[str, Tuple[str, ...]] = {
    "text": (".txt", ".log"),
    "markdown": (".md", ".markdown"),
    "json": (".json",),
    "ipynb": (".ipynb",),
    "xml": (".xml",),
    "html": (".html", ".htm", ".xhtml"),
    "docx": (".docx",),
    "pptx": (".pptx",),
    "xlsx": (".xlsx",),
    "epub": (".epub",),
    "pdf": (".pdf",),
}
_MEDIA_TYPES = {
    "text": "text/plain",
    "markdown": "text/markdown",
    "json": "application/json",
    "ipynb": "application/x-ipynb+json",
    "xml": "application/xml",
    "html": "text/html",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "epub": "application/epub+zip",
    "pdf": "application/pdf",
    "zip": "application/zip",
}


@dataclass(frozen=True, repr=False)
class DetectedFileType:
    file_type: str
    extension: str
    media_type: str
    is_text: bool
    encoding: Optional[str] = None
    confidence: str = "high"
    warnings: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.file_type, str) or not self.file_type:
            raise ValueError("file_type must be a non-empty string")
        if self.extension and (
            not self.extension.startswith(".")
            or self.extension != self.extension.lower()
        ):
            raise ValueError("extension must be lowercase and start with a dot")
        if self.confidence not in {"high", "medium", "low"}:
            raise ValueError("confidence must be high, medium, or low")
        object.__setattr__(self, "warnings", tuple(self.warnings))

    def __repr__(self) -> str:
        return (
            f"DetectedFileType(file_type={self.file_type!r}, "
            f"extension={self.extension!r}, confidence={self.confidence!r}, "
            f"warnings={self.warnings!r})"
        )

    def to_safe_dict(self) -> Dict[str, object]:
        return {
            "file_type": self.file_type,
            "extension": self.extension,
            "media_type": self.media_type,
            "is_text": self.is_text,
            "encoding": self.encoding,
            "confidence": self.confidence,
            "warnings": list(self.warnings),
        }


def _error(code: str, action: str = "choose_another_file") -> DocumentImportError:
    return DocumentImportError(
        code=code,
        message_key=f"document.error.{code}",
        action_key=f"document.action.{action}",
    )


def _encoding_from_bom(prefix: bytes) -> Optional[str]:
    if prefix.startswith(b"\xff\xfe\x00\x00"):
        return "utf-32-le"
    if prefix.startswith(b"\x00\x00\xfe\xff"):
        return "utf-32-be"
    if prefix.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if prefix.startswith(b"\xff\xfe"):
        return "utf-16-le"
    if prefix.startswith(b"\xfe\xff"):
        return "utf-16-be"
    return None


def _decode_prefix(prefix: bytes, encoding: Optional[str]) -> Tuple[str, str]:
    selected = encoding or "utf-8"
    try:
        text = prefix.decode(selected)
    except UnicodeDecodeError:
        raise _error("binary_file") from None
    if text.startswith("\ufeff"):
        text = text[1:]
    return text, selected


def _looks_binary(prefix: bytes, bom_encoding: Optional[str]) -> bool:
    if bom_encoding is not None:
        return False
    if b"\x00" in prefix:
        return True
    controls = sum(
        byte < 32 and byte not in {8, 9, 10, 12, 13} for byte in prefix
    )
    return controls / max(len(prefix), 1) > 0.05


def _warnings_for(file_type: str, extension: str) -> Tuple[str, ...]:
    expected = _EXPECTED_EXTENSIONS.get(file_type)
    if expected is not None and extension not in expected:
        return ("extension_mismatch",)
    return ()


def _detected(
    file_type: str,
    extension: str,
    *,
    is_text: bool,
    encoding: Optional[str] = None,
    confidence: str = "high",
) -> DetectedFileType:
    return DetectedFileType(
        file_type=file_type,
        extension=extension,
        media_type=_MEDIA_TYPES.get(
            file_type,
            "text/plain" if is_text else "application/octet-stream",
        ),
        is_text=is_text,
        encoding=encoding,
        confidence=confidence,
        warnings=_warnings_for(file_type, extension),
    )


def _inspect_zip(
    path: Path, extension: str, limits: DocumentLimits
) -> DetectedFileType:
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if len(infos) > limits.max_archive_members:
                raise _error("archive_too_many_members")
            total_uncompressed = 0
            names = set()
            canonical_names = set()
            for info in infos:
                normalized = info.filename.replace("\\", "/")
                if (
                    normalized.startswith("/")
                    or re.match(r"^[A-Za-z]:/", normalized)
                    or any(part == ".." for part in normalized.split("/"))
                    or stat.S_ISLNK(info.external_attr >> 16)
                ):
                    raise _error("unsafe_archive_member")
                if info.file_size > limits.max_member_bytes:
                    raise _error("archive_member_too_large")
                total_uncompressed += info.file_size
                if total_uncompressed > limits.max_archive_uncompressed_bytes:
                    raise _error("archive_too_large")
                if info.file_size and (
                    info.compress_size == 0
                    or info.file_size / info.compress_size
                    > limits.max_archive_compression_ratio
                ):
                    raise _error("suspicious_archive_compression")
                canonical_name = unicodedata.normalize(
                    "NFKC",
                    posixpath.normpath(normalized),
                ).casefold()
                if canonical_name in canonical_names:
                    raise _error("duplicate_archive_member")
                canonical_names.add(canonical_name)
                names.add(normalized)

            if any(name.lower().endswith("vbaproject.bin") for name in names):
                raise _error("office_macros_not_allowed")
            has_content_types = "[Content_Types].xml" in names
            if has_content_types and "word/document.xml" in names:
                return _detected("docx", extension, is_text=False)
            if has_content_types and "ppt/presentation.xml" in names:
                return _detected("pptx", extension, is_text=False)
            if has_content_types and "xl/workbook.xml" in names:
                return _detected("xlsx", extension, is_text=False)
            if "mimetype" in names and "META-INF/container.xml" in names:
                info = archive.getinfo("mimetype")
                if info.file_size <= 64:
                    with archive.open(info) as member:
                        if member.read(64).strip() == b"application/epub+zip":
                            return _detected("epub", extension, is_text=False)
            if extension in {".docx", ".pptx", ".xlsx", ".epub"}:
                raise _error("invalid_archive")
            return _detected("zip", extension, is_text=False, confidence="medium")
    except DocumentImportError:
        raise
    except (OSError, zipfile.BadZipFile, KeyError):
        raise _error("invalid_archive") from None


def _detect_json(
    text: str, extension: str, complete: bool, encoding: str
) -> Optional[DetectedFileType]:
    stripped = text.lstrip()
    if not stripped.startswith(("{", "[")):
        return None
    parsed = None
    if complete:
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, RecursionError):
            if extension in {".json", ".ipynb"}:
                raise _error("malformed_file") from None
            return None
    if (
        isinstance(parsed, dict)
        and isinstance(parsed.get("cells"), list)
        and isinstance(parsed.get("nbformat"), int)
    ) or (
        not complete
        and '"cells"' in text
        and '"nbformat"' in text
    ):
        return _detected("ipynb", extension, is_text=True, encoding=encoding)
    return _detected("json", extension, is_text=True, encoding=encoding)


def _detect_xml(
    text: str, extension: str, complete: bool, encoding: str
) -> Optional[DetectedFileType]:
    lowered = text.lstrip().lower()
    if not lowered.startswith("<"):
        return None
    if "<!doctype" in lowered or "<!entity" in lowered:
        raise _error("unsafe_xml")
    match = _XML_ROOT.match(text)
    if not match:
        if extension in {".xml", ".html", ".htm", ".xhtml"}:
            raise _error("malformed_file")
        return None
    if complete:
        try:
            ElementTree.fromstring(text)
        except ElementTree.ParseError:
            if extension in {".xml", ".html", ".htm", ".xhtml"}:
                raise _error("malformed_file") from None
            return None
    root = match.group(1).split(":")[-1].lower()
    file_type = "html" if root == "html" else "xml"
    return _detected(file_type, extension, is_text=True, encoding=encoding)


def detect_file_type(
    path: Union[str, Path],
    limits: DocumentLimits = DEFAULT_DOCUMENT_LIMITS,
) -> DetectedFileType:
    source = Path(path)
    try:
        size = source.stat().st_size
    except OSError:
        raise _error("file_unavailable", "reselect_file") from None
    if size == 0:
        raise _error("empty_file")
    if size > limits.max_source_file_bytes:
        raise _error("file_too_large")

    extension = source.suffix.lower()
    try:
        with source.open("rb") as stream:
            prefix = stream.read(DETECTION_PREFIX_BYTES)
    except OSError:
        raise _error("file_unavailable", "reselect_file") from None

    if prefix.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        return _inspect_zip(source, extension, limits)
    if prefix.startswith(b"%PDF-"):
        if extension in _TEXT_EXTENSIONS or extension in {".json", ".ipynb"}:
            raise _error("risky_extension_mismatch")
        return _detected("pdf", extension, is_text=False)
    if extension in {".docx", ".pptx", ".xlsx", ".epub", ".zip", ".pdf"}:
        raise _error("malformed_file")

    bom_encoding = _encoding_from_bom(prefix)
    if _looks_binary(prefix, bom_encoding):
        if extension in _TEXT_EXTENSIONS or extension in {".json", ".ipynb"}:
            raise _error("binary_extension_mismatch")
        raise _error("unsupported_binary")
    try:
        text, encoding = _decode_prefix(prefix, bom_encoding)
    except DocumentImportError:
        if extension in _TEXT_EXTENSIONS or extension in {".json", ".ipynb"}:
            raise _error("binary_extension_mismatch") from None
        raise

    complete = size <= len(prefix)
    json_type = _detect_json(text, extension, complete, encoding)
    if json_type is not None:
        return _enforce_text_size(json_type, size, limits)
    xml_type = _detect_xml(text, extension, complete, encoding)
    if xml_type is not None:
        return _enforce_text_size(xml_type, size, limits)
    if extension in {".json", ".ipynb", ".xml", ".html", ".htm", ".xhtml"}:
        raise _error("malformed_file")

    file_type = _TEXT_EXTENSIONS.get(extension, "text")
    return _enforce_text_size(
        _detected(
            file_type,
            extension,
            is_text=True,
            encoding=encoding,
            confidence="high" if extension in _TEXT_EXTENSIONS else "medium",
        ),
        size,
        limits,
    )


def _enforce_text_size(
    detected: DetectedFileType, size: int, limits: DocumentLimits
) -> DetectedFileType:
    if detected.is_text and size > limits.max_text_file_bytes:
        raise _error("file_too_large")
    return detected
