# Home Entry and Window Experience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make AnkiForge AI directly accessible from Anki's deck-browser home screen and keyboard while turning the main dialog into a safe, single-instance, modeless workbench with remembered window state.

**Architecture:** Keep Anki integration in a small entry-point module, keep singleton ownership in the add-on root, and store only strictly validated geometry in a dedicated `user_files` adapter. `MainDialog` remains responsible for its visual window flags, focus, restore, save, and existing session teardown.

**Tech Stack:** Python 3.10+, Anki `aqt.gui_hooks`, Qt 6 via `aqt.qt`, `unittest`, deterministic `.ankiaddon` packaging.

## Global Constraints

- Preserve the existing Create → Review → Write workflow and layout.
- Do not change Provider, generation, review, duplicate-check, or Anki-write behavior.
- Do not persist API keys, study material, generated cards, review state, source paths, or write history.
- Show the home launcher only on Anki's deck-browser screen.
- Keep the Tools action and use `Ctrl+Alt+F` as its shortcut.
- Home-hook incompatibility must not prevent add-on startup.
- Do not start Anki, call a Provider, or write to a real collection during automated verification.

---

## File Structure

- Create `ankiforge_ai/workbench/window_state.py`: immutable, strictly validated window-state value.
- Create `ankiforge_ai/ui/window_state_adapter.py`: bounded atomic persistence in `user_files/window_state.json`.
- Create `ankiforge_ai/ui/window_experience.py`: Qt-agnostic orchestration helpers for flags and geometry.
- Create `ankiforge_ai/ui/anki_entrypoints.py`: pure HTML/message helpers plus idempotent Anki hook registration.
- Modify `ankiforge_ai/__init__.py`: modeless singleton orchestration and entry-point registration.
- Modify `ankiforge_ai/ui/main_dialog.py`: standard window flags, state restore/save, initial focus.
- Modify `docs/manual_anki_acceptance.md`: real-Anki launcher/window acceptance steps.
- Create focused tests for each boundary and update the lifecycle regression tests.

### Task 1: Strict Window-State Value and Adapter

**Files:**
- Create: `ankiforge_ai/workbench/window_state.py`
- Create: `ankiforge_ai/ui/window_state_adapter.py`
- Create: `tests/test_window_state.py`
- Create: `tests/test_window_state_adapter.py`
- Modify: `tests/test_build_ankiaddon.py`

**Interfaces:**
- Produces: `WorkbenchWindowState(geometry: str = "", maximized: bool = False)`.
- Produces: `WorkbenchWindowState.from_mapping(value)` and `.to_safe_dict()`.
- Produces: `WindowStateAdapter.load() -> WorkbenchWindowState` and `.save(state) -> None`.

- [ ] **Step 1: Write failing value-object tests**

```python
def test_round_trip_accepts_bounded_base64_geometry(self):
    state = WorkbenchWindowState(geometry="AQIDBA==", maximized=True)
    self.assertEqual(
        WorkbenchWindowState.from_mapping(state.to_safe_dict()),
        state,
    )

def test_rejects_unknown_keys_and_secret_shaped_geometry(self):
    with self.assertRaises(ValueError):
        WorkbenchWindowState.from_mapping(
            {"geometry": "AQIDBA==", "maximized": False, "api_key": "x"}
        )
    with self.assertRaises(ValueError):
        WorkbenchWindowState(geometry="sk-abcdefghijklmnopqrstuvwxyz", maximized=False)
```

- [ ] **Step 2: Run `python -m unittest tests.test_window_state -v` and confirm import failure because the value does not exist**

- [ ] **Step 3: Implement the immutable allowlisted value**

```python
@dataclass(frozen=True)
class WorkbenchWindowState:
    geometry: str = ""
    maximized: bool = False

    def __post_init__(self):
        if not isinstance(self.maximized, bool):
            raise ValueError("maximized must be bool")
        if not isinstance(self.geometry, str) or len(self.geometry) > 8192:
            raise ValueError("geometry must be bounded text")
        if self.geometry:
            decoded = base64.b64decode(self.geometry, validate=True)
            if base64.b64encode(decoded).decode("ascii") != self.geometry:
                raise ValueError("geometry must be canonical base64")
```

- [ ] **Step 4: Run the value tests and confirm they pass**

- [ ] **Step 5: Write failing adapter tests for default, atomic round-trip, malformed input, oversized input, and symlinks**

```python
def test_round_trip_uses_only_user_files_window_state_json(self):
    path = Path(directory) / "user_files" / "window_state.json"
    adapter = WindowStateAdapter(path)
    state = WorkbenchWindowState(geometry="AQIDBA==", maximized=True)
    adapter.save(state)
    self.assertEqual(adapter.load(), state)
```

- [ ] **Step 6: Run `python -m unittest tests.test_window_state_adapter -v` and confirm the missing adapter failure**

- [ ] **Step 7: Implement bounded atomic JSON persistence mirroring the existing preferences adapter**

```python
class WindowStateAdapter:
    def load(self) -> WorkbenchWindowState:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return WorkbenchWindowState.from_mapping(payload)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError):
            return WorkbenchWindowState()

    def save(self, state: WorkbenchWindowState) -> None:
        content = json.dumps(state.to_safe_dict(), sort_keys=True).encode("utf-8")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(".window_state.json.tmp")
        temporary.write_bytes(content)
        os.replace(str(temporary), str(self.path))
```

- [ ] **Step 8: Add `user_files/window_state.json` and its temporary file to package exclusions, then run both focused suites**

- [ ] **Step 9: Commit**

```powershell
git add ankiforge_ai/workbench/window_state.py ankiforge_ai/ui/window_state_adapter.py tests/test_window_state.py tests/test_window_state_adapter.py tests/test_build_ankiaddon.py
git commit -m "Add safe workbench window state persistence"
```

### Task 2: Modeless Single-Instance Workbench

**Files:**
- Modify: `ankiforge_ai/__init__.py`
- Modify: `tests/test_pr26_release_metadata_and_lifecycle.py`
- Create: `tests/test_workbench_window_controller.py`

**Interfaces:**
- Produces: `_show_main_dialog(parent, dialog_factory) -> object`.
- Produces: `_clear_main_dialog(dialog) -> None` used by Qt destruction callback.

- [ ] **Step 1: Write failing behavioral tests using a complete fake dialog**

```python
def test_first_open_shows_modeless_dialog_and_retains_singleton(self):
    dialog = FakeDialog()
    returned = ankiforge_ai._show_main_dialog(object(), lambda _parent: dialog)
    self.assertIs(returned, dialog)
    self.assertEqual(dialog.events, ["show", "raise", "activate"])
    self.assertIs(ankiforge_ai._dialog_instance, dialog)

def test_repeat_open_restores_and_focuses_existing_dialog(self):
    dialog = FakeDialog(minimized=True)
    ankiforge_ai._dialog_instance = dialog
    returned = ankiforge_ai._show_main_dialog(object(), fail_if_called)
    self.assertIs(returned, dialog)
    self.assertEqual(dialog.events, ["showNormal", "raise", "activate"])
```

- [ ] **Step 2: Run `python -m unittest tests.test_workbench_window_controller -v` and confirm `_show_main_dialog` is missing**

- [ ] **Step 3: Replace the modal `_open_main_dialog` path with modeless singleton activation and destroyed-signal cleanup**

```python
def _show_main_dialog(parent, dialog_factory):
    global _dialog_instance
    dialog = _dialog_instance
    if dialog is None:
        dialog = dialog_factory(parent)
        _dialog_instance = dialog
        dialog.destroyed.connect(lambda *_: _clear_main_dialog(dialog))
        dialog.show()
    elif dialog.isMinimized():
        dialog.showNormal()
    dialog.raise_()
    dialog.activateWindow()
    return dialog
```

- [ ] **Step 4: Update former modal lifecycle tests to assert close/destruction teardown ownership, then run both lifecycle suites**

- [ ] **Step 5: Commit**

```powershell
git add ankiforge_ai/__init__.py tests/test_pr26_release_metadata_and_lifecycle.py tests/test_workbench_window_controller.py
git commit -m "Open the workbench as a single modeless window"
```

### Task 3: Native Tools Shortcut and Deck-Browser Home Entry

**Files:**
- Create: `ankiforge_ai/ui/anki_entrypoints.py`
- Modify: `ankiforge_ai/__init__.py`
- Create: `tests/test_anki_entrypoints.py`
- Modify: `tests/test_pr26_release_metadata_and_lifecycle.py`

**Interfaces:**
- Produces: `HOME_COMMAND = "ankiforge-ai:open"`.
- Produces: `append_deck_browser_launcher(content, deck_browser) -> None`.
- Produces: `handle_webview_message(handled, message, context, open_workbench)` returning Anki's `(handled, result)` tuple.
- Produces: `register_home_entry(gui_hooks, open_workbench) -> bool`.

- [ ] **Step 1: Write failing tests for one launcher, namespaced message handling, untouched foreign messages, and idempotent registration**

```python
def test_deck_browser_launcher_is_added_once(self):
    content = types.SimpleNamespace(top_links="")
    append_deck_browser_launcher(content, object())
    append_deck_browser_launcher(content, object())
    self.assertEqual(content.top_links.count(HOME_COMMAND), 1)

def test_only_namespaced_message_opens_workbench(self):
    opened = []
    result = handle_webview_message(
        (False, None), HOME_COMMAND, object(), lambda: opened.append(True)
    )
    self.assertEqual(result, (True, None))
    self.assertEqual(opened, [True])
```

- [ ] **Step 2: Run `python -m unittest tests.test_anki_entrypoints -v` and confirm the module is missing**

- [ ] **Step 3: Implement pure escaped launcher markup and hook registration using official `deck_browser_will_render_content` and `webview_did_receive_js_message` hooks**

- [ ] **Step 4: Add `Ctrl+Alt+F` to the existing Tools QAction and register home hooks without making startup depend on them**

- [ ] **Step 5: Run entry-point and lifecycle suites and confirm one menu action and one set of hooks**

- [ ] **Step 6: Commit**

```powershell
git add ankiforge_ai/ui/anki_entrypoints.py ankiforge_ai/__init__.py tests/test_anki_entrypoints.py tests/test_pr26_release_metadata_and_lifecycle.py
git commit -m "Add an Anki home launcher and keyboard shortcut"
```

### Task 4: Standard Window Controls, Geometry Restore, and Initial Focus

**Files:**
- Create: `ankiforge_ai/ui/window_experience.py`
- Modify: `ankiforge_ai/ui/main_dialog.py`
- Create: `tests/test_window_experience.py`
- Create: `tests/test_main_dialog_window_experience.py`

**Interfaces:**
- `MainDialog(parent=None, provider_preview=None, preferences_adapter=None, window_state_adapter=None)` accepts an injected `WindowStateAdapter`.
- `apply_standard_window_flags(dialog, window_type) -> None` applies the four native window-control flags.
- `restore_window_geometry(dialog, state, byte_array_type) -> bool` restores decoded geometry and maximized state.
- `capture_window_state(dialog) -> WorkbenchWindowState` returns only encoded geometry and maximized state.
- `_restore_window_state() -> None` decodes and applies valid geometry.
- `_save_window_state() -> None` stores only geometry and maximized state.

- [ ] **Step 1: Write failing behavioral tests around the Qt-agnostic window helpers**

```python
def test_standard_controls_are_applied(self):
    dialog = RecordingWindow()
    apply_standard_window_flags(dialog, FakeWindowType)
    self.assertEqual(
        dialog.enabled_flags,
        [1, 2, 4, 8, 16],
    )

def test_capture_round_trips_only_geometry_and_maximized_state(self):
    state = capture_window_state(RecordingWindow(geometry=b"geometry", maximized=True))
    self.assertEqual(state.geometry, "Z2VvbWV0cnk=")
    self.assertTrue(state.maximized)
```

- [ ] **Step 2: Run `python -m unittest tests.test_window_experience -v` and confirm the helper module is missing**

- [ ] **Step 3: Add top-level standard window flags, restore state after UI construction, and use a zero-delay focus request for the material editor**

- [ ] **Step 4: Save state before existing idempotent teardown in `closeEvent`; ignore adapter and restore failures**

- [ ] **Step 5: Add a narrow `MainDialog` integration contract test for helper calls and initial focus, then run both focused suites plus existing dialog tests**

- [ ] **Step 6: Commit**

```powershell
git add ankiforge_ai/ui/window_experience.py ankiforge_ai/ui/main_dialog.py tests/test_window_experience.py tests/test_main_dialog_window_experience.py
git commit -m "Polish workbench window controls and state"
```

### Task 5: Documentation and Release-Candidate Verification

**Files:**
- Modify: `docs/manual_anki_acceptance.md`

**Interfaces:**
- No new runtime interface.

- [ ] **Step 1: Add manual acceptance cases for home visibility, light/dark themes, shortcut, singleton restore, monitor changes, geometry restore, and API-key clearing**

- [ ] **Step 2: Run the complete suite**

```powershell
python -m unittest discover
python -m compileall .
git diff --check
```

- [ ] **Step 3: Build twice and compare SHA-256 values**

```powershell
python scripts/build_ankiaddon.py
Get-FileHash dist/ankiforge_ai.ankiaddon -Algorithm SHA256
python scripts/build_ankiaddon.py
Get-FileHash dist/ankiforge_ai.ankiaddon -Algorithm SHA256
```

- [ ] **Step 4: Inspect the archive and confirm forbidden files, config, backups, Anki user data, and high-confidence secrets are absent**

- [ ] **Step 5: Verify `git status --short` and commit the acceptance documentation plus the refreshed tracked package**

```powershell
git add docs/manual_anki_acceptance.md dist/ankiforge_ai.ankiaddon
git commit -m "Prepare home entry experience candidate"
```
