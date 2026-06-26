"""
Writes approved GeneratedCard objects into the Anki collection.

Deliberately does nothing destructive: it only ever calls col.add_note,
never deletes or overwrites existing notes. Cards the user did not approve
(card.approved == False) are silently skipped.
"""

from typing import List

from aqt import mw

from .note_types import ensure_note_type


def add_cards_to_deck(cards: List, deck_name: str) -> int:
    """
    Add all approved cards to `deck_name` (created if it doesn't exist yet).
    Returns the number of cards actually added.
    """
    col = mw.col
    model = ensure_note_type()

    deck_id = col.decks.id(deck_name)
    added = 0

    for card in cards:
        if not card.approved:
            continue

        front = _required_text(card.front, "Front")
        back = _required_text(card.back, "Back")

        note = col.new_note(model)
        note["Front"] = front
        note["Back"] = back
        note["Extra"] = _optional_text(card.extra)
        note["Source"] = _optional_text(card.source)

        for tag in card.tags:
            note.add_tag(tag)

        col.add_note(note, deck_id)
        added += 1

    if added:
        mw.requireReset()

    return added


def _required_text(value, field_name: str) -> str:
    text = _optional_text(value)
    if not text:
        raise ValueError(f"已勾选卡片缺少 {field_name}，请先补全后再写入。")
    return text


def _optional_text(value) -> str:
    return str(value or "").strip()
