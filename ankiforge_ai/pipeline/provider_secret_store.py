"""Secret-store contracts for user-configured pipeline providers."""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ProviderSecretRef:
    """Non-secret reference to the credential associated with a profile."""

    profile_id: str

    def __post_init__(self) -> None:
        _require_text(self.profile_id, "profile_id")

    @property
    def credential_kind(self) -> str:
        return "api_key"

    def to_dict(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "credential_kind": self.credential_kind,
        }


class ProviderSecretValue:
    """Runtime credential wrapper with redacted default display behavior."""

    __slots__ = ("__value",)

    def __init__(self, value: str):
        _require_text(value, "value")
        self.__value = value

    def reveal(self) -> str:
        """Return the credential only at an explicit runtime wiring boundary."""
        return self.__value

    def __repr__(self) -> str:
        return "<redacted>"

    def __str__(self) -> str:
        return "<redacted>"


@runtime_checkable
class ProviderSecretStore(Protocol):
    """Structural contract for a future credential storage backend."""

    def save_secret(
        self,
        ref: ProviderSecretRef,
        value: ProviderSecretValue,
    ) -> None:
        ...

    def load_secret(
        self,
        ref: ProviderSecretRef,
    ) -> ProviderSecretValue | None:
        ...

    def has_secret(self, ref: ProviderSecretRef) -> bool:
        ...

    def delete_secret(self, ref: ProviderSecretRef) -> bool:
        ...


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
