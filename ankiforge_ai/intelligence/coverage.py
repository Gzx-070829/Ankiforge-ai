"""Bounded local coverage checks over knowledge-point and card identifiers."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from itertools import islice
from typing import Mapping


MAX_COVERAGE_POINTS = 96
MAX_COVERAGE_CARDS = 96
MAX_COVERAGE_SECTIONS = 20_000
_SAFE_POINT_ID = re.compile(r"^point-[a-f0-9]{16}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_PRIORITIES = {"high", "medium", "low"}


@dataclass(frozen=True, repr=False)
class CoverageReport:
    missing_high_priority_point_ids: tuple[str, ...]
    uncovered_section_ids: tuple[str, ...]
    overcovered_section_ids: tuple[str, ...]
    duplicate_point_ids: tuple[str, ...]
    card_count: int
    max_cards: int
    overflow_count: int
    supplement_recommended: bool

    def __post_init__(self) -> None:
        for values, limit, name, pattern in (
            (
                self.missing_high_priority_point_ids,
                MAX_COVERAGE_POINTS,
                "missing_high_priority_point_ids",
                _SAFE_POINT_ID,
            ),
            (
                self.uncovered_section_ids,
                MAX_COVERAGE_SECTIONS,
                "uncovered_section_ids",
                _SAFE_ID,
            ),
            (
                self.overcovered_section_ids,
                MAX_COVERAGE_SECTIONS,
                "overcovered_section_ids",
                _SAFE_ID,
            ),
            (
                self.duplicate_point_ids,
                MAX_COVERAGE_POINTS,
                "duplicate_point_ids",
                _SAFE_POINT_ID,
            ),
        ):
            bounded = _bounded_tuple(values, limit, name)
            if len(set(bounded)) != len(bounded) or not all(
                isinstance(item, str) and pattern.fullmatch(item)
                for item in bounded
            ):
                raise ValueError(f"{name} must contain unique safe IDs")
            object.__setattr__(self, name, bounded)
        for value, name in (
            (self.card_count, "card_count"),
            (self.max_cards, "max_cards"),
            (self.overflow_count, "overflow_count"),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer")
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
        if self.max_cards > MAX_COVERAGE_CARDS:
            raise ValueError("max_cards exceeds the approved limit")
        if self.card_count > MAX_COVERAGE_CARDS:
            raise ValueError("card_count exceeds the approved limit")
        if self.overflow_count != max(0, self.card_count - self.max_cards):
            raise ValueError("overflow_count does not match card counts")
        if not isinstance(self.supplement_recommended, bool):
            raise TypeError("supplement_recommended must be a boolean")
        if (
            self.supplement_recommended
            and not self.missing_high_priority_point_ids
        ):
            raise ValueError("only missing high-priority points may be supplemented")
        if self.supplement_recommended and self.card_count >= self.max_cards:
            raise ValueError("supplement requires remaining card capacity")

    def __repr__(self) -> str:
        return (
            "CoverageReport("
            f"missing_high_priority={len(self.missing_high_priority_point_ids)}, "
            f"uncovered_sections={len(self.uncovered_section_ids)}, "
            f"overcovered_sections={len(self.overcovered_section_ids)}, "
            f"duplicate_points={len(self.duplicate_point_ids)}, "
            f"cards={self.card_count}/{self.max_cards}, "
            f"overflow={self.overflow_count})"
        )


def assess_generation_coverage(
    points,
    cards,
    *,
    section_ids,
    max_cards: int = MAX_COVERAGE_CARDS,
) -> CoverageReport:
    if (
        isinstance(max_cards, bool)
        or not isinstance(max_cards, int)
        or max_cards < 0
        or max_cards > MAX_COVERAGE_CARDS
    ):
        raise ValueError("max_cards must be a bounded non-negative integer")
    point_items = _bounded_tuple(points, MAX_COVERAGE_POINTS, "points")
    card_items = _bounded_tuple(cards, MAX_COVERAGE_CARDS, "cards")
    sections = _validated_ids(
        section_ids,
        MAX_COVERAGE_SECTIONS,
        _SAFE_ID,
        "section_ids",
    )
    point_records = []
    point_ids = set()
    section_set = set(sections)
    for point in point_items:
        point_id = _required_value(point, "point_id")
        priority = _required_value(point, "priority")
        section_id = _required_value(point, "section_id")
        if (
            not isinstance(point_id, str)
            or not _SAFE_POINT_ID.fullmatch(point_id)
            or point_id in point_ids
        ):
            raise ValueError("points require unique safe point IDs")
        if priority not in _PRIORITIES:
            raise ValueError("point priority is unsupported")
        if section_id not in section_set:
            raise ValueError("point references an unknown section")
        point_ids.add(point_id)
        point_records.append((point_id, priority, section_id))
    counts_by_point = Counter()
    counts_by_section = Counter()
    for card in card_items:
        point_id = _required_value(card, "point_id")
        section_id = _required_value(card, "section_id")
        if point_id not in point_ids:
            raise ValueError("card references an unknown point")
        expected_section = next(
            item[2] for item in point_records if item[0] == point_id
        )
        if section_id != expected_section:
            raise ValueError("card section does not match its point")
        counts_by_point[point_id] += 1
        counts_by_section[section_id] += 1
    missing_high = tuple(
        point_id
        for point_id, priority, _section_id in point_records
        if priority == "high" and not counts_by_point[point_id]
    )
    uncovered = tuple(
        section_id for section_id in sections if not counts_by_section[section_id]
    )
    average = len(card_items) / max(1, len(sections))
    overcovered = tuple(
        section_id
        for section_id in sections
        if counts_by_section[section_id] > max(2, 2 * average)
    )
    duplicates = tuple(
        point_id
        for point_id, _priority, _section_id in point_records
        if counts_by_point[point_id] > 1
    )
    return CoverageReport(
        missing_high_priority_point_ids=missing_high,
        uncovered_section_ids=uncovered,
        overcovered_section_ids=overcovered,
        duplicate_point_ids=duplicates,
        card_count=len(card_items),
        max_cards=max_cards,
        overflow_count=max(0, len(card_items) - max_cards),
        supplement_recommended=bool(missing_high) and len(card_items) < max_cards,
    )


def _required_value(item: object, name: str):
    if isinstance(item, Mapping):
        if name not in item:
            raise ValueError(f"coverage item requires {name}")
        return item[name]
    if not hasattr(item, name):
        raise ValueError(f"coverage item requires {name}")
    return getattr(item, name)


def _validated_ids(value, limit: int, pattern, name: str) -> tuple[str, ...]:
    result = _bounded_tuple(value, limit, name)
    if len(set(result)) != len(result) or not all(
        isinstance(item, str) and pattern.fullmatch(item) for item in result
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
