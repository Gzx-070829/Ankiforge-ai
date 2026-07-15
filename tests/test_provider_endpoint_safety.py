import unittest
from unittest.mock import patch

from ankiforge_ai.pipeline.openai_compatible_provider import (
    OpenAICompatibleTransportResponse,
)
from ankiforge_ai.pipeline.provider_endpoint_safety import (
    EndpointConfirmationSession,
    assess_provider_endpoint,
    endpoint_confirmation_key,
)
from ankiforge_ai.ui.beginner_ai_card_drafts import (
    BeginnerAICardDraftGenerator,
    BeginnerAIDraftErrorCode,
    BeginnerAIProviderRuntimeSettings,
)


OFFICIAL_HOSTS = {"api.deepseek.com", "api.openai.com"}


class ProviderEndpointSafetyTests(unittest.TestCase):
    def decision(self, url):
        return assess_provider_endpoint(url, official_hosts=OFFICIAL_HOSTS)

    def test_only_exact_official_https_hosts_are_allowed(self):
        for url in (
            "https://api.deepseek.com",
            "https://api.deepseek.com/v1",
            "https://api.openai.com/v1",
            "https://API.OPENAI.COM:443/v1",
        ):
            with self.subTest(url=url):
                self.assertEqual(self.decision(url).kind, "allow")

        for url in (
            "https://api.deepseek.com.evil.example/v1",
            "https://evil-api.deepseek.com/v1",
            "https://api.openai.com:8443/v1",
        ):
            with self.subTest(url=url):
                self.assertEqual(self.decision(url).kind, "confirm")

    def test_custom_public_and_insecure_endpoints_require_confirmation(self):
        for url in (
            "https://provider.example/v1",
            "http://provider.example/v1",
            "http://localhost:11434/v1",
            "http://127.0.0.1:11434/v1",
            "http://[::1]:11434/v1",
            "http://10.1.2.3/v1",
            "http://172.16.10.2/v1",
            "http://192.168.1.2/v1",
            "http://169.254.1.10/v1",
            "https://provider.local/v1",
            "http://ollama:11434/v1",
        ):
            with self.subTest(url=url):
                decision = self.decision(url)
                self.assertEqual(decision.kind, "confirm")
                self.assertIn("API key", decision.user_message_zh)
                self.assertIn("API key", decision.user_message_en)

    def test_dangerous_or_invalid_endpoints_are_denied(self):
        for url in (
            "ftp://provider.example/v1",
            "https:///v1",
            "https://user:pass@provider.example/v1",
            "https://provider.example/v1?token=value",
            "https://provider.example/v1#fragment",
            "http://0.0.0.0/v1",
            "http://[::]/v1",
            "http://169.254.169.254/latest/meta-data",
            "http://169.254.170.2/v2/credentials",
            "http://100.100.100.200/latest/meta-data",
            "http://[fd00:ec2::254]/latest/meta-data",
            "http://[::ffff:169.254.169.254]/latest/meta-data",
            "http://metadata.google.internal/computeMetadata/v1",
            "http://metadata.goog/computeMetadata/v1",
            "http://224.0.0.1/v1",
            "http://0/v1",
            "http://2130706433/v1",
            "http://0177.0.0.1/v1",
            "http://0x7f000001/v1",
        ):
            with self.subTest(url=url):
                self.assertEqual(self.decision(url).kind, "deny")

    def test_display_endpoint_never_contains_sensitive_or_path_data(self):
        decision = self.decision(
            "https://user:password@provider.example:8443/private/path?token=x#frag"
        )

        self.assertEqual(decision.display_endpoint, "https://provider.example:8443")
        rendered = decision.display_endpoint
        for forbidden in ("user", "password", "private/path", "token=x", "frag"):
            self.assertNotIn(forbidden, rendered)

    def test_confirmation_key_uses_only_normalized_scheme_host_and_port(self):
        first = endpoint_confirmation_key("https://Provider.Example:443/v1")
        same = endpoint_confirmation_key("https://provider.example/other/path")
        changed = endpoint_confirmation_key("https://provider.example:8443/v1")

        self.assertEqual(first, same)
        self.assertNotEqual(first, changed)
        self.assertNotIn("provider.example", first)

    def test_confirmation_is_session_only_and_endpoint_specific(self):
        session = EndpointConfirmationSession()
        first = "https://provider.example/v1"
        changed = "https://other.example/v1"

        self.assertFalse(session.is_confirmed(first))
        key = session.confirm(first)
        self.assertTrue(session.is_confirmed(first))
        self.assertEqual(key, endpoint_confirmation_key(first))
        self.assertFalse(session.is_confirmed(changed))
        session.clear()
        self.assertFalse(session.is_confirmed(first))

    def test_assessment_does_not_resolve_dns(self):
        with patch(
            "socket.getaddrinfo",
            side_effect=AssertionError("endpoint assessment must not resolve DNS"),
        ):
            decision = self.decision("https://no-dns-query.invalid/v1")
        self.assertEqual(decision.kind, "confirm")

    def test_http_confirmation_warns_about_plaintext_material_and_key(self):
        decision = self.decision("http://provider.example/v1")

        self.assertEqual(decision.reason_code, "unencrypted_http")
        self.assertIn("明文", decision.user_message_zh)
        self.assertIn("材料", decision.user_message_zh)
        self.assertIn("unencrypted", decision.user_message_en.casefold())
        self.assertIn("material", decision.user_message_en.casefold())

    def test_generator_network_boundary_requires_matching_confirmation(self):
        transport = _RecordingTransport()
        settings = BeginnerAIProviderRuntimeSettings(
            provider_name="OpenAI-compatible",
            base_url="https://provider.example/v1",
            model="model",
            api_key="fake-key",
        )

        blocked = BeginnerAICardDraftGenerator(transport).generate(
            settings,
            "material",
        )
        allowed = BeginnerAICardDraftGenerator(transport).generate(
            settings,
            "material",
            endpoint_confirmation_key=endpoint_confirmation_key(settings.base_url),
        )

        self.assertEqual(
            blocked.error_code,
            BeginnerAIDraftErrorCode.ENDPOINT_NOT_AUTHORIZED,
        )
        self.assertTrue(allowed.success)
        self.assertEqual(len(transport.calls), 1)


class _RecordingTransport:
    def __init__(self):
        self.calls = []

    def post_json(self, **kwargs):
        self.calls.append(kwargs)
        return OpenAICompatibleTransportResponse(
            status_code=200,
            json_body={
                "choices": [
                    {
                        "message": {
                            "content": (
                                '[{"front":"Q","back":"A",'
                                '"source_excerpt":"S"}]'
                            )
                        }
                    }
                ]
            },
        )


if __name__ == "__main__":
    unittest.main()
