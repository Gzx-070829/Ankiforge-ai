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
            "eval/card_quality_benchmark.py",
            "fixtures/intelligence/python.md",
            "screenshots/v0_14/01_zh_default_main.png",
            "models/downloaded.bin",
            "cache/model.bin",
            "temp/conversion.html",
            "tools/pandoc.exe",
            "docs/release.md",
            "user_files/preferences.json",
            "user_files/.preferences.json.tmp",
            "user_files/window_state.json",
            "user_files/.window_state.json.tmp",
            ".env.local",
            "addon_backup/file.py",
            "collection.anki2",
            "export.apkg",
            "debug.log",
            "credentials.json",
            "certificate.pem",
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

    def test_v014_runtime_modules_are_required(self):
        self.assertTrue(
            {
                "anki_writer/minimal_write.py",
                "document/__init__.py",
                "intelligence/__init__.py",
                "pipeline/openai_compatible_provider.py",
                "ui/ai_settings_dialog.py",
                "ui/card_maker_panel.py",
                "ui/main_dialog.py",
            }.issubset(REQUIRED_ARCHIVE_FILES)
        )

    def test_workbench_runtime_modules_are_required(self):
        self.assertTrue(
            {
                "workbench/__init__.py",
                "workbench/generation_lifecycle.py",
                "workbench/models.py",
                "workbench/review_use_cases.py",
                "workbench/write_coordinator.py",
                "workbench/preferences.py",
                "ui/workbench_factory.py",
                "ui/workbench_preferences_adapter.py",
                "ui/window_experience.py",
                "ui/window_state_adapter.py",
                "workbench/window_state.py",
            }.issubset(REQUIRED_ARCHIVE_FILES)
        )

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

    def test_archive_rejects_absolute_ankiforge_self_import(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            archive_path = root / "absolute-self-import.ankiaddon"
            files = []
            for index, archive_name in enumerate(sorted(REQUIRED_ARCHIVE_FILES)):
                source_file = root / f"runtime-{index}.txt"
                content = "pass\n" if archive_name.endswith(".py") else "{}\n"
                source_file.write_text(content, encoding="utf-8")
                files.append((source_file, archive_name))
            bad_module = root / "bad.py"
            bad_module.write_text(
                "from ankiforge_ai.document import DocumentIR\n",
                encoding="utf-8",
            )
            files.append((bad_module, "bad.py"))
            _write_archive(archive_path, files)

            with self.assertRaisesRegex(BuildError, "absolute self-import"):
                _validate_archive(
                    archive_path,
                    {archive_name for _, archive_name in files},
                )

    def test_archive_rejects_eager_pipe_annotation(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            archive_path = root / "eager-pipe-annotation.ankiaddon"
            files = []
            for index, archive_name in enumerate(sorted(REQUIRED_ARCHIVE_FILES)):
                source_file = root / f"runtime-{index}.txt"
                content = "pass\n" if archive_name.endswith(".py") else "{}\n"
                source_file.write_text(content, encoding="utf-8")
                files.append((source_file, archive_name))
            bad_module = root / "bad.py"
            bad_module.write_text(
                "def normalize(value: str | None) -> str:\n"
                "    return value or ''\n",
                encoding="utf-8",
            )
            files.append((bad_module, "bad.py"))
            _write_archive(archive_path, files)

            with self.assertRaisesRegex(BuildError, "postpone annotations"):
                _validate_archive(
                    archive_path,
                    {archive_name for _, archive_name in files},
                )

    def test_archive_rejects_syntax_newer_than_python_39(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            archive_path = root / "newer-python-syntax.ankiaddon"
            files = []
            for index, archive_name in enumerate(sorted(REQUIRED_ARCHIVE_FILES)):
                source_file = root / f"runtime-{index}.txt"
                content = "pass\n" if archive_name.endswith(".py") else "{}\n"
                source_file.write_text(content, encoding="utf-8")
                files.append((source_file, archive_name))
            bad_module = root / "bad.py"
            bad_module.write_text(
                "def describe(value):\n"
                "    match value:\n"
                "        case 1:\n"
                "            return 'one'\n",
                encoding="utf-8",
            )
            files.append((bad_module, "bad.py"))
            _write_archive(archive_path, files)

            with self.assertRaisesRegex(BuildError, "Python 3.9"):
                _validate_archive(
                    archive_path,
                    {archive_name for _, archive_name in files},
                )


if __name__ == "__main__":
    unittest.main()
