# AnkiForge AI v0.6 Provider Dry-run Request Contract

## Purpose

v0.6 PR4 defines a consent-gated, non-executing request description for a
future provider KnowledgePoint dry run. It binds a provider selection,
affirmative consent record, credential reference, and limited source preview
without resolving a credential or invoking a provider.

## Relationship to UserProviderProfile

The request uses the non-secret `ProviderSelection` snapshot created from a
`UserProviderProfile`. It does not read, modify, or persist the profile and does
not contain profile credentials.

## Relationship to ProviderSecretRef and ProviderSecretStore

The request accepts only `ProviderSecretRef` and verifies that its `profile_id`
matches the selected profile. It does not accept `ProviderSecretValue`, access
`ProviderSecretStore`, call `reveal()`, validate a key, or serialize the secret
reference through `to_safe_dict()`.

## Relationship to ProviderSelection and ProviderConsentRecord

The consent record's selection must match the request selection across profile,
provider, display name, model, and base URL. Both objects must retain their
fixed user-content and explicit-consent safety flags.

## Consent Gate Rules

A request cannot be constructed without a `ProviderConsentRecord`. The record
must be affirmative, require explicit consent, and describe sending user
content. Its selection and credential profile must match the request selection.
No request object means no future provider dry run is authorized.

## Secret Boundary

No API key, token, Authorization header, credential value, or secret-store
implementation enters this model. The credential reference and source preview
are excluded from the default representation, and the reference is omitted
from safe dictionary output.

## Source Preview Boundary

The model stores only a chunk identifier, source title, and non-empty preview
of at most 500 characters. It does not accept `SourceChunk`, `source_text`,
`chunk_text`, or `full_source_text` fields.

The length limit is not de-identification. A 500-character preview can still
contain private information and may be the entire content of a short document.
Future callers remain responsible for creating an appropriate preview and for
presenting accurate disclosure before consent.

## Request Model, Not Execution

PR4 provides no `execute`, `send`, `run`, provider, transport, extractor, or
network behavior. Constructing a request only proves that its static inputs
satisfy this contract; it does not perform or guarantee a provider call.

## No Provider Authorization by Itself

This request is an input for a future consent-gated execution service. That
service must separately resolve credentials, revalidate current state, handle
failures safely, and limit output to KnowledgePoint extraction.

## No Anki Write Authorization

A dry-run request does not authorize card creation or Anki writing. Any future
KnowledgePoint result must still pass Human Selection, CardCandidate creation,
Quality Gate, Human Review, Write Eligibility, duplicate checks, and final user
confirmation before an Anki write can occur.

## Localhost Does Not Bypass Consent

`localhost` and `127.0.0.1` selections still send user content and require an
affirmative consent record. Endpoint location does not prove operator identity,
storage behavior, or privacy.

## Security Limitations

- Structural matching cannot prove the UI displayed the disclosure.
- A consent timestamp is caller-supplied and not an audit signature.
- A selection or credential reference may become stale after construction.
- The model cannot prove a referenced credential exists or is valid.
- The preview limit does not remove or anonymize sensitive information.
- Request construction is not permission to execute or write to Anki.

## Non-goals

PR4 does not:

- add UI or a dry-run UI;
- persist consent;
- read or save an API key or access a secret store;
- call `ProviderSecretValue.reveal()`;
- create a provider or transport or call the provider factory;
- access a network or validate a credential;
- invoke a KnowledgePoint extractor or generate a KnowledgePoint;
- generate `CardCandidate`, `HumanReview`, or `GeneratedCard` objects;
- modify `self.cards` or write to Anki;
- modify or migrate the legacy `config.json`;
- add provider presets, token/cost accounting, retry, or backoff.

## Future PRs

A future PR may implement a separate execution service that accepts this
request, revalidates consent, resolves a credential through an approved backend,
and invokes the existing safe KnowledgePoint extraction path. It must not add a
shortcut to card generation or Anki writing.
