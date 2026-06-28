"""Standard-library HTTP transport for OpenAI-compatible providers."""

import json
import urllib.error
import urllib.request
from typing import Callable, Mapping, Optional

from .openai_compatible_provider import OpenAICompatibleTransportResponse


class OpenAICompatibleHTTPTransport:
    """Send JSON requests through an injectable urllib-compatible opener."""

    def __init__(self, opener: Optional[Callable] = None):
        self._opener = urllib.request.urlopen if opener is None else opener

    def post_json(
        self,
        url: str,
        headers: Mapping[str, str],
        payload: Mapping[str, object],
        timeout_seconds: Optional[float],
    ) -> OpenAICompatibleTransportResponse:
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
            error.close()
            return OpenAICompatibleTransportResponse(
                status_code=status_code,
                json_body=None,
            )

        with response:
            status_code = response.getcode()
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
