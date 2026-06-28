import ast
import json
import unittest
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

from ankiforge_ai.pipeline.openai_compatible_provider import (
    OpenAICompatibleProviderConfig,
)
from ankiforge_ai.pipeline.user_provider_config import (
    UserProviderProfile,
    create_openai_compatible_config_from_user_profile,
)


class UserProviderConfigTests(unittest.TestCase):
    def test_profile_is_frozen_and_has_no_secret_fields(self):
        profile = self.profile()

        self.assertNotIn("sends_user_content", {field.name for field in fields(profile)})
        self.assertNotIn(
            "requires_explicit_consent",
            {field.name for field in fields(profile)},
        )
        with self.assertRaises(FrozenInstanceError):
            profile.model_name = "changed"

    def test_safety_properties_cannot_be_forged_by_constructor(self):
        with self.assertRaises(TypeError):
            self.profile(sends_user_content=False)
        with self.assertRaises(TypeError):
            self.profile(requires_explicit_consent=False)

        profile = self.profile(base_url="http://127.0.0.1:8000/v1")
        self.assertTrue(profile.sends_user_content)
        self.assertTrue(profile.requires_explicit_consent)

    def test_localhost_still_requires_consent_and_sends_content(self):
        for base_url in (
            "http://localhost:8000/v1",
            "https://127.0.0.1/v1",
        ):
            with self.subTest(base_url=base_url):
                profile = self.profile(base_url=base_url)
                self.assertTrue(profile.sends_user_content)
                self.assertTrue(profile.requires_explicit_consent)

    def test_safe_outputs_contain_only_non_secret_profile_data(self):
        profile = self.profile()
        rendered = "\n".join(
            (
                repr(profile),
                str(profile),
                json.dumps(profile.to_safe_dict(), ensure_ascii=False),
            )
        ).lower()

        for sensitive_marker in (
            "api_key",
            "apikey",
            "secret",
            "token",
            "authorization",
            "bearer",
            "password",
            "headers",
        ):
            with self.subTest(sensitive_marker=sensitive_marker):
                self.assertNotIn(sensitive_marker, rendered)

    def test_safe_dict_includes_fixed_safety_properties(self):
        data = self.profile().to_safe_dict()

        self.assertTrue(data["sends_user_content"])
        self.assertTrue(data["requires_explicit_consent"])
        self.assertNotIn("api_key", data)

    def test_required_profile_fields_and_timeout_are_validated(self):
        for field_name in (
            "profile_id",
            "provider_id",
            "provider_name",
            "model_name",
            "privacy_notice",
        ):
            with self.subTest(field_name=field_name):
                with self.assertRaises(ValueError):
                    self.profile(**{field_name: " "})
        for timeout in (0, -1, True, "60"):
            with self.subTest(timeout=timeout):
                with self.assertRaises(ValueError):
                    self.profile(timeout_seconds=timeout)
        self.assertIsNone(self.profile(timeout_seconds=None).timeout_seconds)

    def test_http_and_https_urls_are_allowed(self):
        for base_url in (
            "http://api.example.com/v1",
            "https://api.example.com/v1/chat/completions",
        ):
            with self.subTest(base_url=base_url):
                self.assertEqual(self.profile(base_url=base_url).base_url, base_url)

    def test_unsafe_or_incomplete_urls_are_rejected(self):
        invalid_urls = (
            "api.example.com/v1",
            "/relative/path",
            "file:///tmp/provider",
            "data://text/plain,value",
            "https://",
            "http:///v1",
            "https://user@example.com/v1",
            "https://user:password@example.com/v1",
            "https://@example.com/v1",
        )
        for base_url in invalid_urls:
            with self.subTest(base_url=base_url):
                with self.assertRaises(ValueError):
                    self.profile(base_url=base_url)

    def test_runtime_config_uses_existing_fields_and_keeps_key_safe(self):
        profile = self.profile()

        config = create_openai_compatible_config_from_user_profile(
            profile,
            "test-api-key",
        )

        self.assertIsInstance(config, OpenAICompatibleProviderConfig)
        self.assertEqual(config.provider_id, profile.provider_id)
        self.assertEqual(config.provider_name, profile.provider_name)
        self.assertEqual(config.model_name, profile.model_name)
        self.assertEqual(config.base_url, profile.base_url)
        self.assertEqual(config.privacy_notice, profile.privacy_notice)
        self.assertEqual(config.timeout_seconds, profile.timeout_seconds)
        self.assertEqual(config.api_key, "test-api-key")
        self.assertNotIn("test-api-key", repr(config))
        self.assertNotIn("test-api-key", str(config))
        self.assertNotIn("api_key", config.to_dict())

    def test_runtime_key_must_be_explicit_and_is_not_persisted(self):
        with self.assertRaises(TypeError):
            create_openai_compatible_config_from_user_profile(self.profile())
        with self.assertRaises(ValueError):
            create_openai_compatible_config_from_user_profile(self.profile(), " ")
        with self.assertRaises(ValueError):
            create_openai_compatible_config_from_user_profile(object(), "test-api-key")

    def test_module_has_strict_dependency_boundary(self):
        source_path = (
            Path(__file__).parents[1]
            / "ankiforge_ai"
            / "pipeline"
            / "user_provider_config.py"
        )
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_modules = {
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        imported_modules.update(
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        forbidden = (
            "aqt",
            "anki",
            "PyQt",
            "PySide",
            "requests",
            "socket",
            "http.client",
            "urllib.request",
            "os",
            "pathlib",
            "config",
            "writer",
            "orchestrator",
            "review",
            "provider_factory",
            "transport",
        )

        self.assertFalse(
            any(
                module.startswith(prefix)
                for module in imported_modules
                for prefix in forbidden
            )
        )
        self.assertIn("urllib.parse", imported_modules)
        for forbidden_text in (
            "GeneratedCard",
            "CardCandidate",
            "HumanReview",
            "self.cards",
            ".extract(",
            "post_json",
            "urlopen",
        ):
            self.assertNotIn(forbidden_text, source)

    @staticmethod
    def profile(**overrides):
        values = {
            "profile_id": "custom-provider-profile",
            "provider_id": "custom-openai-compatible",
            "provider_name": "Custom Provider",
            "model_name": "knowledge-model",
            "base_url": "https://api.example.com/v1",
            "privacy_notice": "Selected learning text is sent to this provider.",
            "timeout_seconds": 30.0,
        }
        values.update(overrides)
        return UserProviderProfile(**values)


if __name__ == "__main__":
    unittest.main()
