"""Small deterministic benchmark runner for checked-in mock card fixtures."""

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Iterable, Mapping

from ..pipeline.card_quality import evaluate_card_batch
from ..pipeline.generation_settings import GenerationSettings


@dataclass(frozen=True, repr=False)
class BenchmarkCard:
    id: str
    front: str = field(repr=False)
    back: str = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("benchmark card id must be a non-empty string.")
        if not isinstance(self.front, str) or not isinstance(self.back, str):
            raise ValueError("benchmark card front and back must be strings.")

    def __repr__(self) -> str:
        return f"BenchmarkCard(id={self.id!r})"


@dataclass(frozen=True, repr=False)
class CardQualityBenchmarkFixture:
    fixture_id: str
    source_text: str = field(repr=False)
    recommended_mode: str
    expected_good_patterns: tuple[str, ...]
    expected_bad_patterns: tuple[str, ...]
    expected_min_cards: int
    expected_max_cards: int
    notes: str = field(repr=False)
    mock_cards: tuple[BenchmarkCard, ...] = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.fixture_id, str) or not self.fixture_id.strip():
            raise ValueError("fixture_id must be a non-empty string.")
        if not isinstance(self.source_text, str) or not self.source_text.strip():
            raise ValueError("source_text must be a non-empty string.")
        GenerationSettings(card_mode=self.recommended_mode)
        for values, name in (
            (self.expected_good_patterns, "expected_good_patterns"),
            (self.expected_bad_patterns, "expected_bad_patterns"),
        ):
            if not values or not all(
                isinstance(value, str) and value.strip() for value in values
            ):
                raise ValueError(f"{name} must contain non-empty strings.")
        if (
            isinstance(self.expected_min_cards, bool)
            or not isinstance(self.expected_min_cards, int)
            or isinstance(self.expected_max_cards, bool)
            or not isinstance(self.expected_max_cards, int)
            or self.expected_min_cards < 0
            or self.expected_max_cards < self.expected_min_cards
        ):
            raise ValueError("expected card range is invalid.")
        if not self.expected_min_cards <= len(self.mock_cards) <= self.expected_max_cards:
            raise ValueError("mock card count must be inside the expected range.")
        if not isinstance(self.notes, str) or not self.notes.strip():
            raise ValueError("notes must be a non-empty string.")

    def __repr__(self) -> str:
        return (
            "CardQualityBenchmarkFixture("
            f"fixture_id={self.fixture_id!r}, mode={self.recommended_mode!r}, "
            f"card_count={len(self.mock_cards)})"
        )


@dataclass(frozen=True, repr=False)
class BenchmarkSummary:
    pass_count: int
    warning_count: int
    blocking_count: int
    score_distribution: dict[str, int]

    def __post_init__(self) -> None:
        for value, name in (
            (self.pass_count, "pass_count"),
            (self.warning_count, "warning_count"),
            (self.blocking_count, "blocking_count"),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer.")
        if set(self.score_distribution) != {"high", "medium", "low"}:
            raise ValueError("score_distribution must contain high, medium, and low.")
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in self.score_distribution.values()
        ):
            raise ValueError("score distribution counts must be non-negative integers.")
        if sum(self.score_distribution.values()) != self.total_count:
            raise ValueError("score distribution must match the evaluated card count.")

    @property
    def total_count(self) -> int:
        return self.pass_count + self.warning_count + self.blocking_count

    def __repr__(self) -> str:
        return (
            "BenchmarkSummary("
            f"pass_count={self.pass_count}, warning_count={self.warning_count}, "
            f"blocking_count={self.blocking_count})"
        )

    def to_safe_dict(self) -> dict:
        return {
            "pass_count": self.pass_count,
            "warning_count": self.warning_count,
            "blocking_count": self.blocking_count,
            "score_distribution": dict(self.score_distribution),
        }


def load_benchmark_fixture(path: str | Path) -> CardQualityBenchmarkFixture:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return _fixture_from_mapping(payload)


def evaluate_benchmark_fixture(
    fixture: CardQualityBenchmarkFixture | Mapping[str, object],
) -> BenchmarkSummary:
    resolved = (
        fixture
        if isinstance(fixture, CardQualityBenchmarkFixture)
        else _fixture_from_mapping(fixture)
    )
    batch = evaluate_card_batch(
        resolved.mock_cards,
        GenerationSettings(card_mode=resolved.recommended_mode),
        source_text=resolved.source_text,
    )
    return _summary_from_results(item.quality for item in batch.results)


def evaluate_benchmark_suite(
    fixtures: Iterable[CardQualityBenchmarkFixture | Mapping[str, object]],
) -> BenchmarkSummary:
    summaries = tuple(evaluate_benchmark_fixture(item) for item in fixtures)
    distribution = {"high": 0, "medium": 0, "low": 0}
    for summary in summaries:
        for bucket, count in summary.score_distribution.items():
            distribution[bucket] += count
    return BenchmarkSummary(
        pass_count=sum(item.pass_count for item in summaries),
        warning_count=sum(item.warning_count for item in summaries),
        blocking_count=sum(item.blocking_count for item in summaries),
        score_distribution=distribution,
    )


def _fixture_from_mapping(payload: Mapping[str, object]) -> CardQualityBenchmarkFixture:
    if not isinstance(payload, Mapping):
        raise ValueError("benchmark fixture must be a mapping.")
    required = {
        "fixture_id",
        "source_text",
        "recommended_mode",
        "expected_good_patterns",
        "expected_bad_patterns",
        "expected_min_cards",
        "expected_max_cards",
        "notes",
        "mock_cards",
    }
    if set(payload) != required:
        raise ValueError("benchmark fixture fields are incomplete or unknown.")
    cards = payload["mock_cards"]
    if isinstance(cards, (str, bytes)) or not isinstance(cards, list):
        raise ValueError("mock_cards must be a list.")
    return CardQualityBenchmarkFixture(
        fixture_id=payload["fixture_id"],
        source_text=payload["source_text"],
        recommended_mode=payload["recommended_mode"],
        expected_good_patterns=_string_tuple(
            payload["expected_good_patterns"], "expected_good_patterns"
        ),
        expected_bad_patterns=_string_tuple(
            payload["expected_bad_patterns"], "expected_bad_patterns"
        ),
        expected_min_cards=payload["expected_min_cards"],
        expected_max_cards=payload["expected_max_cards"],
        notes=payload["notes"],
        mock_cards=tuple(_benchmark_card(item) for item in cards),
    )


def _benchmark_card(value: object) -> BenchmarkCard:
    if not isinstance(value, Mapping) or set(value) != {"id", "front", "back"}:
        raise ValueError("each mock card must contain id, front, and back.")
    return BenchmarkCard(id=value["id"], front=value["front"], back=value["back"])


def _string_tuple(value: object, name: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, list):
        raise ValueError(f"{name} must be a list.")
    return tuple(value)


def _summary_from_results(results: Iterable[object]) -> BenchmarkSummary:
    values = tuple(results)
    distribution = {"high": 0, "medium": 0, "low": 0}
    for result in values:
        bucket = (
            "high"
            if result.quality_score >= 0.85
            else "medium"
            if result.quality_score >= 0.5
            else "low"
        )
        distribution[bucket] += 1
    return BenchmarkSummary(
        pass_count=sum(result.severity == "info" for result in values),
        warning_count=sum(result.severity == "warning" for result in values),
        blocking_count=sum(result.severity == "blocking" for result in values),
        score_distribution=distribution,
    )
