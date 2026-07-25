import json
import os
import tempfile
import unittest

from ankiforge_ai.config_loader import (
    DEFAULT_CONFIG,
    default_deck_name,
    load_config,
    load_provider_config,
    save_config,
)


class ConfigLoaderTests(unittest.TestCase):
    def test_load_config_merges_defaults(self):
        path = self._write_json({"default_deck": "Custom::Deck"})

        config = load_config(path)

        self.assertEqual(config["default_deck"], "Custom::Deck")
        self.assertEqual(config["ai_provider"], DEFAULT_CONFIG["ai_provider"])
        self.assertEqual(config["model"], DEFAULT_CONFIG["model"])

    def test_provider_config_normalizes_max_cards(self):
        path = self._write_json({"max_cards_per_chunk": 0})

        config = load_provider_config(path)

        self.assertEqual(config.max_cards_per_chunk, DEFAULT_CONFIG["max_cards_per_chunk"])
        self.assertEqual(config.timeout_seconds, DEFAULT_CONFIG["timeout_seconds"])
        self.assertEqual(config.temperature, DEFAULT_CONFIG["temperature"])

    def test_deepseek_preset_fills_base_url_and_model(self):
        path = self._write_json({"ai_provider": "deepseek", "model": "mock-v0.2"})

        config = load_config(path)

        self.assertEqual(config["api_base_url"], "https://api.deepseek.com")
        self.assertEqual(config["model"], "deepseek-chat")

    def test_openai_compatible_requires_user_model_and_base_url(self):
        path = self._write_json({"ai_provider": "openai_compatible", "model": "mock-v0.2"})

        config = load_provider_config(path)

        self.assertEqual(config.model, "")
        self.assertEqual(config.api_base_url, "")
        self.assertEqual(config.api_key, "")

    def test_save_config_refuses_even_empty_api_key(self):
        path = self._write_json({})

        with self.assertRaisesRegex(ValueError, "sensitive fields"):
            save_config({"ai_provider": "mock", "api_key": ""}, path)

    def test_api_key_is_ignored_on_load_and_never_written(self):
        secret = "legacy-secret-that-must-stay-session-only"
        path = self._write_json({"api_key": secret, "model": "model-a"})

        loaded = load_config(path)
        provider_config = load_provider_config(path)
        save_config({"model": "model-b"}, path)
        with open(path, "r", encoding="utf-8") as file:
            saved = json.load(file)

        self.assertEqual(loaded["api_key"], "")
        self.assertEqual(provider_config.api_key, "")
        self.assertNotIn(secret, repr(provider_config))
        self.assertNotIn("api_key", saved)
        self.assertNotIn(secret, json.dumps(saved))

    def test_save_config_refuses_sensitive_field_names_without_writing_values(self):
        sensitive_fields = (
            "api_key",
            "token",
            "access_token",
            "secret",
            "clientSecret",
            "bearer",
            "password",
            "Authorization",
        )
        for field_name in sensitive_fields:
            with self.subTest(field_name=field_name):
                path = self._write_json({"model": "original"})
                sensitive_value = f"must-not-write-{field_name}"

                with self.assertRaisesRegex(ValueError, "sensitive fields") as raised:
                    save_config(
                        {"model": "changed", field_name: sensitive_value},
                        path,
                    )

                with open(path, "r", encoding="utf-8") as file:
                    saved = json.load(file)
                self.assertEqual(saved, {"model": "original"})
                self.assertNotIn(sensitive_value, str(raised.exception))

    def test_save_config_refuses_sensitive_variants_and_nested_fields(self):
        sensitive_configs = (
            {"API-KEY": "value"},
            {"refreshToken": "value"},
            {"credentials": {"client_secret": "value"}},
            {"profiles": [{"bearerToken": "value"}]},
            {"database": {"dbPassword": "value"}},
        )
        for config in sensitive_configs:
            with self.subTest(config=config):
                path = self._write_json({"model": "original"})

                with self.assertRaisesRegex(ValueError, "sensitive fields"):
                    save_config(config, path)

                with open(path, "r", encoding="utf-8") as file:
                    self.assertEqual(json.load(file), {"model": "original"})

    def test_load_config_scrubs_nested_legacy_secrets(self):
        path = self._write_json(
            {
                "model": "model-a",
                "credentials": {"access_token": "legacy", "region": "test"},
                "profiles": [{"clientSecret": "legacy", "name": "safe"}],
            }
        )

        loaded = load_config(path)

        self.assertEqual(loaded["model"], "model-a")
        self.assertEqual(loaded["credentials"], {"region": "test"})
        self.assertEqual(loaded["profiles"], [{"name": "safe"}])
        self.assertNotIn("legacy", repr(loaded))

    def test_default_deck_name_uses_config(self):
        path = self._write_json({"default_deck": "Reading::Inbox"})

        self.assertEqual(default_deck_name(path), "Reading::Inbox")

    def _write_json(self, data):
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        return path


if __name__ == "__main__":
    unittest.main()
