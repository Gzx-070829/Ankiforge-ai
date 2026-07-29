# AnkiForge AI v0.14.1 Packaged Runtime Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the installed `.ankiaddon` load under its Anki-assigned package name, preserve the advertised Python 3.9 compatibility floor, prevent source-layout-only code from shipping, and prepare a verified v0.14.1 startup hotfix without changing Provider or Anki write behavior.

**Architecture:** Keep Anki's required flat add-on archive layout, where `__init__.py` and `manifest.json` live at the archive root. Replace source-root-dependent internal imports with package-relative imports, then enforce that contract both statically and in an isolated installed-layout subprocess. Extend the package validator so absolute `ankiforge_ai` self-imports, eager pipe annotations, Python syntax newer than 3.9, or missing current critical modules fail the build.

**Tech Stack:** Python 3, `unittest`, `ast`, `subprocess`, `tempfile`, ZIP-format `.ankiaddon`, existing deterministic build script.

## Global Constraints

- Do not start a real Provider or perform a network request.
- Do not write to or inspect a real Anki collection.
- Do not persist API keys or introduce `config.json`.
- Preserve the flat Anki add-on archive layout.
- Do not redesign the UI or alter card generation/write semantics.
- Build output must contain no config, secrets, backups, caches, tests, docs, or Anki user data.
- Do not push, merge, update AnkiWeb, create a tag, or create a GitHub Release without separate authorization.

---

### Task 1: Reproduce and lock the installed-package import contract

**Files:**
- Create: `tests/test_installed_package_runtime.py`
- Read: `scripts/build_ankiaddon.py`
- Read: `ankiforge_ai/intelligence/analyzer.py`

**Interfaces:**
- Consumes: repository source directory `ankiforge_ai/`.
- Produces: a regression test that imports the copied package under an arbitrary installed add-on name in an isolated Python subprocess.

- [ ] **Step 1: Write the failing installed-layout test**

```python
def test_pure_runtime_modules_import_under_installed_addon_name(self):
    with tempfile.TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        shutil.copytree(ROOT / "ankiforge_ai", root / "installed_addon")
        script = (
            "import importlib, sys\n"
            "sys.path.insert(0, sys.argv[1])\n"
            "importlib.import_module('installed_addon.intelligence.analyzer')\n"
            "importlib.import_module('installed_addon.importers.source_import')\n"
        )
        result = subprocess.run(
            [sys.executable, "-I", "-c", script, str(root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
```

- [ ] **Step 2: Write the failing static self-import test**

```python
def test_runtime_source_has_no_absolute_self_imports(self):
    violations = find_absolute_self_imports(ROOT / "ankiforge_ai")
    self.assertEqual(violations, [])
```

- [ ] **Step 3: Run the focused tests and verify RED**

Run:

```powershell
python -m unittest tests.test_installed_package_runtime -v
```

Expected: failure showing `ModuleNotFoundError: No module named 'ankiforge_ai'` and the absolute-import violation list.

### Task 2: Convert runtime self-imports to package-relative imports

**Files:**
- Modify: `ankiforge_ai/eval/document_intelligence_benchmark.py`
- Modify: `ankiforge_ai/importers/source_import.py`
- Modify: `ankiforge_ai/intelligence/analyzer.py`
- Modify: `ankiforge_ai/intelligence/critic.py`
- Modify: `ankiforge_ai/intelligence/template_router.py`
- Modify: `ankiforge_ai/intelligence/chunking/models.py`
- Modify: `ankiforge_ai/intelligence/chunking/structural.py`
- Modify: `ankiforge_ai/intelligence/planning/coverage.py`
- Modify: `ankiforge_ai/intelligence/planning/llm_planner.py`
- Modify: `ankiforge_ai/intelligence/planning/local_planner.py`
- Modify: `ankiforge_ai/intelligence/planning/models.py`
- Test: `tests/test_installed_package_runtime.py`

**Interfaces:**
- Consumes: existing `document`, `pipeline`, and `intelligence` package APIs.
- Produces: imports that resolve relative to any Anki-assigned add-on directory name.

- [ ] **Step 1: Replace each `ankiforge_ai...` runtime self-import with the correct relative import depth**

Examples:

```python
# ankiforge_ai/intelligence/analyzer.py
from ..document import BlockKind, DocumentIR, count_blocks_by_kind

# ankiforge_ai/intelligence/chunking/models.py
from ...document import BlockKind, SourceLocation

# ankiforge_ai/importers/source_import.py
from ..document import DocumentImportError
```

- [ ] **Step 2: Run the focused installed-layout tests and verify GREEN**

Run:

```powershell
python -m unittest tests.test_installed_package_runtime -v
```

Expected: all installed-layout and static self-import tests pass.

- [ ] **Step 3: Run focused document/intelligence/import tests**

Run:

```powershell
python -m unittest tests.test_source_import tests.test_document_analyzer tests.test_structural_chunker tests.test_knowledge_planner_v014 tests.test_critic_repair_v014 tests.test_template_router_v014
```

Expected: all focused tests pass.

### Task 3: Make the package build reject source-layout-only or incompatible runtime code

**Files:**
- Modify: `tests/test_build_ankiaddon.py`
- Modify: `scripts/build_ankiaddon.py`

**Interfaces:**
- Consumes: Python archive member names and bytes in `_validate_archive`.
- Produces: `BuildError` when packaged Python imports `ankiforge_ai` absolutely, eagerly evaluates a pipe annotation on Python 3.9, uses newer syntax, or omits a current critical module.

- [ ] **Step 1: Write the failing archive-validation test**

```python
def test_archive_rejects_absolute_ankiforge_self_import(self):
    files = required_test_files(root)
    bad_module = root / "bad.py"
    bad_module.write_text(
        "from ankiforge_ai.document import DocumentIR\n",
        encoding="utf-8",
    )
    files.append((bad_module, "bad.py"))
    _write_archive(archive_path, files)
    with self.assertRaisesRegex(BuildError, "absolute self-import"):
        _validate_archive(archive_path, {name for _, name in files})
```

- [ ] **Step 2: Run the build test and verify RED**

Run:

```powershell
python -m unittest tests.test_build_ankiaddon.BuildAnkiAddonTests.test_archive_rejects_absolute_ankiforge_self_import -v
```

Expected: failure because `_validate_archive` currently accepts the bad import.

- [ ] **Step 3: Add AST-based validation for Python archive members**

Parse each `.py` member and reject:

```python
import ankiforge_ai
from ankiforge_ai.document import DocumentIR
```

Do not reject test files outside the runtime archive; the guard applies to package members.

- [ ] **Step 4: Run all build tests and verify GREEN**

Run:

```powershell
python -m unittest tests.test_build_ankiaddon -v
```

Expected: all build tests pass.

### Task 4: Align v0.14.1 release metadata and acceptance guidance

**Files:**
- Modify: `ankiforge_ai/__init__.py`
- Modify: `ankiforge_ai/manifest.json`
- Modify: `README.md`
- Modify: `README.en.md`
- Modify: `docs/release_notes_v0_14.md`
- Modify: `docs/ankiweb_description_v0_14.md`
- Modify: `docs/manual_anki_acceptance.md`
- Modify: `tests/test_v014_release_contract.py`
- Modify: `tests/test_pr26_release_metadata_and_lifecycle.py`

**Interfaces:**
- Consumes: existing release metadata contract.
- Produces: a single `0.14.1` version and an explicit real-Anki startup acceptance check.

- [ ] **Step 1: Change version-contract expectations to `0.14.1` and verify RED**

Run:

```powershell
python -m unittest tests.test_v014_release_contract tests.test_pr26_release_metadata_and_lifecycle -v
```

Expected: version assertions fail while runtime metadata remains `0.14.0`.

- [ ] **Step 2: Update runtime, manifest, README, release notes, and AnkiWeb draft to `0.14.1`**

Document that v0.14.1 fixes installed-layout startup imports and does not change Provider, review, duplicate-check, or write behavior.

- [ ] **Step 3: Add manual acceptance for Anki 26.05**

Require:

```text
Install the final package, restart Anki 26.05, confirm no startup-failure
dialog, open AnkiForge AI from Tools, then close it without generating or
writing.
```

- [ ] **Step 4: Rebuild the tracked package and verify metadata tests GREEN**

Run:

```powershell
python scripts/build_ankiaddon.py
python -m unittest tests.test_v014_release_contract tests.test_pr26_release_metadata_and_lifecycle -v
```

Expected: runtime, manifest, docs, and packaged metadata all report `0.14.1`.

### Task 5: Full runtime, security, and reproducibility verification

**Files:**
- Verify: entire repository
- Build: `dist/ankiforge_ai.ankiaddon`

**Interfaces:**
- Consumes: completed hotfix source.
- Produces: evidence for merge/publication decision.

- [ ] **Step 1: Run the complete unit suite**

```powershell
python -m unittest discover
```

- [ ] **Step 2: Compile all Python files**

```powershell
python -m compileall .
```

- [ ] **Step 3: Run whitespace validation**

```powershell
git diff --check
```

- [ ] **Step 4: Build twice and compare SHA-256**

```powershell
python scripts/build_ankiaddon.py
Get-FileHash dist/ankiforge_ai.ankiaddon -Algorithm SHA256
python scripts/build_ankiaddon.py
Get-FileHash dist/ankiforge_ai.ankiaddon -Algorithm SHA256
```

The two hashes, file counts, and byte sizes must match.

- [ ] **Step 5: Audit the final archive and tracked files**

Confirm no `config.json`, `.env`, backup, logs, caches, tests, docs, `.anki2`, `.apkg`, collection data, private keys, API keys, passwords, or bearer tokens.

- [ ] **Step 6: Inspect the final diff and commit**

```powershell
git diff --stat
git diff
git status --short
git add <reviewed files>
git commit -m "Fix packaged runtime imports for Anki startup"
git status --short
```

Do not merge or push without separate authorization.
