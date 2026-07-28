"""Local-authoritative critic decisions and one-shot repair validation."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from itertools import islice
from types import MappingProxyType
from typing import Mapping, Optional

from ankiforge_ai.pipeline.card_quality import evaluate_card_quality
from ankiforge_ai.pipeline.generation_settings import GenerationSettings

from .call_budget import CallPurpose
from .generation_run import GenerationRun, reserve_run_call

_SAFE_REASON = re.compile(r"^[a-z][a-z0-9_]{0,119}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_MAX_REASON_CODES = 32
_MAX_CARD_TEXT = 12_000
_MAX_SOURCE_TEXT = 12_000
_SOURCE_GROUNDING_RULE = "source_not_grounded_simple"
_GROUNDING_TOKEN = re.compile(r"[a-z0-9_]{3,}", re.IGNORECASE)
_GROUNDING_STOPWORDS = frozenset(
    {
        "and",
        "are",
        "but",
        "for",
        "from",
        "has",
        "have",
        "into",
        "not",
        "that",
        "the",
        "this",
        "was",
        "what",
        "when",
        "where",
        "which",
        "with",
    }
)


class CriticAction(str, Enum):
    PASS = "pass"
    FLAG = "flag"
    REPAIR = "repair"
    REJECT = "reject"


@dataclass(frozen=True, repr=False)
class CriticDecision:
    action: CriticAction
    reason_codes: tuple[str, ...] = ()
    local_blocking: bool = False

    def __post_init__(self) -> None:
        try:
            action = CriticAction(self.action)
        except (TypeError, ValueError):
            raise ValueError("critic action is unsupported") from None
        reasons = _bounded_tuple(
            self.reason_codes,
            _MAX_REASON_CODES,
            "reason_codes",
        )
        if len(set(reasons)) != len(reasons) or not all(
            isinstance(item, str) and _SAFE_REASON.fullmatch(item)
            for item in reasons
        ):
            raise ValueError("reason_codes must contain unique safe codes")
        if not isinstance(self.local_blocking, bool):
            raise TypeError("local_blocking must be a boolean")
        if self.local_blocking and action not in {
            CriticAction.REPAIR,
            CriticAction.REJECT,
        }:
            raise ValueError("local blocking decisions must repair or reject")
        object.__setattr__(self, "action", action)
        object.__setattr__(self, "reason_codes", reasons)

    def __repr__(self) -> str:
        return (
            "CriticDecision("
            f"action={self.action.value!r}, reason_codes={self.reason_codes!r}, "
            f"local_blocking={self.local_blocking})"
        )


@dataclass(frozen=True, repr=False)
class RepairResult:
    run: GenerationRun
    candidate_id: str
    card: object
    decision: CriticDecision
    attempted: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.run, GenerationRun):
            raise TypeError("run must be a GenerationRun")
        if not isinstance(self.candidate_id, str) or not _SAFE_ID.fullmatch(
            self.candidate_id
        ):
            raise ValueError("candidate_id must be a safe stable identifier")
        if not isinstance(self.decision, CriticDecision):
            raise TypeError("decision must be a CriticDecision")
        if not isinstance(self.attempted, bool):
            raise TypeError("attempted must be a boolean")
        object.__setattr__(self, "card", _freeze_card(self.card))

    @property
    def accepted(self) -> bool:
        return self.decision.action in {CriticAction.PASS, CriticAction.FLAG}

    def __repr__(self) -> str:
        return (
            "RepairResult("
            f"run_id={self.run.run_id!r}, calls={self.run.call_budget.call_count}, "
            f"candidate_id={self.candidate_id!r}, accepted={self.accepted}, "
            f"decision={self.decision!r})"
        )


def decide_card(
    *,
    card: object,
    source_text: str,
    model_decision: object = None,
    repair_attempted: bool = False,
    settings: Optional[GenerationSettings] = None,
) -> CriticDecision:
    """Resolve a decision while keeping deterministic local blocks authoritative."""

    if not isinstance(source_text, str):
        raise TypeError("source_text must be a string")
    if len(source_text) > _MAX_SOURCE_TEXT:
        raise ValueError("source_text exceeds the critic limit")
    if not isinstance(repair_attempted, bool):
        raise TypeError("repair_attempted must be a boolean")
    front = _card_value(card, "front")
    back = _card_value(card, "back")
    _validate_card_text(front, "front")
    _validate_card_text(back, "back")
    quality = evaluate_card_quality(
        front,
        back,
        settings,
        source_text=source_text,
    )
    local_reason_codes = tuple(
        _public_reason_code(issue.warning_id)
        for issue in quality.issues
        if issue.blocking or issue.warning_id == _SOURCE_GROUNDING_RULE
    )
    if back and source_text and not _is_locally_grounded(back, source_text):
        local_reason_codes = (*local_reason_codes, "source_not_grounded")
    local_reason_codes = tuple(dict.fromkeys(local_reason_codes))
    if local_reason_codes:
        if repair_attempted:
            return CriticDecision(
                CriticAction.REJECT,
                (*local_reason_codes, "repair_failed_local_validation"),
                local_blocking=True,
            )
        return CriticDecision(
            CriticAction.REPAIR,
            local_reason_codes,
            local_blocking=True,
        )
    return _parse_model_decision(model_decision, repair_attempted=repair_attempted)


def repair_and_revalidate(
    *,
    run: GenerationRun,
    point_id: str,
    card: object,
    source_text: str,
    repair_callback,
    settings: Optional[GenerationSettings] = None,
) -> RepairResult:
    """Make exactly one injected repair call, then run local validation again."""

    if not callable(repair_callback):
        raise TypeError("repair_callback must be callable")
    candidate_id = _candidate_id(card)
    if not isinstance(source_text, str):
        raise TypeError("source_text must be a string")
    if len(source_text) > _MAX_SOURCE_TEXT:
        raise ValueError("source_text exceeds the critic limit")
    frozen_input = _freeze_card(card)
    billed_run = reserve_run_call(
        run,
        CallPurpose.REPAIR,
        point_id=point_id,
    )
    try:
        repaired_card = repair_callback(frozen_input, source_text)
    except Exception:
        return RepairResult(
            run=billed_run,
            candidate_id=candidate_id,
            card=frozen_input,
            decision=CriticDecision(
                CriticAction.REJECT,
                ("repair_callback_failed",),
                local_blocking=True,
            ),
        )
    try:
        repaired_id = _candidate_id(repaired_card)
        if repaired_id != candidate_id:
            raise ValueError("repair changed candidate identity")
        decision = decide_card(
            card=repaired_card,
            source_text=source_text,
            model_decision=CriticDecision(CriticAction.PASS),
            repair_attempted=True,
            settings=settings,
        )
        return RepairResult(
            run=billed_run,
            candidate_id=candidate_id,
            card=repaired_card,
            decision=decision,
        )
    except Exception:
        return RepairResult(
            run=billed_run,
            candidate_id=candidate_id,
            card=frozen_input,
            decision=CriticDecision(
                CriticAction.REJECT,
                ("repair_output_invalid",),
                local_blocking=True,
            ),
        )


def _parse_model_decision(
    value: object,
    *,
    repair_attempted: bool,
) -> CriticDecision:
    if value is None:
        return CriticDecision(CriticAction.PASS)
    if isinstance(value, CriticDecision):
        action = value.action
        reasons = value.reason_codes
    elif isinstance(value, Mapping):
        raw_action = value.get("action")
        try:
            action = CriticAction(raw_action)
        except (TypeError, ValueError):
            return CriticDecision(
                CriticAction.FLAG,
                ("critic_output_invalid",),
            )
        raw_reasons = value.get("reason_codes", ())
        reasons = _safe_model_reason_codes(raw_reasons)
    elif isinstance(value, str):
        try:
            action = CriticAction(value)
        except ValueError:
            return CriticDecision(
                CriticAction.FLAG,
                ("critic_output_invalid",),
            )
        reasons = ()
    else:
        return CriticDecision(
            CriticAction.FLAG,
            ("critic_output_invalid",),
        )
    if action is CriticAction.REPAIR and repair_attempted:
        return CriticDecision(
            CriticAction.REJECT,
            (*reasons, "repair_limit_reached"),
        )
    return CriticDecision(action, reasons)


def _safe_model_reason_codes(value: object) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)):
        return ()
    try:
        candidates = tuple(islice(iter(value), _MAX_REASON_CODES + 1))
    except TypeError:
        return ()
    if len(candidates) > _MAX_REASON_CODES:
        return ("critic_reason_limit",)
    result = []
    seen = set()
    for item in candidates:
        if (
            isinstance(item, str)
            and _SAFE_REASON.fullmatch(item)
            and item not in seen
        ):
            seen.add(item)
            result.append(item)
    return tuple(result)


def _public_reason_code(rule_id: str) -> str:
    if rule_id == _SOURCE_GROUNDING_RULE:
        return "source_not_grounded"
    return rule_id


def _is_locally_grounded(card_text: str, source_text: str) -> bool:
    card_normalized = unicodedata.normalize("NFKC", card_text).casefold()
    source_normalized = unicodedata.normalize("NFKC", source_text).casefold()
    card_tokens = {
        item
        for item in _GROUNDING_TOKEN.findall(card_normalized)
        if item not in _GROUNDING_STOPWORDS
    }
    source_tokens = set(_GROUNDING_TOKEN.findall(source_normalized))
    if card_tokens:
        return len(card_tokens & source_tokens) / len(card_tokens) >= 0.6
    card_cjk = _cjk_bigrams(card_normalized)
    source_cjk = _cjk_bigrams(source_normalized)
    return bool(card_cjk) and len(card_cjk & source_cjk) / len(card_cjk) >= 0.5


def _cjk_bigrams(text: str) -> set[str]:
    characters = "".join(
        character for character in text if "\u3400" <= character <= "\u9fff"
    )
    return {
        characters[index : index + 2]
        for index in range(len(characters) - 1)
    }


def _candidate_id(card: object) -> str:
    value = _card_value(card, "candidate_id")
    if value is None:
        value = _card_value(card, "id")
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise ValueError("card requires a safe candidate_id")
    return value


def _card_value(card: object, name: str):
    if isinstance(card, Mapping):
        return card.get(name)
    return getattr(card, name, None)


def _validate_card_text(value: object, name: str) -> None:
    if value is not None and not isinstance(value, str):
        raise TypeError(f"card {name} must be a string")
    if isinstance(value, str) and len(value) > _MAX_CARD_TEXT:
        raise ValueError(f"card {name} exceeds the critic limit")


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
