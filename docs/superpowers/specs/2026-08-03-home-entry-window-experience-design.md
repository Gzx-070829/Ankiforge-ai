# AnkiForge AI Home Entry and Window Experience Design

## Context

AnkiForge AI currently registers one action under Anki's **Tools** menu and
opens the workbench with `QDialog.exec()`. This makes a frequent workflow feel
buried and gives the window modal-dialog behavior even though users treat it as
a reusable workbench.

This change improves access and window behavior only. It does not change AI
providers, generation, review, duplicate checking, or Anki writes.

## Goals

- Put one compact AnkiForge AI entry on Anki's deck-browser home screen.
- Keep the existing Tools menu entry as a dependable fallback.
- Give the menu action an application shortcut: `Ctrl+Alt+F`.
- Keep at most one workbench window alive.
- Reopening an existing workbench restores, raises, and activates it.
- Give the workbench standard minimize, maximize, restore, and close controls.
- Remember only window geometry and maximized state between launches.
- Preserve the existing Create → Review → Write layout and session-only key
  policy.

## Non-goals

- No toolbar icon, floating button, tray icon, or startup auto-open.
- No entry inside the reviewer, editor, browser, or preferences screens.
- No redesign of the workbench contents.
- No persistence of API keys, study material, generated cards, review state,
  source paths, or write history.
- No Provider calls, Anki writes, or collection access from the launcher.

## Approaches Considered

### 1. Shortcut only

Lowest compatibility risk, but discoverability remains poor and mouse-first
users still have to learn an invisible command.

### 2. Deck-browser button only

Easy to discover, but keyboard users gain nothing and an already-open window
still needs explicit activation behavior.

### 3. Deck-browser button, shortcut, and single-instance modeless window

Recommended. It provides a visible primary entry, a fast expert path, and
workbench-like window behavior without adding controls to the core workflow.

## Selected Design

### Entry points

A small entry-point module owns registration and guards against duplicate hook
or action registration during add-on reloads.

- The Tools action remains labelled `AnkiForge AI`.
- The same action carries `Ctrl+Alt+F`.
- An official Anki deck-browser rendering hook adds one compact,
  theme-compatible `AnkiForge AI` link/button to the home screen.
- An official webview message hook routes only the add-on's namespaced launch
  message to the same open function.
- Other webview messages are returned untouched.

If a future Anki version does not expose the expected deck-browser hook, the
add-on still loads and the Tools action plus shortcut remain available.

### Window lifecycle

The public workbench remains a `QDialog`, but it is displayed modelessly with
`show()` instead of nested `exec()`.

- First activation constructs and shows `MainDialog`.
- Later activations call `showNormal()` when minimized, then `raise_()` and
  `activateWindow()`.
- The dialog uses normal top-level window flags with minimize, maximize, and
  close controls.
- Closing still calls the existing idempotent session teardown, clearing the
  API key and transient workflow data.
- Qt deletion clears the module-level singleton reference, allowing a fresh
  workbench to be opened later.

### Window-state persistence

Window state uses a separate, narrowly-scoped adapter under the add-on's
preserved `user_files` directory. It stores only:

- a bounded base64-encoded Qt geometry value;
- whether the window was maximized.

The adapter rejects unknown keys, malformed values, oversized files, symlinks,
and secret-shaped data. Invalid or off-screen geometry falls back to the
current 1200 × 840 default; Qt's restore behavior and an available-screen check
prevent an inaccessible window after monitor changes.

The existing `preferences.json` schema is not expanded, keeping generation
preferences independent from operating-system window state.

### Focus and accessibility

- A newly opened workbench places keyboard focus in the study-material editor.
- Existing accessible button text remains unchanged.
- The home entry is concise in Chinese and English and inherits Anki theme
  colors instead of shipping a separate visual panel.
- The shortcut is visible in the Tools menu through the native QAction.

## Failure Handling

- Home-entry hook incompatibility must not block add-on startup.
- A malformed window-state file is ignored; it never blocks the workbench.
- Failure to save geometry is silent because it is a non-critical convenience.
- Repeated registration and repeated activation remain idempotent.
- Session teardown remains idempotent even if Qt emits multiple close/destroy
  paths.

## Testing

Test-first coverage will verify:

- first activation creates and shows exactly one modeless window;
- repeat activation restores and focuses the existing window;
- close/destruction clears the singleton and tears down sensitive session data;
- Tools registration is not duplicated and carries the shortcut;
- deck-browser content receives one launcher and other contexts do not;
- only the namespaced webview command is handled;
- window state accepts valid geometry but rejects unknown, malformed,
  oversized, symlinked, or secret-shaped content;
- `MainDialog` requests standard window controls, restores/saves geometry, and
  focuses the material editor;
- the complete unit suite, `compileall`, package build, reproducibility check,
  forbidden-file inspection, and `git diff --check` pass.

## Manual Anki Acceptance

On the supported Anki release and on both light and dark themes:

1. Confirm the deck-browser home entry is visible but unobtrusive.
2. Open it, minimize it, and invoke the entry again; the same window returns.
3. Invoke `Ctrl+Alt+F` and the Tools action; neither creates a duplicate.
4. Resize, maximize, close, and reopen; the window returns accessibly.
5. Move between monitors and verify the window cannot reopen off-screen.
6. Close with an API key entered and reopen; the key must be empty.
7. Confirm reviewer, Browser, and editor surfaces receive no new launcher.
