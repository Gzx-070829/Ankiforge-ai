import re
from os import PathLike, fspath
from typing import Union


MAX_SOURCE_LABEL_CHARS = 120
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]+")
_WHITESPACE = re.compile(r"\s+")


def get_safe_source_label(value: Union[str, PathLike]) -> str:
    raw = fspath(value) if not isinstance(value, str) else value
    if any(0xD800 <= ord(character) <= 0xDFFF for character in raw):
        raise ValueError("invalid Unicode in source label")
    normalized = raw.replace("\\", "/").rsplit("/", 1)[-1]
    normalized = _CONTROL_CHARACTERS.sub(" ", normalized)
    normalized = _WHITESPACE.sub(" ", normalized).strip()
    if not normalized or normalized in {".", ".."}:
        return "document"
    if len(normalized) > MAX_SOURCE_LABEL_CHARS:
        normalized = normalized[:MAX_SOURCE_LABEL_CHARS].rstrip()
    return normalized or "document"
