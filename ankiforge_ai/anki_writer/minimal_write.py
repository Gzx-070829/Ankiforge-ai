"""Minimal explicit Anki note creation for an immutable beginner command."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ..pipeline.write_traceability import validate_tags


WRITE_TARGET_ERROR_COPY = (
    "无法使用所选牌组、笔记类型或字段。没有创建新的 Anki note。"
)
WRITE_CARD_ERROR_COPY = "这张候选卡写入失败；没有修改已有 note 或 card。"


class BeginnerWrittenCardState(str, Enum):
    CREATED = "created"
    FAILED = "failed"


class BeginnerWriteResultState(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass(frozen=True, repr=False)
class BeginnerWriteCardCommand:
    candidate_id: str
    front: str = field(repr=False)
    back: str = field(repr=False)
    source: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        for value, name in (
            (self.candidate_id, "candidate_id"),
            (self.front, "front"),
            (self.back, "back"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string.")
        if not isinstance(self.source, str):
            raise ValueError("source must be a string.")

    def __repr__(self) -> str:
        return (
            "BeginnerWriteCardCommand("
            f"candidate_id={self.candidate_id!r}, "
            f"front_chars={len(self.front)}, back_chars={len(self.back)}, "
            f"source_chars={len(self.source)})"
        )

    def to_safe_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "front_chars": len(self.front),
            "back_chars": len(self.back),
            "source_chars": len(self.source),
        }


@dataclass(frozen=True, repr=False)
class BeginnerWriteCommand:
    snapshot_id: str
    deck_id: int
    deck_name: str
    note_type_id: int
    note_type_name: str
    front_field: str
    back_field: str
    source_field: Optional[str]
    cards: tuple[BeginnerWriteCardCommand, ...] = field(repr=False)
    skipped_count: int = 0
    tags: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot_id, str) or not self.snapshot_id.strip():
            raise ValueError("snapshot_id must be a non-empty string.")
        for value, name in (
            (self.deck_id, "deck_id"),
            (self.note_type_id, "note_type_id"),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{name} must be an integer.")
        for value, name in (
            (self.deck_name, "deck_name"),
            (self.note_type_name, "note_type_name"),
            (self.front_field, "front_field"),
            (self.back_field, "back_field"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string.")
        if self.front_field == self.back_field:
            raise ValueError("front_field and back_field must be different.")
        if self.source_field is not None and (
            not isinstance(self.source_field, str) or not self.source_field.strip()
        ):
            raise ValueError("source_field must be non-empty or None.")
        mapped_fields = tuple(
            item
            for item in (self.front_field, self.back_field, self.source_field)
            if item
        )
        if len(set(mapped_fields)) != len(mapped_fields):
            raise ValueError("mapped fields must be unique.")
        if not isinstance(self.cards, tuple) or not self.cards or not all(
            isinstance(item, BeginnerWriteCardCommand) for item in self.cards
        ):
            raise ValueError("cards must contain BeginnerWriteCardCommand values.")
        candidate_ids = tuple(item.candidate_id for item in self.cards)
        if len(set(candidate_ids)) != len(candidate_ids):
            raise ValueError("candidate ids must be unique.")
        _validate_count(self.skipped_count, "skipped_count")
        validate_tags(self.tags, allow_empty=True)

    @property
    def requested_count(self) -> int:
        return len(self.cards)

    def __repr__(self) -> str:
        return (
            "BeginnerWriteCommand("
            f"snapshot_id={self.snapshot_id!r}, deck_id={self.deck_id}, "
            f"note_type_id={self.note_type_id}, "
            f"requested_count={self.requested_count}, "
            f"skipped_count={self.skipped_count}, tag_count={len(self.tags)})"
        )

    def to_safe_dict(self) -> dict:
        return {
            "snapshot_id": self.snapshot_id,
            "deck_id": self.deck_id,
            "deck_name": self.deck_name,
            "note_type_id": self.note_type_id,
            "note_type_name": self.note_type_name,
            "front_field": self.front_field,
            "back_field": self.back_field,
            "source_field": self.source_field,
            "requested_count": self.requested_count,
            "skipped_count": self.skipped_count,
            "tag_count": len(self.tags),
        }


@dataclass(frozen=True)
class BeginnerWrittenCardResult:
    candidate_id: str
    state: BeginnerWrittenCardState
    note_id: Optional[int] = None
    error_code: Optional[str] = None
    user_message: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_id, str) or not self.candidate_id.strip():
            raise ValueError("candidate_id must be a non-empty string.")
        if not isinstance(self.state, BeginnerWrittenCardState):
            raise ValueError("state must be a BeginnerWrittenCardState.")
        if self.note_id is not None and (
            isinstance(self.note_id, bool) or not isinstance(self.note_id, int)
        ):
            raise ValueError("note_id must be an integer or None.")


@dataclass(frozen=True)
class BeginnerWriteResult:
    snapshot_id: str
    card_results: tuple[BeginnerWrittenCardResult, ...]
    skipped_count: int = 0

    @property
    def created_note_ids(self) -> tuple[int, ...]:
        return tuple(
            item.note_id
            for item in self.card_results
            if item.state is BeginnerWrittenCardState.CREATED
            and item.note_id is not None
        )

    @property
    def success_count(self) -> int:
        return len(self.created_note_ids)

    @property
    def failed_count(self) -> int:
        return sum(
            item.state is BeginnerWrittenCardState.FAILED
            for item in self.card_results
        )

    @property
    def state(self) -> BeginnerWriteResultState:
        if self.success_count and self.failed_count:
            return BeginnerWriteResultState.PARTIAL
        if self.success_count:
            return BeginnerWriteResultState.SUCCESS
        return BeginnerWriteResultState.FAILED

    @property
    def user_message(self) -> str:
        if self.state is BeginnerWriteResultState.SUCCESS:
            return "写入完成，请在 Anki 中检查新卡片。"
        if self.state is BeginnerWriteResultState.PARTIAL:
            return "部分候选卡写入成功；请查看逐张结果。"
        return "写入失败。没有误报成功，也没有修改已有 note 或 card。"

    def to_safe_dict(self) -> dict:
        return {
            "snapshot_id": self.snapshot_id,
            "state": self.state.value,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "created_note_ids": self.created_note_ids,
        }


class MinimalAnkiWriter:
    """Create only new notes in already-existing Anki structures."""

    def __init__(self, collection):
        self._collection = collection

    def write(self, command: BeginnerWriteCommand) -> BeginnerWriteResult:
        if not isinstance(command, BeginnerWriteCommand):
            raise ValueError("command must be a BeginnerWriteCommand.")
        try:
            note_type = self._validate_existing_target(command)
        except Exception:
            return _all_failed_result(
                command,
                "target_unavailable",
                WRITE_TARGET_ERROR_COPY,
            )

        results = []
        for card in command.cards:
            try:
                note = self._collection.new_note(note_type)
                note[command.front_field] = card.front
                note[command.back_field] = card.back
                if command.source_field:
                    note[command.source_field] = card.source
                if command.tags:
                    add_tag = getattr(note, "add_tag", None)
                    if not callable(add_tag):
                        raise ValueError("Anki note does not support tag application.")
                    for tag in command.tags:
                        add_tag(tag)
                operation_result = self._collection.add_note(note, command.deck_id)
                note_id = _created_note_id(operation_result, note)
                results.append(
                    BeginnerWrittenCardResult(
                        candidate_id=card.candidate_id,
                        state=BeginnerWrittenCardState.CREATED,
                        note_id=note_id,
                    )
                )
            except Exception:
                results.append(
                    BeginnerWrittenCardResult(
                        candidate_id=card.candidate_id,
                        state=BeginnerWrittenCardState.FAILED,
                        error_code="note_create_failed",
                        user_message=WRITE_CARD_ERROR_COPY,
                    )
                )
        return BeginnerWriteResult(
            snapshot_id=command.snapshot_id,
            card_results=tuple(results),
            skipped_count=command.skipped_count,
        )

    def _validate_existing_target(self, command: BeginnerWriteCommand):
        deck = self._collection.decks.get(command.deck_id)
        if (
            not isinstance(deck, dict)
            or deck.get("id") != command.deck_id
            or deck.get("name") != command.deck_name
        ):
            raise ValueError("deck is unavailable.")
        note_type = self._collection.models.get(command.note_type_id)
        if (
            not isinstance(note_type, dict)
            or note_type.get("id") != command.note_type_id
            or note_type.get("name") != command.note_type_name
        ):
            raise ValueError("note type is unavailable.")
        raw_fields = note_type.get("flds")
        if not isinstance(raw_fields, list):
            raise ValueError("note type fields are unavailable.")
        field_names = {
            item.get("name")
            for item in raw_fields
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        }
        required = {command.front_field, command.back_field}
        if command.source_field:
            required.add(command.source_field)
        if not required.issubset(field_names):
            raise ValueError("mapped fields are unavailable.")
        return note_type


def _all_failed_result(command, error_code, message):
    return BeginnerWriteResult(
        snapshot_id=command.snapshot_id,
        card_results=tuple(
            BeginnerWrittenCardResult(
                candidate_id=card.candidate_id,
                state=BeginnerWrittenCardState.FAILED,
                error_code=error_code,
                user_message=message,
            )
            for card in command.cards
        ),
        skipped_count=command.skipped_count,
    )


def _created_note_id(operation_result, note) -> int:
    candidates = (
        operation_result if isinstance(operation_result, int) else None,
        getattr(operation_result, "id", None),
        getattr(note, "id", None),
    )
    for value in candidates:
        if not isinstance(value, bool) and isinstance(value, int) and value > 0:
            return value
    raise ValueError("Anki did not return a created note id.")


def _validate_count(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer.")
