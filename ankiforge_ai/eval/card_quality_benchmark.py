"""Versioned deterministic benchmark for sanitized local card fixtures."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from types import MappingProxyType
from typing import Iterable, Mapping, Optional

from ..intelligence.deduplication import deduplicate_cards
from ..pipeline.card_quality import evaluate_card_batch
from ..pipeline.generation_settings import GenerationSettings


BENCHMARK_SCHEMA_VERSION = 1
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_PUBLIC_STATUSES = {"ready", "review", "blocked"}
_DUPLICATE_KINDS = {"exact", "canonical", "similar"}


@dataclass(frozen=True, repr=False)
class BenchmarkCard:
    id: str
    front: str = field(repr=False)
    back: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_safe_id(self.id, "benchmark card id")
        if not isinstance(self.front, str) or not isinstance(self.back, str):
            raise ValueError("benchmark card front and back must be strings.")

    def __repr__(self) -> str:
        return f"BenchmarkCard(id={self.id!r})"


@dataclass(frozen=True, repr=False)
class BenchmarkExpectedOutcome:
    status: str
    rule_ids: tuple[str, ...]
    duplicate_kind: Optional[str] = None

    def __post_init__(self) -> None:
        if self.status not in _PUBLIC_STATUSES:
            raise ValueError("expected benchmark status is unsupported")
        rules = _validated_rule_ids(self.rule_ids)
        if self.duplicate_kind is not None and self.duplicate_kind not in _DUPLICATE_KINDS:
            raise ValueError("expected duplicate kind is unsupported")
        object.__setattr__(self, "rule_ids", rules)

    def __repr__(self) -> str:
        return (
            "BenchmarkExpectedOutcome("
            f"status={self.status!r}, rules={len(self.rule_ids)}, "
            f"duplicate_kind={self.duplicate_kind!r})"
        )


@dataclass(frozen=True, repr=False)
class CardQualityBenchmarkFixture:
    schema_version: int
    fixture_id: str
    source_text: str = field(repr=False)
    recommended_mode: str
    expected_good_patterns: tuple[str, ...]
    expected_bad_patterns: tuple[str, ...]
    expected_min_cards: int
    expected_max_cards: int
    notes: str = field(repr=False)
    mock_cards: tuple[BenchmarkCard, ...] = field(repr=False)
    expected_outcomes: Mapping[str, BenchmarkExpectedOutcome] = field(repr=False)

    def __post_init__(self) -> None:
        if self.schema_version != BENCHMARK_SCHEMA_VERSION:
            raise ValueError("benchmark fixture schema version is unsupported")
        _require_safe_id(self.fixture_id, "fixture_id")
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
        cards = tuple(self.mock_cards)
        if not self.expected_min_cards <= len(cards) <= self.expected_max_cards:
            raise ValueError("mock card count must be inside the expected range.")
        card_ids = tuple(item.id for item in cards)
        if len(set(card_ids)) != len(card_ids):
            raise ValueError("benchmark card IDs must be unique")
        if not isinstance(self.notes, str) or not self.notes.strip():
            raise ValueError("notes must be a non-empty string.")
        outcomes = dict(self.expected_outcomes)
        if set(outcomes) != set(card_ids) or not all(
            isinstance(value, BenchmarkExpectedOutcome) for value in outcomes.values()
        ):
            raise ValueError("expected outcomes must match benchmark card IDs")
        object.__setattr__(self, "mock_cards", cards)
        object.__setattr__(self, "expected_outcomes", MappingProxyType(outcomes))

    def __repr__(self) -> str:
        return (
            "CardQualityBenchmarkFixture("
            f"schema_version={self.schema_version}, fixture_id={self.fixture_id!r}, "
            f"mode={self.recommended_mode!r}, card_count={len(self.mock_cards)})"
        )


@dataclass(frozen=True, repr=False)
class BenchmarkCardOutcome:
    candidate_id: str
    status: str
    quality_score: float
    score_rank: str
    rule_ids: tuple[str, ...]
    duplicate_kind: Optional[str] = None

    def __post_init__(self) -> None:
        _require_safe_id(self.candidate_id, "candidate_id")
        if self.status not in _PUBLIC_STATUSES:
            raise ValueError("benchmark outcome status is unsupported")
        if (
            isinstance(self.quality_score, bool)
            or not isinstance(self.quality_score, (int, float))
            or not 0.0 <= self.quality_score <= 1.0
        ):
            raise ValueError("quality score must be bounded")
        if self.score_rank not in {"high", "medium", "low"}:
            raise ValueError("score rank is unsupported")
        rules = _validated_rule_ids(self.rule_ids)
        if self.duplicate_kind is not None and self.duplicate_kind not in _DUPLICATE_KINDS:
            raise ValueError("duplicate kind is unsupported")
        object.__setattr__(self, "rule_ids", rules)

    def __repr__(self) -> str:
        return (
            "BenchmarkCardOutcome("
            f"candidate_id={self.candidate_id!r}, status={self.status!r}, "
            f"score_rank={self.score_rank!r}, rules={len(self.rule_ids)}, "
            f"duplicate_kind={self.duplicate_kind!r})"
        )


@dataclass(frozen=True, repr=False)
class BenchmarkFixtureReport:
    fixture_id: str
    expected_min_cards: int
    expected_max_cards: int
    outcomes: tuple[BenchmarkCardOutcome, ...]
    coverage_met: bool
    matches_expectations: bool

    def __post_init__(self) -> None:
        _require_safe_id(self.fixture_id, "fixture_id")
        if not all(isinstance(item, BenchmarkCardOutcome) for item in self.outcomes):
            raise TypeError("outcomes must contain BenchmarkCardOutcome values")
        if not isinstance(self.coverage_met, bool) or not isinstance(
            self.matches_expectations, bool
        ):
            raise TypeError("benchmark report flags must be booleans")

    def __repr__(self) -> str:
        return (
            "BenchmarkFixtureReport("
            f"fixture_id={self.fixture_id!r}, cards={len(self.outcomes)}, "
            f"coverage_met={self.coverage_met}, "
            f"matches_expectations={self.matches_expectations})"
        )


@dataclass(frozen=True, repr=False)
class BenchmarkSummary:
    pass_count: int
    warning_count: int
    blocking_count: int
    score_distribution: Mapping[str, int]
    status_distribution: Mapping[str, int]
    rule_counts: Mapping[str, int]
    duplicate_distribution: Mapping[str, int]

    def __post_init__(self) -> None:
        for value, name in (
            (self.pass_count, "pass_count"),
            (self.warning_count, "warning_count"),
            (self.blocking_count, "blocking_count"),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer.")
        distributions = (
            (self.score_distribution, {"high", "medium", "low"}, "score"),
            (self.status_distribution, _PUBLIC_STATUSES, "status"),
            (self.duplicate_distribution, _DUPLICATE_KINDS, "duplicate"),
        )
        for values, expected, name in distributions:
            if set(values) != expected or any(
                isinstance(value, bool) or not isinstance(value, int) or value < 0
                for value in values.values()
            ):
                raise ValueError(f"{name} distribution is invalid")
        if sum(self.score_distribution.values()) != self.total_count:
            raise ValueError("score distribution must match the evaluated card count.")
        if sum(self.status_distribution.values()) != self.total_count:
            raise ValueError("status distribution must match the evaluated card count.")
        rules = dict(self.rule_counts)
        if any(
            not isinstance(key, str)
            or not _SAFE_ID.fullmatch(key)
            or isinstance(value, bool)
            or not isinstance(value, int)
            or value < 1
            for key, value in rules.items()
        ):
            raise ValueError("rule counts must contain safe positive counts")
        object.__setattr__(self, "score_distribution", MappingProxyType(dict(self.score_distribution)))
        object.__setattr__(self, "status_distribution", MappingProxyType(dict(self.status_distribution)))
        object.__setattr__(self, "rule_counts", MappingProxyType(rules))
        object.__setattr__(
            self,
            "duplicate_distribution",
            MappingProxyType(dict(self.duplicate_distribution)),
        )

    @property
    def total_count(self) -> int:
        return self.pass_count + self.warning_count + self.blocking_count

    def __repr__(self) -> str:
        return (
            "BenchmarkSummary("
            f"pass_count={self.pass_count}, warning_count={self.warning_count}, "
            f"blocking_count={self.blocking_count}, rules={len(self.rule_counts)})"
        )

    def to_safe_dict(self) -> dict:
        return {
            "pass_count": self.pass_count,
            "warning_count": self.warning_count,
            "blocking_count": self.blocking_count,
            "score_distribution": dict(self.score_distribution),
            "status_distribution": dict(self.status_distribution),
            "rule_counts": dict(self.rule_counts),
            "duplicate_distribution": dict(self.duplicate_distribution),
        }


def load_benchmark_fixture(path: str | Path) -> CardQualityBenchmarkFixture:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return _fixture_from_mapping(payload)


def evaluate_benchmark_fixture_report(
    fixture: CardQualityBenchmarkFixture | Mapping[str, object],
) -> BenchmarkFixtureReport:
    resolved = _coerce_fixture(fixture)
    source_id = f"fixture:{resolved.fixture_id}"
    deduplication = deduplicate_cards(
        tuple(
            {
                "candidate_id": item.id,
                "front": item.front,
                "back": item.back,
                "point_id": source_id,
            }
            for item in resolved.mock_cards
        )
    )
    duplicate_kind_by_id = {
        item.candidate_id: item.kind for item in deduplication.matches
    }
    batch = evaluate_card_batch(
        resolved.mock_cards,
        GenerationSettings(card_mode=resolved.recommended_mode),
        source_text=resolved.source_text,
        duplicate_matches=deduplication.matches,
    )
    outcomes = tuple(
        BenchmarkCardOutcome(
            candidate_id=item.candidate_id,
            status=item.quality.status,
            quality_score=item.quality.quality_score,
            score_rank=_score_rank(item.quality.quality_score),
            rule_ids=item.quality.warning_ids,
            duplicate_kind=duplicate_kind_by_id.get(item.candidate_id),
        )
        for item in batch.results
    )
    matches_expectations = all(
        _outcome_matches_expected(item, resolved.expected_outcomes[item.candidate_id])
        for item in outcomes
    )
    return BenchmarkFixtureReport(
        fixture_id=resolved.fixture_id,
        expected_min_cards=resolved.expected_min_cards,
        expected_max_cards=resolved.expected_max_cards,
        outcomes=outcomes,
        coverage_met=(
            resolved.expected_min_cards <= len(outcomes) <= resolved.expected_max_cards
        ),
        matches_expectations=matches_expectations,
    )


def evaluate_benchmark_fixture(
    fixture: CardQualityBenchmarkFixture | Mapping[str, object],
) -> BenchmarkSummary:
    return _summary_from_outcomes(evaluate_benchmark_fixture_report(fixture).outcomes)


def evaluate_benchmark_suite(
    fixtures: Iterable[CardQualityBenchmarkFixture | Mapping[str, object]],
) -> BenchmarkSummary:
    reports = tuple(evaluate_benchmark_fixture_report(item) for item in fixtures)
    return _summary_from_outcomes(
        outcome for report in reports for outcome in report.outcomes
    )


def _coerce_fixture(
    fixture: CardQualityBenchmarkFixture | Mapping[str, object],
) -> CardQualityBenchmarkFixture:
    return fixture if isinstance(fixture, CardQualityBenchmarkFixture) else _fixture_from_mapping(fixture)


def _fixture_from_mapping(payload: Mapping[str, object]) -> CardQualityBenchmarkFixture:
    if not isinstance(payload, Mapping):
        raise ValueError("benchmark fixture must be a mapping.")
    required = {
        "schema_version",
        "fixture_id",
        "source_text",
        "recommended_mode",
        "expected_good_patterns",
        "expected_bad_patterns",
        "expected_min_cards",
        "expected_max_cards",
        "notes",
        "mock_cards",
        "expected_outcomes",
    }
    if set(payload) != required:
        raise ValueError("benchmark fixture fields are incomplete or unknown.")
    cards = payload["mock_cards"]
    if isinstance(cards, (str, bytes)) or not isinstance(cards, list):
        raise ValueError("mock_cards must be a list.")
    outcomes = payload["expected_outcomes"]
    if not isinstance(outcomes, Mapping):
        raise ValueError("expected_outcomes must be a mapping")
    return CardQualityBenchmarkFixture(
        schema_version=payload["schema_version"],
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
        expected_outcomes=MappingProxyType(
            {key: _expected_outcome(value) for key, value in outcomes.items()}
        ),
    )


def _benchmark_card(value: object) -> BenchmarkCard:
    if not isinstance(value, Mapping) or set(value) != {"id", "front", "back"}:
        raise ValueError("each mock card must contain id, front, and back.")
    return BenchmarkCard(id=value["id"], front=value["front"], back=value["back"])


def _expected_outcome(value: object) -> BenchmarkExpectedOutcome:
    if not isinstance(value, Mapping) or set(value) != {
        "status",
        "rule_ids",
        "duplicate_kind",
    }:
        raise ValueError("each expected outcome has an invalid schema")
    return BenchmarkExpectedOutcome(
        status=value["status"],
        rule_ids=_string_tuple(value["rule_ids"], "rule_ids", allow_empty=True),
        duplicate_kind=value["duplicate_kind"],
    )


def _string_tuple(
    value: object,
    name: str,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, list):
        raise ValueError(f"{name} must be a list.")
    result = tuple(value)
    if not allow_empty and not result:
        raise ValueError(f"{name} must not be empty")
    return result


def _validated_rule_ids(value) -> tuple[str, ...]:
    rules = tuple(value)
    if len(set(rules)) != len(rules) or not all(
        isinstance(item, str) and _SAFE_ID.fullmatch(item) for item in rules
    ):
        raise ValueError("rule IDs must be unique safe identifiers")
    return rules


def _outcome_matches_expected(
    outcome: BenchmarkCardOutcome,
    expected: BenchmarkExpectedOutcome,
) -> bool:
    return (
        outcome.status == expected.status
        and outcome.rule_ids == expected.rule_ids
        and outcome.duplicate_kind == expected.duplicate_kind
    )


def _score_rank(value: float) -> str:
    return "high" if value >= 0.85 else "medium" if value >= 0.5 else "low"


def _summary_from_outcomes(outcomes: Iterable[BenchmarkCardOutcome]) -> BenchmarkSummary:
    values = tuple(outcomes)
    score_distribution = {"high": 0, "medium": 0, "low": 0}
    status_distribution = {"ready": 0, "review": 0, "blocked": 0}
    duplicate_distribution = {"exact": 0, "canonical": 0, "similar": 0}
    rule_counts = {}
    for item in values:
        score_distribution[item.score_rank] += 1
        status_distribution[item.status] += 1
        if item.duplicate_kind is not None:
            duplicate_distribution[item.duplicate_kind] += 1
        for rule_id in item.rule_ids:
            rule_counts[rule_id] = rule_counts.get(rule_id, 0) + 1
    return BenchmarkSummary(
        pass_count=status_distribution["ready"],
        warning_count=status_distribution["review"],
        blocking_count=status_distribution["blocked"],
        score_distribution=score_distribution,
        status_distribution=status_distribution,
        rule_counts=rule_counts,
        duplicate_distribution=duplicate_distribution,
    )


def _require_safe_id(value, name: str) -> None:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise ValueError(f"{name} must be a safe non-empty identifier")


__all__ = [
    "BENCHMARK_SCHEMA_VERSION",
    "BenchmarkCard",
    "BenchmarkCardOutcome",
    "BenchmarkExpectedOutcome",
    "BenchmarkFixtureReport",
    "BenchmarkSummary",
    "CardQualityBenchmarkFixture",
    "evaluate_benchmark_fixture",
    "evaluate_benchmark_fixture_report",
    "evaluate_benchmark_suite",
    "load_benchmark_fixture",
]
