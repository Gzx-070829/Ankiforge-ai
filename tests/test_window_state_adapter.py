import json
from pathlib import Path
import tempfile
import unittest

from ankiforge_ai.ui.window_state_adapter import (
    MAX_WINDOW_STATE_FILE_BYTES,
    WindowStateAdapter,
)
from ankiforge_ai.workbench.window_state import WorkbenchWindowState


class WindowStateAdapterTests(unittest.TestCase):
    def test_missing_file_loads_safe_default(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "user_files" / "window_state.json"

            self.assertEqual(
                WindowStateAdapter(path).load(),
                WorkbenchWindowState.defaults(),
            )

    def test_round_trip_uses_only_user_files_window_state_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "user_files" / "window_state.json"
            adapter = WindowStateAdapter(path)
            state = WorkbenchWindowState(
                geometry="AQIDBA==",
                maximized=True,
            )

            adapter.save(state)

            self.assertEqual(adapter.load(), state)
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                {"geometry": "AQIDBA==", "maximized": True},
            )
            self.assertFalse(
                path.with_name(".window_state.json.tmp").exists()
            )

    def test_path_must_end_in_preserved_user_files_location(self):
        with tempfile.TemporaryDirectory() as directory:
            for path in (
                Path(directory) / "window_state.json",
                Path(directory) / "user_files" / "other.json",
            ):
                with self.subTest(path=path):
                    with self.assertRaises(ValueError):
                        WindowStateAdapter(path)

    def test_malformed_unknown_and_oversized_files_load_safe_default(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "user_files" / "window_state.json"
            path.parent.mkdir(parents=True)
            adapter = WindowStateAdapter(path)
            payloads = (
                b"not json",
                b'{"geometry":"AQIDBA==","maximized":false,"token":"x"}',
                b"x" * (MAX_WINDOW_STATE_FILE_BYTES + 1),
            )

            for payload in payloads:
                with self.subTest(size=len(payload)):
                    path.write_bytes(payload)
                    self.assertEqual(
                        adapter.load(),
                        WorkbenchWindowState.defaults(),
                    )

    def test_save_rejects_symlinked_file_or_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real_directory = root / "real_user_files"
            real_directory.mkdir()
            linked_directory = root / "user_files"
            try:
                linked_directory.symlink_to(
                    real_directory,
                    target_is_directory=True,
                )
            except OSError:
                self.skipTest("symlinks are unavailable on this system")

            adapter = WindowStateAdapter(
                linked_directory / "window_state.json"
            )
            with self.assertRaises(ValueError):
                adapter.save(WorkbenchWindowState.defaults())


if __name__ == "__main__":
    unittest.main()
