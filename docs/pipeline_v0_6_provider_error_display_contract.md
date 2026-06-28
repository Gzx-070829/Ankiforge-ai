# AnkiForge AI v0.6 Provider Error Display Contract

## Purpose

v0.6 PR5 defines a fixed taxonomy and safe display mapping for future provider
failures. It gives ordinary users understandable, actionable messages and gives
developers stable, non-sensitive diagnostic codes without accepting or showing
raw exceptions, provider responses, credentials, or user material.

## Error Kind Taxonomy

`ProviderErrorKind` covers authentication, network, timeout, rate limit, quota,
invalid request, invalid JSON, malformed response, provider availability,
content policy, and unknown failures. The mapping accepts only these normalized
kinds, not SDK exception classes or arbitrary raw error strings.

## ProviderErrorDisplay Contract

`ProviderErrorDisplay` is a frozen DTO containing the normalized kind, user
title, user message, suggested action, a conservative retryable flag, and a
safe diagnostic code. It validates every display field independently of the
mapping helper and serializes only those fields through `to_safe_dict()`.

## Safe User-facing Messages

All messages come from a fixed local template table. Authentication text never
shows a credential. Invalid JSON and malformed response text never shows the
raw response. Content-policy text never repeats submitted material. Rate and
quota messages describe only the broad condition and do not claim knowledge of
specific billing details.

An optional provider name is treated only as a display label. Empty, overlong,
control-character, or obviously credential/raw-data-like labels are rejected.

## Developer Diagnostic Limits

`safe_diagnostic_code` is derived only from the normalized taxonomy. It is not
an exception class, stack trace, request identifier, provider body, or payload.
Detailed debugging must use a separately designed, privacy-reviewed mechanism;
PR5 intentionally provides none.

## Why Raw Exceptions Are Not Displayed

Exception messages may contain endpoint details, request fragments, SDK state,
or credential-adjacent data. The helper does not accept an exception or raw
message, so no fallback can accidentally copy one into user-visible text.

## Why Raw Provider Responses Are Not Displayed

Provider bodies can repeat user material and may include internal diagnostics.
PR5 accepts no response or payload and never stores or serializes either.

## Relationship to ProviderDryRunRequest

The display mapping does not import, inspect, execute, or modify a
`ProviderDryRunRequest`. A future execution service may choose a normalized
error kind after a failed request, but PR5 does not implement that classifier.

## Relationship to Future Provider Execution Service

A future service may map its already-normalized failure kind through this
module. That service must keep raw exceptions and provider bodies outside the
display contract and must preserve consent, credential, and KnowledgePoint-only
boundaries.

## Relationship to UI

PR5 adds no dialog, notification, settings page, or other UI. A future UI may
render the safe DTO, but must never fall back to raw exception text when a
mapping is unavailable.

## Relationship to Retry and Backoff

`retryable` is display metadata only. It does not schedule, count, delay, or
execute another request. PR5 contains no retry, backoff, sleep, callback, or
rate-limit implementation.

## Relationship to Old config.json

PR5 does not read, modify, or migrate the legacy `config.json` or old provider
settings. Existing provider and review workflows remain unchanged.

## Security Limitations

- Upstream code may select the wrong normalized error kind.
- Fixed messages intentionally omit detailed debugging information.
- Provider-name validation reduces accidental disclosure but cannot prove trust.
- A retryable flag does not guarantee that retrying is safe or will succeed.
- Localization and privacy-reviewed developer diagnostics remain future work.

## Non-goals

PR5 does not:

- add UI, dialogs, notifications, logging, telemetry, or crash reporting;
- read or save credentials or access a secret store;
- create a provider or transport or call the provider factory;
- access a network or catch SDK or HTTP exceptions;
- classify raw exceptions;
- implement retry, backoff, token/cost accounting, or provider presets;
- call a KnowledgePoint extractor or generate pipeline output models;
- modify `self.cards` or write to Anki;
- modify or migrate the legacy `config.json`.

## Future PRs

Future work may define a privacy-reviewed exception classifier in the provider
execution service and connect this safe DTO to a user interface. Those changes
must remain separate from retries, credentials, raw diagnostics, and Anki
writing.
