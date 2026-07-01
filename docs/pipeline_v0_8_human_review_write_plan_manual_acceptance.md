# AnkiForge AI v0.8 Human Review and Write Plan Manual Acceptance

## 1. Purpose

This procedure verifies the complete v0.8 local Human Review and write-planning
preview chain in Anki. It must not save review state, run duplicate checking,
call a provider or writer, access a real collection, or write a note.

Do not enter a credential, click a legacy write action, or start a real-provider
or writer harness during this acceptance run.

## 2. Test Record

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

- [ ] Full unit tests, `compileall`, and `git diff --check` pass.
- [ ] Anki was closed before any separately authorized runtime-file sync.
- [ ] The local add-on `config.json` was neither copied nor overwritten.
- [ ] Its before/after SHA-256 values match.
- [ ] `addons21` contains one `ankiforge_ai` directory.
- [ ] The rollback backup exists under `Anki2/addon_backups`.
- [ ] Network and collection changes can be independently observed.

## 4. Add-on and Main Window

1. Start Anki normally.
2. Open the Tools menu.
3. Confirm exactly one `AnkiForge AI` item exists.
4. Open the main dialog.

Acceptance:

- [ ] Only one add-on/menu entry is present.
- [ ] The main window opens without an exception.
- [ ] Legacy settings and the candidate table remain operational.
- [ ] Merely opening the UI creates no note and changes no collection data.

## 5. PR1 Human Review Decision Draft

1. Open the Human Review decision draft entry.
2. Inspect the empty state and candidate/Quality Gate summary.
3. Exercise `pending`, `rejected`, and `needs_edit`.
4. Exercise `approved` with each relevant Quality Gate status.
5. Enter a non-sensitive reviewer note.

Acceptance:

- [ ] The entry and dialog open normally.
- [ ] Empty, candidate, and Quality Gate states are understandable.
- [ ] `pending`, `rejected`, and `needs_edit` produce local draft states.
- [ ] `failed`, `unchecked`, or error quality cannot form a valid approved
      draft.
- [ ] `warning` and `passed` quality can form a valid approved draft.
- [ ] The reviewer note remains local to the dialog.
- [ ] Approved is explicitly not write authorization.

## 6. PR2 Local HumanReview Preview

1. Select a candidate and decision.
2. Generate the local HumanReview preview.
3. Change the decision, reviewer note, and selected candidate.

Acceptance:

- [ ] The preview shows the local decision, note summary, and quality state.
- [ ] It says no formal HumanReview or write authorization is created.
- [ ] Changing an upstream input clears the old preview.
- [ ] No draft or preview survives closing and reopening the dialog.

## 7. PR3 Write Eligibility Summary

Generate Write Eligibility for representative decisions and quality states.

Acceptance:

- [ ] `eligible`, `blocked`, `needs_review`, and `unknown` display reasonably.
- [ ] Blocking reasons match the decision and Quality Gate state.
- [ ] Eligibility is explicitly not write authorization.
- [ ] No Write Plan, `GeneratedCard`, or `WriteReadyPreviewItem` is created.
- [ ] Changing candidate, decision, note, or local review clears stale
      eligibility and downstream previews.

## 8. PR4 Read-Only Write Plan

Generate a read-only Write Plan preview for ready, blocked, needs-review, and
unknown eligibility states.

Acceptance:

- [ ] Status is `ready_preview`, `blocked`, `needs_review`, or `unknown` as
      appropriate.
- [ ] Fixed mappings show Front→Front, Back→Back, and Source→Source.
- [ ] Tags show `AnkiForgeAI`, `pipeline-preview`, and `human-reviewed`.
- [ ] Note type and deck say they are not bound to real Anki targets.
- [ ] Duplicate check is shown as unexecuted.
- [ ] The preview is explicitly not a real or executable Write Plan.
- [ ] It grants no write authorization and calls no writer.
- [ ] Changing any upstream state clears the old Write Plan preview.

## 9. PR5 Duplicate Readiness and Final Confirmation

Generate the final-confirmation contract preview from each Write Plan status.

Acceptance:

- [ ] `ready_preview` maps to `ready_for_future_confirmation`.
- [ ] Blocked, needs-review, and unknown states remain appropriately bounded.
- [ ] Duplicate check status is `not_run`.
- [ ] Duplicate check requirement is `required_before_write`.
- [ ] Duplicate result is `unknown`.
- [ ] Final confirmation is `not_requested`.
- [ ] Write authorization is `not_granted`.
- [ ] Write execution is `will_not_execute`.
- [ ] Required future steps are explanatory and do not execute anything.
- [ ] The preview says it is not user confirmation or write authorization.
- [ ] Changing candidate, decision, note, local review, eligibility, or Write
      Plan clears the old final-confirmation preview.

## 10. Dialog Layout and Lifetime

1. Inspect the dialog on a common-height display.
2. Scroll from the first summary to the final-confirmation section.
3. Confirm every command row remains usable.
4. Close and reopen the dialog.

Acceptance:

- [ ] The dialog stays within the available screen.
- [ ] The content area scrolls.
- [ ] Bottom buttons remain outside the scroll area, visible, and clickable.
- [ ] Closing discards the draft and every downstream preview.

## 11. Forbidden Control Audit

Confirm there is no control for:

- [ ] API key or credential input;
- [ ] save or apply;
- [ ] provider invocation or network send;
- [ ] real duplicate-check execution;
- [ ] create `GeneratedCard` or `WriteReadyPreviewItem`;
- [ ] confirm write or approve-and-write;
- [ ] execute a Write Plan;
- [ ] add or write a note to Anki; or
- [ ] access or bind a real Anki collection.

Buttons containing “不写入” are preview-only commands and must not call a
write path.

## 12. No-Side-Effect Verification

Before closing Anki, confirm:

- [ ] no new note was created;
- [ ] no existing note was changed;
- [ ] no deck or note type was changed;
- [ ] no duplicate check was executed;
- [ ] no collection content was read by this preview flow;
- [ ] no writer was called;
- [ ] no provider invocation occurred;
- [ ] no network activity from the add-on occurred;
- [ ] `self.cards` and the legacy candidate flow were not modified;
- [ ] local `config.json` remains unchanged; and
- [ ] the add-on backup remains intact.

Any failure is a v0.8 release blocker. Preserve the repository, local config,
and backup state, record the exact failing step, and do not infer permission to
repair or enable a real write path.
