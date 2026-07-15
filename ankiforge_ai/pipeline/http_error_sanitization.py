"""Bounded, secret-aware parsing of untrusted provider HTTP error bodies."""

from __future__ import annotations

import json
import re
from typing import Iterable


MAX_PROVIDER_ERROR_BODY_BYTES = 8192
MAX_PROVIDER_ERROR_DETAIL_CHARS = 300

_AUTHORIZATION_RE = re.compile(
    r"(?i)\bauthorization\s*[:=]\s*(?:bearer\s+)?[^\s,;]+"
)
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
_SK_KEY_RE = re.compile(r"(?i)\bsk-[A-Za-z0-9_-]+")
_LABELLED_SECRET_RE = re.compile(
    r"(?i)\b(?:api[_ -]?key|token|password)\s*[:=]\s*[^\s,;]+"
)


def sanitize_provider_error_body(
    body: object,
    *,
    sensitive_values: Iterable[str] = (),
) -> str:
    """Extract one short detail and discard all raw input after this call."""

    if not isinstance(body, (bytes, bytearray)):
        return ""
    bounded = bytes(body[:MAX_PROVIDER_ERROR_BODY_BYTES])
    text = bounded.decode("utf-8", errors="replace")
    detail = _extract_detail(text)
    return sanitize_provider_error_detail(
        detail,
        sensitive_values=sensitive_values,
    )


def sanitize_provider_error_detail(
    detail: object,
    *,
    sensitive_values: Iterable[str] = (),
) -> str:
    """Enforce the safe diagnostic invariant for any injected transport."""

    if not isinstance(detail, str):
        return ""

    for secret in sorted(
        {str(value) for value in sensitive_values if str(value)},
        key=len,
        reverse=True,
    ):
        detail = detail.replace(secret, "[redacted]")
    detail = _AUTHORIZATION_RE.sub("[redacted]", detail)
    detail = _BEARER_RE.sub("[redacted]", detail)
    detail = _SK_KEY_RE.sub("[redacted]", detail)
    detail = _LABELLED_SECRET_RE.sub("[redacted]", detail)
    detail = " ".join(detail.split())
    if len(detail) > MAX_PROVIDER_ERROR_DETAIL_CHARS:
        detail = detail[: MAX_PROVIDER_ERROR_DETAIL_CHARS - 1].rstrip() + "…"
    return detail


def _extract_detail(text: str) -> str:
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return text
    if not isinstance(payload, dict):
        return ""
    error = payload.get("error")
    if isinstance(error, dict) and isinstance(error.get("message"), str):
        return error["message"]
    for key in ("message", "detail"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return ""
