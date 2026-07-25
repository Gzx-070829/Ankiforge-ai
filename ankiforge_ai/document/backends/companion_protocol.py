from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from ..models import DocumentIR
from ..serialization import document_from_safe_json, document_to_safe_json


PROTOCOL_VERSION = 1
MAX_COMPANION_JSON_BYTES = 6 * 1024 * 1024
MAX_IDENTIFIER_CHARS = 128
MAX_CAPABILITIES = 64
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


def _validate_version(value: int) -> None:
    if type(value) is not int or value != PROTOCOL_VERSION:
        raise ValueError("unsupported companion protocol version")


def _validate_identifier(value: str, name: str) -> None:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise ValueError(f"{name} must be a bounded safe identifier")


def _decode_json(payload: str) -> Dict[str, object]:
    if not isinstance(payload, str):
        raise TypeError("companion JSON must be text")
    try:
        encoded_length = len(payload.encode("utf-8"))
    except UnicodeEncodeError:
        raise ValueError("companion JSON must contain valid Unicode") from None
    if encoded_length > MAX_COMPANION_JSON_BYTES:
        raise ValueError("companion JSON exceeds bounded size")
    try:
        value = json.loads(payload, object_pairs_hook=_reject_duplicate_keys)
    except (json.JSONDecodeError, RecursionError, UnicodeError):
        raise ValueError("invalid companion JSON") from None
    if not isinstance(value, dict):
        raise ValueError("companion JSON must be an object")
    return value


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate companion JSON key")
        result[key] = value
    return result


def _require_exact_keys(
    value: Dict[str, object],
    expected: frozenset[str],
    label: str,
) -> None:
    actual = frozenset(value)
    if actual - expected:
        raise ValueError(f"{label} has unexpected fields")
    if expected - actual:
        raise ValueError(f"{label} is missing required fields")


def _encode_json(value: Dict[str, object]) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    if len(payload.encode("utf-8")) > MAX_COMPANION_JSON_BYTES:
        raise ValueError("companion JSON exceeds bounded size")
    return payload


@dataclass(frozen=True)
class CompanionRequest:
    protocol_version: int
    request_id: str
    operation: str
    capability: Optional[str] = None
    local_file_token: Optional[str] = None

    _KEYS = frozenset(
        {
            "protocol_version",
            "request_id",
            "operation",
            "capability",
            "local_file_token",
        }
    )

    def __post_init__(self) -> None:
        _validate_version(self.protocol_version)
        _validate_identifier(self.request_id, "request_id")
        if self.operation not in {"capabilities", "health", "convert", "cancel"}:
            raise ValueError("unsupported companion operation")
        if self.capability is not None:
            _validate_identifier(self.capability, "capability")
        if self.local_file_token is not None:
            _validate_identifier(self.local_file_token, "local_file_token")
        if self.operation == "convert" and (
            self.capability is None or self.local_file_token is None
        ):
            raise ValueError("convert requires capability and local_file_token")
        if self.operation != "convert" and self.local_file_token is not None:
            raise ValueError("only convert may carry a local_file_token")
        if self.operation in {"capabilities", "health"} and self.capability is not None:
            raise ValueError("capability query fields are fixed by the operation")

    def to_json(self) -> str:
        return _encode_json(
            {
                "protocol_version": self.protocol_version,
                "request_id": self.request_id,
                "operation": self.operation,
                "capability": self.capability,
                "local_file_token": self.local_file_token,
            }
        )

    @classmethod
    def from_json(cls, payload: str) -> "CompanionRequest":
        value = _decode_json(payload)
        _require_exact_keys(value, cls._KEYS, "companion request")
        _validate_version(value["protocol_version"])
        try:
            return cls(**value)
        except (TypeError, ValueError):
            raise ValueError("invalid companion request") from None


@dataclass(frozen=True)
class CompanionProgress:
    protocol_version: int
    request_id: str
    stage: str
    completed: int
    total: int

    _KEYS = frozenset(
        {"protocol_version", "request_id", "stage", "completed", "total"}
    )

    def __post_init__(self) -> None:
        _validate_version(self.protocol_version)
        _validate_identifier(self.request_id, "request_id")
        _validate_identifier(self.stage, "stage")
        if any(
            isinstance(value, bool) or not isinstance(value, int)
            for value in (self.completed, self.total)
        ):
            raise TypeError("progress counters must be integers")
        if not 0 <= self.completed <= self.total <= 1_000_000_000:
            raise ValueError("progress counters must be bounded and ordered")

    def to_json(self) -> str:
        return _encode_json(
            {
                "protocol_version": self.protocol_version,
                "request_id": self.request_id,
                "stage": self.stage,
                "completed": self.completed,
                "total": self.total,
            }
        )

    @classmethod
    def from_json(cls, payload: str) -> "CompanionProgress":
        value = _decode_json(payload)
        _require_exact_keys(value, cls._KEYS, "companion progress")
        _validate_version(value["protocol_version"])
        try:
            return cls(**value)
        except (TypeError, ValueError):
            raise ValueError("invalid companion progress") from None


@dataclass(frozen=True, repr=False)
class CompanionResponse:
    protocol_version: int
    request_id: str
    status: str
    capabilities: Tuple[str, ...] = ()
    document: Optional[DocumentIR] = None
    error_code: Optional[str] = None
    message_key: Optional[str] = None
    action_key: Optional[str] = None

    _KEYS = frozenset(
        {
            "protocol_version",
            "request_id",
            "status",
            "capabilities",
            "document",
            "error_code",
            "message_key",
            "action_key",
        }
    )

    def __post_init__(self) -> None:
        _validate_version(self.protocol_version)
        _validate_identifier(self.request_id, "request_id")
        if self.status not in {"ok", "error", "cancelled"}:
            raise ValueError("unsupported companion response status")
        capabilities = tuple(self.capabilities)
        if len(capabilities) > MAX_CAPABILITIES:
            raise ValueError("too many companion capabilities")
        for capability in capabilities:
            _validate_identifier(capability, "capability")
        object.__setattr__(self, "capabilities", capabilities)
        for name in ("error_code", "message_key", "action_key"):
            value = getattr(self, name)
            if value is not None:
                _validate_identifier(value, name)
        error_fields = (self.error_code, self.message_key, self.action_key)
        if self.status == "error":
            if any(value is None for value in error_fields):
                raise ValueError("error response requires structured error fields")
            if self.document is not None or capabilities:
                raise ValueError("error response cannot carry a result")
        elif any(value is not None for value in error_fields):
            raise ValueError("non-error response cannot carry error fields")
        if self.status == "cancelled" and (
            self.document is not None or capabilities
        ):
            raise ValueError("cancelled response cannot carry a result")
        if self.status == "ok" and self.document is not None and capabilities:
            raise ValueError("response carries one result kind")

    def __repr__(self) -> str:
        return (
            f"CompanionResponse(protocol_version={self.protocol_version}, "
            f"request_id={self.request_id!r}, status={self.status!r}, "
            f"capability_count={len(self.capabilities)}, "
            f"has_document={self.document is not None}, "
            f"error_code={self.error_code!r})"
        )

    def to_json(self) -> str:
        document = (
            json.loads(document_to_safe_json(self.document))
            if self.document is not None
            else None
        )
        return _encode_json(
            {
                "protocol_version": self.protocol_version,
                "request_id": self.request_id,
                "status": self.status,
                "capabilities": list(self.capabilities),
                "document": document,
                "error_code": self.error_code,
                "message_key": self.message_key,
                "action_key": self.action_key,
            }
        )

    @classmethod
    def from_json(cls, payload: str) -> "CompanionResponse":
        value = _decode_json(payload)
        _require_exact_keys(value, cls._KEYS, "companion response")
        _validate_version(value["protocol_version"])
        capabilities = value.get("capabilities")
        if not isinstance(capabilities, list):
            raise ValueError("invalid companion response")
        document_value = value.get("document")
        document = None
        if document_value is not None:
            try:
                document = document_from_safe_json(
                    json.dumps(
                        document_value,
                        ensure_ascii=False,
                        allow_nan=False,
                        separators=(",", ":"),
                    )
                )
            except (TypeError, ValueError):
                raise ValueError("invalid companion response") from None
        value["capabilities"] = tuple(capabilities)
        value["document"] = document
        try:
            return cls(**value)
        except (TypeError, ValueError):
            raise ValueError("invalid companion response") from None
