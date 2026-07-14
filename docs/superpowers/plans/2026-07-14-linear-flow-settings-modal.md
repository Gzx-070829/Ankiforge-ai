# Linear Flow + AI Settings Modal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the main-screen AI Provider form with a polished session-only modal while reorganizing the main window into a linear create → review → write flow.

**Architecture:** `MainDialog` owns the header action and status chip, `AiSettingsDialog` owns a temporary settings draft, and `CardMakerPanel` owns the accepted in-memory `BeginnerAIProviderRuntimeSettings`. The generation and Anki write pipelines remain unchanged; only the UI composition and the source of runtime settings change.

**Tech Stack:** Python 3, Anki `aqt.qt` compatibility layer, Qt layouts/QSS, `unittest`, deterministic ZIP packaging.

## Global Constraints

- Work only on `v0.12.5-pr23-linear-flow-settings-modal`; do not merge or push `main`.
- Do not call a real Provider, launch Anki, write to an Anki collection, upload AnkiWeb, create a tag, or create a Release.
- Do not change provider transport, prompt profiles, card modes, quality validation, duplicate checking, safe writing, confirmation, tags, source, or undo behavior.
- API key remains current-session memory only and must not enter config, logs, documentation, snapshots, string representations, or package extras.
- Main screen contains no Provider, Model, API key, API key hint, debug entry, or long safety explanation.
- The three core dialog rows remain stable; Base URL and Timeout appear only for `OpenAI-compatible` so existing provider capability is not removed.
- Use the approved palette, 24 px outer margin/gap, 16 px section gap, 40 px controls, 44 px main CTAs, and 10–12 px radii.
- Keep one final PR23 commit with message `Move AI provider settings into session dialog`; amend the existing design commit after implementation.

---

## File map

- Create `ankiforge_ai/ui/ai_settings_dialog.py`: modal UI, provider preset selection, local draft validation, safe accepted runtime settings, frameless title drag behavior.
- Modify `ankiforge_ai/ui/card_maker_panel.py`: linear panel layout, accepted runtime settings state, Generate button placement, empty-state glyph, session discard.
- Modify `ankiforge_ai/ui/main_dialog.py`: header AI action/status chip and dialog orchestration.
- Modify `ankiforge_ai/ui/product_i18n.py`: Chinese/English dialog, status, and short workflow copy.
- Modify `ankiforge_ai/ui/product_styles.py`: approved tokens and selectors for header, main surfaces, dialog, controls, and button hierarchy.
- Modify `ankiforge_ai/__init__.py` and `ankiforge_ai/manifest.json`: version `0.12.5`.
- Create `tests/test_linear_flow_settings_modal.py`: PR23 UI, session-only, copy, version, and structure contracts.
- Update existing UI/source tests that encode the old provider section and old palette.
- Update `docs/ui_linear_flow_settings_modal_v0_12_5.md` with the compatible-provider conditional fields.
- Create/update a static preview and screenshots under `docs/` without adding runtime dependencies.

### Task 1: Lock the PR23 contracts with failing tests

**Files:**
- Create: `tests/test_linear_flow_settings_modal.py`
- Modify: `tests/test_provider_form_layout_hotfix.py`
- Modify: `tests/test_single_screen_card_maker.py`
- Modify: `tests/test_product_styles.py`

**Interfaces:**
- Consumes: repository source files and `PRODUCT_COPY`.
- Produces: source-level contracts for `AiSettingsDialog`, `CardMakerPanel.set_ai_runtime_settings`, header settings action/status, and v0.12.5 version.

- [ ] **Step 1: Write failing source-contract tests**

```python
def test_main_layout_excludes_provider_form_and_keeps_linear_ctas(self):
    builder = function_source(panel_source(), "_build_ui")
    assert "_build_provider_section" not in builder
    assert "_build_create_panel" in builder
    assert "_build_review_panel" in builder
    assert "columns.addWidget(left, 45)" in builder
    assert "columns.addWidget(right, 55)" in builder

def test_dialog_owns_provider_model_and_api_key(self):
    source = dialog_source()
    for name in ("provider_combo", "model_input", "api_key_input"):
        assert f"self.{name}" in source
    assert source.count('self.t("api_key_help")') == 1
    assert "QLineEdit.EchoMode.Password" in source

def test_api_key_lives_only_in_safe_runtime_settings(self):
    panel = panel_source()
    assert "self._ai_runtime_settings = None" in panel
    assert "def set_ai_runtime_settings" in panel
    assert "save_config" not in dialog_source()
    assert "write_config" not in dialog_source()
```

- [ ] **Step 2: Run the focused tests and verify the intended failures**

Run: `python -m unittest tests.test_linear_flow_settings_modal tests.test_provider_form_layout_hotfix tests.test_single_screen_card_maker tests.test_product_styles`

Expected: failures for missing dialog, old `_build_provider_section` placement, old palette, and v0.12.3 version; no unrelated runtime error.

- [ ] **Step 3: Replace obsolete assertions rather than weakening safety assertions**

Old tests must stop requiring Provider fields on the main panel. Keep their guarantees by asserting the same fixed-label, stretching-control, password-echo, single-hint, and OpenAI-compatible conditional behavior inside `AiSettingsDialog`.

### Task 2: Implement the session-only AI Settings modal

**Files:**
- Create: `ankiforge_ai/ui/ai_settings_dialog.py`
- Modify: `ankiforge_ai/ui/product_i18n.py`
- Test: `tests/test_linear_flow_settings_modal.py`

**Interfaces:**
- Consumes: `BeginnerAIProviderRuntimeSettings`, `product_text(language, key)`.
- Produces:
  - `AiSettingsDialog(parent=None, language="zh", settings=None)`
  - `AiSettingsDialog.runtime_settings() -> BeginnerAIProviderRuntimeSettings | None`
  - `AiSettingsDialog.t(key, **values) -> str`

- [ ] **Step 1: Add Chinese/English keys**

Add matching keys to both locales:

```python
"ai_settings": "AI 设置",
"ai_not_configured": "AI 未配置",
"ai_configured": "{provider} · 已配置",
"save_session_settings": "保存本次设置",
"close": "关闭",
"ai_settings_session_note": "API key 仅在本次 Anki 窗口中使用，不会写入配置文件。",
"ai_settings_invalid": "请填写有效的 Provider、Model 和 API key。",
```

Use concise English equivalents: `AI Settings`, `AI not configured`, `{provider} · Configured`, `Save for this session`, `Close`, and the approved session-only note.

- [ ] **Step 2: Implement dialog construction and provider presets**

```python
class AiSettingsDialog(QDialog):
    PROVIDERS = (
        ("DeepSeek", "https://api.deepseek.com", "deepseek-v4-flash"),
        ("OpenAI", "https://api.openai.com/v1", "gpt-4o-mini"),
        ("OpenAI-compatible", "", ""),
    )

    def __init__(self, parent=None, language="zh", settings=None):
        super().__init__(parent)
        self.language = language
        self._accepted_settings = None
        self._initial_settings = settings
        self._drag_offset = None
        self._build_ui()
        self._load_settings(settings)
```

The form uses explicit `QHBoxLayout` rows, a fixed 96 px label, a stretching field, 40 px controls, and a nested API-key field with one hint. `OpenAI-compatible` reveals Base URL and Timeout below the core rows; other presets keep them hidden and derive the preset URL.

- [ ] **Step 3: Implement safe acceptance**

```python
def _save(self):
    provider_name, preset_url, _suggested = self.provider_combo.currentData()
    try:
        settings = BeginnerAIProviderRuntimeSettings(
            provider_name=provider_name,
            base_url=(self.base_url_input.text() or preset_url).strip(),
            model=self.model_input.text().strip(),
            api_key=self.api_key_input.text().strip(),
            timeout_seconds=self.timeout_input.value(),
        )
    except ValueError:
        self.error_label.setText(self.t("ai_settings_invalid"))
        self.error_label.setVisible(True)
        return
    self._accepted_settings = settings
    self.accept()
```

`runtime_settings()` returns `_accepted_settings`. Cancel, custom close, window close, and Escape never mutate the caller's accepted settings.

- [ ] **Step 4: Implement frameless behavior with compatibility-safe APIs**

Use `Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog` when `WindowType` exists, otherwise the Qt5 constants. The title bar handles press/move/release with global positions; the custom close button calls `reject()`. Add a drop shadow only when `QGraphicsDropShadowEffect` is available.

- [ ] **Step 5: Run focused dialog tests**

Run: `python -m unittest tests.test_linear_flow_settings_modal tests.test_provider_form_layout_hotfix`

Expected: dialog structure, single hint, password mode, preset behavior, safe runtime representation, and locale completeness pass.

### Task 3: Refactor CardMakerPanel into a linear create/review layout

**Files:**
- Modify: `ankiforge_ai/ui/card_maker_panel.py`
- Test: `tests/test_linear_flow_settings_modal.py`
- Test: `tests/test_single_screen_card_maker.py`

**Interfaces:**
- Consumes: `BeginnerAIProviderRuntimeSettings | None` from MainDialog.
- Produces:
  - `set_ai_runtime_settings(settings: BeginnerAIProviderRuntimeSettings) -> None`
  - `ai_runtime_settings() -> BeginnerAIProviderRuntimeSettings | None`
  - `clear_ai_runtime_settings() -> None`

- [ ] **Step 1: Replace visible provider widgets with runtime state**

Initialize `self._ai_runtime_settings = None`. `set_ai_runtime_settings` rejects non-settings values, stores only the immutable safe runtime object, calls `session.mark_ai_runtime_settings_changed()`, clears generated state through the existing upstream-change path, and refreshes UI state.

- [ ] **Step 2: Recompose the main columns**

```python
left_layout.addWidget(self._build_create_panel(), 1)
right_layout.addWidget(self._build_review_panel(), 1)
columns.addWidget(left, 45)
columns.addWidget(right, 55)
```

`_build_create_panel()` contains material content, a subtle generation-preference region, status feedback, and the full-width Generate button at the bottom. `_build_review_panel()` contains the generated-card region and compact write footer. It reuses the existing material/generation/cards/write builders or their content layouts without inserting nested section cards.

- [ ] **Step 3: Make the textarea and card list the dominant flexible areas**

Remove the textarea maximum height, keep a practical minimum, and add it with stretch. Allow the card scroll area to grow without the old 280 px maximum. Keep generation settings collapsed and card mode visible.

- [ ] **Step 4: Use accepted settings without changing generation logic**

```python
def _ai_settings_are_ready(self):
    return bool(self.session.material_text.strip() and self._ai_runtime_settings)

def _generate_cards(self):
    if not self._ai_settings_are_ready():
        self._set_generation_message("generation_requirements")
        return
    settings = self._ai_runtime_settings
    # existing generation settings, session transitions, generator call,
    # result handling, rendering, and write-state clearing remain unchanged
```

- [ ] **Step 5: Clear the secret on session discard**

`discard_session()` sets `_ai_runtime_settings = None` before closing the session. It does not serialize or display the previous object.

- [ ] **Step 6: Run focused panel tests**

Run: `python -m unittest tests.test_linear_flow_settings_modal tests.test_single_screen_card_maker tests.test_generation_settings tests.test_ui_copy_hotfix tests.test_ui_rescue_v0_12_2`

Expected: linear layout and existing generation/write safety contracts pass.

### Task 4: Add header orchestration and status

**Files:**
- Modify: `ankiforge_ai/ui/main_dialog.py`
- Modify: `ankiforge_ai/ui/product_i18n.py`
- Test: `tests/test_linear_flow_settings_modal.py`

**Interfaces:**
- Consumes: `AiSettingsDialog` and CardMakerPanel settings accessors.
- Produces: `_open_ai_settings()` and `_refresh_ai_status()`.

- [ ] **Step 1: Add header status and action**

Place `ai_status_label` and `ai_settings_btn` before the language button. Use object names `AiStatusChip` and `AiSettingsButton`. Keep advanced/debug widgets uninserted or permanently hidden.

- [ ] **Step 2: Wire dialog acceptance**

```python
def _open_ai_settings(self):
    dialog = AiSettingsDialog(
        parent=self,
        language=self.ui_language,
        settings=self.card_maker_panel.ai_runtime_settings(),
    )
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return
    self.card_maker_panel.set_ai_runtime_settings(dialog.runtime_settings())
    self._refresh_ai_status()
```

Use the Qt5-compatible accepted constant fallback already used elsewhere in the project when required.

- [ ] **Step 3: Retranslate header status and action**

`toggle_language()` updates `ai_settings_btn` and calls `_refresh_ai_status()`. Configured copy contains the provider name but never model, URL, or API key.

- [ ] **Step 4: Run focused header tests**

Run: `python -m unittest tests.test_linear_flow_settings_modal tests.test_single_screen_card_maker tests.test_product_i18n`

Expected: action/status, language parity, no debug entry, and no main-screen provider copy pass.

### Task 5: Apply the approved product styling and version

**Files:**
- Modify: `ankiforge_ai/ui/product_styles.py`
- Modify: `ankiforge_ai/__init__.py`
- Modify: `ankiforge_ai/manifest.json`
- Modify: `tests/test_product_styles.py`
- Test: `tests/test_linear_flow_settings_modal.py`

**Interfaces:**
- Consumes: object names and roles from Tasks 2–4.
- Produces: one scoped stylesheet covering main dialog, panels, modal, controls, CTAs, focus, status chip, and empty state.

- [ ] **Step 1: Replace old gray/blue tokens**

Ensure the stylesheet contains the approved values `#0D1117`, `#111827`, `#161B22`, `#0F141B`, `#1C2430`, `#263241`, `#334155`, `#F8FAFC`, `#CBD5E1`, `#7D8EA3`, `#7C5CFF`, and `#8B73FF`.

- [ ] **Step 2: Style by stable object names and roles**

Add selectors for `#CreatePanel`, `#ReviewPanel`, `#WriteFooter`, `#AiStatusChip`, `#AiSettingsButton`, `#AiSettingsDialog`, `#AiSettingsSurface`, `#AiSettingsTitleBar`, and primary/secondary roles. Main-screen primary buttons are 44 px; dialog buttons are at least 36 px.

- [ ] **Step 3: Set version to 0.12.5**

Update both runtime and manifest versions and assert equality in tests.

- [ ] **Step 4: Run style/version tests**

Run: `python -m unittest tests.test_product_styles tests.test_linear_flow_settings_modal`

Expected: approved palette, object selectors, focus/hover/disabled states, and version checks pass.

### Task 6: Documentation preview and screenshot acceptance artifacts

**Files:**
- Modify: `docs/ui_linear_flow_settings_modal_v0_12_5.md`
- Create: `docs/ui_preview_v0_12_5.html`
- Create: `docs/screenshots/v0_12_5_linear_flow_zh_default.png`
- Create: `docs/screenshots/v0_12_5_ai_settings_modal.png`
- Create: `docs/screenshots/v0_12_5_ai_configured.png`
- Create: `docs/screenshots/v0_12_5_generation_settings_expanded.png`
- Create: `docs/screenshots/v0_12_5_linear_flow_en_default.png`

**Interfaces:**
- Consumes: implemented copy, layout, and style tokens.
- Produces: static, dependency-free visual evidence matching the PyQt design.

- [ ] **Step 1: Update the design spec for compatible-provider fields**

Document that Base URL and Timeout appear only after choosing `OpenAI-compatible`, preserving current functionality without returning provider configuration to the main screen.

- [ ] **Step 2: Build a static preview with five named states**

The HTML must render Chinese default, modal open, configured status, generation options expanded, and English default. It must not contain a real key; use the placeholder only.

- [ ] **Step 3: Capture the five required PNGs**

Use local headless browser rendering at a consistent desktop viewport. Inspect every image for overlap, clipping, duplicate hint text, debug copy, and main-screen provider fields.

### Task 7: Full verification, deterministic package, audit, and final commit

**Files:**
- Modify: any UI tests whose old source-level expectations conflict with the approved structure.
- Package: `dist/ankiforge_ai.ankiaddon`

**Interfaces:**
- Consumes: complete PR23 tree.
- Produces: verified local package and one clean PR23 commit.

- [ ] **Step 1: Run the full suite**

Run: `python -m unittest discover`

Expected: all tests pass; record the exact count.

- [ ] **Step 2: Compile and check whitespace**

Run: `python -m compileall .` and `git diff --check`.

Expected: both exit 0.

- [ ] **Step 3: Build twice and compare**

Run `python scripts/build_ankiaddon.py`, hash `dist/ankiforge_ai.ankiaddon`, repeat, and assert equal SHA-256 and size.

- [ ] **Step 4: Inspect the archive and repository**

Require forbidden files = 0, no `config.json`, `.env`, backup, tests, docs, pycache, pyc, logs, `.anki2`, `.apkg`, collection data, or high-confidence real secret in the package. Classify test fake keys separately from real credentials.

- [ ] **Step 5: Amend the design commit into the final PR23 commit**

Stage only PR23 files and run:

```bash
git commit --amend -m "Move AI provider settings into session dialog"
```

Verify branch, commit, and clean status. Push only `v0.12.5-pr23-linear-flow-settings-modal` to `public` if all checks pass. Do not merge or push `main`.
