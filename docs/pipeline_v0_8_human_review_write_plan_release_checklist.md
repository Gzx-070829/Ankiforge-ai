# AnkiForge AI v0.8 Human Review and Write Plan Release Checklist

## 1. Purpose

This checklist closes the v0.8 local Human Review and write-planning preview
chain delivered by PR1 through PR5. Every capability in this release is an
in-memory UI draft, read-only summary, or explanatory contract.

Passing this checklist does not authorize a real duplicate check, writer call,
or Anki note mutation. v0.8 contains no real-writer PR.

## 2. Delivered Capability

- PR1 adds the local Human Review decision draft UI for `pending`, `approved`,
  `rejected`, and `needs_edit` decisions, with Quality Gate approval gating.
- PR2 adapts a valid decision draft into a local `HumanReview` preview without
  constructing or saving a formal review object.
- PR3 derives a read-only Write Eligibility summary. Eligibility describes a
  local condition; it is not write authorization.
- PR4 derives a read-only Write Plan preview with fixed field mapping, tags,
  and explicitly unbound note-type/deck targets. It is not a real Write Plan.
- PR5 derives duplicate-check readiness and a final-confirmation contract
  preview. It neither checks duplicates nor requests user confirmation.

The PR5 baseline is 575 passing unit tests, successful `compileall`, and a
successful Git whitespace check.

## 3. Final v0.8 Safety Boundary

Confirm that the complete v0.8 flow:

- [ ] does not call a provider;
- [ ] does not access the network;
- [ ] does not accept an API key;
- [ ] does not save a review decision or reviewer note;
- [ ] does not save a Write Plan or final-confirmation preview;
- [ ] does not generate a formal `GeneratedCard`;
- [ ] does not generate a `WriteReadyPreviewItem`;
- [ ] does not execute duplicate checking;
- [ ] does not access an Anki collection, deck, note type, or note data;
- [ ] does not create or update a note;
- [ ] does not call a writer;
- [ ] does not write to Anki;
- [ ] does not modify legacy `self.cards`; and
- [ ] discards all drafts and previews when the dialog closes.

## 4. Meaning Boundaries

Each statement below is a release invariant:

- [ ] `approved` means only a local review-draft decision; it is not write
      authorization.
- [ ] Write Eligibility means only a local read-only eligibility summary; it
      is not write authorization.
- [ ] `ready_preview` means only that a read-only mapping preview can be shown;
      it is not a real or executable Write Plan.
- [ ] `ready_for_future_confirmation` means only that future gates can be
      explained; it is not user confirmation.
- [ ] The final-confirmation preview is not consent, final confirmation, or
      authorization.
- [ ] `not_run`, `unknown`, `not_requested`, `not_granted`, and
      `will_not_execute` remain explicit in the PR5 preview.

## 5. UI and Regression Checklist

- [ ] Anki shows exactly one AnkiForge AI menu entry.
- [ ] The main window and Human Review draft entry open normally.
- [ ] PR1 decision and Quality Gate behavior is correct.
- [ ] PR2 local HumanReview preview is correct.
- [ ] PR3 Write Eligibility status and reasons are correct.
- [ ] PR4 fixed field mappings, tags, and unbound targets are correct.
- [ ] PR5 duplicate readiness and final-confirmation contract are correct.
- [ ] Changing candidate, decision, note, or any upstream preview clears all
      stale downstream previews.
- [ ] The dialog remains screen-bounded and scrollable.
- [ ] Bottom command rows remain visible and clickable.
- [ ] No save, apply, execute, duplicate-check, confirm-write,
      approve-and-write, provider, generation, or Anki-write control exists.
- [ ] Opening and closing the flow creates no note and changes no collection.

The detailed procedure is in
`docs/pipeline_v0_8_human_review_write_plan_manual_acceptance.md`.

## 6. Repository and Configuration Safety

- [ ] `ankiforge_ai/config.json` is not tracked by Git.
- [ ] `.gitignore` continues to exclude local configuration, environment
      files, Python cache files, Anki databases/packages, `addons21`, and
      `addon_backups`.
- [ ] `ankiforge_ai/config.example.json` remains tracked and contains only a
      sanitized template with an empty `api_key`.
- [ ] No local `.env`, Anki database, `.apkg`, add-on backup, or local
      `config.json` is staged.
- [ ] The add-on `config.json` is not copied, replaced, deleted, or modified.
- [ ] Its SHA-256 remains unchanged across any explicitly authorized runtime
      sync.
- [ ] The add-on backup remains under `Anki2/addon_backups`, outside
      `addons21`.
- [ ] `addons21` contains only one AnkiForge AI directory named
      `ankiforge_ai`.

## 7. Automatic Verification

Run from the repository root on the exact release candidate:

```bash
python -m unittest discover -s tests
python -m compileall .
git diff --check
git status --short
```

- [ ] The full offline unit-test suite passes.
- [ ] `compileall` passes.
- [ ] `git diff --check` passes.
- [ ] The worktree is clean after the local merge.
- [ ] Tests invoke no provider, network, writer, duplicate checker, or Anki
      collection.
- [ ] Tests contain no real credential or user Anki data.

## 8. Manual Acceptance Sign-Off

- [ ] PR1 Human Review draft acceptance passes.
- [ ] PR2 local HumanReview preview acceptance passes.
- [ ] PR3 Write Eligibility acceptance passes.
- [ ] PR4 read-only Write Plan acceptance passes.
- [ ] PR5 final-confirmation contract acceptance passes.
- [ ] Stale-preview clearing and dialog-lifetime acceptance passes.
- [ ] No dangerous control is present.
- [ ] No note or collection mutation is observed.
- [ ] No provider invocation or network activity is observed.
- [ ] Local add-on configuration and backup remain intact.

Record the exact branch/commit, tester, date, environment, and result in the
manual acceptance document. Any unchecked safety item is a release blocker.

## 9. Git and Release State

- [ ] PR1 through PR6 are present in local `main` history.
- [ ] The final local `main` worktree is clean.
- [ ] Local `origin/main` remains
      `534f2edce93866cc813b643a0c2f4e71d6329faa` unless the user separately
      authorizes a push.
- [ ] No PR6 command fetches, pulls, or pushes.
- [ ] No v0.8 commit is pushed without explicit later authorization.

## 10. Seal Decision

v0.8 may be sealed only when every automatic, manual, configuration, backup,
and Git-state check above passes. v0.8 deliberately ends at read-only planning
and confirmation-contract explanation.

Entering a real writer must occur in v0.9 or later through a separately scoped
PR, separate tests, separate manual acceptance, and explicit user
authorization. It must not be inferred from this checklist or from any v0.8
status.
