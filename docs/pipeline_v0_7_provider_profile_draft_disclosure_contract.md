# AnkiForge AI v0.7 Provider Draft Send Disclosure Contract

## 1. Scope

v0.7 PR4 adds a presentation-only disclosure to the existing PR2/PR3 local
provider draft dialog. It distinguishes the current local preview operation
from a possible future real-provider send.

The disclosure is explanation, not consent, authorization, activation,
provider verification, runtime readiness, or execution.

## 2. Input and Layering

The pure Python adapter accepts only a PR3
`ProviderProfileDraftReadOnlyPreview`. It does not accept raw widgets, legacy
configuration, `UserProviderProfile`, `ProviderSelection`,
`ProviderConsentRecord`, a credential, API key, secret reference, source
document, or runtime provider configuration.

The dialog sequence is:

```text
local widgets
  -> PR2 local validation
  -> PR3 read-only-style local summary
  -> PR4 send disclosure
  -> local dialog rendering
```

Empty and invalid PR3 previews produce no PR4 disclosure. The disclosure group
is hidden until a valid local draft exists.

## 3. Current Local Operation

The disclosure states that the current update operation:

- only refreshes the local preview;
- does not save settings or accept an API key;
- does not send content or call a provider;
- does not read a source document, clipboard, Anki content, cards, or the Anki
  collection;
- does not create a consent record;
- does not generate cards; and
- does not write to Anki.

## 4. Future Send Explanation

For a valid draft, the disclosure explains that a future real-provider flow
may send only a short preview explicitly selected by the user to the provider
and Base URL shown in the draft summary. Any such future send must request
explicit agreement again.

The target stage remains fixed at `knowledge_point_extraction`.

The exact boundary text states:

```text
本披露不构成 consent 或执行授权
本披露不代表 provider 已验证、激活或可运行
```

## 5. No Consent or Runtime Authority

PR4 has no consent checkbox, agree button, authorize button, save, apply,
enable, send, run, provider-verification, approve, card-generation, or
Anki-write command.

It neither imports nor creates `ProviderSelection`, `ProviderConsentRecord`,
`ReadOnlyProviderPreview`, a runtime provider configuration, a provider,
transport, executor, network client, writer, or Anki collection object.

## 6. Safe Presentation

The user-visible PR3 group already shows the provider and Base URL. PR4 refers
to those values as the future recipient without copying them into the PR4
object.

`ProviderProfileDraftSendDisclosure` contains only fixed messages and display
rows. Display-row values remain excluded from repr, and `to_safe_dict()` emits
only labels, value presence, and lengths. No logging or persistence is added.

## 7. UI Integration

PR4 adds one group to the existing local draft dialog:

```text
未来发送披露（仅说明，不授权）
```

It contains separate `当前本地操作` and `未来真实 Provider 流程` sections.
No MainDialog entry or button is added. The existing update and close buttons
remain the only commands. Closing the dialog discards all state.

The safety notice and bottom command row remain outside the scroll area. The
draft form, PR3 summary, safety state, and PR4 disclosure share a vertically
scrollable middle area. The dialog bounds its initial height to the primary
screen's available geometry so disclosure content cannot push the update and
close buttons off-screen.

## 8. Isolation

PR4 does not read `self.config`, legacy provider controls, `api_key_input`,
source documents, clipboard content, `self.cards`, Anki cards, or the Anki
collection. It does not modify PR1, MainDialog, legacy settings, `config.json`,
the candidate table, provider execution, or the Anki writer.

## 9. Automatic Tests

Pure Python tests cover strict PR3 input typing, empty/invalid suppression,
valid current/future disclosure rows, forged-state rejection, fixed consent
and execution disclaimers, safe repr/dictionary output, forbidden imports and
calls, dialog sequencing, hidden invalid state, unchanged button surface, and
MainDialog isolation.

Tests import no Qt, Anki, provider runtime, or network library and make no
network request.

## 10. Manual Anki Acceptance

1. Confirm the Anki menu still contains one AnkiForge AI entry.
2. Open the main window and confirm PR1 and the PR2/PR3 entry still work.
3. Open the local draft dialog and confirm the disclosure is absent while the
   draft is empty.
4. Enter an invalid URL and confirm only local validation errors appear.
5. Enter a valid draft and update the preview.
6. Confirm the disclosure appears with separate current and future sections.
7. Confirm current behavior says no save, key input, send, provider call,
   source/Anki read, consent creation, card generation, or Anki write.
8. Confirm future behavior requires explicit agreement again and is limited to
   an explicitly selected short preview for KnowledgePoint extraction.
9. Confirm the disclosure does not claim consent, execution authorization,
   provider verification, activation, or runtime readiness.
10. Confirm no consent, authorize, save, send, run, approve, or Anki-write
    control exists.
11. On a common-height screen, scroll through the middle content and confirm
    the update and close buttons remain visible and clickable at all times.
12. Close and reopen; confirm the draft and disclosure are discarded.
13. Confirm legacy settings, candidates, and the Anki collection are unchanged
    and no network request occurs.

## 11. Non-Goals

PR4 does not persist or activate a profile, create or save consent, accept or
inspect credentials, select or read source material, construct a runtime
preview, execute a dry run, call a provider, generate pipeline objects or
cards, write Anki notes, change note types, modify legacy settings, or push to
GitHub.
