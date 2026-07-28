"""Bounded row-aware splitting for serialized table blocks."""

from itertools import chain

from .token_budget import _bounded_split_tuple, iter_text_to_budget


def iter_table_text(
    text: str,
    *,
    target_chars: int,
    max_chars: int,
):
    if len(text) <= max_chars:
        yield text
        return
    lines = iter(_iter_lines(text))
    header = next(lines, "")
    if len(header) + 1 >= max_chars:
        raise ValueError("table header exceeds chunk budget")
    first_row = next(lines, None)
    if first_row is None:
        yield from iter_text_to_budget(
            text,
            target_chars=target_chars,
            max_chars=max_chars,
        )
        return

    row_budget = max_chars - len(header) - 1
    target_row_budget = max(1, target_chars - len(header) - 1)

    current_rows = []
    current_length = len(header)
    for row in chain((first_row,), lines):
        addition = 1 + len(row)
        if current_rows and current_length + addition > target_chars:
            yield header + "\n" + "\n".join(current_rows)
            current_rows = []
            current_length = len(header)
        if current_length + addition <= max_chars:
            current_rows.append(row)
            current_length += addition
            if current_length >= target_chars:
                yield header + "\n" + "\n".join(current_rows)
                current_rows = []
                current_length = len(header)
            continue
        if current_rows:
            yield header + "\n" + "\n".join(current_rows)
            current_rows = []
            current_length = len(header)
        row_parts = iter_text_to_budget(
            row,
            target_chars=target_row_budget,
            max_chars=row_budget,
        )
        for part in row_parts:
            yield header + "\n" + part
    if current_rows:
        yield header + "\n" + "\n".join(current_rows)


def _iter_lines(text: str):
    """Yield lines lazily while recognizing LF, CRLF, and CR separators."""
    start = 0
    index = 0
    text_length = len(text)
    while index < text_length:
        character = text[index]
        if character not in {"\n", "\r"}:
            index += 1
            continue
        yield text[start:index]
        if (
            character == "\r"
            and index + 1 < text_length
            and text[index + 1] == "\n"
        ):
            index += 2
        else:
            index += 1
        start = index
    if start < text_length:
        yield text[start:text_length]


def split_table_text(
    text: str,
    *,
    target_chars: int,
    max_chars: int,
) -> tuple[str, ...]:
    return _bounded_split_tuple(
        iter_table_text(
            text,
            target_chars=target_chars,
            max_chars=max_chars,
        )
    )
