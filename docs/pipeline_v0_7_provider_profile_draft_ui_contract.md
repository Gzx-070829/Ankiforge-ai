# AnkiForge AI v0.7 Provider Profile Draft Preview UI Contract

## 1. Scope

v0.7 PR2 adds a local, non-persistent editor and preview for non-sensitive
provider profile fields. It is not provider configuration, activation,
credential handling, consent, execution, card generation, or Anki writing.

PR2 does not change the PR1 `ReadOnlyProviderPreviewDialog` or its read-only
contract.

## 2. UI Entry and Lifetime

The main dialog adds a distinct button beside the provider-settings header:

```text
新 Pipeline Provider 本地草稿预览
```

It opens an independent dialog titled with the same text. Every ordinary open
starts with a blank draft. A developer may explicitly inject only a
`ProviderProfileDraftInput` when constructing the dialog.

The draft lives only in the open dialog's widgets. Closing the dialog discards
it. Reopening through the normal entry starts blank again.

## 3. Allowed Draft Fields

The dialog can edit only:

- provider;
- model;
- base URL; and
- privacy notice.

It displays the target stage as the fixed, read-only value:

```text
knowledge_point_extraction
```

The target stage cannot be changed to card generation or any other stage.

## 4. Local Validation and Preview

The pure Python presenter trims surrounding whitespace and requires every
editable field to be non-empty before it renders the profile rows.

For a complete draft it uses `UserProviderProfile` only as a validation
boundary. This reuses the existing HTTP/HTTPS URL rules and rejects incomplete
URLs and URLs with embedded usernames or passwords. PR2 never calls
`create_openai_compatible_config_from_user_profile` and never creates a runtime
provider configuration.

The update command is labeled `更新本地预览（仅本地）`. It only reconstructs
an immutable draft value from the four local widgets and rerenders the dialog.
It has no persistence or execution authority.

## 5. Safe Presentation Boundary

Draft input values and display-row values are excluded from dataclass repr.
`to_safe_dict()` records only field presence, lengths, fixed labels, fixed
safety values, and validation messages. It does not copy the user-entered
provider, model, URL, or privacy notice into diagnostic-safe output.

Validation errors never echo the rejected URL or other draft values.

Every empty, invalid, or valid state displays fixed boundaries stating that
the draft:

- exists only in the current dialog and is discarded on close;
- will not save settings;
- will not send user content;
- will not call a provider;
- will not generate cards; and
- will not write to Anki.

## 6. Credential Boundary

The dialog has no API key or credential input. Its public draft dataclass and
presenter function signatures have no API key, secret, token, credential, or
`has_secret` field.

PR2 does not read, save, reveal, migrate, validate, infer, or report credential
state. It does not import or call a secret store.

The required user notice says:

```text
仅本地草稿；不保存设置；不接收 API key；不发送资料；不调用 provider；
不生成卡片；不写入 Anki；关闭后丢弃。
```

## 7. Legacy Configuration Isolation

The new MainDialog handler only constructs `ProviderProfileDraftDialog` with
its parent. It does not reference `self.config`, legacy `config.json`,
`provider_combo`, `model_input`, `api_base_url_input`, or `api_key_input`.

The new helper and dialog do not import `config_loader`. The existing legacy
MainDialog settings continue their pre-existing behavior, but no legacy value
is used to initialize, validate, preview, or retain the PR2 draft.

## 8. Execution and Anki Isolation

PR2 does not import or call a provider factory, transport, executor, network
library, orchestrator, writer, Anki collection API, or note-type API.

It does not create `KnowledgePoint`, `CardCandidate`, or `HumanReview` objects.
It does not read or modify `self.cards`.

## 9. Automatic Tests

Pure Python tests cover:

- blank, valid, and invalid drafts;
- whitespace normalization and required fields;
- HTTP/HTTPS URL validation and embedded-credential rejection;
- the fixed target stage and fixed no-save/no-run/no-write rows;
- public field and function signatures;
- repr and safe-summary value exclusion;
- forbidden imports and calls;
- MainDialog handler isolation from legacy and card state; and
- the exact allowed Qt input and button surface through source AST checks.

The tests do not import Qt, Anki, or network libraries.

## 10. Manual Anki Acceptance

1. Restart Anki and open `Tools -> AnkiForge AI`.
2. Confirm the PR1 read-only button is unchanged.
3. Confirm the separate button reads
   `新 Pipeline Provider 本地草稿预览`.
4. Open it and confirm provider, model, base URL, and privacy notice are blank.
5. Confirm target stage is visible and cannot be edited.
6. Confirm the complete local-only notice and fixed safety rows are visible.
7. Enter a valid draft and update the preview; confirm normalized fields appear.
8. Enter a non-HTTP URL and a URL with embedded credentials; confirm only local,
   value-free validation messages appear.
9. Confirm there is no API key, save, apply, enable, send, run, provider
   validation, approve, card-generation, or Anki-write control.
10. Close and reopen; confirm the draft is blank again.
11. Confirm legacy settings, local `config.json`, `self.cards`, the preview
    table, and the Anki collection remain unchanged.
12. Confirm the dialog works without network access and sends no request.

## 11. Non-Goals

PR2 does not:

- persist, restore, select, activate, or validate a real provider profile;
- accept or inspect credentials;
- create or change consent;
- build a PR1 runtime provider preview;
- call a real or mock provider;
- prepare or execute a dry run;
- generate knowledge points, candidates, reviews, or cards;
- write to Anki or change note types;
- refactor the legacy provider settings; or
- push changes to GitHub.
