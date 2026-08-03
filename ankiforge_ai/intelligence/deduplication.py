"""Deterministic bounded cross-chunk card deduplication."""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from itertools import islice
from types import MappingProxyType
from typing import Mapping


MAX_DEDUP_CARDS = 96
MAX_CARD_TEXT_CHARS = 12_000
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_WORD_TOKEN = re.compile(r"[a-z0-9_]{2,}", re.IGNORECASE)
_CJK = re.compile(r"[\u3400-\u9fff]")
_MATCH_REASONS = {
    "exact": "exact_text",
    "canonical": "normalized_text",
}


@dataclass(frozen=True, repr=False)
class DuplicateMatch:
    candidate_id: str
    matched_candidate_id: str
    kind: str
    reason_code: str
    similarity: float

    def __post_init__(self) -> None:
        for value, name in (
            (self.candidate_id, "candidate_id"),
            (self.matched_candidate_id, "matched_candidate_id"),
        ):
            if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
                raise ValueError(f"{name} must be a safe identifier")
        if self.candidate_id == self.matched_candidate_id:
            raise ValueError("a duplicate match must identify a different candidate")
        if self.kind not in {"exact", "canonical", "similar"}:
            raise ValueError("duplicate match kind is unsupported")
        allowed_reason = {
            "exact": {"exact_text"},
            "canonical": {"normalized_text"},
            "similar": {
                "shared_source_token_overlap",
                "shared_source_character_overlap",
            },
        }[self.kind]
        if self.reason_code not in allowed_reason:
            raise ValueError("duplicate match reason does not match its kind")
        if (
            isinstance(self.similarity, bool)
            or not isinstance(self.similarity, (int, float))
            or not math.isfinite(self.similarity)
            or not 0.0 <= self.similarity <= 1.0
        ):
            raise ValueError("duplicate match similarity must be bounded")

    def __repr__(self) -> str:
        return (
            "DuplicateMatch("
            f"candidate_id={self.candidate_id!r}, "
            f"matched_candidate_id={self.matched_candidate_id!r}, "
            f"kind={self.kind!r}, reason_code={self.reason_code!r}, "
            f"similarity={self.similarity:.3f})"
        )

    def to_safe_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "matched_candidate_id": self.matched_candidate_id,
            "kind": self.kind,
            "reason_code": self.reason_code,
            "similarity": self.similarity,
        }


@dataclass(frozen=True, repr=False)
class DeduplicationResult:
    unique_cards: tuple[object, ...]
    duplicate_candidate_ids: tuple[str, ...]
    exact_duplicate_ids: tuple[str, ...]
    canonical_duplicate_ids: tuple[str, ...]
    similar_duplicate_ids: tuple[str, ...]
    matches: tuple[DuplicateMatch, ...]
    comparison_count: int
    semantic_dedup_used: bool = False

    def __post_init__(self) -> None:
        unique = _bounded_tuple(
            self.unique_cards,
            MAX_DEDUP_CARDS,
            "unique_cards",
        )
        object.__setattr__(
            self,
            "unique_cards",
            tuple(_freeze_card(card) for card in unique),
        )
        groups = []
        for name in (
            "duplicate_candidate_ids",
            "exact_duplicate_ids",
            "canonical_duplicate_ids",
            "similar_duplicate_ids",
        ):
            values = _validated_ids(getattr(self, name), name)
            object.__setattr__(self, name, values)
            groups.append(values)
        duplicate_ids, exact_ids, canonical_ids, similar_ids = groups
        categorized = set(exact_ids) | set(canonical_ids) | set(similar_ids)
        if set(duplicate_ids) != categorized:
            raise ValueError("duplicate IDs must match categorized duplicates")
        if (
            set(exact_ids) & set(canonical_ids)
            or set(exact_ids) & set(similar_ids)
            or set(canonical_ids) & set(similar_ids)
        ):
            raise ValueError("duplicate categories must not overlap")
        matches = _bounded_tuple(self.matches, MAX_DEDUP_CARDS, "matches")
        if not all(isinstance(item, DuplicateMatch) for item in matches):
            raise TypeError("matches must contain DuplicateMatch values")
        if tuple(item.candidate_id for item in matches) != duplicate_ids:
            raise ValueError("duplicate matches must align with duplicate IDs")
        category_by_id = {
            **{item: "exact" for item in exact_ids},
            **{item: "canonical" for item in canonical_ids},
            **{item: "similar" for item in similar_ids},
        }
        if any(category_by_id[item.candidate_id] != item.kind for item in matches):
            raise ValueError("duplicate match kinds must align with categories")
        object.__setattr__(self, "matches", matches)
        max_comparisons = MAX_DEDUP_CARDS * (MAX_DEDUP_CARDS - 1) // 2
        if (
            isinstance(self.comparison_count, bool)
            or not isinstance(self.comparison_count, int)
            or not 0 <= self.comparison_count <= max_comparisons
        ):
            raise ValueError("comparison_count is outside the bounded range")
        if not isinstance(self.semantic_dedup_used, bool):
            raise TypeError("semantic_dedup_used must be a boolean")
        if self.semantic_dedup_used:
            raise ValueError("semantic deduplication is disabled")

    def __repr__(self) -> str:
        return (
            "DeduplicationResult("
            f"unique={len(self.unique_cards)}, "
            f"duplicates={len(self.duplicate_candidate_ids)}, "
            f"exact={len(self.exact_duplicate_ids)}, "
            f"canonical={len(self.canonical_duplicate_ids)}, "
            f"similar={len(self.similar_duplicate_ids)}, "
            f"comparisons={self.comparison_count}, semantic=False)"
        )


def deduplicate_cards(
    cards,
    *,
    similarity_threshold: float = 0.86,
    semantic_matcher=None,
    enable_semantic: bool = False,
) -> DeduplicationResult:
    if isinstance(similarity_threshold, bool) or not isinstance(
        similarity_threshold, (int, float)
    ):
        raise TypeError("similarity_threshold must be a finite number")
    if (
        not math.isfinite(similarity_threshold)
        or not 0.5 <= similarity_threshold <= 1.0
    ):
        raise ValueError("similarity_threshold must be between 0.5 and 1.0")
    if not isinstance(enable_semantic, bool):
        raise TypeError("enable_semantic must be a boolean")
    if enable_semantic:
        raise ValueError("semantic deduplication is disabled")
    if semantic_matcher is not None and not callable(semantic_matcher):
        raise TypeError("semantic_matcher must be callable")
    card_items = _bounded_tuple(cards, MAX_DEDUP_CARDS, "cards")
    records = tuple(_card_record(card) for card in card_items)
    if len({item["candidate_id"] for item in records}) != len(records):
        raise ValueError("candidate IDs must be unique")
    unique_records = []
    duplicate_kinds = {}
    duplicate_matches = {}
    comparison_count = 0
    for record in records:
        duplicate_kind = None
        for kept in unique_records:
            comparison_count += 1
            similarity = 0.0
            reason_code = None
            if record["exact_key"] == kept["exact_key"]:
                duplicate_kind = "exact"
                similarity = 1.0
                reason_code = _MATCH_REASONS[duplicate_kind]
                break
            if record["canonical_key"] == kept["canonical_key"]:
                duplicate_kind = "canonical"
                similarity = 1.0
                reason_code = _MATCH_REASONS[duplicate_kind]
                break
            if record["source_ids"] & kept["source_ids"]:
                token_similarity = _similarity(record["tokens"], kept["tokens"])
                character_similarity = _similarity(
                    record["character_ngrams"],
                    kept["character_ngrams"],
                )
                similarity = max(token_similarity, character_similarity)
                if similarity >= similarity_threshold:
                    duplicate_kind = "similar"
                    reason_code = (
                        "shared_source_character_overlap"
                        if character_similarity > token_similarity
                        else "shared_source_token_overlap"
                    )
                    break
        if duplicate_kind is None:
            unique_records.append(record)
        else:
            duplicate_kinds[record["candidate_id"]] = duplicate_kind
            duplicate_matches[record["candidate_id"]] = DuplicateMatch(
                candidate_id=record["candidate_id"],
                matched_candidate_id=kept["candidate_id"],
                kind=duplicate_kind,
                reason_code=reason_code,
                similarity=round(similarity, 3),
            )
    duplicate_ids = tuple(
        record["candidate_id"]
        for record in records
        if record["candidate_id"] in duplicate_kinds
    )
    return DeduplicationResult(
        unique_cards=tuple(record["card"] for record in unique_records),
        duplicate_candidate_ids=duplicate_ids,
        exact_duplicate_ids=tuple(
            item for item in duplicate_ids if duplicate_kinds[item] == "exact"
        ),
        canonical_duplicate_ids=tuple(
            item for item in duplicate_ids if duplicate_kinds[item] == "canonical"
        ),
        similar_duplicate_ids=tuple(
            item for item in duplicate_ids if duplicate_kinds[item] == "similar"
        ),
        matches=tuple(duplicate_matches[item] for item in duplicate_ids),
        comparison_count=comparison_count,
        semantic_dedup_used=False,
    )


def canonicalize_card_text(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("card text must be a string")
    if len(value) > MAX_CARD_TEXT_CHARS:
        raise ValueError("card text exceeds the deduplication limit")
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(
        character
        for character in normalized
        if not unicodedata.category(character).startswith(("P", "Z"))
        and not character.isspace()
    )


def _card_record(card: object) -> dict:
    candidate_id = _card_value(card, "candidate_id")
    if candidate_id is None:
        candidate_id = _card_value(card, "id")
    if not isinstance(candidate_id, str) or not _SAFE_ID.fullmatch(candidate_id):
        raise ValueError("card requires a safe candidate_id")
    front = _card_value(card, "front")
    if front is None:
        front = _card_value(card, "front_preview")
    back = _card_value(card, "back")
    if back is None:
        back = _card_value(card, "back_preview")
    if not isinstance(front, str) or not isinstance(back, str):
        raise TypeError("card front and back must be strings")
    if len(front) > MAX_CARD_TEXT_CHARS or len(back) > MAX_CARD_TEXT_CHARS:
        raise ValueError("card text exceeds the deduplication limit")
    canonical_front = canonicalize_card_text(front)
    canonical_back = canonicalize_card_text(back)
    source_ids = set()
    for name in ("chunk_id", "point_id"):
        value = _card_value(card, name)
        if isinstance(value, str) and _SAFE_ID.fullmatch(value):
            source_ids.add(value)
    source_chunk_ids = _card_value(card, "source_chunk_ids")
    if source_chunk_ids is not None:
        for item in _bounded_tuple(source_chunk_ids, 4, "source_chunk_ids"):
            if not isinstance(item, str) or not _SAFE_ID.fullmatch(item):
                raise ValueError("source_chunk_ids must contain safe IDs")
            source_ids.add(item)
    source_span = _card_value(card, "source_span")
    if source_span is not None:
        for name in ("document_id", "block_id"):
            value = getattr(source_span, name, None)
            if isinstance(value, str) and _SAFE_ID.fullmatch(value):
                source_ids.add(value)
    canonical_combined = f"{canonical_front}\n{canonical_back}"
    return {
        "candidate_id": candidate_id,
        "card": _freeze_card(card),
        "exact_key": (front, back),
        "canonical_key": (canonical_front, canonical_back),
        "tokens": _similarity_tokens(f"{front}\n{back}"),
        "character_ngrams": _character_ngrams(canonical_combined),
        "source_ids": frozenset(source_ids),
    }


def _similarity_tokens(text: str) -> frozenset[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    tokens = set(_WORD_TOKEN.findall(normalized))
    cjk = "".join(_CJK.findall(normalized))
    tokens.update(
        f"cjk:{cjk[index:index + 2]}" for index in range(len(cjk) - 1)
    )
    return frozenset(tokens)


def _similarity(left: frozenset[str], right: frozenset[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _character_ngrams(text: str, size: int = 3) -> frozenset[str]:
    if len(text) < size:
        return frozenset((text,)) if text else frozenset()
    return frozenset(text[index : index + size] for index in range(len(text) - size + 1))


def _card_value(card: object, name: str):
    if isinstance(card, Mapping):
        return card.get(name)
    return getattr(card, name, None)


def _freeze_card(card: object):
    if isinstance(card, Mapping):
        return MappingProxyType(
            {
                key: _freeze_value(value)
                for key, value in card.items()
                if isinstance(key, str)
            }
        )
    return card


def _freeze_value(value):
    if isinstance(value, Mapping):
        return MappingProxyType(
            {
                key: _freeze_value(item)
                for key, item in value.items()
                if isinstance(key, str)
            }
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_value(item) for item in value)
    return value


def _validated_ids(value, name: str) -> tuple[str, ...]:
    result = _bounded_tuple(value, MAX_DEDUP_CARDS, name)
    if len(set(result)) != len(result) or not all(
        isinstance(item, str) and _SAFE_ID.fullmatch(item) for item in result
    ):
        raise ValueError(f"{name} must contain unique safe IDs")
    return result


def _bounded_tuple(value, limit: int, name: str) -> tuple:
    if isinstance(value, (str, bytes)):
        raise TypeError(f"{name} must be a sequence")
    try:
        result = tuple(islice(iter(value), limit + 1))
    except TypeError:
        raise TypeError(f"{name} must be iterable") from None
    if len(result) > limit:
        raise ValueError(f"{name} exceeds its approved limit")
    return result
