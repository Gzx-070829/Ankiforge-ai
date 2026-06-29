# v0.6 Provider Dry-Run Execution Boundary

## Purpose

PR7a defines a pure Python execution boundary for a consent-gated provider
dry run. It accepts an already validated `ProviderDryRunRequest`, requires an
explicit executor, and returns a read-only result that stops at
`knowledge_point_extraction`.

The production module contains only an executor protocol and boundary models.
The fake executor used for automatic verification exists only in the test
suite.

## Execution Input

`ProviderDryRunExecutionInput` carries the existing request with its `repr`
disabled. It does not add a full-source field. Fake execution can read only the
existing `source_excerpt_preview`, which remains limited by the PR4 request
contract. Its safe dictionary reports the profile ID, chunk ID, preview length,
and target stage without returning the preview text, consent text, or secret
reference.

The preview length limit is a data-minimization boundary, not anonymization or
de-identification. Preview text can still contain private information.

## Executor Contract

`ProviderDryRunExecutor` is a structural protocol. PR7a requires callers to
provide an executor explicitly and does not create one. A normalized executor
outcome is either:

* success with a tuple of zero or more `KnowledgePoint` values; or
* failure with one normalized `ProviderErrorKind` and no knowledge points.

The outcome cannot carry raw exceptions, stack traces, response bodies,
provider payloads, credentials, authorization headers, or source text. PR7a
does not classify real SDK or HTTP exceptions and does not broadly catch an
executor exception. Real exception classification is deferred.

## Boundary Validation

Before invoking the explicit executor, the boundary revalidates that:

* the target stage is `knowledge_point_extraction`;
* the selection, consent record, and secret-reference profile agree;
* the selection sends user content and requires explicit consent; and
* consent is an explicit affirmative record.

Local endpoints such as `localhost` and `127.0.0.1` receive no consent
exception. They remain provider destinations that can receive user content.

## Result Contract

`ProviderDryRunExecutionResult` is frozen. Knowledge points are stored as a
tuple and omitted from `repr`. Its safe dictionary exposes only safe request
identifiers, preview length, knowledge-point count, fixed safety flags, and an
optional `ProviderErrorDisplay` projection.

The following properties are fixed and cannot be enabled through constructor
arguments:

* `target_stage == "knowledge_point_extraction"`
* `will_write_to_anki is False`
* `will_generate_cards is False`
* `will_create_anki_notes is False`
* `will_modify_self_cards is False`

Normalized executor errors are mapped through the existing fixed provider
error-display taxonomy. Raw exception messages and raw provider bodies are
never copied into the result.

## Non-Goals

PR7a does not:

* call a real provider or execute a real provider dry run;
* read, validate, save, print, or serialize an API key;
* access `ProviderSecretStore` or call `ProviderSecretValue.reveal()`;
* create or call an HTTP transport or provider factory;
* access the network, environment variables, files, UI, or an Anki deck;
* integrate with UI, Qt, `aqt`, Anki, the orchestrator, or the review bridge;
* generate `CardCandidate`, `HumanReview`, or final Anki notes;
* modify `self.cards`, call a writer, or write to Anki;
* alter note types, legacy configuration, or legacy provider behavior; or
* implement retry, backoff, token accounting, cost accounting, or logging.

## Downstream Safety

The result stops at knowledge-point extraction. Any later product path must
still pass through Human Selection, CardCandidate generation, Quality Gate,
Human Review, Write Eligibility, duplicate checks, and final human
confirmation before any Anki write can occur.

PR7b may discuss a manual real-provider dry-run harness. It must remain behind
the explicit consent and secret boundaries and must not convert this execution
result into Anki cards or notes.
