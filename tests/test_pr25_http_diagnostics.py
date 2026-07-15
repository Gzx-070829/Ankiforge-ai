import unittest

from ankiforge_ai.pipeline.openai_compatible_provider import (
    OpenAICompatibleTransportResponse,
)
from ankiforge_ai.ui.beginner_ai_card_drafts import (
    BeginnerAICardDraftGenerator,
    BeginnerAIProviderRuntimeSettings,
    generation_error_message_key,
)


class StubTransport:
    def __init__(self, status_code, detail=""):
        self.response = OpenAICompatibleTransportResponse(
            status_code=status_code,
            json_body=None,
            error_detail=detail,
        )

    def post_json(self, **kwargs):
        return self.response


class PR25HTTPDiagnosticsTests(unittest.TestCase):
    def settings(self):
        return BeginnerAIProviderRuntimeSettings(
            provider_name="DeepSeek",
            base_url="https://api.deepseek.com",
            model="model",
            api_key="fake-key",
        )

    def test_status_codes_map_to_stable_ui_messages(self):
        expected = {
            401: "generation_http_auth",
            403: "generation_http_auth",
            404: "generation_http_not_found",
            408: "generation_http_timeout",
            429: "generation_http_rate_limit",
            500: "generation_http_unavailable",
            502: "generation_http_unavailable",
            503: "generation_http_unavailable",
            418: "generation_failed",
        }
        for status_code, message_key in expected.items():
            with self.subTest(status_code=status_code):
                result = BeginnerAICardDraftGenerator(
                    StubTransport(status_code, "safe short detail")
                ).generate(self.settings(), "material")
                self.assertEqual(result.http_status_code, status_code)
                self.assertEqual(generation_error_message_key(result), message_key)

    def test_sanitized_detail_is_not_in_repr_or_safe_dict(self):
        detail = "provider diagnostic that must not enter repr"
        result = BeginnerAICardDraftGenerator(
            StubTransport(500, detail)
        ).generate(self.settings(), "material")

        rendered = repr(result) + str(result.to_safe_dict())
        self.assertEqual(result.sanitized_detail, detail)
        self.assertNotIn(detail, rendered)
        self.assertNotIn("raw_body", result.to_safe_dict())

    def test_response_dto_enforces_bounded_single_line_redacted_detail(self):
        secret = "dto-secret-value"
        response = OpenAICompatibleTransportResponse(
            status_code=500,
            json_body=None,
            error_detail=(
                f"Authorization=Bearer {secret}\n" + "diagnostic " * 100
            ),
        )

        self.assertNotIn(secret, response.error_detail)
        self.assertNotIn("\n", response.error_detail)
        self.assertLessEqual(len(response.error_detail), 300)


if __name__ == "__main__":
    unittest.main()
