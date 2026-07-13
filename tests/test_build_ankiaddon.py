import tempfile
import unittest
import zipfile
from pathlib import Path, PurePosixPath

from scripts.build_ankiaddon import (
    BuildError,
    REQUIRED_ARCHIVE_FILES,
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
            "importers/source_import.py",
            "manifest.json",
            "ui/card_maker_panel.py",
            "ui/file_drop_text_edit.py",
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
            valid_archive = root / "valid.ankiaddon"
            files = []
            for index, archive_name in enumerate(sorted(REQUIRED_ARCHIVE_FILES)):
                source_file = root / f"runtime-{index}.txt"
                source_file.write_text(archive_name, encoding="utf-8")
                files.append((source_file, archive_name))
            _write_archive(valid_archive, files)
            self.assertEqual(
                _validate_archive(valid_archive, {name for _, name in files}),
                len(files),
            )

            invalid_archive = root / "invalid.ankiaddon"
            with zipfile.ZipFile(invalid_archive, mode="w") as archive:
                archive.writestr("config.json", "{}")
            with self.assertRaises(BuildError):
                _validate_archive(invalid_archive, {"config.json"})

    def test_pr16_runtime_modules_are_required(self):
        self.assertIn("importers/source_import.py", REQUIRED_ARCHIVE_FILES)
        self.assertIn("ui/file_drop_text_edit.py", REQUIRED_ARCHIVE_FILES)

    def test_archive_writer_is_byte_for_byte_deterministic(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "module.py"
            source.write_text("value = 1\n", encoding="utf-8")
            files = [(source, "module.py")]
            first = root / "first.ankiaddon"
            second = root / "second.ankiaddon"

            _write_archive(first, files)
            _write_archive(second, files)

            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_archive_writer_normalizes_text_line_endings(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            lf_source = root / "lf.py"
            crlf_source = root / "crlf.py"
            lf_source.write_bytes(b"first = 1\nsecond = 2\n")
            crlf_source.write_bytes(b"first = 1\r\nsecond = 2\r\n")
            lf_archive = root / "lf.ankiaddon"
            crlf_archive = root / "crlf.ankiaddon"

            _write_archive(lf_archive, [(lf_source, "module.py")])
            _write_archive(crlf_archive, [(crlf_source, "module.py")])

            self.assertEqual(lf_archive.read_bytes(), crlf_archive.read_bytes())


if __name__ == "__main__":
    unittest.main()
