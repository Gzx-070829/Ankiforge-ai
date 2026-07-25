import json
from pathlib import Path
import sys
import types
import unittest
from unittest import mock
import zipfile

import ankiforge_ai


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_VERSION = "0.13.2"
EXPECTED_TAG = f"v{EXPECTED_VERSION}-product-grade-preview"


class RecordingDialog:
    def __init__(self, parent, *, exec_error=None):
        self.parent = parent
        self.exec_error = exec_error
        self.events = []

    def exec(self):
        self.events.append("exec")
        if self.exec_error is not None:
            raise self.exec_error
        return 0

    def _teardown_session(self):
        self.events.append("teardown")

    def deleteLater(self):
        self.events.append("deleteLater")


class Pr26ReleaseMetadataAndLifecycleTests(unittest.TestCase):
    def tearDown(self):
        ankiforge_ai._dialog_instance = None

    def test_runtime_and_release_documents_use_one_version(self):
        manifest = json.loads(
            (REPOSITORY_ROOT / "ankiforge_ai" / "manifest.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(ankiforge_ai.__version__, EXPECTED_VERSION)
        self.assertEqual(manifest["version"], EXPECTED_VERSION)
        self.assertEqual(manifest["human_version"], EXPECTED_VERSION)
        for relative_path in (
            "README.md",
            "README.en.md",
            "docs/release_notes_v0_13_product_grade.md",
            "docs/ankiweb_description_v0_13.md",
        ):
            with self.subTest(path=relative_path):
                content = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
                self.assertIn(EXPECTED_TAG, content)
                self.assertNotIn("v0.13.0-product-grade-preview", content)
                self.assertNotIn("v0.13.1-product-grade-preview", content)

    def test_tracked_package_uses_the_same_runtime_version(self):
        package_path = REPOSITORY_ROOT / "dist" / "ankiforge_ai.ankiaddon"

        with zipfile.ZipFile(package_path, mode="r") as archive:
            package_manifest = json.loads(
                archive.read("manifest.json").decode("utf-8")
            )
            package_entry = archive.read("__init__.py").decode("utf-8")

        self.assertEqual(package_manifest["version"], EXPECTED_VERSION)
        self.assertEqual(package_manifest["human_version"], EXPECTED_VERSION)
        self.assertIn(f'__version__ = "{EXPECTED_VERSION}"', package_entry)

    def test_open_main_dialog_tears_down_deletes_and_clears_global(self):
        dialog = RecordingDialog(parent=object())
        open_dialog = getattr(ankiforge_ai, "_open_main_dialog", None)

        self.assertTrue(callable(open_dialog))
        open_dialog(dialog.parent, lambda _parent: dialog)

        self.assertEqual(dialog.events, ["exec", "teardown", "deleteLater"])
        self.assertIsNone(ankiforge_ai._dialog_instance)

    def test_open_main_dialog_cleans_up_when_exec_raises(self):
        dialog = RecordingDialog(parent=object(), exec_error=RuntimeError("boom"))
        open_dialog = getattr(ankiforge_ai, "_open_main_dialog", None)

        self.assertTrue(callable(open_dialog))
        with self.assertRaisesRegex(RuntimeError, "boom"):
            open_dialog(dialog.parent, lambda _parent: dialog)

        self.assertEqual(dialog.events, ["exec", "teardown", "deleteLater"])
        self.assertIsNone(ankiforge_ai._dialog_instance)

    def test_existing_menu_action_prevents_duplicate_registration(self):
        class FakeSignal:
            def __init__(self):
                self.callback = None

            def connect(self, callback):
                self.callback = callback

        class FakeAction:
            def __init__(self, label, parent):
                self.label = label
                self.parent = parent
                self.triggered = FakeSignal()

        class FakeMenu:
            def __init__(self):
                self.actions = []

            def addAction(self, action):
                self.actions.append(action)

        menu = FakeMenu()
        fake_mw = types.SimpleNamespace(
            form=types.SimpleNamespace(menuTools=menu)
        )
        fake_aqt = types.ModuleType("aqt")
        fake_qt = types.ModuleType("aqt.qt")
        fake_main_dialog = types.ModuleType("ankiforge_ai.ui.main_dialog")
        fake_aqt.mw = fake_mw
        fake_qt.QAction = FakeAction
        fake_main_dialog.MainDialog = RecordingDialog
        injected = {
            "aqt": fake_aqt,
            "aqt.qt": fake_qt,
            "ankiforge_ai.ui.main_dialog": fake_main_dialog,
        }
        original = getattr(ankiforge_ai, "_menu_action", None)
        try:
            ankiforge_ai._menu_action = None
            with mock.patch.dict(sys.modules, injected):
                first = ankiforge_ai._register_menu_action()
                second = ankiforge_ai._register_menu_action()

            self.assertIs(first, second)
            self.assertEqual(len(menu.actions), 1)
            self.assertEqual(first.label, "AnkiForge AI")
        finally:
            ankiforge_ai._menu_action = original

    def test_current_ai_settings_do_not_read_legacy_config(self):
        for relative_path in (
            "ankiforge_ai/ui/ai_settings_dialog.py",
            "ankiforge_ai/ui/card_maker_panel.py",
            "ankiforge_ai/ui/main_dialog.py",
        ):
            with self.subTest(path=relative_path):
                source = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
                self.assertNotIn("config_loader", source)
                self.assertNotIn("load_config(", source)
                self.assertNotIn("load_provider_config(", source)

    def test_current_guides_do_not_advertise_cloze_as_selectable(self):
        modes = (
            REPOSITORY_ROOT / "docs" / "card_modes_and_templates.md"
        ).read_text(encoding="utf-8")
        getting_started = (
            REPOSITORY_ROOT / "docs" / "getting_started.md"
        ).read_text(encoding="utf-8")

        self.assertIn("当前公共 UI 不开放 `cloze_candidate`", modes)
        self.assertIn("not a public card mode", modes)
        self.assertIn("v0.13.2 当前不开放 Cloze 选择", getting_started)
        self.assertNotIn("Cloze 只在模板和笔记类型均兼容时使用", getting_started)


if __name__ == "__main__":
    unittest.main()
