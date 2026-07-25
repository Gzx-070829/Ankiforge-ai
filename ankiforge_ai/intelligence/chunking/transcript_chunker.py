"""Timestamp-friendly bounded transcript splitting."""

from .token_budget import _bounded_split_tuple, iter_text_to_budget


def iter_transcript_text(
    text: str,
    *,
    target_chars: int,
    max_chars: int,
):
    yield from iter_text_to_budget(
        text,
        target_chars=target_chars,
        max_chars=max_chars,
    )


def split_transcript_text(
    text: str,
    *,
    target_chars: int,
    max_chars: int,
) -> tuple[str, ...]:
    return _bounded_split_tuple(
        iter_transcript_text(
            text,
            target_chars=target_chars,
            max_chars=max_chars,
        )
    )
