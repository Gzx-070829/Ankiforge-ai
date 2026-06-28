# AnkiForge AI v0.6 Provider Consent Contract

## Purpose

v0.6 PR3 defines safe, in-memory snapshots for provider selection and explicit
consent. These contracts let a future UI state which provider was selected,
what disclosure was accepted, and when consent occurred without reading a
credential or invoking a provider.

## Relationship to UserProviderProfile

`ProviderSelection` copies only the non-secret identity, display, model, and
endpoint fields from a validated `UserProviderProfile`. The profile remains
unchanged. Selection never carries an API key, source text, chunk content, or
request headers.

## Relationship to ProviderSecretStore

PR3 does not import or read `ProviderSecretRef`, `ProviderSecretValue`, or
`ProviderSecretStore`. Selecting a profile and consenting to send material are
separate from resolving a credential. Future wiring must preserve that
separation and resolve a key only at a narrow, consent-gated runtime boundary.

## ProviderSelection Contract

`ProviderSelection` is a frozen snapshot containing `profile_id`, provider
identity and name, model name, and an HTTP or HTTPS base URL. Embedded URL
credentials are rejected. Its `sends_user_content` and
`requires_explicit_consent` properties are always `True` and cannot be supplied
as constructor flags.

## Explicit Consent Contract

`ProviderConsentRecord` is a frozen affirmative record containing the
selection, non-empty consent text, non-empty privacy notice, and a
timezone-aware timestamp. It has fixed `sends_user_content`,
`requires_explicit_consent`, and `has_explicit_consent` properties, all `True`.
Callers cannot supply or override these flags.

All values must be supplied explicitly. PR3 provides no current-time default,
default consent text, default disclosure, or mutable decision flag.

## Absence Means No Consent

No `ProviderConsentRecord` means the user has not consented. A refusal or
cancelled flow must not create an affirmative record. The model deliberately
does not represent a missing record as an implicit or default approval.

## Why Consent Is Not UI Yet

This contract contains no dialog, settings page, checkbox, or persistence. A
future UI must present the provider identity, endpoint, privacy notice, and the
fact that user material will be sent before it creates a record.

## Consent Does Not Authorize Provider Calls by Itself

A consent record is evidence for a future gate; it does not call a provider,
factory, transport, extractor, or network. A future consent-gated service must
also verify that the record matches the current selection and request.

## Consent Does Not Authorize Anki Writing

Consent only concerns a future KnowledgePoint dry run. It does not authorize
card generation or Anki writing. Any later result must still pass Human
Selection, Quality Gate, Human Review, Write Eligibility, duplicate checks,
and final user confirmation before an Anki write can occur.

## Localhost Does Not Bypass Consent

`localhost` and `127.0.0.1` selections still report that they send user content
and require explicit consent. Endpoint location does not prove who controls the
service or how it stores submitted material.

## Future Consent-gated Dry-run Request

A later PR may define a service that requires a matching selection, affirmative
consent record, and separately resolved credential before it creates a dry-run
request. PR3 does not create that request or perform KnowledgePoint extraction.

## Relationship to Old config.json

PR3 does not read, modify, or migrate the legacy `config.json` or old provider
settings. The existing provider and review workflow remain unchanged.

## Security Limitations

- A record is not signed, encrypted, persisted, or independently auditable.
- Its timestamp is supplied by the caller and does not prove when a UI action occurred.
- The model cannot prove that the disclosure was visibly presented to a user.
- A selection is a snapshot and may become stale if a profile changes later.
- Consent does not establish endpoint trust or validate a credential.

## Non-goals

PR3 does not:

- add UI, a consent dialog, or a provider settings page;
- save consent to disk;
- read or save an API key or access a secret store;
- create a provider or transport or call the provider factory;
- access a network or validate a credential;
- create a dry-run request;
- generate `KnowledgePoint`, `CardCandidate`, `HumanReview`, or `GeneratedCard`;
- modify `self.cards` or write to Anki;
- change or migrate the legacy `config.json`;
- add provider presets, token/cost accounting, retry, or backoff.

## Future PRs

Future work may add a consent gate service, safe dry-run request model, and an
explicit UI flow. Those changes must remain separate from credential storage,
card generation, and Anki writing, and must preserve every downstream human
review gate.
