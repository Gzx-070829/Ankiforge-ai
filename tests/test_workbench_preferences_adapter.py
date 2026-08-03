import json
import tempfile
import unittest
from pathlib import Path

from ankiforge_ai.ui.workbench_preferences_adapter import (
    MAX_PREFERENCES_FILE_BYTES,
    WorkbenchPreferencesAdapter,
)
from ankiforge_ai.workbench.preferences import WorkbenchPreferences


class WorkbenchPreferencesAdapterTests(unittest.TestCase):
    def test_missing_file_loads_stable_defaults_without_creating_a_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "user_files" / "preferences.json"
            adapter = WorkbenchPreferencesAdapter(path)

            self.assertEqual(adapter.load(), WorkbenchPreferences.defaults())
            self.assertFalse(path.exists())

    def test_save_is_atomic_and_contains_only_the_safe_allowlist(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "user_files" / "preferences.json"
            adapter = WorkbenchPreferencesAdapter(path)
            preferences = WorkbenchPreferences.defaults().with_updates(
                ui_language="en",
                provider_name="OpenAI",
                model_name="gpt-4o-mini",
            )

            adapter.save(preferences)

            self.assertEqual(adapter.load(), preferences)
            payload = json.loads(path.read_text(encoding="utf-8"))
            rendered = json.dumps(payload).casefold()
            for forbidden in (
                "api_key",
                "token",
                "secret",
                "password",
                "authorization",
                "bearer",
                "cookie",
                "base_url",
                "material",
                "source_path",
                "review_state",
                "write_history",
            ):
                self.assertNotIn(forbidden, rendered)
            self.assertFalse(path.with_name(".preferences.json.tmp").exists())

    def test_invalid_sensitive_or_oversized_disk_data_falls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "user_files" / "preferences.json"
            path.parent.mkdir(parents=True)
            adapter = WorkbenchPreferencesAdapter(path)
            base = WorkbenchPreferences.defaults().to_safe_dict()

            for payload in (
                b"not-json",
                json.dumps({**base, "api_key": "must-not-load"}).encode(),
                b"{" + b" " * MAX_PREFERENCES_FILE_BYTES + b"}",
            ):
                with self.subTest(size=len(payload)):
                    path.write_bytes(payload)
                    self.assertEqual(
                        adapter.load(),
                        WorkbenchPreferences.defaults(),
                    )

    def test_adapter_refuses_non_preference_objects_and_symlink_like_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "user_files" / "preferences.json"
            adapter = WorkbenchPreferencesAdapter(path)

            with self.assertRaises(TypeError):
                adapter.save({"ui_language": "en"})


if __name__ == "__main__":
    unittest.main()
