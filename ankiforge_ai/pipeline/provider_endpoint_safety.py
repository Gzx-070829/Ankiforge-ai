"""Lexical provider endpoint risk classification for a desktop add-on.

This module intentionally performs no DNS lookup.  It is a confirmation policy,
not a claim of complete SSRF prevention; local providers remain supported.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import ipaddress
import re
from typing import Collection, Literal
from urllib.parse import SplitResult, urlsplit


_CONFIRM_MESSAGE_ZH = (
    "你正在使用自定义或非公开 HTTPS Provider 地址。请确认这是你信任的服务。"
    "API key 会发送到该地址。"
)
_CONFIRM_MESSAGE_EN = (
    "You are using a custom or non-public provider endpoint. Only continue if "
    "you trust this service. Your API key will be sent to this endpoint."
)
_HTTP_CONFIRM_MESSAGE_ZH = (
    "你正在使用未加密的 HTTP Provider 地址。学习材料和 API key 可能以明文"
    "传输。仅在你信任该服务和网络时继续。"
)
_HTTP_CONFIRM_MESSAGE_EN = (
    "You are using an unencrypted HTTP provider endpoint. Your study material "
    "and API key may be sent in plaintext. Only continue if you trust this "
    "service and network."
)
_DENY_MESSAGE_ZH = "该 Provider 地址不符合当前安全要求，请检查后重试。"
_DENY_MESSAGE_EN = (
    "This provider endpoint does not meet the current safety requirements."
)
DEFAULT_OFFICIAL_PROVIDER_HOSTS = frozenset(
    {"api.deepseek.com", "api.openai.com"}
)
_METADATA_HOSTS = frozenset(
    {"metadata.google.internal", "metadata.goog"}
)
_METADATA_ADDRESSES = frozenset(
    ipaddress.ip_address(value)
    for value in (
        "100.100.100.200",
        "169.254.169.254",
        "169.254.170.2",
        "fd00:ec2::254",
    )
)


@dataclass(frozen=True)
class EndpointSafetyDecision:
    kind: Literal["allow", "confirm", "deny"]
    reason_code: str
    display_endpoint: str
    user_message_zh: str
    user_message_en: str


@dataclass(frozen=True)
class _ParsedEndpoint:
    parsed: SplitResult
    scheme: str
    host: str
    port: int | None
    display_endpoint: str


class EndpointConfirmationSession:
    """In-memory confirmation keys; callers must clear it with the UI session."""

    def __init__(self, keys: Collection[str] = ()):
        self._keys = {str(key) for key in keys if str(key)}

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(sorted(self._keys))

    def is_confirmed(self, url: str) -> bool:
        return endpoint_confirmation_key(url) in self._keys

    def confirm(self, url: str) -> str:
        key = endpoint_confirmation_key(url)
        self._keys.add(key)
        return key

    def add_key(self, key: str) -> None:
        if not isinstance(key, str) or not key:
            raise ValueError("confirmation key must be a non-empty string")
        self._keys.add(key)

    def clear(self) -> None:
        self._keys.clear()

    def __repr__(self) -> str:
        return f"EndpointConfirmationSession(key_count={len(self._keys)})"


def assess_provider_endpoint(
    url: str,
    *,
    official_hosts: Collection[str],
) -> EndpointSafetyDecision:
    """Classify one URL without resolving or contacting its host."""

    try:
        endpoint = _parse_endpoint(url)
    except ValueError:
        return _deny("invalid_url", "")

    parsed = endpoint.parsed
    if endpoint.scheme not in {"http", "https"}:
        return _deny("unsupported_scheme", endpoint.display_endpoint)
    if not endpoint.host:
        return _deny("missing_host", endpoint.display_endpoint)
    if parsed.username is not None or parsed.password is not None:
        return _deny("embedded_credentials", endpoint.display_endpoint)
    if parsed.query:
        return _deny("query_not_allowed", endpoint.display_endpoint)
    if parsed.fragment:
        return _deny("fragment_not_allowed", endpoint.display_endpoint)

    host = endpoint.host
    if host in _METADATA_HOSTS:
        return _deny("metadata_endpoint", endpoint.display_endpoint)

    address = _ip_address(host)
    if address is not None:
        effective_address = getattr(address, "ipv4_mapped", None) or address
        if (
            address in _METADATA_ADDRESSES
            or effective_address in _METADATA_ADDRESSES
        ):
            return _deny("metadata_endpoint", endpoint.display_endpoint)
        if effective_address.is_unspecified:
            return _deny("unspecified_address", endpoint.display_endpoint)
        if effective_address.is_multicast:
            return _deny("multicast_address", endpoint.display_endpoint)
        if effective_address.is_loopback:
            return _confirm("loopback_address", endpoint.display_endpoint)
        if effective_address.is_link_local:
            return _confirm("link_local_address", endpoint.display_endpoint)
        if effective_address.is_private:
            return _confirm("private_address", endpoint.display_endpoint)
    elif _looks_like_noncanonical_numeric_address(host):
        return _deny("invalid_numeric_address", endpoint.display_endpoint)

    normalized_official_hosts = {
        str(item).strip().casefold().rstrip(".")
        for item in official_hosts
        if str(item).strip()
    }
    if (
        endpoint.scheme == "https"
        and host in normalized_official_hosts
        and endpoint.port in {None, 443}
    ):
        return _allow("official_https", endpoint.display_endpoint)

    if endpoint.scheme == "http":
        return _confirm("unencrypted_http", endpoint.display_endpoint)
    if host == "localhost" or host.endswith(".localhost"):
        return _confirm("localhost", endpoint.display_endpoint)
    if host.endswith(".local"):
        return _confirm("local_hostname", endpoint.display_endpoint)
    if "." not in host:
        return _confirm("bare_hostname", endpoint.display_endpoint)
    return _confirm("custom_https", endpoint.display_endpoint)


def endpoint_confirmation_key(url: str) -> str:
    """Return a non-reversible key for normalized scheme/host/port only."""

    endpoint = _parse_endpoint(url)
    if not endpoint.host or endpoint.scheme not in {"http", "https"}:
        raise ValueError("endpoint must be an HTTP or HTTPS URL with a host")
    normalized = endpoint.display_endpoint.encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def endpoint_is_authorized(
    url: str,
    *,
    official_hosts: Collection[str],
    confirmation_key: str | None,
) -> bool:
    """Enforce the same decision at the network boundary."""

    decision = assess_provider_endpoint(url, official_hosts=official_hosts)
    if decision.kind == "allow":
        return True
    if decision.kind == "deny" or not confirmation_key:
        return False
    try:
        return confirmation_key == endpoint_confirmation_key(url)
    except ValueError:
        return False


def _parse_endpoint(url: str) -> _ParsedEndpoint:
    if not isinstance(url, str) or not url.strip():
        raise ValueError("endpoint must be a non-empty string")
    stripped = url.strip()
    if any(ord(character) < 32 for character in stripped):
        raise ValueError("endpoint contains control characters")
    try:
        parsed = urlsplit(stripped)
        scheme = parsed.scheme.casefold()
        host = (parsed.hostname or "").casefold().rstrip(".")
        port = parsed.port
    except (TypeError, ValueError):
        raise ValueError("endpoint cannot be parsed") from None
    normalized_port = port
    if (scheme == "https" and port == 443) or (scheme == "http" and port == 80):
        normalized_port = None
    host_display = f"[{host}]" if ":" in host else host
    display = f"{scheme}://{host_display}" if scheme and host else ""
    if normalized_port is not None and display:
        display += f":{normalized_port}"
    return _ParsedEndpoint(parsed, scheme, host, normalized_port, display)


def _ip_address(host: str):
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        return None


def _looks_like_noncanonical_numeric_address(host: str) -> bool:
    if re.fullmatch(r"(?:[0-9]+|0x[0-9a-f]+)", host, flags=re.IGNORECASE):
        return True
    if host.count(".") != 3:
        return False
    return all(
        re.fullmatch(
            r"(?:[0-9]+|0x[0-9a-f]+)",
            part,
            flags=re.IGNORECASE,
        )
        for part in host.split(".")
    )


def _allow(reason_code: str, display_endpoint: str) -> EndpointSafetyDecision:
    return EndpointSafetyDecision(
        "allow",
        reason_code,
        display_endpoint,
        "这是官方 HTTPS Provider 地址。",
        "This is an official HTTPS provider endpoint.",
    )


def _confirm(reason_code: str, display_endpoint: str) -> EndpointSafetyDecision:
    message_zh = (
        _HTTP_CONFIRM_MESSAGE_ZH
        if reason_code == "unencrypted_http"
        else _CONFIRM_MESSAGE_ZH
    )
    message_en = (
        _HTTP_CONFIRM_MESSAGE_EN
        if reason_code == "unencrypted_http"
        else _CONFIRM_MESSAGE_EN
    )
    return EndpointSafetyDecision(
        "confirm",
        reason_code,
        display_endpoint,
        message_zh,
        message_en,
    )


def _deny(reason_code: str, display_endpoint: str) -> EndpointSafetyDecision:
    return EndpointSafetyDecision(
        "deny",
        reason_code,
        display_endpoint,
        _DENY_MESSAGE_ZH,
        _DENY_MESSAGE_EN,
    )
