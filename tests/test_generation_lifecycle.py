import ast
from pathlib import Path
import unittest

import ankiforge_ai.workbench as workbench
from ankiforge_ai.ui import intelligent_generation_task_controller as controller
from ankiforge_ai.workbench.generation_lifecycle import (
    GenerationLifecycleResult,
    IntelligentGenerationProgress,
    apply_coverage_supplement,
    execute_generation_lifecycle,
    execute_failed_retry_lifecycle,
)


class GenerationLifecycleArchitectureTests(unittest.TestCase):
    def test_lifecycle_entry_points_are_exported_by_workbench(self):
        self.assertIs(
            workbench.execute_generation_lifecycle,
            execute_generation_lifecycle,
        )
        self.assertIs(
            workbench.execute_failed_retry_lifecycle,
            execute_failed_retry_lifecycle,
        )

    def test_pure_lifecycle_module_has_no_ui_qt_aqt_or_writer_import(self):
        path = Path("ankiforge_ai/workbench/generation_lifecycle.py")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(item.name.split(".")[0] for item in node.names)
            elif isinstance(node, ast.ImportFrom):
                roots.add((node.module or "").split(".")[0])

        self.assertFalse(
            {"aqt", "PyQt5", "PyQt6", "ui", "anki_writer"} & roots
        )

    def test_controller_private_names_are_compatibility_aliases(self):
        self.assertIs(
            controller._execute_lifecycle,
            execute_generation_lifecycle,
        )
        self.assertIs(
            controller._execute_failed_retry_lifecycle,
            execute_failed_retry_lifecycle,
        )
        self.assertIs(
            controller._apply_coverage_supplement,
            apply_coverage_supplement,
        )
        self.assertIs(controller._WorkerResult, GenerationLifecycleResult)
        self.assertIs(
            controller.IntelligentGenerationProgress,
            IntelligentGenerationProgress,
        )


if __name__ == "__main__":
    unittest.main()
