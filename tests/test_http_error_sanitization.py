import io
import unittest
import urllib.error

from ankiforge_ai.pipeline.http_error_sanitization import (
    MAX_PROVIDER_ERROR_BODY_BYTES,
    MAX_PROVIDER_ERROR_DETAIL_CHARS,
    sanitize_provider_error_body,
)
from ankiforge_ai.pipeline.openai_compatible_http_transport import (
    OpenAICompatibleHTTPTransport,
)


class RecordingBytesIO(io.BytesIO):
    def __init__(self, value):
        super().__init__(value)
        self.requested_sizes = []

    def read(self, size=-1):
        self.requested_sizes.append(size)
        return super().read(size)


class RaisingOpener:
    def __init__(self, code, body):
        self.stream = RecordingBytesIO(body)
        self.code = code

    def __call__(self, request, timeout=None):
        raise urllib.error.HTTPError(
            request.full_url,
            self.code,
            "provider error",
            hdrs=None,
            fp=self.stream,
        )


class HTTPErrorSanitizationTests(unittest.TestCase):
    def test_extracts_supported_json_shapes(self):
        cases = (
            (b'{"error":{"message":"bad model"}}', "bad model"),
            (b'{"message":"quota reached"}', "quota reached"),
            (b'{"detail":"temporarily unavailable"}', "temporarily unavailable"),
        )
        for body, expected in cases:
            with self.subTest(body=body):
                self.assertEqual(sanitize_provider_error_body(body), expected)

    def test_malformed_json_and_plain_text_are_safe_and_bounded(self):
        detail = sanitize_provider_error_body(
            ("provider failure\n" + "x" * 1000).encode("utf-8")
        )

        self.assertNotIn("\n", detail)
        self.assertLessEqual(len(detail), MAX_PROVIDER_ERROR_DETAIL_CHARS)

    def test_long_material_echo_is_never_retained_in_full(self):
        material_echo = "private-study-material " * 100

        detail = sanitize_provider_error_body(material_echo.encode("utf-8"))

        self.assertLessEqual(len(detail), MAX_PROVIDER_ERROR_DETAIL_CHARS)
        self.assertNotEqual(detail, material_echo.strip())

    def test_tokens_and_authorization_values_are_redacted(self):
        secret = "session-secret-value-1234567890"
        body = (
            '{"error":{"message":"Authorization: Bearer '
            + secret
            + ' sk-live-looking-secret-1234567890"}}'
        ).encode("utf-8")

        detail = sanitize_provider_error_body(
            body,
            sensitive_values=(secret,),
        )

        self.assertNotIn(secret, detail)
        self.assertNotIn("sk-live-looking-secret", detail)
        self.assertNotIn("Bearer", detail)
        self.assertIn("[redacted]", detail)

    def test_equals_authorization_and_short_sk_values_are_redacted(self):
        detail = sanitize_provider_error_body(
            b'{"message":"Authorization=custom-secret sk-x"}'
        )

        self.assertNotIn("custom-secret", detail)
        self.assertNotIn("sk-x", detail)
        self.assertGreaterEqual(detail.count("[redacted]"), 1)

    def test_http_transport_reads_at_most_8192_and_never_stores_raw_body(self):
        secret = "transport-secret-1234567890"
        body = (
            '{"error":{"message":"Bearer '
            + secret
            + " "
            + "private-material " * 1000
            + '"}}'
        ).encode("utf-8")
        opener = RaisingOpener(429, body)

        result = OpenAICompatibleHTTPTransport(opener=opener).post_json(
            url="https://provider.example/v1/chat/completions",
            headers={"Authorization": f"Bearer {secret}"},
            payload={"messages": []},
            timeout_seconds=5,
        )

        self.assertEqual(result.status_code, 429)
        self.assertEqual(opener.stream.requested_sizes, [MAX_PROVIDER_ERROR_BODY_BYTES])
        self.assertLessEqual(len(result.error_detail), MAX_PROVIDER_ERROR_DETAIL_CHARS)
        self.assertNotIn(secret, result.error_detail)
        self.assertNotIn(secret, repr(result))
        self.assertFalse(hasattr(result, "raw_body"))

    def test_error_response_repr_does_not_include_sanitized_detail(self):
        opener = RaisingOpener(500, b"private provider diagnostic")

        result = OpenAICompatibleHTTPTransport(opener=opener).post_json(
            url="https://provider.example/v1/chat/completions",
            headers={"Authorization": "Bearer fake-key"},
            payload={},
            timeout_seconds=5,
        )

        self.assertEqual(result.error_detail, "private provider diagnostic")
        self.assertNotIn("private provider diagnostic", repr(result))


if __name__ == "__main__":
    unittest.main()
