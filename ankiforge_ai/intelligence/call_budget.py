"""Immutable call reservations for one bounded intelligence run."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from itertools import islice
import re
from typing import Optional

from .models import IntelligenceLevel


MAX_AI_CALLS_PER_RUN = 12
_SAFE_REASON = re.compile(r"^[a-z][a-z0-9_]{0,119}$")
_CALL_POLICY = {
    IntelligenceLevel.FAST: (1, 3),
    IntelligenceLevel.STANDARD: (3, 8),
    IntelligenceLevel.DEEP: (4, 12),
}
_ALLOWED_PURPOSES = {
    IntelligenceLevel.FAST: frozenset({"generate"}),
    IntelligenceLevel.STANDARD: frozenset({"planner", "generate", "repair"}),
    IntelligenceLevel.DEEP: frozenset(
        {"planner", "generate", "critic", "repair", "supplement"}
    ),
}


class CallPurpose(str, Enum):
    PLANNER = "planner"
    GENERATE = "generate"
    CRITIC = "critic"
    REPAIR = "repair"
    SUPPLEMENT = "supplement"


@dataclass(frozen=True, repr=False)
class CallReservation:
    sequence: int
    purpose: CallPurpose

    def __post_init__(self) -> None:
        if (
            isinstance(self.sequence, bool)
            or not isinstance(self.sequence, int)
            or self.sequence < 1
            or self.sequence > MAX_AI_CALLS_PER_RUN
        ):
            raise ValueError("reservation sequence must be a bounded integer")
        try:
            purpose = CallPurpose(self.purpose)
        except (TypeError, ValueError):
            raise ValueError("reservation purpose is unsupported") from None
        object.__setattr__(self, "purpose", purpose)

    def __repr__(self) -> str:
        return (
            "CallReservation("
            f"sequence={self.sequence}, purpose={self.purpose.value!r})"
        )


class CallBudgetError(ValueError):
    """A safe structured rejection that never includes caller/provider data."""

    def __init__(
        self,
        reason_code: str,
        *,
        call_count: int,
        call_limit: int,
        purpose: Optional[CallPurpose] = None,
    ) -> None:
        if (
            not isinstance(reason_code, str)
            or not _SAFE_REASON.fullmatch(reason_code)
        ):
            raise ValueError("reason_code must be a safe bounded code")
        for value, name in (
            (call_count, "call_count"),
            (call_limit, "call_limit"),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer")
        if (
            call_count < 0
            or call_limit < 1
            or call_limit > MAX_AI_CALLS_PER_RUN
            or call_count > call_limit
        ):
            raise ValueError("call counts must be within the global budget")
        if purpose is not None and not isinstance(purpose, CallPurpose):
            raise TypeError("purpose must be a CallPurpose")
        self.reason_code = reason_code
        self.call_count = call_count
        self.call_limit = call_limit
        self.purpose = purpose
        super().__init__(reason_code)

    def __repr__(self) -> str:
        purpose = None if self.purpose is None else self.purpose.value
        return (
            "CallBudgetError("
            f"reason_code={self.reason_code!r}, calls={self.call_count}/"
            f"{self.call_limit}, purpose={purpose!r})"
        )

    __str__ = __repr__


@dataclass(frozen=True, repr=False)
class CallBudget:
    level: IntelligenceLevel = IntelligenceLevel.STANDARD
    call_count: int = 0
    reservations: tuple[CallReservation, ...] = ()
    minimum_calls: Optional[int] = None
    call_limit: Optional[int] = None

    def __post_init__(self) -> None:
        try:
            level = IntelligenceLevel(self.level)
        except (TypeError, ValueError):
            raise ValueError("level must be fast, standard, or deep") from None
        minimum, limit = _CALL_POLICY[level]
        resolved_minimum = minimum if self.minimum_calls is None else self.minimum_calls
        resolved_limit = limit if self.call_limit is None else self.call_limit
        for value, name in (
            (self.call_count, "call_count"),
            (resolved_minimum, "minimum_calls"),
            (resolved_limit, "call_limit"),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer")
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
        if (resolved_minimum, resolved_limit) != (minimum, limit):
            raise ValueError("call range does not match the level policy")
        if resolved_limit > MAX_AI_CALLS_PER_RUN:
            raise ValueError("call limit exceeds the global ceiling")
        raw_reservations = _bounded_tuple(
            self.reservations,
            resolved_limit,
            "reservations",
        )
        try:
            reservations = tuple(
                item
                if isinstance(item, CallReservation)
                else CallReservation(*item)
                for item in raw_reservations
            )
        except (TypeError, ValueError):
            raise ValueError("reservations must contain valid call reservations") from None
        if self.call_count != len(reservations):
            raise ValueError("call_count must match reservation count")
        if tuple(item.sequence for item in reservations) != tuple(
            range(1, len(reservations) + 1)
        ):
            raise ValueError("reservation sequences must be contiguous")
        if any(item.purpose.value not in _ALLOWED_PURPOSES[level] for item in reservations):
            raise ValueError("reservation purpose does not match the level policy")
        object.__setattr__(self, "level", level)
        object.__setattr__(self, "minimum_calls", resolved_minimum)
        object.__setattr__(self, "call_limit", resolved_limit)
        object.__setattr__(self, "reservations", reservations)

    @classmethod
    def for_level(cls, level: IntelligenceLevel) -> "CallBudget":
        return cls(level=level)

    @property
    def remaining_calls(self) -> int:
        return self.call_limit - self.call_count

    def reserve(self, purpose: CallPurpose) -> "CallBudget":
        try:
            normalized = CallPurpose(purpose)
        except (TypeError, ValueError):
            raise CallBudgetError(
                "call_purpose_invalid",
                call_count=self.call_count,
                call_limit=self.call_limit,
            ) from None
        if normalized.value not in _ALLOWED_PURPOSES[self.level]:
            raise CallBudgetError(
                "call_not_allowed",
                call_count=self.call_count,
                call_limit=self.call_limit,
                purpose=normalized,
            )
        if self.call_count >= self.call_limit:
            raise CallBudgetError(
                "call_budget_exhausted",
                call_count=self.call_count,
                call_limit=self.call_limit,
                purpose=normalized,
            )
        reservation = CallReservation(self.call_count + 1, normalized)
        return replace(
            self,
            call_count=self.call_count + 1,
            reservations=(*self.reservations, reservation),
        )

    def __repr__(self) -> str:
        last_purpose = (
            None if not self.reservations else self.reservations[-1].purpose.value
        )
        return (
            "CallBudget("
            f"level={self.level.value!r}, calls={self.call_count}/"
            f"{self.call_limit}, last_purpose={last_purpose!r})"
        )


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
