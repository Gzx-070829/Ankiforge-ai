import ast
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

from ankiforge_ai.ui.product_i18n import PRODUCT_COPY


class FileDropImportContractTests(unittest.TestCase):
    def test_file_picker_and_placeholder_cover_supported_extensions(self):
        zh = PRODUCT_COPY["zh"]
        en = PRODUCT_COPY["en"]

        self.assertEqual(zh["choose_file"], "选择文件")
        self.assertEqual(en["choose_file"], "Choose file")
        for suffix in (".md", ".txt", ".docx", ".pdf"):
            self.assertIn(suffix, zh["material_placeholder"])
            self.assertIn(suffix, en["material_placeholder"])
            self.assertIn(suffix, zh["source_file_filter"])
            self.assertIn(suffix, en["source_file_filter"])

    def test_drop_widget_accepts_only_local_file_urls_for_callback(self):
        source = self.drop_widget_source()
        drag_enter = self.function_source(source, "dragEnterEvent")
        drop = self.function_source(source, "dropEvent")
        local_paths = self.function_source(source, "_local_paths")

        self.assertIn("self.setAcceptDrops(True)", source)
        self.assertIn("event.acceptProposedAction()", drag_enter)
        self.assertIn("self._files_dropped(paths)", drop)
        self.assertIn("mime_data.hasUrls()", local_paths)
        self.assertIn("url.isLocalFile()", local_paths)
        self.assertIn("url.toLocalFile()", local_paths)

    def test_drop_widget_runtime_routes_local_files_in_order(self):
        drop_text_edit = self.load_drop_text_edit_class()
        received = []
        widget = drop_text_edit(files_dropped=received.append)
        event = FakeDropEvent(
            FakeMimeData(
                urls=(
                    FakeUrl("C:/first.md"),
                    FakeUrl("https://example.invalid/file.md", local=False),
                    FakeUrl("C:/second.txt"),
                )
            )
        )

        widget.dragEnterEvent(event)
        widget.dropEvent(event)

        self.assertTrue(widget.accept_drops)
        self.assertTrue(event.accepted)
        self.assertEqual(received, [("C:/first.md", "C:/second.txt")])
        self.assertEqual(widget.delegated_events, [])

    def test_drop_widget_runtime_delegates_plain_text(self):
        drop_text_edit = self.load_drop_text_edit_class()
        widget = drop_text_edit(files_dropped=lambda _paths: None)
        event = FakeDropEvent(FakeMimeData(urls=(), has_urls=False))

        widget.dragEnterEvent(event)
        widget.dragMoveEvent(event)
        widget.dropEvent(event)

        self.assertFalse(event.accepted)
        self.assertEqual(
            widget.delegated_events,
            ["dragEnterEvent", "dragMoveEvent", "dropEvent"],
        )

    def test_panel_uses_one_import_path_for_picker_and_drop(self):
        source = self.panel_source()
        picker = self.function_source(source, "_choose_source_file")
        dropped = self.function_source(source, "_handle_dropped_files")
        importer = self.function_source(source, "_import_source_path")

        self.assertIn("self._import_source_path(Path(path))", picker)
        self.assertIn("paths[0]", dropped)
        self.assertIn('"source_import_first_only"', dropped)
        self.assertIn("import_source_file", importer)
        self.assertIn("except SourceImportError", importer)
        self.assertIn("self._set_source_import_error(", importer)
        self.assertIn("error.code", importer)
        self.assertIn("warning_keys=extra_warnings", importer)
        for forbidden in (
            "_generate_cards",
            "BeginnerAICardDraftGenerator",
            "MinimalAnkiWriter",
            "execute_beginner_write_if_confirmed",
            "traceback",
        ):
            self.assertNotIn(forbidden, picker + dropped + importer)

    def test_existing_text_is_appended_and_feedback_is_visible(self):
        source = self.panel_source()
        apply_import = self.function_source(source, "_apply_imported_source")
        material_section = self.function_source(source, "_build_material_section")

        self.assertIn("merge_imported_source_text", apply_import)
        self.assertIn('warnings.append("source_import_appended")', apply_import)
        self.assertIn('"source_imported"', apply_import)
        self.assertIn("material_import_status_label", material_section)
        self.assertIn("material_import_warning_label", material_section)
        self.assertIn('setProperty("role", "status")', material_section)
        self.assertIn('setProperty("role", "warning")', material_section)

    def test_friendly_errors_and_text_only_warnings_are_bilingual(self):
        zh = PRODUCT_COPY["zh"]
        en = PRODUCT_COPY["en"]

        self.assertEqual(
            zh["source_import_error_unsupported_type"],
            "暂不支持该文件类型。",
        )
        self.assertEqual(
            en["source_import_error_unsupported_type"],
            "This file type is not supported yet.",
        )
        self.assertIn("仅提取文本", zh["docx_text_only"])
        self.assertIn("text only", en["docx_text_only"])
        self.assertIn("当前环境无法解析 PDF", zh["source_import_error_pdf_unavailable"])
        self.assertIn("PDF parsing is unavailable", en["source_import_error_pdf_unavailable"])

    @staticmethod
    def function_source(source, name):
        tree = ast.parse(source)
        node = next(
            item
            for item in ast.walk(tree)
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            and item.name == name
        )
        return ast.get_source_segment(source, node) or ""

    @staticmethod
    def root():
        return Path(__file__).parents[1]

    def panel_source(self):
        return (
            self.root() / "ankiforge_ai" / "ui" / "card_maker_panel.py"
        ).read_text(encoding="utf-8")

    def drop_widget_source(self):
        return (
            self.root() / "ankiforge_ai" / "ui" / "file_drop_text_edit.py"
        ).read_text(encoding="utf-8")

    def load_drop_text_edit_class(self):
        qt_module = types.ModuleType("aqt.qt")
        qt_module.QTextEdit = FakeQTextEdit
        aqt_module = types.ModuleType("aqt")
        aqt_module.qt = qt_module
        module_path = (
            self.root() / "ankiforge_ai" / "ui" / "file_drop_text_edit.py"
        )
        spec = importlib.util.spec_from_file_location(
            "pr16_file_drop_text_edit_runtime",
            module_path,
        )
        module = importlib.util.module_from_spec(spec)
        with mock.patch.dict(
            sys.modules,
            {"aqt": aqt_module, "aqt.qt": qt_module},
        ):
            spec.loader.exec_module(module)
        return module.FileDropTextEdit


class FakeQTextEdit:
    def __init__(self, _parent=None):
        self.accept_drops = False
        self.delegated_events = []

    def setAcceptDrops(self, enabled):
        self.accept_drops = enabled

    def dragEnterEvent(self, _event):
        self.delegated_events.append("dragEnterEvent")

    def dragMoveEvent(self, _event):
        self.delegated_events.append("dragMoveEvent")

    def dropEvent(self, _event):
        self.delegated_events.append("dropEvent")


class FakeUrl:
    def __init__(self, value, *, local=True):
        self.value = value
        self.local = local

    def isLocalFile(self):
        return self.local

    def toLocalFile(self):
        return self.value if self.local else ""


class FakeMimeData:
    def __init__(self, *, urls, has_urls=True):
        self._urls = urls
        self._has_urls = has_urls

    def hasUrls(self):
        return self._has_urls

    def urls(self):
        return self._urls


class FakeDropEvent:
    def __init__(self, mime_data):
        self._mime_data = mime_data
        self.accepted = False

    def mimeData(self):
        return self._mime_data

    def acceptProposedAction(self):
        self.accepted = True


if __name__ == "__main__":
    unittest.main()
