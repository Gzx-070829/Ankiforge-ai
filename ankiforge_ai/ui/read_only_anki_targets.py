"""Read-only Anki target discovery and beginner field-mapping previews."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


ANKI_TARGET_READ_ERROR_COPY = (
    "无法读取 Anki 牌组或笔记类型。没有写入 Anki。"
)
ANKI_DECK_EMPTY_COPY = "当前没有可选择的牌组。没有写入 Anki。"
ANKI_NOTE_TYPE_EMPTY_COPY = "当前没有可选择的笔记类型。没有写入 Anki。"
ANKI_FIELD_EMPTY_COPY = "所选笔记类型没有可映射字段。没有写入 Anki。"
ANKI_MAPPING_PREVIEW_SAFETY_COPY = "当前只是预览，尚未写入 Anki。"


class BeginnerAnkiReadState(str, Enum):
    IDLE = "idle"
    SUCCESS = "success"
    EMPTY = "empty"
    ERROR = "error"


@dataclass(frozen=True)
class BeginnerAnkiDeckOption:
    id: int
    name: str

    def __post_init__(self) -> None:
        _validate_id_and_name(self.id, self.name, "deck")


@dataclass(frozen=True)
class BeginnerAnkiNoteTypeOption:
    id: int
    name: str

    def __post_init__(self) -> None:
        _validate_id_and_name(self.id, self.name, "note type")


@dataclass(frozen=True)
class BeginnerAnkiTargetSnapshot:
    state: BeginnerAnkiReadState
    decks: tuple[BeginnerAnkiDeckOption, ...] = field(default_factory=tuple)
    note_types: tuple[BeginnerAnkiNoteTypeOption, ...] = field(
        default_factory=tuple
    )
    user_message: str = ""

    @property
    def success(self) -> bool:
        return self.state in {
            BeginnerAnkiReadState.SUCCESS,
            BeginnerAnkiReadState.EMPTY,
        }

    def to_safe_dict(self) -> dict:
        return {
            "state": self.state.value,
            "deck_count": len(self.decks),
            "note_type_count": len(self.note_types),
            "user_message": self.user_message,
            "read_only": True,
            "will_write_to_anki": False,
        }


@dataclass(frozen=True)
class BeginnerAnkiFieldSnapshot:
    state: BeginnerAnkiReadState
    note_type_id: Optional[int]
    fields: tuple[str, ...] = field(default_factory=tuple)
    user_message: str = ""

    @property
    def success(self) -> bool:
        return self.state in {
            BeginnerAnkiReadState.SUCCESS,
            BeginnerAnkiReadState.EMPTY,
        }

    def to_safe_dict(self) -> dict:
        return {
            "state": self.state.value,
            "note_type_id_present": self.note_type_id is not None,
            "field_count": len(self.fields),
            "user_message": self.user_message,
            "read_only": True,
            "will_write_to_anki": False,
        }


@dataclass(frozen=True)
class BeginnerFieldMappingPreview:
    deck: BeginnerAnkiDeckOption
    note_type: BeginnerAnkiNoteTypeOption
    front_field: str
    back_field: str
    source_field: Optional[str]
    summary_lines: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.deck, BeginnerAnkiDeckOption):
            raise ValueError("deck must be a BeginnerAnkiDeckOption.")
        if not isinstance(self.note_type, BeginnerAnkiNoteTypeOption):
            raise ValueError("note_type must be a BeginnerAnkiNoteTypeOption.")
        for value, name in (
            (self.front_field, "front_field"),
            (self.back_field, "back_field"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string.")
        if self.source_field is not None and (
            not isinstance(self.source_field, str) or not self.source_field.strip()
        ):
            raise ValueError("source_field must be non-empty or None.")
        if not isinstance(self.summary_lines, tuple) or not self.summary_lines:
            raise ValueError("summary_lines must be a non-empty tuple.")

    @property
    def read_only(self) -> bool:
        return True

    @property
    def will_write_to_anki(self) -> bool:
        return False

    def to_safe_dict(self) -> dict:
        return {
            "deck_id": self.deck.id,
            "deck_name": self.deck.name,
            "note_type_id": self.note_type.id,
            "note_type_name": self.note_type.name,
            "front_field": self.front_field,
            "back_field": self.back_field,
            "source_field": self.source_field,
            "read_only": self.read_only,
            "will_write_to_anki": self.will_write_to_anki,
        }


class ReadOnlyAnkiTargetAdapter:
    """Read deck, note type, and field metadata without mutation methods."""

    def __init__(self, collection):
        self._collection = collection

    def read_targets(self) -> BeginnerAnkiTargetSnapshot:
        try:
            decks = _read_named_options(
                self._collection.decks.all_names_and_ids(),
                BeginnerAnkiDeckOption,
            )
            note_types = _read_named_options(
                self._collection.models.all_names_and_ids(),
                BeginnerAnkiNoteTypeOption,
            )
        except Exception:
            return BeginnerAnkiTargetSnapshot(
                state=BeginnerAnkiReadState.ERROR,
                user_message=ANKI_TARGET_READ_ERROR_COPY,
            )

        if not decks or not note_types:
            messages = []
            if not decks:
                messages.append(ANKI_DECK_EMPTY_COPY)
            if not note_types:
                messages.append(ANKI_NOTE_TYPE_EMPTY_COPY)
            return BeginnerAnkiTargetSnapshot(
                state=BeginnerAnkiReadState.EMPTY,
                decks=decks,
                note_types=note_types,
                user_message="\n".join(messages),
            )
        return BeginnerAnkiTargetSnapshot(
            state=BeginnerAnkiReadState.SUCCESS,
            decks=decks,
            note_types=note_types,
            user_message=(
                "已读取 Anki 牌组和笔记类型，仅用于当前只读预览。"
                "尚未写入 Anki。"
            ),
        )

    def read_fields(self, note_type_id: int) -> BeginnerAnkiFieldSnapshot:
        try:
            if isinstance(note_type_id, bool) or not isinstance(note_type_id, int):
                raise ValueError("note_type_id must be an integer.")
            note_type = self._collection.models.get(note_type_id)
            fields = _read_field_names(note_type)
        except Exception:
            return BeginnerAnkiFieldSnapshot(
                state=BeginnerAnkiReadState.ERROR,
                note_type_id=None,
                user_message=ANKI_TARGET_READ_ERROR_COPY,
            )

        if not fields:
            return BeginnerAnkiFieldSnapshot(
                state=BeginnerAnkiReadState.EMPTY,
                note_type_id=note_type_id,
                user_message=ANKI_FIELD_EMPTY_COPY,
            )
        return BeginnerAnkiFieldSnapshot(
            state=BeginnerAnkiReadState.SUCCESS,
            note_type_id=note_type_id,
            fields=fields,
            user_message=(
                "已读取所选笔记类型的字段，仅用于当前只读预览。"
                "尚未写入 Anki。"
            ),
        )


def build_beginner_field_mapping_preview(
    deck: BeginnerAnkiDeckOption,
    note_type: BeginnerAnkiNoteTypeOption,
    available_fields: tuple[str, ...],
    front_field: str,
    back_field: str,
    source_field: Optional[str] = None,
) -> BeginnerFieldMappingPreview:
    """Build a display-only mapping without preparing any write object."""

    if not isinstance(available_fields, tuple) or not all(
        isinstance(item, str) and item for item in available_fields
    ):
        raise ValueError("available_fields must contain non-empty strings.")
    selected = tuple(
        item for item in (front_field, back_field, source_field) if item
    )
    if any(item not in available_fields for item in selected):
        raise ValueError("mapped fields must exist on the selected note type.")
    source_display = source_field or "不映射"
    return BeginnerFieldMappingPreview(
        deck=deck,
        note_type=note_type,
        front_field=front_field,
        back_field=back_field,
        source_field=source_field,
        summary_lines=(
            ANKI_MAPPING_PREVIEW_SAFETY_COPY,
            f"未来写入目标牌组：{deck.name}",
            f"未来使用笔记类型：{note_type.name}",
            f"正面 → {front_field}",
            f"背面 → {back_field}",
            f"来源 → {source_display}",
        ),
    )


def _read_named_options(items, option_type):
    options = []
    for item in items:
        item_id, name = _item_id_and_name(item)
        options.append(option_type(id=item_id, name=name))
    return tuple(sorted(options, key=lambda option: option.name.casefold()))


def _item_id_and_name(item) -> tuple[int, str]:
    if isinstance(item, dict):
        item_id = item.get("id")
        name = item.get("name")
    else:
        item_id = getattr(item, "id", None)
        name = getattr(item, "name", None)
    _validate_id_and_name(item_id, name, "Anki item")
    return item_id, name.strip()


def _read_field_names(note_type) -> tuple[str, ...]:
    if not isinstance(note_type, dict):
        raise ValueError("note type metadata must be a mapping.")
    raw_fields = note_type.get("flds")
    if not isinstance(raw_fields, list):
        raise ValueError("note type fields must be a list.")
    names = []
    for item in raw_fields:
        name = item.get("name") if isinstance(item, dict) else None
        if not isinstance(name, str) or not name.strip():
            raise ValueError("field name must be a non-empty string.")
        names.append(name.strip())
    return tuple(names)


def _validate_id_and_name(item_id, name, label: str) -> None:
    if isinstance(item_id, bool) or not isinstance(item_id, int):
        raise ValueError(f"{label} id must be an integer.")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"{label} name must be a non-empty string.")
