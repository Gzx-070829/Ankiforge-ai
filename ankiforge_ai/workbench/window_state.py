"""Strict non-sensitive state for the workbench window only."""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
import re
from typing import Mapping


MAX_GEOMETRY_TEXT_LENGTH = 8192
_ALLOWED_FIELDS = frozenset({"geometry", "maximized"})
_SECRET_SHAPED_BYTES = re.compile(
    rb"(?:sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|bearer\s+|"
    rb"github_pat_|gh[pousr]_)",
    re.IGNORECASE,
)


@dataclass(frozen=True, repr=False)
class WorkbenchWindowState:
    """One bounded Qt geometry value and its maximized flag."""

    geometry: str = ""
    maximized: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.maximized, bool):
            raise ValueError("maximized must be bool")
        if (
            not isinstance(self.geometry, str)
            or len(self.geometry) > MAX_GEOMETRY_TEXT_LENGTH
        ):
            raise ValueError("geometry must be bounded text")
        if not self.geometry:
            return
        try:
            decoded = base64.b64decode(self.geometry, validate=True)
        except (ValueError, binascii.Error) as error:
            raise ValueError("geometry must be canonical base64") from error
        canonical = base64.b64encode(decoded).decode("ascii")
        if canonical != self.geometry:
            raise ValueError("geometry must be canonical base64")
        if _SECRET_SHAPED_BYTES.search(decoded):
            raise ValueError("geometry must not contain secret-shaped data")

    @classmethod
    def defaults(cls) -> "WorkbenchWindowState":
        return cls()

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, object],
    ) -> "WorkbenchWindowState":
        if not isinstance(value, Mapping):
            raise ValueError("window state must be an object")
        if set(value) != _ALLOWED_FIELDS:
            raise ValueError("window state contains unsupported fields")
        return cls(
            geometry=value["geometry"],
            maximized=value["maximized"],
        )

    def to_safe_dict(self) -> dict:
        return {
            "geometry": self.geometry,
            "maximized": self.maximized,
        }

    def __repr__(self) -> str:
        return (
            "WorkbenchWindowState("
            f"geometry_present={bool(self.geometry)!r}, "
            f"maximized={self.maximized!r})"
        )
