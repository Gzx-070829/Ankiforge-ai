import ast
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.build_ankiaddon import _collect_runtime_files


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _uses_eager_pipe_annotation(tree):
    for node in ast.walk(tree):
        annotations = []
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            arguments = (
                *node.args.posonlyargs,
                *node.args.args,
                *node.args.kwonlyargs,
            )
            annotations.extend(
                argument.annotation
                for argument in arguments
                if argument.annotation is not None
            )
            if node.args.vararg and node.args.vararg.annotation is not None:
                annotations.append(node.args.vararg.annotation)
            if node.args.kwarg and node.args.kwarg.annotation is not None:
                annotations.append(node.args.kwarg.annotation)
            if node.returns is not None:
                annotations.append(node.returns)
        elif isinstance(node, ast.AnnAssign):
            annotations.append(node.annotation)
        if any(
            isinstance(part, ast.BinOp) and isinstance(part.op, ast.BitOr)
            for annotation in annotations
            for part in ast.walk(annotation)
        ):
            return True
    return False


def _postpones_annotations(tree):
    return any(
        isinstance(node, ast.ImportFrom)
        and node.module == "__future__"
        and any(alias.name == "annotations" for alias in node.names)
        for node in tree.body
    )


class InstalledPackageRuntimeTests(unittest.TestCase):
    maxDiff = None

    def test_addon_starts_under_anki_assigned_package_name(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            installed_package = root / "installed_addon"
            for source_path, archive_name in _collect_runtime_files(
                REPOSITORY_ROOT / "ankiforge_ai"
            ):
                destination = installed_package / Path(archive_name)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(source_path.read_bytes())

            script = "\n".join(
                (
                    "import importlib",
                    "import sys",
                    "import types",
                    "sys.path.insert(0, sys.argv[1])",
                    "class DummyMeta(type):",
                    "    def __getattr__(cls, _name): return cls",
                    "class Dummy(metaclass=DummyMeta):",
                    "    def __init__(self, *_args, **_kwargs): self.triggered = self",
                    "    def connect(self, _callback): return None",
                    "    def addAction(self, _action): return None",
                    "    def setShortcut(self, _shortcut): return None",
                    "aqt = types.ModuleType('aqt')",
                    "aqt.__path__ = []",
                    "qt = types.ModuleType('aqt.qt')",
                    "qt.__getattr__ = lambda _name: Dummy",
                    "mw = Dummy()",
                    "mw.form = Dummy()",
                    "mw.form.menuTools = Dummy()",
                    "aqt.mw = mw",
                    "sys.modules['aqt'] = aqt",
                    "sys.modules['aqt.qt'] = qt",
                    "importlib.import_module('installed_addon')",
                    "importlib.import_module('installed_addon.intelligence')",
                    "importlib.import_module('installed_addon.importers.source_import')",
                    "importlib.import_module('installed_addon.workbench')",
                    "importlib.import_module('installed_addon.workbench.generation_lifecycle')",
                    "importlib.import_module('installed_addon.workbench.write_coordinator')",
                )
            )
            result = subprocess.run(
                [sys.executable, "-I", "-c", script, str(root)],
                capture_output=True,
                check=False,
                text=True,
                timeout=30,
            )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_python_39_runtime_does_not_evaluate_pipe_annotations(self):
        violations = []
        source_root = REPOSITORY_ROOT / "ankiforge_ai"
        for source_path in sorted(source_root.rglob("*.py")):
            archive_name = source_path.relative_to(source_root).as_posix()
            tree = ast.parse(
                source_path.read_text(encoding="utf-8"),
                filename=archive_name,
            )
            if _uses_eager_pipe_annotation(tree) and not _postpones_annotations(tree):
                violations.append(archive_name)

        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
