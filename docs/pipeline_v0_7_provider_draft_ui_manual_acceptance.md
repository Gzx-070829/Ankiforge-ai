# AnkiForge AI v0.7 Provider Draft UI Manual Acceptance

## 1. Purpose

This procedure verifies the complete v0.7 provider draft UI in Anki without
saving a new-pipeline profile, entering a credential, sending material, calling
a provider, generating cards, or writing an Anki note.

Do not enter a real or test API key. Do not select an action that writes notes.
Do not start the developer-only real-provider harness.

## 2. Test Record

Record the environment before acceptance:

```text
Date:
Tester:
Repository branch:
Repository commit:
Anki version:
Operating system:
Add-on directory:
Backup directory:
config.json SHA-256 before:
config.json SHA-256 after:
Result: PASS / FAIL
Notes:
```

## 3. Preconditions

- [ ] The repository worktree contains only the intended release candidate.
- [ ] The required automatic tests, `compileall`, and whitespace check pass.
- [ ] Anki is fully closed before runtime files are synchronized.
- [ ] Only required runtime files are copied; tests and docs are not installed
      as add-on runtime files.
- [ ] The existing local `config.json` is neither replaced nor deleted.
- [ ] Its SHA-256 is recorded before and after sync and remains unchanged.
- [ ] `addons21` contains only one AnkiForge AI directory named
      `ankiforge_ai`.
- [ ] The rollback backup exists under `Anki2/addon_backups`, not `addons21`.
- [ ] Network access is disabled or independently observed so an unexpected
      request would be visible.

## 4. Add-on and Main Window

1. Start Anki normally.
2. Open the Tools menu.
3. Confirm exactly one `AnkiForge AI` menu item exists.
4. Open it and confirm the main dialog appears without an exception.

Acceptance:

- [ ] There is one add-on/menu entry, not a duplicate loaded from a backup.
- [ ] The main window opens and legacy provider settings remain present.
- [ ] The candidate table remains present and unchanged.
- [ ] No note or collection change occurs merely by opening the window.

## 5. PR1 Read-Only Preview

1. Select `新 Pipeline Provider 只读预览`.
2. Confirm the normal, non-injected path shows the safe empty state.
3. Inspect the available commands.
4. Close the dialog.

Acceptance:

- [ ] The entry and dialog title clearly identify the new pipeline preview.
- [ ] The empty state does not infer values from legacy settings.
- [ ] Target stage and fixed no-card/no-Anki-write boundaries are visible.
- [ ] The only command is close.
- [ ] No key, consent, save, send, run, approve, generation, or write command
      exists.

## 6. PR2 Local Draft Editor

1. Select `新 Pipeline Provider 本地草稿预览`.
2. Confirm provider, model, base URL, and privacy notice start blank.
3. Confirm target stage is fixed at `knowledge_point_extraction`.
4. Enter a valid, non-sensitive local test draft using an HTTP or HTTPS URL.
5. Select `更新本地预览（仅本地）`.

Acceptance:

- [ ] Only the four allowed non-sensitive fields are editable.
- [ ] No legacy provider, model, base URL, or API key is prefilled.
- [ ] The update action changes only the open dialog's local preview.
- [ ] Current-state text says no save, no key input, no send, no provider call,
      no source/Anki read, no consent creation, no card generation, and no Anki
      write.

## 7. Local URL Validation

1. Enter `ftp://example.com` and update the preview.
2. Enter `https://user:pass@example.com` and update the preview.
3. Restore a valid HTTP or HTTPS URL.

Acceptance:

- [ ] The non-HTTP(S) URL produces a local validation error.
- [ ] The embedded username/password produces a local validation error.
- [ ] Rejected values are not echoed in diagnostic-style output.
- [ ] Invalid drafts show neither provider summary rows nor future-send
      disclosure.
- [ ] No provider or network request occurs during validation.

## 8. PR3 Safety Summary

With a complete valid draft, update the local preview and confirm:

- [ ] `Provider 安全信息` shows Provider, Model, Base URL, Privacy notice, and
      Target stage.
- [ ] `草稿安全状态` says the source is a local draft.
- [ ] Activation status is `未激活`.
- [ ] Provider verification is `未执行`.
- [ ] Consent is inapplicable because the draft is inactive.
- [ ] Save, send, provider call, card generation, and Anki write remain `否`.
- [ ] The UI says format validity is not provider verification.
- [ ] The UI says the safety summary is not a runtime preview.
- [ ] The UI says the local draft is not saved configuration.
- [ ] No credential, key-presence, secret-presence, provider-ready, or runtime-
      readiness state is displayed.

## 9. PR4 Future Send Disclosure

With the same valid draft, inspect
`未来发送披露（仅说明，不授权）`.

Acceptance:

- [ ] The current section says the operation is local preview only.
- [ ] It says the current action does not save settings, accept a key, send
      material, call a provider, read source/Anki content, create consent,
      generate cards, or write Anki.
- [ ] The future section identifies the recipient as the provider/Base URL
      shown above.
- [ ] It limits future content to a short preview explicitly selected by the
      user.
- [ ] It says explicit agreement must be requested again before sending.
- [ ] It says the disclosure is not consent or execution authorization.
- [ ] It says the provider is not thereby verified, activated, or runnable.
- [ ] Target stage remains `knowledge_point_extraction`.

## 10. Scroll and Fixed Buttons

1. Use a common-height display or reduce the available window height.
2. Open a valid draft so all PR2, PR3, and PR4 sections are visible.
3. Scroll from the top to the bottom of the middle content area.

Acceptance:

- [ ] The dialog remains within the available screen height.
- [ ] The middle form, summary, safety, and disclosure content scrolls.
- [ ] The top safety notice remains outside the scroll area.
- [ ] `更新本地预览（仅本地）` remains visible and clickable.
- [ ] `关闭` remains visible and clickable.
- [ ] Content height cannot push either button off-screen.

## 11. Forbidden Control Audit

Confirm there is no control that accepts or performs:

- [ ] API key or credential input;
- [ ] save, apply, or enable;
- [ ] consent, agree, or authorize;
- [ ] send, run, or provider verification;
- [ ] approve or card generation; or
- [ ] write/add note to Anki.

The permitted commands remain local preview update and close only.

## 12. Draft Lifetime and Regression

1. Enter a distinctive non-sensitive draft and update it.
2. Close the local draft dialog.
3. Reopen it through the normal entry.
4. Reinspect legacy settings and the candidate table.

Acceptance:

- [ ] The reopened draft is blank.
- [ ] The prior safety summary and disclosure are gone.
- [ ] Legacy settings retain their pre-existing behavior.
- [ ] The candidate table and `self.cards` behavior show no regression.
- [ ] The local add-on `config.json` remains unchanged.

## 13. No-Side-Effect Verification

Before closing Anki, confirm:

- [ ] no new note was created;
- [ ] no existing note was changed;
- [ ] no note type was changed;
- [ ] no provider invocation was observed;
- [ ] no network activity from the add-on was observed;
- [ ] no source document, clipboard, card, or collection content was read by
      the local draft flow;
- [ ] no consent record or provider runtime configuration was created; and
- [ ] the add-on backup remains intact.

Any failure is a v0.7 release blocker. Stop, preserve the repository and backup
state, and document the exact failing step before changing code.
