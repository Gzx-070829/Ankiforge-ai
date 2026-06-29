# AnkiForge AI v0.7 Read-Only Provider Preview UI Contract

## 1. Scope

v0.7 PR1 adds the first UI renderer for the v0.6 provider safety projection.
It is a read-only preview, not provider settings, consent, execution, card
generation, or Anki writing.

The UI is deliberately separate from the legacy provider settings and review
table.

## 2. UI Entry

The main dialog adds a button labeled `新 Pipeline Provider 只读预览` beside
the existing provider-settings header. The label distinguishes the new
pipeline preview from the legacy provider configuration.

The preview opens in an independent dialog titled
`新 Pipeline Provider 只读预览`. The only command in the dialog is `关闭`.

## 3. Explicit Preview Injection

`MainDialog` accepts an optional explicitly injected `ReadOnlyProviderPreview`.
The normal plugin entry continues to call `MainDialog` without a preview.

PR1 does not build a provider profile in the UI. It does not inspect the old
provider combo, model field, base URL field, API key field, legacy
`config.json`, or global state to guess a new-pipeline provider status.

When no preview is injected, the dialog displays:

```text
新 pipeline provider 尚未配置
```

The empty state still states that the target is KnowledgePoint extraction and
that cards, Anki notes, and Anki writes are disabled.

## 4. Whitelisted Display Data

The pure Python presenter reads individual fields from the existing
`ReadOnlyProviderPreview`. It does not dump the object or use a generic
dataclass serializer.

The UI may display only:

- provider name and provider ID;
- model name and base URL;
- privacy notice;
- whether a credential is configured, explicitly labeled as unvalidated;
- consent status and safe consent timestamp;
- whether user content would be sent and explicit consent is required;
- target stage;
- fixed no-write flags;
- a dry-run source title, chunk ID, excerpt length, and short excerpt; and
- the fixed safe fields from `ProviderErrorDisplay`.

The presenter does not accept a provider profile, consent record, dry-run
request, secret reference, secret value, raw exception, or raw provider body.

## 5. Credential Status

The UI renders only one of these states:

```text
已配置，未验证
未配置，未验证
```

This boolean does not mean the key is valid or that a provider call is
authorized. PR1 does not read, save, migrate, reveal, or validate an API key.
It does not access a secret store.

## 6. Consent and Dry-Run Preview

The dialog can show whether an affirmative consent record exists, but it does
not create or change consent. It contains no consent button.

If the safe projection includes a dry-run preview, the UI can show its source
title, chunk ID, length, and user-visible excerpt. The display helper applies
a defensive 500-character maximum. The excerpt is excluded from helper repr
and safe dictionary output.

The dialog does not send the excerpt. It contains no run or send button and
does not call a provider, factory, transport, executor, or network API.

## 7. Safe Error Display

An optional error section renders only the existing `ProviderErrorDisplay`
kind, title, message, suggested action, retryability, and diagnostic code.

PR1 does not accept, classify, log, or display raw exceptions, stack traces,
provider bodies, prompts, credentials, or full source text.

## 8. Fixed No-Write Boundary

Every populated or empty preview shows these fixed states:

```text
target_stage = knowledge_point_extraction
will_write_to_anki = false
will_generate_cards = false
will_create_anki_notes = false
```

The UI does not generate `KnowledgePoint`, `CardCandidate`, or `HumanReview`
objects. It does not modify `self.cards`, call the writer, create an Anki note,
or change a note type.

## 9. Automatic Tests

The presenter tests are pure Python and do not import Qt, Anki, or `aqt`. They
cover the empty state, credential and consent states, dry-run presence, safe
errors, excerpt truncation, fixed no-write flags, sensitive-output exclusion,
and the dependency boundary.

Qt dialog behavior remains a manual acceptance item to avoid adding a brittle
Qt test harness to the existing offline suite.

## 10. Manual Anki Acceptance

1. Install the branch without replacing the local legacy `config.json`.
2. Restart Anki and open `Tools -> AnkiForge AI`.
3. Confirm the button reads `新 Pipeline Provider 只读预览`.
4. Open it through the normal plugin entry and confirm the safe empty state.
5. Confirm the dialog has only a close button and no key, save, consent, send,
   run, approve, card-generation, or Anki-write control.
6. In a developer-only Anki debug session, inject a safe
   `ReadOnlyProviderPreview` fixture and inspect configured/missing credential,
   consent, dry-run, excerpt, and safe-error states.
7. Confirm closing the dialog leaves the candidate table, `self.cards`, legacy
   settings, generation flow, review flow, and Anki collection unchanged.
8. Confirm no network request occurs.

## 11. Non-Goals

PR1 does not:

- add ordinary-user provider configuration or profile creation;
- add API key entry, storage, migration, reveal, or validation;
- add a consent dialog or consent persistence;
- execute a dry run or call a real provider;
- change the legacy provider or `config.json` behavior;
- modify the provider factory, transport, executor, orchestrator, or review
  bridge;
- generate cards or change the current candidate workflow;
- write to Anki or change a note type;
- implement an exception classifier; or
- implement the rest of v0.7.
