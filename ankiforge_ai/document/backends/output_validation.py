from __future__ import annotations

import re
import unicodedata


_MAX_LEXICAL_TOKEN_CHARS = 4_096
_MAX_HTML_TAG_CHARS = 1_024
_CREDENTIAL_LIKE = re.compile(
    r"(?:\bsk-[A-Za-z0-9_-]{12,}\b|"
    r"\bbearer\s+[A-Za-z0-9._~+/=-]{12,}\b|"
    r"\bAKIA[A-Z0-9]{16}\b)",
    re.IGNORECASE,
)


def validate_safe_output_text(value: str) -> None:
    if not isinstance(value, str):
        raise ValueError("unsafe backend output")
    if (
        "\x00" in value
        or _contains_unsafe_path_token(value)
        or _CREDENTIAL_LIKE.search(value)
    ):
        raise ValueError("unsafe backend output")


def _contains_unsafe_path_token(value: str) -> bool:
    index = 0
    token_chars = 0
    length = len(value)
    while index < length:
        character = value[index]
        if character.isspace():
            token_chars = 0
            index += 1
            continue
        token_chars += 1
        if token_chars > _MAX_LEXICAL_TOKEN_CHARS:
            return True

        if (
            character.isascii()
            and character.isalpha()
            and index + 2 < length
            and value[index + 1] == ":"
            and value[index + 2] in "/\\"
            and _is_lexical_root(value, index)
        ):
            return True

        uri_end = _uri_end(value, index)
        if uri_end is not None:
            token_chars += uri_end - index - 1
            if token_chars > _MAX_LEXICAL_TOKEN_CHARS:
                return True
            index = uri_end
            continue

        closing_tag_end = _html_closing_tag_end(value, index)
        if closing_tag_end is not None:
            token_chars += closing_tag_end - index - 1
            if token_chars > _MAX_LEXICAL_TOKEN_CHARS:
                return True
            index = closing_tag_end
            continue

        if (
            character == "/"
            and _is_html_self_closing_marker(value, index)
        ):
            index += 1
            continue
        if character in "/\\" and _is_lexical_root(value, index):
            return True
        index += 1
    return False


def _is_lexical_root(value: str, index: int) -> bool:
    if index == 0:
        return True
    previous = value[index - 1]
    if previous.isspace():
        return True
    category = unicodedata.category(previous)
    return category[0] in {"P", "S"} and previous not in "/\\"


def _uri_end(value: str, start: int):
    if not _is_lexical_root(value, start):
        return None
    length = len(value)
    if start >= length or not value[start].isascii() or not value[start].isalpha():
        return None
    index = start + 1
    while index < length:
        character = value[index]
        if character == ":":
            break
        if not (
            character.isascii()
            and (character.isalnum() or character in "+.-")
        ):
            return None
        index += 1
    if index + 2 >= length or value[index : index + 3] != "://":
        return None
    index += 3
    while index < length and not value[index].isspace():
        if value[index] in ">\"'":
            break
        index += 1
    return index


def _html_closing_tag_end(value: str, start: int):
    length = len(value)
    if (
        start + 3 >= length
        or value[start : start + 2] != "</"
        or not value[start + 2].isascii()
        or not value[start + 2].isalpha()
    ):
        return None
    index = start + 3
    while index < length:
        character = value[index]
        if character == ">":
            return index + 1
        if character.isspace():
            while index < length and value[index].isspace():
                index += 1
            return index + 1 if index < length and value[index] == ">" else None
        if not (
            character.isascii()
            and (character.isalnum() or character in "-_:")
        ):
            return None
        index += 1
    return None


def _is_html_self_closing_marker(value: str, slash: int) -> bool:
    if slash + 1 >= len(value) or value[slash + 1] != ">":
        return False
    minimum = max(0, slash - _MAX_HTML_TAG_CHARS)
    opening = value.rfind("<", minimum, slash)
    if opening < 0 or opening + 1 >= slash:
        return False
    first = value[opening + 1]
    if not first.isascii() or not first.isalpha():
        return False

    preceding = slash - 1
    while preceding > opening and value[preceding].isspace():
        preceding -= 1
    if value[preceding] == "=":
        return False

    quote = None
    index = opening + 1
    while index < slash:
        character = value[index]
        if character in "\r\n<>":
            return False
        if quote is None and character in "\"'":
            quote = character
        elif quote == character:
            quote = None
        index += 1
    return quote is None
