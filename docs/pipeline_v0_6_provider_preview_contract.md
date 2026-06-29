# AnkiForge AI v0.6 Provider Preview Contract

## Purpose

v0.6 PR6 defines read-only provider and dry-run preview projections for a future
user interface. It shows which provider is selected, whether consent and a
credential configuration are present, what short excerpt a user is considering
sending, and any already-safe provider error display.

PR6 is a preview model, not a provider execution layer.

## Safe Projection Boundary

Preview DTOs store primitive display fields and safe sub-DTOs only. They do not
retain `UserProviderProfile`, `ProviderSelection`, `ProviderConsentRecord`,
`ProviderDryRunRequest`, `ProviderSecretRef`, `ProviderSecretValue`, or
`ProviderSecretStore` objects.

All dictionary output uses explicit field allowlists. PR6 does not use
`dataclasses.asdict()` because recursive serialization could expose newly added
nested fields in the future.

## Credential Status

`has_secret` is a boolean supplied by an external caller. It means only that a
credential is reported as configured. It does not mean the key is valid, that
PR6 read or verified it, that a provider can be called, or that a real dry run
can execute. A future UI should present this as `configured` or `missing`, never
as `valid`.

PR6 does not read, validate, save, serialize, or display an API key and does not
access a secret store.

## Consent Status

No consent record produces `has_consent=False`. An affirmative matching record
produces `has_consent=True` and a safe ISO timestamp. A dry-run preview cannot
be built without matching consent. `localhost` and `127.0.0.1` do not bypass
this requirement.

## Dry-run Request Preview

The dry-run preview stores a profile identifier, source chunk identifier,
source title, a short excerpt, and its length. It omits the original request,
credential reference, full source text, and chunk text. Its target stage is
always `knowledge_point_extraction`.

The excerpt remains user material. Its 500-character limit is not
de-identification and does not prove it is not the entirety of a short source.

## Safe and User-visible Dictionaries

`to_safe_dict()` is a log-safe and diagnostic-safe summary. It excludes the
source excerpt and consent text. It may report that an excerpt exists and its
length.

`to_user_visible_dict()` may include the short source excerpt so a user can see
what is proposed for a future send. It is not log-safe and must not be sent to
diagnostic logs, error logs, telemetry, or crash reports.

Both methods omit credential references, credential values, raw exceptions,
raw responses, and raw bodies.

## Safe Error Display

PR6 may carry the existing `ProviderErrorDisplay` safe projection. It does not
accept raw exceptions, SDK errors, provider bodies, or stack traces and does
not implement a second error mapping.

## No Provider Execution

PR6 does not execute a provider dry run, create a provider, call the provider
factory, invoke a transport, access a network, or validate credentials. The
presence of a preview is not execution authorization.

## No Pipeline Output or Anki Write

All preview objects report that they do not send full source text, generate
cards, create Anki notes, or write to Anki. PR6 does not generate
`KnowledgePoint`, `CardCandidate`, or `HumanReview` objects.

Any future real provider remains limited to KnowledgePoint extraction. Results
must still pass Human Selection, Quality Gate, Human Review, Write Eligibility,
duplicate checks, and final user confirmation before Anki writing.

## Relationship to Legacy Configuration

PR6 does not read, modify, or migrate the legacy `config.json`, API key, note
type, provider workflow, or review workflow.

## Non-goals

PR6 does not:

- add UI, Qt, Anki integration, or consent dialogs;
- access a secret store or call `reveal()`;
- read, save, migrate, or validate an API key;
- create or call providers, factories, transports, or orchestrators;
- execute a dry run or access a network;
- add provider presets, catalogs, prompt management, token/cost accounting,
  retry, backoff, telemetry, or log upload;
- generate pipeline output objects or modify `self.cards`;
- call a writer, create an Anki note, write to Anki, or change note-type fields.

## Future Work

A future PR may connect these projections to a read-only UI. That UI must keep
safe summaries separate from user-visible excerpts and must not treat preview,
consent, or credential status as authorization to execute or write to Anki.
