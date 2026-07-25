"""Opt-in aggregate-only deck-style profile foundation.

This module contains no Anki query or collection access. Callers may construct a
read-only query specification and pass already sampled note-shaped data to the
pure summarizer.
"""

from __future__ import annotations

import html
import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from itertools import islice
from typing import Mapping, Optional


DEFAULT_DECK_STYLE_MAX_NOTES = 20
MAX_STYLE_FIELDS = 32
MAX_STYLE_TAGS = 16
MAX_STYLE_HINTS = 8
MAX_STYLE_TEXT_CHARS = 12_000
REAL_DECK_STYLE_SAMPLING_ENABLED = False
_HTML_TAG = re.compile(r"</?[A-Za-z][^>\n]{0,200}>")
_BULLET_LINE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")
_ABSOLUTE_WINDOWS_PATH = re.compile(r"^[A-Za-z]:[\\/]")


@dataclass(frozen=True, repr=False)
class DeckStyleQuery:
    enabled: bool = False
    selected_deck_id: Optional[int] = None
    selected_deck_label: Optional[str] = None
    max_notes: int = DEFAULT_DECK_STYLE_MAX_NOTES
    include_descendants: bool = False
    allow_full_scan: bool = False
    allow_mutation: bool = False
    aggregate_only: bool = True
    real_sampling_enabled: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise TypeError("enabled must be a boolean")
        _validate_max_notes(self.max_notes)
        if self.enabled:
            _validate_deck_id(self.selected_deck_id)
            label = _validate_deck_label(self.selected_deck_label)
            object.__setattr__(self, "selected_deck_label", label)
        elif self.selected_deck_id is not None or self.selected_deck_label is not None:
            raise ValueError("disabled deck style cannot select a deck")
        for value, name, expected in (
            (self.include_descendants, "include_descendants", False),
            (self.allow_full_scan, "allow_full_scan", False),
            (self.allow_mutation, "allow_mutation", False),
            (self.aggregate_only, "aggregate_only", True),
            (self.real_sampling_enabled, "real_sampling_enabled", False),
        ):
            if not isinstance(value, bool):
                raise TypeError(f"{name} must be a boolean")
            if value is not expected:
                if name == "real_sampling_enabled":
                    raise ValueError("real sampling is disabled")
                raise ValueError(f"{name} violates the read-only query policy")

    def __repr__(self) -> str:
        return (
            "DeckStyleQuery("
            f"enabled={self.enabled}, selected_deck_id={self.selected_deck_id!r}, "
            f"selected_deck_label={self.selected_deck_label!r}, "
            f"max_notes={self.max_notes}, aggregate_only=True)"
        )


@dataclass(frozen=True, repr=False)
class DeckStyleProfile:
    enabled: bool = False
    selected_deck_id: Optional[int] = None
    selected_deck_label: Optional[str] = None
    sampled_note_count: int = 0
    field_names: tuple[str, ...] = ()
    front_length_range: tuple[int, int] = (0, 0)
    back_length_range: tuple[int, int] = (0, 0)
    bullet_ratio: float = 0.0
    html_ratio: float = 0.0
    common_layout_patterns: tuple[str, ...] = ()
    common_tags: tuple[str, ...] = ()
    preferred_template_hints: tuple[str, ...] = ()
    examples_included: bool = False
    real_sampling_enabled: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise TypeError("enabled must be a boolean")
        if self.enabled:
            _validate_deck_id(self.selected_deck_id)
            label = _validate_deck_label(self.selected_deck_label)
            object.__setattr__(self, "selected_deck_label", label)
        elif self.selected_deck_id is not None or self.selected_deck_label is not None:
            raise ValueError("disabled profile cannot select a deck")
        if (
            isinstance(self.sampled_note_count, bool)
            or not isinstance(self.sampled_note_count, int)
            or not 0 <= self.sampled_note_count <= DEFAULT_DECK_STYLE_MAX_NOTES
        ):
            raise ValueError("sampled_note_count must be between zero and twenty")
        field_names = _validated_labels(
            self.field_names,
            MAX_STYLE_FIELDS,
            "field_names",
        )
        patterns = _validated_values(
            self.common_layout_patterns,
            ("plain", "bulleted", "html"),
            "common_layout_patterns",
        )
        tags = _validated_labels(
            self.common_tags,
            MAX_STYLE_TAGS,
            "common_tags",
        )
        hints = _validated_labels(
            self.preferred_template_hints,
            MAX_STYLE_HINTS,
            "preferred_template_hints",
        )
        front_range = _validated_range(
            self.front_length_range,
            "front_length_range",
        )
        back_range = _validated_range(
            self.back_length_range,
            "back_length_range",
        )
        for value, name in (
            (self.bullet_ratio, "bullet_ratio"),
            (self.html_ratio, "html_ratio"),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be a finite ratio")
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between zero and one")
            object.__setattr__(self, name, float(value))
        for value, name in (
            (self.examples_included, "examples_included"),
            (self.real_sampling_enabled, "real_sampling_enabled"),
        ):
            if not isinstance(value, bool):
                raise TypeError(f"{name} must be a boolean")
            if value:
                if name == "real_sampling_enabled":
                    raise ValueError("real sampling is disabled")
                raise ValueError("note examples are disabled by default")
        if not self.enabled and (
            self.sampled_note_count
            or field_names
            or patterns
            or tags
            or hints
            or front_range != (0, 0)
            or back_range != (0, 0)
            or self.bullet_ratio
            or self.html_ratio
        ):
            raise ValueError("disabled profile cannot contain sampled aggregates")
        object.__setattr__(self, "field_names", field_names)
        object.__setattr__(self, "front_length_range", front_range)
        object.__setattr__(self, "back_length_range", back_range)
        object.__setattr__(self, "common_layout_patterns", patterns)
        object.__setattr__(self, "common_tags", tags)
        object.__setattr__(self, "preferred_template_hints", hints)

    def to_provider_payload(self) -> dict:
        if not self.enabled:
            return {"enabled": False}
        return {
            "enabled": True,
            "sampled_note_count": self.sampled_note_count,
            "field_names": self.field_names,
            "front_length_range": self.front_length_range,
            "back_length_range": self.back_length_range,
            "bullet_ratio": self.bullet_ratio,
            "html_ratio": self.html_ratio,
            "common_layout_patterns": self.common_layout_patterns,
            "common_tags": self.common_tags,
            "preferred_template_hints": self.preferred_template_hints,
            "examples_included": False,
        }

    def __repr__(self) -> str:
        return (
            "DeckStyleProfile("
            f"enabled={self.enabled}, selected_deck_id={self.selected_deck_id!r}, "
            f"selected_deck_label={self.selected_deck_label!r}, "
            f"sampled_notes={self.sampled_note_count}, "
            f"fields={len(self.field_names)}, layouts={len(self.common_layout_patterns)}, "
            f"tags={len(self.common_tags)}, hints={len(self.preferred_template_hints)}, "
            f"examples=False, real_sampling=False)"
        )


def build_deck_style_query(
    *,
    enabled: bool = False,
    selected_deck_id: Optional[int] = None,
    selected_deck_label: Optional[str] = None,
    max_notes: int = DEFAULT_DECK_STYLE_MAX_NOTES,
    enable_real_sampling: bool = False,
) -> DeckStyleQuery:
    return DeckStyleQuery(
        enabled=enabled,
        selected_deck_id=selected_deck_id,
        selected_deck_label=selected_deck_label,
        max_notes=max_notes,
        real_sampling_enabled=enable_real_sampling,
    )


def summarize_deck_style(
    notes,
    *,
    query: Optional[DeckStyleQuery] = None,
) -> DeckStyleProfile:
    resolved = DeckStyleQuery() if query is None else query
    if not isinstance(resolved, DeckStyleQuery):
        raise TypeError("query must be a DeckStyleQuery")
    if not resolved.enabled:
        return DeckStyleProfile()
    try:
        note_items = tuple(islice(iter(notes), resolved.max_notes))
    except TypeError:
        raise TypeError("notes must be iterable") from None
    field_names = []
    seen_field_names = set()
    front_lengths = []
    back_lengths = []
    tag_counts = Counter()
    tag_first_seen = {}
    hint_counts = Counter()
    hint_first_seen = {}
    html_notes = 0
    bullet_notes = 0
    plain_notes = 0
    for note_index, note in enumerate(note_items):
        fields, front, back, tags, hint = _validated_note(note)
        for field_name in fields:
            if field_name not in seen_field_names:
                if len(field_names) >= MAX_STYLE_FIELDS:
                    raise ValueError("note field names exceed the approved limit")
                seen_field_names.add(field_name)
                field_names.append(field_name)
        front_lengths.append(len(_plain_text(front)))
        back_lengths.append(len(_plain_text(back)))
        combined = f"{front}\n{back}"
        has_html = bool(_HTML_TAG.search(combined))
        has_bullets = any(_BULLET_LINE.match(line) for line in combined.splitlines())
        html_notes += has_html
        bullet_notes += has_bullets
        plain_notes += not has_html and not has_bullets
        for tag in tags:
            if tag not in tag_first_seen:
                tag_first_seen[tag] = len(tag_first_seen)
            tag_counts[tag] += 1
        if hint:
            if hint not in hint_first_seen:
                hint_first_seen[hint] = len(hint_first_seen)
            hint_counts[hint] += 1
    sampled_count = len(note_items)
    layouts = tuple(
        name
        for name, present in (
            ("plain", bool(plain_notes)),
            ("bulleted", bool(bullet_notes)),
            ("html", bool(html_notes)),
        )
        if present
    )
    return DeckStyleProfile(
        enabled=True,
        selected_deck_id=resolved.selected_deck_id,
        selected_deck_label=resolved.selected_deck_label,
        sampled_note_count=sampled_count,
        field_names=tuple(field_names),
        front_length_range=_length_range(front_lengths),
        back_length_range=_length_range(back_lengths),
        bullet_ratio=0.0 if not sampled_count else round(bullet_notes / sampled_count, 4),
        html_ratio=0.0 if not sampled_count else round(html_notes / sampled_count, 4),
        common_layout_patterns=layouts,
        common_tags=_ranked_values(tag_counts, tag_first_seen, MAX_STYLE_TAGS),
        preferred_template_hints=_ranked_values(
            hint_counts,
            hint_first_seen,
            MAX_STYLE_HINTS,
        ),
    )


def _validated_note(note: object):
    if not isinstance(note, Mapping):
        raise TypeError("deck style notes must be mappings")
    fields = note.get("fields")
    if not isinstance(fields, Mapping):
        raise TypeError("note fields must be a mapping")
    try:
        field_keys = tuple(islice(iter(fields), MAX_STYLE_FIELDS + 1))
    except TypeError:
        raise TypeError("note fields must be iterable") from None
    if len(field_keys) > MAX_STYLE_FIELDS:
        raise ValueError("note fields exceed the approved limit")
    normalized_fields = {}
    for name in field_keys:
        value = fields[name]
        label = _validate_aggregate_label(name, "field name")
        if not isinstance(value, str):
            raise TypeError("note field values must be strings")
        if len(value) > MAX_STYLE_TEXT_CHARS:
            raise ValueError("note field value exceeds the style limit")
        normalized_fields[label] = value
    front_field = note.get("front_field")
    back_field = note.get("back_field")
    if not isinstance(front_field, str) or not isinstance(back_field, str):
        raise TypeError("front_field and back_field must be strings")
    if front_field not in normalized_fields or back_field not in normalized_fields:
        raise ValueError("named front/back fields must exist")
    tags = note.get("tags", ())
    tags = _validated_labels(tags, MAX_STYLE_TAGS, "note tags")
    hint = note.get("template_hint", "")
    if hint:
        hint = _validate_aggregate_label(hint, "template hint")
    elif not isinstance(hint, str):
        raise TypeError("template_hint must be a string")
    return (
        normalized_fields,
        normalized_fields[front_field],
        normalized_fields[back_field],
        tags,
        hint,
    )


def _plain_text(value: str) -> str:
    return html.unescape(_HTML_TAG.sub("", value)).strip()


def _length_range(values) -> tuple[int, int]:
    if not values:
        return (0, 0)
    return (min(values), max(values))


def _ranked_values(counts, first_seen, limit: int) -> tuple[str, ...]:
    return tuple(
        sorted(
            counts,
            key=lambda item: (-counts[item], first_seen[item]),
        )[:limit]
    )


def _validate_deck_id(value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("selected_deck_id must be a positive integer")


def _validate_deck_label(value: object) -> str:
    try:
        label = _validate_aggregate_label(value, "deck label")
    except (TypeError, ValueError):
        raise ValueError("deck label must be a safe bounded label") from None
    normalized = label.replace("\\", "/")
    if (
        normalized.startswith("/")
        or _ABSOLUTE_WINDOWS_PATH.match(label)
        or any(part == ".." for part in normalized.split("/"))
        or "/" in normalized
    ):
        raise ValueError("deck label must not contain a path")
    return label


def _validate_aggregate_label(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    normalized = unicodedata.normalize("NFKC", value).strip()
    if (
        not normalized
        or len(normalized) > 120
        or any(unicodedata.category(character).startswith("C") for character in normalized)
    ):
        raise ValueError(f"{name} must be a safe bounded label")
    return normalized


def _validate_max_notes(value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("max_notes must be an integer")
    if not 1 <= value <= DEFAULT_DECK_STYLE_MAX_NOTES:
        raise ValueError("max_notes must be between one and twenty")


def _validated_labels(value, limit: int, name: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)):
        raise TypeError(f"{name} must be a sequence")
    try:
        result = tuple(islice(iter(value), limit + 1))
    except TypeError:
        raise TypeError(f"{name} must be iterable") from None
    if len(result) > limit:
        raise ValueError(f"{name} exceeds the approved limit")
    labels = tuple(_validate_aggregate_label(item, name) for item in result)
    if len(set(labels)) != len(labels):
        raise ValueError(f"{name} must contain unique labels")
    return labels


def _validated_values(value, allowed, name: str) -> tuple[str, ...]:
    result = _validated_labels(value, len(allowed), name)
    if any(item not in allowed for item in result):
        raise ValueError(f"{name} contains an unsupported value")
    return result


def _validated_range(value, name: str) -> tuple[int, int]:
    if isinstance(value, (str, bytes)):
        raise TypeError(f"{name} must contain two integers")
    try:
        result = tuple(value)
    except TypeError:
        raise TypeError(f"{name} must contain two integers") from None
    if len(result) != 2:
        raise ValueError(f"{name} must contain two integers")
    if any(
        isinstance(item, bool)
        or not isinstance(item, int)
        or not 0 <= item <= MAX_STYLE_TEXT_CHARS
        for item in result
    ):
        raise ValueError(f"{name} must contain bounded non-negative integers")
    if result[0] > result[1]:
        raise ValueError(f"{name} minimum exceeds maximum")
    return result
