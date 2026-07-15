"""Standard-library HTTP transport for OpenAI-compatible providers."""

import json
import urllib.error
import urllib.request
from typing import Callable, Mapping, Optional

from .http_error_sanitization import (
    MAX_PROVIDER_ERROR_BODY_BYTES,
    sanitize_provider_error_body,
)
from .openai_compatible_provider import OpenAICompatibleTransportResponse
from .provider_endpoint_safety import (
    DEFAULT_OFFICIAL_PROVIDER_HOSTS,
    assess_provider_endpoint,
)


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Keep credentials bound to the endpoint the user approved."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _open_without_redirects(request, timeout=None):
    opener = urllib.request.build_opener(_NoRedirectHandler())
    return opener.open(request, timeout=timeout)


class OpenAICompatibleHTTPTransport:
    """Send JSON requests through an injectable urllib-compatible opener."""

    def __init__(self, opener: Optional[Callable] = None):
        self._opener = _open_without_redirects if opener is None else opener

    def post_json(
        self,
        url: str,
        headers: Mapping[str, str],
        payload: Mapping[str, object],
        timeout_seconds: Optional[float],
    ) -> OpenAICompatibleTransportResponse:
        decision = assess_provider_endpoint(
            url,
            official_hosts=DEFAULT_OFFICIAL_PROVIDER_HOSTS,
        )
        if decision.kind == "deny":
            raise ValueError("provider endpoint is denied")
        request = urllib.request.Request(
            url=url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=dict(headers),
            method="POST",
        )

        try:
            response = self._opener(request, timeout=timeout_seconds)
        except urllib.error.HTTPError as error:
            status_code = error.code
            try:
                body = error.read(MAX_PROVIDER_ERROR_BODY_BYTES)
            except (OSError, ValueError):
                body = b""
            finally:
                try:
                    error.close()
                except OSError:
                    pass
            return OpenAICompatibleTransportResponse(
                status_code=status_code,
                json_body=None,
                error_detail=sanitize_provider_error_body(
                    body,
                    sensitive_values=_authorization_secrets(headers),
                ),
            )

        with response:
            status_code = response.getcode()
            if not 200 <= status_code < 300:
                body = response.read(MAX_PROVIDER_ERROR_BODY_BYTES)
                return OpenAICompatibleTransportResponse(
                    status_code=status_code,
                    json_body=None,
                    error_detail=sanitize_provider_error_body(
                        body,
                        sensitive_values=_authorization_secrets(headers),
                    ),
                )
            body = response.read()

        return OpenAICompatibleTransportResponse(
            status_code=status_code,
            json_body=_decode_json_body(body),
        )


def _decode_json_body(body: object) -> object:
    if not isinstance(body, (bytes, bytearray)):
        return None
    try:
        text = bytes(body).decode("utf-8")
        return json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _authorization_secrets(headers: Mapping[str, str]) -> tuple[str, ...]:
    values = []
    for name, value in headers.items():
        if str(name).casefold() != "authorization":
            continue
        text = str(value or "")
        if text:
            values.append(text)
        if text.casefold().startswith("bearer "):
            token = text[7:].strip()
            if token:
                values.append(token)
    return tuple(values)
