# AnkiForge AI v0.7 Provider Draft UI Release Checklist

## 1. Scope

This checklist closes the v0.7 provider draft UI work delivered by PR1 through
PR4. It records the release boundary for a local, non-persistent provider draft
and its read-only safety projections.

v0.7 does not provide ordinary-user provider execution, credential storage,
consent creation, card generation, or Anki writing. A checked item in this
document is evidence only for the named UI and safety boundary; it is not
authorization to call a provider.

## 2. Delivered Capability

- PR1 renders an explicitly injected new-pipeline provider preview or a safe
  empty state in an independent read-only dialog.
- PR2 adds an independent, in-memory editor for provider, model, base URL, and
  privacy notice, with a fixed `knowledge_point_extraction` target stage.
- PR3 adapts a valid local draft into a PR1-style safety summary without
  constructing a runtime `ReadOnlyProviderPreview`.
- PR4 explains the difference between the current local action and a possible
  future real-provider send. The disclosure is explanation only.

The baseline after the PR4 merge is 511 passing unit tests, successful
`compileall`, and a successful Git whitespace check.

## 3. Current Local Preview Boundary

Confirm every current local draft action:

- [ ] does not save settings;
- [ ] does not accept an API key;
- [ ] does not send user material;
- [ ] does not call a provider;
- [ ] does not read a source document, clipboard, Anki card, or Anki
      collection;
- [ ] does not create a consent record;
- [ ] does not generate KnowledgePoints, CardCandidates, reviews, or cards;
- [ ] does not write an Anki note or change a note type; and
- [ ] is discarded when the dialog closes.

The local preview may display the non-sensitive values entered into the open
dialog. Those values are not written to logs, configuration, or diagnostic-safe
output.

## 4. Future Send Disclosure Boundary

- [ ] The UI says a future real-provider flow may send only material explicitly
      selected by the user.
- [ ] The UI says explicit agreement must be requested again before a future
      send.
- [ ] The disclosure does not create or imply consent.
- [ ] The disclosure does not authorize execution.
- [ ] The disclosure does not claim that the provider is verified, activated,
      configured, ready, or reachable.
- [ ] The disclosure does not weaken the fixed
      `knowledge_point_extraction` target stage.
- [ ] No local or localhost endpoint bypass is claimed.

## 5. UI Surface Checklist

- [ ] Anki has only one AnkiForge AI add-on/menu entry.
- [ ] PR1 and PR2 use distinct, clearly labeled entries.
- [ ] PR3 and PR4 extend only the PR2 local draft dialog.
- [ ] The editable fields are limited to provider, model, base URL, and privacy
      notice.
- [ ] Target stage is visible and read-only.
- [ ] HTTP and HTTPS URLs are accepted after local validation.
- [ ] Non-HTTP(S) URLs and embedded URL credentials are rejected locally.
- [ ] Empty and invalid drafts do not produce provider or future-send summaries.
- [ ] The middle content area scrolls when required.
- [ ] The update and close buttons remain fixed outside the scroll area.
- [ ] No key, save, apply, enable, consent, authorize, send, run, provider-
      verification, approve, card-generation, or Anki-write control exists.

The complete manual procedure is in
`docs/pipeline_v0_7_provider_draft_ui_manual_acceptance.md`.

## 6. Configuration and Repository Safety

- [ ] `ankiforge_ai/config.json` is not tracked by Git.
- [ ] `.gitignore` covers local `config.json`, environment files, Python cache
      files, Anki databases/packages, `addons21`, and `addon_backups`.
- [ ] `ankiforge_ai/config.example.json` is tracked and contains only a
      sanitized template with empty credential-bearing values.
- [ ] The local add-on `config.json` is preserved during manual code sync.
- [ ] The Anki add-on backup remains outside `addons21` under
      `Anki2/addon_backups`.
- [ ] No add-on backup, Anki database, `.apkg`, local environment file, or local
      configuration is staged.
- [ ] The configured GitHub remote is private.
- [ ] Local v0.7 commits after `534f2ed` remain unpushed until an explicit later
      release or v0.8 instruction.

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
- [ ] The intended release branch or merge commit is clean.
- [ ] Automatic tests make no real provider or network request.
- [ ] Tests contain no real API key, token, credential, source material, or
      user Anki data.

## 8. Manual Acceptance Sign-Off

- [ ] PR1 read-only preview acceptance passes.
- [ ] PR2 local draft acceptance passes.
- [ ] PR3 read-only-style safety summary acceptance passes.
- [ ] PR4 future-send disclosure acceptance passes.
- [ ] Scroll and fixed-button regression acceptance passes.
- [ ] Legacy provider settings and the candidate table remain operational.
- [ ] No note is created or changed.
- [ ] No provider invocation or network activity is observed.
- [ ] The local add-on configuration and backup remain intact.

Record the exact branch/commit, Anki version, tester, date, and any observation
in the manual acceptance document. Any unchecked safety item is a release
blocker.

## 9. Release Decision

v0.7 provider draft UI is ready to merge locally only when:

- [ ] PR1 through PR5 are present in the local `main` history;
- [ ] all automatic and manual checks above pass;
- [ ] the worktree is clean after the merge;
- [ ] no unexpected file is tracked or staged; and
- [ ] no push occurs without a separate explicit instruction.

## 10. Deferred Work and Non-Goals

The following remain future work:

- persistent new-pipeline provider profiles;
- a production credential-storage backend;
- an explicit consent flow tied to the exact provider selection and exact
  source preview;
- an ordinary-user controlled provider dry run;
- provider verification or readiness checks;
- card generation, Human Review, Write Eligibility, and final write
  confirmation; and
- any v0.8 Anki write bridge or public release work.

This checklist adds no UI, persistence, consent, provider call, network access,
card-generation path, Anki write, configuration change, or GitHub push.
