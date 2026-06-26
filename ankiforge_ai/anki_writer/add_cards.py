"""Writes approved GeneratedCard objects into the Anki collection.

Deliberately does nothing destructive: it only ever calls col.add_note,
never deletes or overwrites existing notes. Cards the user did not approve
(card.approved == False) are silently skipped.
"""

from dataclasses import dataclass
from typing import Iterable, List, Set, Tuple


@dataclass
class AddCardsResult:
    added: int = 0
    skipped_duplicates: int = 0


DuplicateKey = Tuple[str, str]


def add_cards_to_deck(cards: List, deck_name: str) -> AddCardsResult:
    """
    Add all approved cards to `deck_name` (created if it doesn't exist yet).

    Returns counts for cards added and cards skipped because the same note
    type already has the same Front + Source. Existing notes are never edited.
    """
    from aqt import mw

    from .note_types import ensure_note_type

    col = mw.col
    model = ensure_note_type()
    existing_keys = _load_existing_duplicate_keys(col, model)
    writable_cards, skipped_duplicates = split_new_and_duplicate_cards(
        cards,
        existing_keys,
    )

    deck_id = col.decks.id(deck_name)
    added = 0

    for card in writable_cards:
        front = _required_text(card.front, "Front")
        back = _required_text(card.back, "Back")
        tags = normalize_tags(card.tags)

        note = col.new_note(model)
        note["Front"] = front
        note["Back"] = back
        note["Extra"] = _optional_text(card.extra)
        note["Source"] = _optional_text(card.source)
        note["Tags"] = format_tags_field(tags)

        for tag in tags:
            note.add_tag(tag)

        col.add_note(note, deck_id)
        added += 1

    if added:
        mw.requireReset()

    return AddCardsResult(added=added, skipped_duplicates=skipped_duplicates)


def split_new_and_duplicate_cards(
    cards: Iterable,
    existing_keys: Iterable[DuplicateKey],
) -> Tuple[List, int]:
    """Return approved, non-duplicate cards plus a skipped duplicate count."""
    seen: Set[DuplicateKey] = {
        make_duplicate_key(front, source) for front, source in existing_keys
    }
    writable_cards = []
    skipped_duplicates = 0

    for card in cards:
        if not card.approved:
            continue

        front = _required_text(card.front, "Front")
        _required_text(card.back, "Back")
        key = make_duplicate_key(front, card.source)
        if key in seen:
            skipped_duplicates += 1
            continue

        seen.add(key)
        writable_cards.append(card)

    return writable_cards, skipped_duplicates


def make_duplicate_key(front, source) -> DuplicateKey:
    """Duplicate rule for v0.1.2: same note type, same Front, same Source."""
    return (normalize_duplicate_text(front), normalize_duplicate_text(source))


def normalize_duplicate_text(value) -> str:
    """Normalize duplicate keys with strip + whitespace collapsing only."""
    return " ".join(str(value or "").split())


def format_tags_field(tags) -> str:
    return " ".join(normalize_tags(tags))


def normalize_tags(tags) -> List[str]:
    normalized = []
    seen = set()
    for tag in tags or []:
        text = _optional_text(tag)
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


def _load_existing_duplicate_keys(col, model) -> Set[DuplicateKey]:
    note_ids = _note_ids_for_model(col, model)
    keys = set()

    for note_id in note_ids:
        note = col.get_note(note_id)
        keys.add(
            make_duplicate_key(
                _note_field(note, "Front"),
                _note_field(note, "Source"),
            )
        )

    return keys


def _note_ids_for_model(col, model) -> List[int]:
    """Return all note ids for a model without relying on Anki search syntax."""
    model_id = model.get("id")
    if model_id is None:
        return []
    return list(col.db.list("select id from notes where mid = ?", model_id))


def _note_field(note, field_name: str) -> str:
    try:
        return note[field_name]
    except KeyError:
        return ""


def _required_text(value, field_name: str) -> str:
    text = _optional_text(value)
    if not text:
        raise ValueError(f"已勾选卡片缺少 {field_name}，请先补全后再写入。")
    return text


def _optional_text(value) -> str:
    return str(value or "").strip()
