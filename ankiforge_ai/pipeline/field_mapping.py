"""Pure field-role suggestions and mapping completeness checks."""

from dataclasses import dataclass
import re
from typing import Iterable, Optional


_FRONT_ALIASES = ("front", "question", "正面", "问题", "题目")
_BACK_ALIASES = ("back", "answer", "背面", "答案")
_SOURCE_ALIASES = ("source", "来源", "extra", "出处")
_CLOZE_FRONT_ALIASES = ("text", "文本", "文字")
_CLOZE_BACK_ALIASES = ("backextra", "back extra", "背面额外", "额外")


@dataclass(frozen=True)
class FieldMappingSuggestion:
    front_field: Optional[str]
    back_field: Optional[str]
    source_field: Optional[str]

    @property
    def complete(self) -> bool:
        return bool(self.front_field and self.back_field)


@dataclass(frozen=True)
class MappingAssessment:
    front_field: Optional[str]
    back_field: Optional[str]
    source_field: Optional[str]
    blocking_reasons: tuple[str, ...]
    source_optional: bool = True
    cloze_compatible: bool = True

    @property
    def complete(self) -> bool:
        return not self.blocking_reasons

    def to_safe_dict(self) -> dict:
        return {
            "complete": self.complete,
            "front_selected": bool(self.front_field),
            "back_selected": bool(self.back_field),
            "source_selected": bool(self.source_field),
            "source_optional": self.source_optional,
            "cloze_compatible": self.cloze_compatible,
            "blocking_reasons": self.blocking_reasons,
        }


def suggest_field_mapping(
    available_fields: Iterable[str],
    note_type_name: str = "",
    template_id: str = "basic_qa",
) -> FieldMappingSuggestion:
    fields = _coerce_fields(available_fields)
    _validate_text(note_type_name, "note_type_name")
    _validate_text(template_id, "template_id", allow_empty=False)
    cloze = template_id == "cloze_candidate"
    front_aliases = (*_CLOZE_FRONT_ALIASES, *_FRONT_ALIASES) if cloze else _FRONT_ALIASES
    back_aliases = (*_CLOZE_BACK_ALIASES, *_BACK_ALIASES) if cloze else _BACK_ALIASES
    front = _find_alias(fields, front_aliases)
    back = _find_alias(fields, back_aliases, excluded={front} if front else set())
    source = _find_alias(
        fields,
        _SOURCE_ALIASES,
        excluded={item for item in (front, back) if item},
    )
    return FieldMappingSuggestion(front, back, source)


def assess_field_mapping(
    available_fields: Iterable[str],
    front_field: Optional[str],
    back_field: Optional[str],
    source_field: Optional[str] = None,
    *,
    note_type_name: str = "",
    template_id: str = "basic_qa",
) -> MappingAssessment:
    fields = _coerce_fields(available_fields)
    _validate_text(note_type_name, "note_type_name")
    _validate_text(template_id, "template_id", allow_empty=False)
    front = _coerce_selection(front_field, "front_field")
    back = _coerce_selection(back_field, "back_field")
    source = _coerce_selection(source_field, "source_field")
    reasons = []
    if front is None:
        reasons.append("front_field_required")
    if back is None:
        reasons.append("back_field_required")
    selected = tuple(item for item in (front, back, source) if item is not None)
    if any(item not in fields for item in selected):
        reasons.append("mapped_field_missing")
    if len(selected) != len(set(selected)):
        reasons.append("mapped_fields_not_unique")
    cloze_compatible = _cloze_compatible(
        template_id,
        note_type_name,
        fields,
        front,
    )
    if not cloze_compatible:
        reasons.append("cloze_note_type_incompatible")
    return MappingAssessment(
        front_field=front,
        back_field=back,
        source_field=source,
        blocking_reasons=tuple(dict.fromkeys(reasons)),
        cloze_compatible=cloze_compatible,
    )


def _coerce_fields(values: Iterable[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise ValueError("available_fields must be an iterable of field names.")
    fields = tuple(values)
    if not fields or not all(isinstance(item, str) and item.strip() for item in fields):
        raise ValueError("available_fields must contain non-empty strings.")
    return tuple(item.strip() for item in fields)


def _coerce_selection(value: Optional[str], name: str) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string or None.")
    return value.strip()


def _find_alias(
    fields: tuple[str, ...],
    aliases: tuple[str, ...],
    excluded: set[str] | None = None,
) -> Optional[str]:
    excluded = excluded or set()
    normalized_fields = {_normalize(item): item for item in fields if item not in excluded}
    for alias in aliases:
        match = normalized_fields.get(_normalize(alias))
        if match is not None:
            return match
    return None


def _cloze_compatible(
    template_id: str,
    note_type_name: str,
    fields: tuple[str, ...],
    front_field: Optional[str],
) -> bool:
    if template_id != "cloze_candidate":
        return True
    name = _normalize(note_type_name)
    note_type_matches = "cloze" in name or "填空" in note_type_name
    text_fields = {_normalize(item) for item in fields}
    front_matches = bool(
        front_field
        and _normalize(front_field) in {_normalize(item) for item in _CLOZE_FRONT_ALIASES}
    )
    return note_type_matches and front_matches and bool(
        text_fields & {_normalize(item) for item in _CLOZE_FRONT_ALIASES}
    )


def _normalize(value: str) -> str:
    return re.sub(r"[\s_-]+", "", value.strip().casefold())


def _validate_text(value: object, name: str, *, allow_empty: bool = True) -> None:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ValueError(f"{name} must be a string.")
