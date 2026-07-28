import builtins
import dataclasses
import importlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


OPTIONAL_MODULES = ("docling", "markitdown")


class DocumentBackendCapabilityTests(unittest.TestCase):
    def test_core_and_backend_imports_do_not_touch_optional_modules(self):
        original_import = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if name.split(".", 1)[0] in OPTIONAL_MODULES:
                raise AssertionError(f"optional import attempted: {name}")
            return original_import(name, *args, **kwargs)

        for name in tuple(sys.modules):
            if name.split(".", 1)[0] in OPTIONAL_MODULES:
                sys.modules.pop(name)

        with mock.patch("builtins.__import__", side_effect=guarded_import):
            importlib.import_module("ankiforge_ai.document")
            backends = importlib.import_module("ankiforge_ai.document.backends")
            backends.DoclingBackend()
            backends.MarkItDownBackend()

        self.assertTrue(all(name not in sys.modules for name in OPTIONAL_MODULES))

    def test_probes_are_absence_safe_and_default_off(self):
        from ankiforge_ai.document.backends import (
            DoclingBackend,
            MarkItDownBackend,
            PandocBackend,
        )

        with mock.patch(
            "ankiforge_ai.document.backends.detection.importlib.util.find_spec",
            return_value=None,
        ):
            docling = DoclingBackend()
            markitdown = MarkItDownBackend()
            self.assertFalse(docling.probe().available)
            self.assertFalse(markitdown.probe().available)

        pandoc = PandocBackend()
        self.assertFalse(pandoc.probe().available)
        for backend in (docling, markitdown, pandoc):
            capability = backend.capabilities()
            self.assertFalse(capability.enabled_by_default)
            self.assertTrue(capability.local_only)
            self.assertFalse(capability.ocr_enabled)
            self.assertFalse(capability.remote_enabled)
            self.assertFalse(capability.plugins_enabled)
            self.assertFalse(capability.downloads_enabled)
            self.assertNotIn("Traceback", repr(backend.probe()))

    def test_public_backend_models_have_no_url_or_credential_fields(self):
        from ankiforge_ai.document.backends import (
            BackendCapability,
            BackendCommand,
            BackendProbe,
            BackendResult,
        )

        forbidden = ("url", "credential", "secret", "api_key", "cookie")
        for model in (
            BackendCapability,
            BackendCommand,
            BackendProbe,
            BackendResult,
        ):
            names = {field.name.casefold() for field in dataclasses.fields(model)}
            self.assertFalse(
                any(token in name for token in forbidden for name in names),
                (model.__name__, names),
            )

    def test_pandoc_probe_rejects_a_regular_non_executable_file(self):
        from ankiforge_ai.document.backends.detection import (
            probe_absolute_executable,
        )

        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "pandoc.txt"
            candidate.write_text("not an executable", encoding="utf-8")
            probe = probe_absolute_executable("pandoc", candidate)

        self.assertFalse(probe.available)
        self.assertEqual(probe.reason_code, "invalid_executable")


if __name__ == "__main__":
    unittest.main()
