"""Character-budget splitting with no tokenizer or model dependency."""

from itertools import islice


MAX_CHUNK_CHARS = 12_000
MAX_DOCUMENT_CHUNKS = 48


def iter_text_to_budget(
    text: str,
    *,
    target_chars: int,
    max_chars: int,
):
    """Yield bounded pieces lazily without dropping or overlapping characters."""

    if not isinstance(text, str):
        raise TypeError("text must be a string")
    _validate_budget(target_chars, max_chars)
    if len(text) <= max_chars:
        yield text
        return

    start = 0
    length = len(text)
    while length - start > max_chars:
        preferred_end = min(length, start + target_chars)
        hard_end = min(length, start + max_chars)
        split_at = _preferred_split(text, start, preferred_end, hard_end)
        yield text[start:split_at]
        start = split_at
    if start < length:
        yield text[start:]


def split_text_to_budget(
    text: str,
    *,
    target_chars: int,
    max_chars: int,
) -> tuple[str, ...]:
    """Split text without dropping characters, preferring structural separators."""

    return _bounded_split_tuple(
        iter_text_to_budget(
            text,
            target_chars=target_chars,
            max_chars=max_chars,
        )
    )


def _preferred_split(text: str, start: int, preferred_end: int, hard_end: int) -> int:
    minimum = start + max(1, (preferred_end - start) // 2)
    for separator in ("\n\n", "\n", ". ", "。", "; ", "；", " "):
        index = text.rfind(separator, minimum, preferred_end)
        if index >= minimum:
            return index + len(separator)
    for separator in ("\n\n", "\n", ". ", "。", "; ", "；", " "):
        index = text.rfind(separator, preferred_end, hard_end)
        if index >= preferred_end:
            return index + len(separator)
    return preferred_end if preferred_end > start else hard_end


def _validate_budget(target_chars: int, max_chars: int) -> None:
    for value, name in (
        (target_chars, "target_chars"),
        (max_chars, "max_chars"),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    if target_chars > max_chars:
        raise ValueError("target_chars must not exceed max_chars")
    if max_chars > MAX_CHUNK_CHARS:
        raise ValueError("max_chars must not exceed MAX_CHUNK_CHARS")


def _bounded_split_tuple(pieces) -> tuple[str, ...]:
    result = tuple(islice(iter(pieces), MAX_DOCUMENT_CHUNKS + 1))
    if len(result) > MAX_DOCUMENT_CHUNKS:
        raise ValueError("split exceeds MAX_DOCUMENT_CHUNKS")
    return result
