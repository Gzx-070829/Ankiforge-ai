"""Pure helpers for the review workflow UI."""

from typing import Iterable, List, Sequence, Tuple

ALL_CHUNKS_LABEL = "全部 headings"


def format_chunk_label(chunk, index: int = 0) -> str:
    heading = str(getattr(chunk, "heading", "") or "Untitled").strip() or "Untitled"
    level = int(getattr(chunk, "level", 0) or 0)
    prefix = f"H{level}" if level > 0 else "Untitled"
    return f"{prefix} {heading}"


def chunks_for_combo_index(chunks: Sequence, combo_index: int, current_only: bool):
    """Map UI combo index to chunks without relying on label text."""
    if not current_only:
        return list(chunks), ALL_CHUNKS_LABEL

    chunk_index = combo_index - 1
    if chunk_index < 0 or chunk_index >= len(chunks):
        return [], ""

    chunk = chunks[chunk_index]
    return [chunk], format_chunk_label(chunk, chunk_index)


def cap_cards(cards: Iterable, max_cards: int) -> List:
    limit = max(0, int(max_cards or 0))
    return list(cards)[:limit]


def cap_cards_per_chunk(card_batches: Iterable[Iterable], max_cards_per_chunk: int) -> List:
    capped = []
    for cards in card_batches:
        capped.extend(cap_cards(cards, max_cards_per_chunk))
    return capped


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
