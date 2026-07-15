"""Deterministic hard gates for an explicitly confirmed Anki write."""

from dataclasses import dataclass


@dataclass(frozen=True)
class WriteSafetySnapshot:
    kept_count: int
    blocking_write_count: int
    mapping_complete: bool
    duplicate_check_complete: bool
    final_confirmation_confirmed: bool
    target_valid: bool
    generation_complete: bool

    def __post_init__(self) -> None:
        for value, name in (
            (self.kept_count, "kept_count"),
            (self.blocking_write_count, "blocking_write_count"),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer.")
        if self.blocking_write_count > self.kept_count:
            raise ValueError("blocking_write_count cannot exceed kept_count.")
        for value, name in (
            (self.mapping_complete, "mapping_complete"),
            (self.duplicate_check_complete, "duplicate_check_complete"),
            (self.final_confirmation_confirmed, "final_confirmation_confirmed"),
            (self.target_valid, "target_valid"),
            (self.generation_complete, "generation_complete"),
        ):
            if not isinstance(value, bool):
                raise ValueError(f"{name} must be a boolean.")


@dataclass(frozen=True)
class WriteSafetyDecision:
    allowed: bool
    writable_count: int
    blocking_reasons: tuple[str, ...]

    def to_safe_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "writable_count": self.writable_count,
            "blocking_reason_count": len(self.blocking_reasons),
            "blocking_reasons": self.blocking_reasons,
        }


def evaluate_write_safety(snapshot: WriteSafetySnapshot) -> WriteSafetyDecision:
    if not isinstance(snapshot, WriteSafetySnapshot):
        raise ValueError("snapshot must be a WriteSafetySnapshot.")
    reasons = []
    if snapshot.kept_count == 0:
        reasons.append("no_kept_cards")
    if snapshot.blocking_write_count:
        reasons.append("blocking_cards_in_write_list")
    if not snapshot.mapping_complete:
        reasons.append("mapping_incomplete")
    if not snapshot.duplicate_check_complete:
        reasons.append("duplicate_not_checked")
    if not snapshot.final_confirmation_confirmed:
        reasons.append("final_confirmation_required")
    if not snapshot.target_valid:
        reasons.append("write_target_invalid")
    if not snapshot.generation_complete:
        reasons.append("generation_in_progress")
    blocking_reasons = tuple(reasons)
    return WriteSafetyDecision(
        allowed=not blocking_reasons,
        writable_count=snapshot.kept_count - snapshot.blocking_write_count,
        blocking_reasons=blocking_reasons,
    )
