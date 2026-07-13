"""Deterministic, explainable quality checks for candidate cards."""

from dataclasses import dataclass, field
import re
from typing import Iterable, Mapping, Optional

from .generation_settings import GenerationSettings, coerce_generation_settings


_GENERIC_FRONT_PATTERNS = (
    re.compile(r"(?:请|试着)?解释(?:以下|这个|上述)?内容", re.IGNORECASE),
    re.compile(r"根据(?:这份|上述|以下)?材料(?:可知|回答)?", re.IGNORECASE),
    re.compile(r"\b(?:explain|describe) (?:this|the following|the material)\b", re.IGNORECASE),
    re.compile(r"\bwhat (?:is|does) (?:this|the material)\b", re.IGNORECASE),
)
_BOILERPLATE_PATTERNS = (
    re.compile(r"根据(?:这份|上述|以下)?材料(?:可知|回答)?", re.IGNORECASE),
    re.compile(r"\baccording to (?:the|this) material\b", re.IGNORECASE),
    re.compile(r"\bthe material (?:says|states|shows)\b", re.IGNORECASE),
)
_MARKDOWN_RESIDUE = re.compile(
    r"```|(?:^|\n)\s{0,3}#{1,6}\s|!??\[[^\]]*\]\([^)]*\)|\*\*[^*]+\*\*|__[^_]+__"
)
_BULLET_LINE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")


@dataclass(frozen=True)
class CardQualityIssue:
    warning_id: str
    severity: str
    suggestion_id: str

    def __post_init__(self) -> None:
        if self.severity not in {"info", "warning", "blocking"}:
            raise ValueError("severity must be info, warning, or blocking.")
        if not self.warning_id or not self.suggestion_id:
            raise ValueError("quality issue identifiers must be non-empty.")


@dataclass(frozen=True, repr=False)
class CardQualityResult:
    quality_score: float
    issues: tuple[CardQualityIssue, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not 0.0 <= self.quality_score <= 1.0:
            raise ValueError("quality_score must be between 0.0 and 1.0.")
        if not all(isinstance(item, CardQualityIssue) for item in self.issues):
            raise ValueError("issues must contain CardQualityIssue values.")

    @property
    def warning_ids(self) -> tuple[str, ...]:
        return tuple(item.warning_id for item in self.issues)

    @property
    def blocking_count(self) -> int:
        return sum(item.severity == "blocking" for item in self.issues)

    @property
    def warning_count(self) -> int:
        return sum(item.severity == "warning" for item in self.issues)

    @property
    def is_blocking(self) -> bool:
        return bool(self.blocking_count)

    @property
    def severity(self) -> str:
        if self.is_blocking:
            return "blocking"
        if self.warning_count:
            return "warning"
        return "info"

    def __repr__(self) -> str:
        return (
            "CardQualityResult("
            f"quality_score={self.quality_score:.2f}, severity={self.severity!r}, "
            f"issue_count={len(self.issues)})"
        )

    def to_safe_dict(self) -> dict:
        return {
            "quality_score": self.quality_score,
            "severity": self.severity,
            "issue_count": len(self.issues),
            "blocking_count": self.blocking_count,
            "warning_count": self.warning_count,
            "warning_ids": self.warning_ids,
        }


@dataclass(frozen=True, repr=False)
class CandidateQualityResult:
    candidate_id: str
    quality: CardQualityResult

    def __repr__(self) -> str:
        return (
            "CandidateQualityResult("
            f"candidate_id={self.candidate_id!r}, quality={self.quality!r})"
        )


@dataclass(frozen=True, repr=False)
class CardQualityBatch:
    results: tuple[CandidateQualityResult, ...]

    def for_candidate(self, candidate_id: str) -> CardQualityResult:
        for item in self.results:
            if item.candidate_id == candidate_id:
                return item.quality
        raise KeyError(candidate_id)

    @property
    def warning_count(self) -> int:
        return sum(item.quality.warning_count for item in self.results)

    @property
    def blocking_count(self) -> int:
        return sum(item.quality.blocking_count for item in self.results)

    def __repr__(self) -> str:
        return (
            "CardQualityBatch("
            f"candidate_count={len(self.results)}, warning_count={self.warning_count}, "
            f"blocking_count={self.blocking_count})"
        )


def evaluate_card_quality(
    front: object,
    back: object,
    settings: Optional[GenerationSettings] = None,
) -> CardQualityResult:
    resolved = coerce_generation_settings(settings)
    front_text = _text(front)
    back_text = _text(back)
    issues: list[CardQualityIssue] = []

    if not front_text:
        issues.append(_issue("empty_front", "blocking"))
    if not back_text:
        issues.append(_issue("empty_back", "blocking"))

    front_core = re.sub(r"[\s?？!！。，,.、:：;；]", "", front_text)
    if front_text and len(front_core) < 4:
        issues.append(_issue("short_front"))
    if front_text and any(pattern.search(front_text) for pattern in _GENERIC_FRONT_PATTERNS):
        issues.append(_issue("generic_front"))

    max_back_chars = 240 if resolved.answer_length == "short" else 500
    if resolved.card_mode == "quick_review":
        max_back_chars = min(max_back_chars, 140)
    if len(back_text) > max_back_chars:
        issues.append(_issue("long_back"))

    if front_text.count("?") + front_text.count("？") > 1:
        issues.append(_issue("multiple_questions"))

    bullet_count = sum(
        bool(_BULLET_LINE.match(line)) for line in back_text.splitlines()
    )
    multi_front = bool(
        re.search(r"(?:以及|并说明|分别|同时|\band\b.+\band\b)", front_text, re.IGNORECASE)
    )
    if bullet_count >= 3 or multi_front:
        issues.append(_issue("multi_point_card"))

    combined = f"{front_text}\n{back_text}"
    if any(pattern.search(combined) for pattern in _BOILERPLATE_PATTERNS):
        issues.append(_issue("boilerplate_phrase"))
    if _MARKDOWN_RESIDUE.search(combined):
        issues.append(_issue("markdown_residue"))

    return _build_result(tuple(_dedupe_issues(issues)))


def evaluate_card_batch(
    cards: Iterable[object],
    settings: Optional[GenerationSettings] = None,
) -> CardQualityBatch:
    resolved = coerce_generation_settings(settings)
    results: list[CandidateQualityResult] = []
    seen: set[tuple[str, str]] = set()
    for index, card in enumerate(tuple(cards), start=1):
        candidate_id = _card_value(card, "id") or _card_value(card, "candidate_id")
        if not isinstance(candidate_id, str) or not candidate_id:
            candidate_id = f"candidate-{index}"
        front = _card_value(card, "front")
        if front is None:
            front = _card_value(card, "front_preview")
        back = _card_value(card, "back")
        if back is None:
            back = _card_value(card, "back_preview")
        quality = evaluate_card_quality(front, back, resolved)
        duplicate_key = (_normalize_duplicate(front), _normalize_duplicate(back))
        if duplicate_key != ("", "") and duplicate_key in seen:
            quality = _with_issue(quality, _issue("duplicate_candidate"))
        else:
            seen.add(duplicate_key)
        results.append(CandidateQualityResult(candidate_id, quality))
    return CardQualityBatch(tuple(results))


def _issue(warning_id: str, severity: str = "warning") -> CardQualityIssue:
    return CardQualityIssue(
        warning_id=warning_id,
        severity=severity,
        suggestion_id=f"{warning_id}_suggestion",
    )


def _build_result(issues: tuple[CardQualityIssue, ...]) -> CardQualityResult:
    penalty = sum(
        0.55 if item.severity == "blocking" else 0.12
        if item.severity == "warning"
        else 0.04
        for item in issues
    )
    return CardQualityResult(round(max(0.0, 1.0 - penalty), 2), issues)


def _with_issue(
    result: CardQualityResult,
    issue: CardQualityIssue,
) -> CardQualityResult:
    if issue.warning_id in result.warning_ids:
        return result
    return _build_result((*result.issues, issue))


def _dedupe_issues(issues: Iterable[CardQualityIssue]) -> list[CardQualityIssue]:
    seen = set()
    return [
        item
        for item in issues
        if not (item.warning_id in seen or seen.add(item.warning_id))
    ]


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _card_value(card: object, name: str):
    if isinstance(card, Mapping):
        return card.get(name)
    return getattr(card, name, None)


def _normalize_duplicate(value: object) -> str:
    return " ".join(_text(value).casefold().split())
