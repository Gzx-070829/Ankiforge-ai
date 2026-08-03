import ast
from pathlib import Path
import unittest


class WorkbenchArchitectureTests(unittest.TestCase):
    def test_workbench_modules_do_not_import_ui_qt_aqt_or_anki_adapters(self):
        forbidden = {"aqt", "PyQt5", "PyQt6", "ui", "anki_writer"}
        for path in Path("ankiforge_ai/workbench").rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            roots = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    roots.update(
                        item.name.split(".")[0] for item in node.names
                    )
                elif isinstance(node, ast.ImportFrom):
                    roots.add((node.module or "").split(".")[0])
            self.assertFalse(forbidden & roots, path.as_posix())

    def test_card_maker_panel_uses_composition_roots_not_anki_implementations(self):
        source = Path("ankiforge_ai/ui/card_maker_panel.py").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("from ..anki_writer", source)
        self.assertNotIn("MinimalAnkiWriter", source)
        self.assertNotIn("ReadOnlyAnkiTargetAdapter", source)
        self.assertNotIn("ReadOnlyDuplicateCheckAdapter", source)
        self.assertIn("create_workbench_write_coordinator", source)

    def test_ci_runs_tests_compilation_and_package_validation(self):
        workflow = Path(".github/workflows/ci.yml")
        self.assertTrue(workflow.exists())
        source = workflow.read_text(encoding="utf-8")

        self.assertIn("python -m unittest discover", source)
        self.assertIn("python -m compileall -q .", source)
        self.assertIn("python scripts/build_ankiaddon.py", source)
        self.assertIn('python-version: ["3.9", "3.13"]', source)
        self.assertNotIn("secrets.", source)


if __name__ == "__main__":
    unittest.main()
