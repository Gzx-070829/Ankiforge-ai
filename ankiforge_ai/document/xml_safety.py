from __future__ import annotations

from xml.etree import ElementTree

from .errors import DocumentImportError
from .limits import DEFAULT_DOCUMENT_LIMITS, DocumentLimits


def _error(code: str) -> DocumentImportError:
    return DocumentImportError(
        code=code,
        message_key=f"document.error.{code}",
        action_key="document.action.choose_another_file",
    )


def _security_text(payload: bytes) -> str:
    encodings = []
    if payload.startswith((b"\xff\xfe", b"\xfe\xff")):
        encodings.append("utf-16")
    if payload.startswith((b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff")):
        encodings.insert(0, "utf-32")
    encodings.extend(("utf-8-sig", "ascii"))
    for encoding in encodings:
        try:
            return payload.decode(encoding).upper()
        except (UnicodeDecodeError, LookupError):
            pass
    return payload.replace(b"\x00", b"").decode("ascii", "ignore").upper()


class _BoundedBuilder(ElementTree.TreeBuilder):
    def __init__(self, limits: DocumentLimits):
        super().__init__()
        self.limits = limits
        self.depth = 0
        self.elements = 0
        self.text_chars = 0

    def start(self, tag, attrs):
        self.depth += 1
        self.elements += 1
        self.text_chars += sum(len(str(value)) for value in attrs.values())
        if (
            self.depth > self.limits.max_xml_depth
            or self.elements > self.limits.max_xml_elements
            or self.text_chars > self.limits.max_text_chars
        ):
            raise _error("document_too_complex")
        return super().start(tag, attrs)

    def end(self, tag):
        result = super().end(tag)
        self.depth -= 1
        return result

    def data(self, data):
        self.text_chars += len(data)
        if self.text_chars > self.limits.max_text_chars:
            raise _error("document_too_complex")
        return super().data(data)


def parse_xml_bounded(
    payload: bytes,
    limits: DocumentLimits = DEFAULT_DOCUMENT_LIMITS,
) -> ElementTree.Element:
    if not isinstance(payload, bytes):
        raise TypeError("payload must be bytes")
    security = "".join(_security_text(payload).split())
    if "<!DOCTYPE" in security or "<!ENTITY" in security:
        raise _error("xml_not_safe")
    try:
        parser = ElementTree.XMLParser(target=_BoundedBuilder(limits))
        for offset in range(0, len(payload), 64 * 1024):
            parser.feed(payload[offset : offset + 64 * 1024])
        return parser.close()
    except DocumentImportError:
        raise
    except (ElementTree.ParseError, LookupError, UnicodeError, ValueError):
        raise _error("malformed_file") from None


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
