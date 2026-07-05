import tempfile
import unittest
import zipfile
from pathlib import Path, PurePosixPath

from scripts.build_ankiaddon import (
    BuildError,
    _blocked_reason,
    _is_non_runtime_file,
    _validate_archive,
    _write_archive,
)


class BuildAnkiAddonTests(unittest.TestCase):
    def test_dangerous_paths_are_blocked(self):
        paths = (
            "config.json",
            "__pycache__/module.pyc",
            "tests/test_example.py",
            "docs/release.md",
            ".env.local",
            "addon_backup/file.py",
            "collection.anki2",
            "export.apkg",
            "debug.log",
        )

        for path in paths:
            with self.subTest(path=path):
                self.assertIsNotNone(_blocked_reason(PurePosixPath(path)))

    def test_runtime_paths_are_not_blocked(self):
        for path in (
            "__init__.py",
            "manifest.json",
            "ui/card_maker_panel.py",
            "theme/style.css",
        ):
            with self.subTest(path=path):
                self.assertIsNone(_blocked_reason(PurePosixPath(path)))

    def test_repository_documents_are_explicitly_non_runtime(self):
        for path in (
            "README.md",
            "README.en.md",
            "LICENSE",
            "config.md",
            "config.example.json",
        ):
            with self.subTest(path=path):
                self.assertTrue(_is_non_runtime_file(Path(path)))

    def test_archive_round_trip_and_forbidden_member_rejection(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            init_file = root / "__init__.py"
            manifest_file = root / "manifest.json"
            init_file.write_text("", encoding="utf-8")
            manifest_file.write_text("{}", encoding="utf-8")

            valid_archive = root / "valid.ankiaddon"
            files = [
                (init_file, "__init__.py"),
                (manifest_file, "manifest.json"),
            ]
            _write_archive(valid_archive, files)
            self.assertEqual(
                _validate_archive(valid_archive, {name for _, name in files}),
                2,
            )

            invalid_archive = root / "invalid.ankiaddon"
            with zipfile.ZipFile(invalid_archive, mode="w") as archive:
                archive.writestr("config.json", "{}")
            with self.assertRaises(BuildError):
                _validate_archive(invalid_archive, {"config.json"})


if __name__ == "__main__":
    unittest.main()
