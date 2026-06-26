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

    def test_save_config_preserves_empty_api_key(self):
        path = self._write_json({})

        save_config({"ai_provider": "mock", "api_key": ""}, path)
        config = load_config(path)

        self.assertEqual(config["api_key"], "")

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
