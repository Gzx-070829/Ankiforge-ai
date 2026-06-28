# AnkiForge AI v0.6 Secret Store Contract

## Purpose

v0.6 PR2 defines how the new pipeline refers to, carries, and requests an API
key without placing that key in `UserProviderProfile` or ordinary safe output.
It establishes a small secret-store Protocol and credential lifecycle boundary.
It does not select or implement a persistent storage technology.

## ProviderSecretRef

`ProviderSecretRef` is a frozen, non-secret reference containing only a
`profile_id`. Its `credential_kind` property is fixed to `api_key` and cannot
be supplied or changed by callers. Its dictionary representation contains
only the profile identifier and credential kind, never credential material.

## ProviderSecretValue

`ProviderSecretValue` wraps a non-empty runtime credential. Its normal string
and representation output is always `<redacted>`. It has no dictionary or JSON
serialization API. Obtaining the plaintext requires an explicit `reveal()`
call at a future, narrowly controlled wiring boundary.

This wrapper is not encryption. Python cannot reliably clear the credential
from memory. A debugger, crash dump, malicious store, or code deliberately
accessing process memory may still recover it. Redacted display behavior only
reduces accidental disclosure through logs and diagnostics.

## ProviderSecretStore Protocol

`ProviderSecretStore` defines `save_secret`, `load_secret`, `has_secret`, and
`delete_secret`. A missing credential is represented by `None`; deleting a
missing credential returns `False`.

The runtime-checkable Protocol verifies structural compatibility only. It
cannot prove that an implementation encrypts data, applies correct access
controls, avoids logging credentials, or securely deletes values.

## Why PR2 Has No Production Backend

Credential backends have platform-specific security, packaging, permission,
backup, deletion, and migration concerns. Selecting one inside this contract
PR would mix policy with implementation and make rollback harder. Windows
Credential Manager, macOS Keychain, Linux Secret Service, keyring integration,
and encrypted-file storage are therefore deferred.

## Why the Test Fake Is Not Production Storage

The test suite defines a small process-memory fake solely to verify Protocol
semantics. It is not shipped from the production module, is not exported by
the pipeline package, provides no encryption or persistence, and must never be
used as production credential storage.

## Relationship to UserProviderProfile

`UserProviderProfile` remains unchanged and contains only non-secret provider
metadata. A future caller may create a `ProviderSecretRef` from the profile's
identifier, but PR2 does not add the reference to the profile or resolve a
credential into a runtime provider configuration.

## Relationship to Old config.json

The legacy `config.json`, config loader, provider settings, and stored key
behavior remain separate and unchanged. PR2 does not read, write, inspect, or
migrate legacy API keys. Any future migration requires its own explicit and
reversible design.

## Relationship to UI

PR2 adds no provider selection, key entry, consent, status, or error UI. It
does not change `main_dialog.py` or any existing review workflow.

## Relationship to Provider Factory and Transport

PR2 does not create a provider or transport, modify the provider factory, call
a provider, verify a credential, or access the network. Future wiring must
resolve a secret only after explicit user consent and keep the plaintext
boundary as narrow as possible.

## Security Limitations

- Secret values remain present in Python process memory.
- The wrapper cannot protect against a debugger, crash dump, or malicious code.
- Protocol conformance is not a security audit of an implementation.
- Secure deletion, rotation, revocation, backup, and recovery are unresolved.
- Error and logging discipline must also be enforced by every future backend.

## Non-goals

PR2 does not:

- implement Windows Credential Manager, macOS Keychain, or Linux Secret Service;
- integrate `keyring` or implement encrypted-file storage;
- read or modify the legacy `config.json` or migrate a legacy API key;
- connect UI or a consent flow;
- create a provider or transport;
- call a real provider, access a network, or validate an API key;
- generate `KnowledgePoint`, `CardCandidate`, or `HumanReview` objects;
- write to Anki;
- modify the legacy provider or config flow.

## Future PRs

Future work may evaluate platform credential backends, define safe failure and
availability behavior, implement explicit key replacement and deletion, and
connect credential resolution to a consent-gated provider dry run. Each step
must remain separate from the legacy config flow and from Anki writing.
