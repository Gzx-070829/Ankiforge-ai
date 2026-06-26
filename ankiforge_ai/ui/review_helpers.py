"""Pure helpers for the review workflow UI."""

from typing import Iterable, List, Sequence, Tuple


def format_chunk_label(chunk, index: int = 0) -> str:
    heading = str(getattr(chunk, "heading", "") or "Untitled").strip() or "Untitled"
    level = int(getattr(chunk, "level", 0) or 0)
    prefix = f"H{level}" if level > 0 else "Untitled"
    return f"{prefix} {heading}"


def summarize_text(text, max_chars: int = 90) -> str:
    normalized = " ".join(str(text or "").split())
    if len(normalized) <= max_chars:
        return normalized
    if max_chars <= 3:
        return normalized[:max_chars]
    return normalized[: max_chars - 3].rstrip() + "..."


def tags_to_text(tags: Iterable) -> str:
    return " ".join(str(tag).strip() for tag in tags or [] if str(tag).strip())


def tags_from_text(text: str) -> List[str]:
    raw = str(text or "")
    for separator in [",", "，", ";", "；", "\n", "\t"]:
        raw = raw.replace(separator, " ")

    tags = []
    seen = set()
    for token in raw.split(" "):
        tag = token.strip()
        if not tag or tag in seen:
            continue
        seen.add(tag)
        tags.append(tag)
    return tags


def invert_flags(flags: Sequence[bool]) -> List[bool]:
    return [not flag for flag in flags]


def remove_items_by_flags(items: Sequence, flags: Sequence[bool]) -> Tuple[List, int]:
    remaining = [item for item, selected in zip(items, flags) if not selected]
    return remaining, len(items) - len(remaining)


def keep_items_by_flags(items: Sequence, flags: Sequence[bool]) -> Tuple[List, int]:
    remaining = [item for item, selected in zip(items, flags) if selected]
    return remaining, len(items) - len(remaining)
