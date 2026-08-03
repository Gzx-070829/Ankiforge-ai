"""Build and validate the AnkiForge AI AnkiWeb package.

Run this script from the repository root. The archive contains files relative
to ``ankiforge_ai/`` so Anki sees ``__init__.py`` and ``manifest.json`` at the
archive root. Repository documentation, configuration examples, and licenses
are intentionally excluded: the .ankiaddon is a runtime-only package.
"""

from __future__ import annotations

import ast
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath


SOURCE_DIRECTORY = "ankiforge_ai"
OUTPUT_PATH = Path("dist") / "ankiforge_ai.ankiaddon"
TEMP_OUTPUT_NAME = ".ankiforge_ai.ankiaddon.tmp"

BLOCKED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "addons21",
    "docs",
    "eval",
    "fixtures",
    "screenshots",
    "models",
    "cache",
    "temp",
    "tmp",
    "tools",
    "tests",
    "user_files",
}
BLOCKED_FILENAMES = {
    ".env",
    ".ds_store",
    "collection.anki2",
    "config.json",
    "credentials.json",
    "secrets.json",
    "thumbs.db",
}
BLOCKED_SUFFIXES = {
    ".anki2",
    ".apkg",
    ".log",
    ".pyc",
    ".key",
    ".pem",
    ".p12",
    ".pfx",
}
NON_RUNTIME_FILENAMES = {
    "config.example.json",
    "config.md",
}
ALLOWED_RUNTIME_SUFFIXES = {
    ".css",
    ".gif",
    ".html",
    ".ico",
    ".jpeg",
    ".jpg",
    ".js",
    ".json",
    ".otf",
    ".png",
    ".py",
    ".svg",
    ".ttf",
    ".webp",
    ".woff",
    ".woff2",
}
TEXT_RUNTIME_SUFFIXES = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".py",
    ".svg",
}
REQUIRED_ARCHIVE_FILES = {
    "__init__.py",
    "anki_writer/minimal_write.py",
    "document/__init__.py",
    "importers/source_import.py",
    "intelligence/__init__.py",
    "manifest.json",
    "pipeline/openai_compatible_provider.py",
    "ui/ai_settings_dialog.py",
    "ui/card_maker_panel.py",
    "ui/file_drop_text_edit.py",
    "ui/main_dialog.py",
    "ui/review_session_adapter.py",
    "ui/workbench_factory.py",
    "ui/workbench_preferences_adapter.py",
    "workbench/__init__.py",
    "workbench/generation_lifecycle.py",
    "workbench/legacy_bridge.py",
    "workbench/models.py",
    "workbench/preferences.py",
    "workbench/review_use_cases.py",
    "workbench/store.py",
    "workbench/transitions.py",
    "workbench/write_coordinator.py",
}
SECRET_PATTERNS = {
    "OpenAI-style API key": re.compile(rb"sk-[A-Za-z0-9_-]{20,}"),
    "AWS access key": re.compile(rb"AKIA[0-9A-Z]{16}"),
    "GitHub token": re.compile(
        rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,})"
    ),
    "private key": re.compile(
        rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    ),
}


class BuildError(RuntimeError):
    """Raised when the package cannot be built safely."""


def _uses_pipe_annotation(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        annotations: list[ast.expr] = []
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


def _postpones_annotations(tree: ast.Module) -> bool:
    return any(
        isinstance(node, ast.ImportFrom)
        and node.module == "__future__"
        and any(alias.name == "annotations" for alias in node.names)
        for node in tree.body
    )


def _validate_python_member(archive_name: str, content: bytes) -> None:
    try:
        source = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise BuildError(
            f"Python archive member is not UTF-8: {archive_name}"
        ) from error
    try:
        tree = ast.parse(
            source,
            filename=archive_name,
            feature_version=(3, 9),
        )
    except SyntaxError as error:
        raise BuildError(
            "Python archive member is not valid Python 3.9 syntax: "
            f"{archive_name}:{error.lineno}"
        ) from error
    if _uses_pipe_annotation(tree) and not _postpones_annotations(tree):
        raise BuildError(
            "Python archive member must postpone annotations for the supported "
            f"Python 3.9 runtime: {archive_name}"
        )

    for node in ast.walk(tree):
        modules = ()
        if isinstance(node, ast.Import):
            modules = tuple(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules = (node.module,)
        if any(
            module == SOURCE_DIRECTORY
            or module.startswith(f"{SOURCE_DIRECTORY}.")
            for module in modules
        ):
            raise BuildError(
                "Python archive member uses an absolute self-import; "
                f"use a package-relative import: {archive_name}:{node.lineno}"
            )


def _blocked_reason(path: PurePosixPath) -> str | None:
    lowered_parts = tuple(part.casefold() for part in path.parts)
    if any(part in BLOCKED_PARTS for part in lowered_parts):
        return "blocked directory"
    if any("backup" in part for part in lowered_parts):
        return "backup path"

    name = lowered_parts[-1]
    if name in BLOCKED_FILENAMES:
        return "blocked filename"
    if name.startswith(".env."):
        return "environment file"
    if any(name.endswith(suffix) for suffix in BLOCKED_SUFFIXES):
        return "blocked file type"
    return None


def _is_non_runtime_file(relative_path: Path) -> bool:
    name = relative_path.name.casefold()
    if name in NON_RUNTIME_FILENAMES:
        return True
    if name == "readme" or name.startswith("readme."):
        return True
    return name == "license" or name.startswith("license.")


def _collect_runtime_files(source_directory: Path) -> list[tuple[Path, str]]:
    runtime_files: list[tuple[Path, str]] = []
    for candidate in sorted(source_directory.rglob("*")):
        relative_path = candidate.relative_to(source_directory)
        archive_name = relative_path.as_posix()
        archive_path = PurePosixPath(archive_name)

        if _blocked_reason(archive_path) is not None:
            continue
        if candidate.is_symlink():
            raise BuildError(f"Symlinks are not allowed: {relative_path}")
        if candidate.is_dir():
            continue
        if not candidate.is_file():
            raise BuildError(f"Unsupported filesystem entry: {relative_path}")
        if _is_non_runtime_file(relative_path):
            continue
        if candidate.suffix.casefold() not in ALLOWED_RUNTIME_SUFFIXES:
            raise BuildError(
                f"Unclassified file type; explicitly include or exclude it: "
                f"{relative_path}"
            )

        runtime_files.append((candidate, archive_name))

    if not runtime_files:
        raise BuildError("No runtime files were found to package.")
    return runtime_files


def _write_archive(
    archive_path: Path,
    runtime_files: list[tuple[Path, str]],
) -> None:
    with zipfile.ZipFile(
        archive_path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for source_path, archive_name in runtime_files:
            # Fixed metadata makes repeated builds from identical sources stable.
            info = zipfile.ZipInfo(archive_name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            content = source_path.read_bytes()
            if PurePosixPath(archive_name).suffix.casefold() in TEXT_RUNTIME_SUFFIXES:
                content = content.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
            archive.writestr(info, content)


def _validate_archive(archive_path: Path, expected_names: set[str]) -> int:
    with zipfile.ZipFile(archive_path, mode="r") as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise BuildError(f"Corrupt archive member: {bad_member}")

        names = archive.namelist()
        if len(names) != len(set(names)):
            raise BuildError("The archive contains duplicate paths.")

        for name in names:
            if "\\" in name:
                raise BuildError(f"Archive path uses a backslash: {name}")
            member_path = PurePosixPath(name)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise BuildError(f"Unsafe archive path: {name}")
            reason = _blocked_reason(member_path)
            if reason is not None:
                raise BuildError(f"Forbidden archive member ({reason}): {name}")

            content = archive.read(name)
            for label, pattern in SECRET_PATTERNS.items():
                if pattern.search(content):
                    raise BuildError(f"Possible {label} found in archive member: {name}")
            if member_path.suffix.casefold() == ".py":
                _validate_python_member(name, content)

        actual_names = set(names)
        if actual_names != expected_names:
            missing = sorted(expected_names - actual_names)
            unexpected = sorted(actual_names - expected_names)
            raise BuildError(
                f"Archive contents differ from the build plan; "
                f"missing={missing}, unexpected={unexpected}"
            )

        missing_required = sorted(REQUIRED_ARCHIVE_FILES - actual_names)
        if missing_required:
            raise BuildError(f"Required add-on files are missing: {missing_required}")
        return len(names)


def build() -> tuple[Path, int, int]:
    repository_root = Path(__file__).resolve().parents[1]
    if Path.cwd().resolve() != repository_root:
        raise BuildError(
            f"Run this script from the repository root: {repository_root}"
        )

    source_directory = repository_root / SOURCE_DIRECTORY
    if not source_directory.is_dir():
        raise BuildError(f"Source directory does not exist: {source_directory}")

    output_path = repository_root / OUTPUT_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.parent / TEMP_OUTPUT_NAME

    if output_path.exists():
        output_path.unlink()
    if temporary_path.exists():
        temporary_path.unlink()

    runtime_files = _collect_runtime_files(source_directory)
    expected_names = {archive_name for _, archive_name in runtime_files}

    try:
        _write_archive(temporary_path, runtime_files)
        file_count = _validate_archive(temporary_path, expected_names)
        temporary_path.replace(output_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()

    size_bytes = output_path.stat().st_size
    return output_path.relative_to(repository_root), file_count, size_bytes


def main() -> int:
    try:
        output_path, file_count, size_bytes = build()
    except (BuildError, OSError, zipfile.BadZipFile) as error:
        print(f"Build failed: {error}", file=sys.stderr)
        return 1

    print(f"Built: {output_path.as_posix()}")
    print(f"Files: {file_count}")
    print(f"Size: {size_bytes} bytes")
    print("Validation: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
