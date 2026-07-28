# v0.14 UI Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the v0.13-style material-first workbench hierarchy on the v0.14 main screen without changing import, generation, Provider, review, or Anki-write behavior.

**Architecture:** Keep `CardMakerPanel` as the existing integration boundary. Recompose only its already-created widgets: add an inline material-import row and move document-intelligence controls into the already-collapsed generation-settings container. Keep all controllers, session mutations, signal connections, and write controls untouched. Use the existing translation catalog and stylesheet rather than a new UI framework or persistence layer.

**Tech Stack:** Python, Anki/Qt (`aqt.qt`), `unittest`, existing static UI-contract tests, existing `.ankiaddon` build script.

## Global Constraints

- Remain on `v0.14.0-pr28-ui-convergence` until the completed branch is merged into `main`.
- Do not alter document parsing, queue semantics, Provider requests, API-key session-only handling, review decisions, duplicate checks, or Anki write confirmation.
- Do not add persistence, network behavior, OCR, or collection writes.
- Keep `card_mode` visible with the current `concept` default; advanced generation settings stay closed initially.
- Keep AI Provider, Model, and API key controls in `AiSettingsDialog` only.
- Preserve Chinese/English catalog key parity and use product-facing copy.
- Use `python -m unittest discover`, `python -m compileall .`, `git diff --check`, and `python scripts/build_ankiaddon.py` before merge.

---

### Task 1: Add a regression contract for the visual hierarchy

**Files:**
- Create: `tests/test_ui_convergence_v014.py`
- Read: `ankiforge_ai/ui/card_maker_panel.py`, `ankiforge_ai/ui/product_i18n.py`, `ankiforge_ai/ui/product_styles.py`

**Interfaces:**
- Consumes: existing `CardMakerPanel._build_material_section`, `CardMakerPanel._build_generation_section`, `PRODUCT_COPY`, and `PRODUCT_DARK_STYLESHEET`.
- Produces: source-level regression tests that fail if the initial main-screen hierarchy reverts to file-first or exposes advanced document intelligence controls by default.

- [ ] **Step 1: Write the failing test**

```python
def test_material_editor_precedes_a_compact_inline_import_row(self):
    material = self.function_source("_build_material_section")
    self.assertIn('setObjectName("MaterialImportRow")', material)
    self.assertIn("self.material_import_hint_label", material)
    self.assertLess(
        material.index("layout.addWidget(self.material_input, 1)"),
        material.index("self.material_import_hint_label"),
    )
    self.assertLess(
        material.index("self.material_import_hint_label"),
        material.index("self.document_queue_container"),
    )

def test_intelligence_controls_are_inside_collapsed_generation_settings(self):
    generation = self.function_source("_build_generation_section")
    self.assertLess(
        generation.index("self.card_mode_combo"),
        generation.index("self.generation_settings_container"),
    )
    self.assertIn("self._add_form_row(advanced_form, self.intelligence_level_label", generation)
    self.assertIn("self.generation_settings_container.setVisible(False)", generation)
```

- [ ] **Step 2: Run the new test to verify it fails**

Run: `python -m unittest discover -s tests -p test_ui_convergence_v014.py`

Expected: failure because `MaterialImportRow` and `advanced_form` do not yet exist, and the intelligence selector is still in the visible top form.

- [ ] **Step 3: Extend the test for bilingual copy and visual hooks**

```python
def test_copy_and_styles_make_import_secondary_and_settings_quiet(self):
    for language in ("zh", "en"):
        self.assertTrue(PRODUCT_COPY[language]["material_import_hint"])
        self.assertTrue(PRODUCT_COPY[language]["more_options"])
    self.assertIn("QFrame#MaterialImportRow", PRODUCT_DARK_STYLESHEET)
    self.assertIn("QFrame#GenerationSettingsDisclosure", PRODUCT_DARK_STYLESHEET)
```

- [ ] **Step 4: Re-run the focused test and preserve its expected red state**

Run: `python -m unittest discover -s tests -p test_ui_convergence_v014.py`

Expected: it still fails only for the new UI structure/copy/style hooks; do not add production code yet.

- [ ] **Step 5: Commit the red test**

```bash
git add tests/test_ui_convergence_v014.py
git commit -m "test: cover v0.14 material-first UI hierarchy"
```

### Task 2: Recompose the existing material and generation widgets

**Files:**
- Modify: `ankiforge_ai/ui/card_maker_panel.py:235-330, 626-858, 1481-1489`
- Modify: `ankiforge_ai/ui/product_i18n.py:42-44, 150-152, 332-334, 476-478`
- Modify: `ankiforge_ai/ui/product_styles.py:186-197`
- Test: `tests/test_ui_convergence_v014.py`

**Interfaces:**
- Consumes: existing `FileDropTextEdit`, `_enqueue_document_paths`, `_render_document_queue`, `_update_intelligence_estimate`, `_toggle_generation_settings`, and all existing combo-box signal connections.
- Produces: the same import and generation state transitions with a material-first initial visual hierarchy.

- [ ] **Step 1: Implement the inline import row in `_build_material_section`**

```python
self.material_import_row = QFrame()
self.material_import_row.setObjectName("MaterialImportRow")
import_row = QHBoxLayout(self.material_import_row)
import_row.setContentsMargins(0, 0, 0, 0)
self.material_import_hint_label = QLabel(self.t("material_import_hint"))
self.material_import_hint_label.setProperty("role", "secondary")
import_row.addWidget(self.material_import_hint_label, 1)
import_row.addWidget(self.choose_file_btn)
layout.addWidget(self.material_import_row)
```

Keep `self.choose_file_btn.clicked.connect(self._choose_source_file)`, document queue rendering, warnings, retry behavior, example material, capabilities help, and character count intact. Add `material_import_hint_label` to `_retranslate_ui`.

- [ ] **Step 2: Put all document-intelligence controls behind the existing disclosure**

```python
self.generation_settings_container = QFrame()
self.generation_settings_container.setObjectName("GenerationSettingsDisclosure")
advanced_layout = QVBoxLayout(self.generation_settings_container)
advanced_form = QFormLayout()
self._configure_form_layout(advanced_form)
self._add_form_row(
    advanced_form,
    self.intelligence_level_label,
    self.intelligence_level_combo,
)
advanced_layout.addLayout(advanced_form)
self.generation_settings_container.setVisible(False)
```

Keep the card-mode form and description outside this container. Add the existing card-count, answer-length, output-language, estimate label, plan-details button, and plan-details container to `advanced_layout`; do not change their defaults, handlers, or controller calls. Preserve the current `more_options` toggle method and retranslation flow.

- [ ] **Step 3: Apply restrained copy and stylesheet hooks**

```python
"material_import_hint": "也可拖入 TXT、MD 或 DOCX 文件",
"more_options": "生成设置（可选）",
"more_options_collapse": "收起生成设置",
```

Use equivalent concise English values. Add only `QFrame#MaterialImportRow` and `QFrame#GenerationSettingsDisclosure` rules to reinforce hierarchy; replace the material editor’s dashed empty-state border with a subtle solid border. Do not introduce a new palette, icon system, component library, or fixed geometry.

- [ ] **Step 4: Run the focused regression test to verify it passes**

Run: `python -m unittest discover -s tests -p test_ui_convergence_v014.py`

Expected: all UI-convergence assertions pass.

- [ ] **Step 5: Run the adjacent contract tests**

Run: `python -m unittest tests.test_linear_flow_settings_modal tests.test_universal_document_ui_contract tests.test_v1_core_ui_contract tests.test_product_i18n tests.test_product_styles tests.test_ui_copy_hotfix`

Expected: all selected tests pass, demonstrating that the settings modal, import queue, document-intelligence behavior, safety copy, styles, and language catalog remain intact.

- [ ] **Step 6: Commit the green implementation**

```bash
git add ankiforge_ai/ui/card_maker_panel.py ankiforge_ai/ui/product_i18n.py ankiforge_ai/ui/product_styles.py tests/test_ui_convergence_v014.py
git commit -m "Polish v0.14 material-first main screen"
```

### Task 3: Document manual acceptance and produce release-ready evidence

**Files:**
- Modify: `docs/manual_anki_acceptance.md`
- Read: `scripts/build_ankiaddon.py`, `tests/test_build_ankiaddon.py`

**Interfaces:**
- Consumes: the completed UI and existing packaging/forbidden-file checks.
- Produces: a concrete manual Anki acceptance checklist and fresh package evidence before merging to `main`.

- [ ] **Step 1: Add the manual UI acceptance checklist**

Add a v0.14 UI-convergence section that requires a tester to verify: the text editor is the first and largest material control; selecting and dropping a TXT/MD/DOCX file still queues it; generation settings are closed on first open and expand correctly; language switching updates the import hint; AI Settings remains a separate dialog; candidate review, duplicate check, and final write confirmation behave as before.

- [ ] **Step 2: Run the full test suite**

Run: `python -m unittest discover`

Expected: exit code 0 with no failures.

- [ ] **Step 3: Run syntax, diff, and package verification**

Run:

```bash
python -m compileall .
git diff --check
python scripts/build_ankiaddon.py
```

Expected: compilation and diff checks exit 0; the build reports the package file count and size and rejects forbidden files.

- [ ] **Step 4: Record package integrity evidence**

Run:

```powershell
Get-FileHash dist/ankiforge_ai.ankiaddon -Algorithm SHA256
python scripts/build_ankiaddon.py
Get-FileHash dist/ankiforge_ai.ankiaddon -Algorithm SHA256
```

Expected: both SHA-256 values are identical; package content contains no config, backup, secret, or Anki collection data.

- [ ] **Step 5: Commit documentation and merge only after all evidence is green**

```bash
git add docs/manual_anki_acceptance.md
git commit -m "Document v0.14 UI convergence acceptance"
git checkout main
git merge --no-ff v0.14.0-pr28-ui-convergence
git push public main
```

Do not create a tag, GitHub Release, or AnkiWeb update in this task. Stop instead of merging if verification, package safety checks, or a merge conflict fails.
