# AnkiForge AI v0.6 Provider Config Contract

## 1. PR1 Scope

v0.6 PR1 introduces a non-secret, user-facing provider profile for the new
KnowledgePoint extraction pipeline. It defines what may be displayed or saved
as provider metadata and keeps runtime credentials outside that profile.

This is an internal contract only. It does not expose a real-provider feature
in the plugin UI and does not send any user content.

## 2. Non-secret Provider Profile

`UserProviderProfile` contains a profile identifier, provider display data,
model name, base URL, privacy notice, and timeout. It is frozen and has no API
key, Authorization header, token, password, or generic secret field.

For every profile, including localhost and `127.0.0.1` endpoints:

- `sends_user_content` is always `True`.
- `requires_explicit_consent` is always `True`.

These values are read-only properties rather than constructor fields. A caller
cannot label a real OpenAI-compatible request as local-only or consent-free.

## 3. Runtime Credential Boundary

`create_openai_compatible_config_from_user_profile(profile, api_key)` accepts a
credential explicitly at runtime and combines it with the non-secret profile
using the existing `OpenAICompatibleProviderConfig` contract. The helper does
not read environment variables, files, Anki config, the legacy `config.json`,
or global state. It does not save or verify the key, create a provider, call a
transport, or access the network.

The runtime config already excludes its credential from `repr()`, `str()`, and
`to_dict()`. PR1 does not change the legacy provider or config flow.

## 4. URL Safety

Profile base URLs must use an explicit `http://` or `https://` scheme and
include a hostname. Relative paths, missing schemes, `file://`, `data://`, and
URLs containing embedded usernames or passwords are rejected.

Allowing a localhost endpoint does not weaken disclosure or consent rules.

## 5. Non-goals

PR1 explicitly does not:

- add a provider dry-run context helper;
- add provider presets;
- implement key storage;
- add a consent UI;
- connect a real provider;
- connect any UI;
- change the legacy `config.json`;
- migrate legacy configuration;
- write to Anki;
- generate `CardCandidate`;
- generate `HumanReview`;
- bypass Human Selection, Quality Gate, or Human Review.

Future PRs must design credential storage and explicit user consent separately
before any ordinary-user real-provider entry point is enabled.
