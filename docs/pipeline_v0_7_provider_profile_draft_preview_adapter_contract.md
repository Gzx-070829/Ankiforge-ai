# AnkiForge AI v0.7 Provider Profile Draft Preview Adapter Contract

## 1. Scope

v0.7 PR3 adapts the validated PR2 local provider draft view into a presentation-
only summary whose grouping resembles the PR1 read-only provider preview.

The adapter does not create a PR1 runtime preview. It has no authority to save,
activate, verify, send, execute, generate, or write anything.

## 2. Input Boundary

The adapter accepts only `ProviderProfileDraftViewData`, the output type of the
PR2 helper. It does not accept a raw draft, legacy configuration, user provider
profile, provider selection, consent record, credential reference, API key, or
runtime provider configuration.

The dialog follows this sequence when the user selects
`更新本地预览（仅本地）`:

```text
local widgets
  -> ProviderProfileDraftInput
  -> build_provider_profile_draft_view_data()
  -> build_provider_profile_draft_read_only_preview()
  -> local dialog rendering
```

## 3. Output Type

`ProviderProfileDraftReadOnlyPreview` is a frozen presentation type containing:

- empty and valid state flags;
- a fixed summary message;
- whitelisted provider display rows;
- fixed local-draft status rows; and
- safe, value-free validation errors.

It has no secret, credential, consent-record, dry-run, readiness, runtime
configuration, provider instance, or Anki object field.

## 4. Defensive Input Validation

The adapter does not trust a manually constructed instance merely because it
has the expected type. It verifies that:

- every input retains the exact PR2 fixed no-save/no-send/no-call/no-write rows;
- an empty view is invalid and has no provider rows or validation errors;
- an invalid view has errors and no provider rows;
- a valid view has the exact five provider row labels and no errors; and
- the target stage remains `knowledge_point_extraction`.

Forged positive execution flags, inconsistent states, alternate target stages,
or altered provider-row shapes are rejected.

## 5. Read-Only-Style Provider Group

For a valid draft the adapter exposes the PR2-whitelisted local display rows:

```text
Provider
Model
Base URL
Privacy notice
Target stage
```

The values may be displayed inside the currently open dialog. They are not
copied into repr, logs, diagnostic-safe output, configuration, or persistence.

Empty and invalid drafts do not produce provider rows.

## 6. Fixed Draft Status Group

Every adapter result shows these fixed presentation rows:

```text
Preview source: 仅本地草稿
Activation status: 未激活
Provider verification: 未执行
Consent status: 不适用（未激活）
Will save settings: 否
Will send content: 否
Will call provider: 否
Will generate cards: 否
Will write to Anki: 否
```

`Consent status` describes fixed non-applicability in this inactive local-draft
flow. It does not inspect or create a consent record.

The adapter does not display credential status, secret presence, key existence,
dry-run status, runtime readiness, or provider readiness.

## 7. User-Facing Meaning

A valid local draft displays this exact warning:

```text
格式有效 ≠ provider 已验证；安全摘要 ≠ runtime preview；
本地草稿 ≠ 已保存配置。
```

This separates local syntax validation from provider verification, runtime
preview construction, activation, and persistence.

## 8. Safe Serialization

The adapter reuses PR2 display rows whose values are excluded from repr.
`to_safe_dict()` records row labels, presence, and lengths but not complete
provider, model, URL, or privacy-notice values.

Validation errors do not echo rejected values. No logging call is added.

## 9. Runtime and Dependency Isolation

The adapter does not import or call:

- `ReadOnlyProviderPreview`;
- `build_read_only_provider_preview`;
- the PR1 presenter or dialog;
- `create_openai_compatible_config_from_user_profile`;
- legacy config loading or saving;
- a secret store, provider factory, transport, or executor;
- requests, httpx, aiohttp, urllib, sockets, or other network APIs;
- pipeline orchestration, card generation, writer, Anki, or Qt.

The dialog remains the only Qt renderer. Its update path calls the PR2 helper
and then this adapter.

## 10. UI Integration

PR3 adds no menu or MainDialog entry. The existing PR2 dialog and update button
remain in place. The two output groups are titled:

```text
Provider 安全信息
草稿安全状态
```

No save, apply, enable, send, run, provider-verification, approve, card-
generation, or Anki-write button is added. Closing the dialog discards all
widget and preview state.

## 11. Automatic Tests

Pure Python tests cover:

- strict input type acceptance;
- empty, invalid, and valid transformations;
- exact provider and fixed status rows;
- fixed target stage;
- forged-state rejection;
- public field and function signatures;
- repr and safe-dictionary value exclusion;
- forbidden runtime imports and calls;
- dialog helper-to-adapter sequencing; and
- unchanged button surface and read-only-style group titles.

The tests do not import Qt, Anki, or network libraries.

## 12. Manual Anki Acceptance

1. Open the existing PR2 local draft dialog.
2. Confirm no new entry or button exists.
3. Confirm empty and invalid drafts show no provider summary rows.
4. Enter a valid HTTP/HTTPS draft and update the local preview.
5. Confirm `Provider 安全信息` displays the five whitelisted fields.
6. Confirm `草稿安全状态` displays the nine fixed inactive/local-only rows.
7. Confirm the three distinction statements are visible.
8. Confirm no credential, secret-presence, dry-run, readiness, or provider-ready
   state is shown.
9. Close and reopen; confirm the draft and summary are gone.
10. Confirm PR1, legacy settings, local config, candidate table, and Anki
    collection remain unchanged, with no network request.

## 13. Non-Goals

PR3 does not save or activate a profile, inspect credentials, create consent,
construct a runtime preview, validate a real provider, execute a dry run,
generate pipeline objects or cards, write Anki notes, change note types, modify
legacy settings, or push to GitHub.
