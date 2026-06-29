# v0.6 Real Provider Dry-Run Executor

## Purpose

PR7b-1 defines a real-provider-capable executor boundary for an explicitly
consented OpenAI-compatible dry run. The supported helper always passes this
executor through the PR7a execution boundary. The result stops at
KnowledgePoint extraction.

PR7b-1 does not provide a CLI and does not provide a normal-user UI. PR7b-2 is
reserved for discussion of a developer-only manual harness.
PR7b-1 does not write to Anki.

## Explicit Dependencies

`OpenAICompatibleProviderDryRunExecutor` requires three explicit inputs:

* a non-secret `UserProviderProfile`;
* an implementation of the `ProviderSecretStore` contract; and
* an injected OpenAI-compatible transport.

It does not create a default HTTP transport. Automatic tests inject a fake
transport and are entirely offline. PR7b-1 does not read environment
variables, files, Anki configuration, or legacy `config.json` behavior.

## Consent And Execution Boundary

The public execution helper delegates to PR7a
`execute_provider_dry_run_with_boundary()`. Before loading a secret, PR7a and
the executor both verify the profile, provider selection, affirmative consent,
secret reference, and `knowledge_point_extraction` target. `localhost` and
`127.0.0.1` receive no consent exception.

Only the existing `source_excerpt_preview` becomes the text of the in-memory
`SourceChunk`. No full source, file, UI text, Anki deck, clipboard, or external
notes are read.

## Secret Reveal Boundary

`_extract_inside_secret_reveal_boundary()` is the only function in the module
allowed to call `ProviderSecretValue.reveal()`. The revealed value is a local
variable used only to create the runtime OpenAI-compatible config. Config,
provider, and extractor objects remain local to the same call and are not
stored on the executor or returned.

This is lifecycle minimization, not encryption. Python strings cannot be
reliably zeroed, and debuggers, crash dumps, tracebacks, or a malicious secret
store may still observe runtime memory. PR7b-1 does not save, print, log,
serialize, validate, or migrate an API key.

## Error Boundary

The executor recognizes only a minimal set of structured outcomes:

* a missing secret maps to the existing authentication display category;
* `invalid_json` maps to the existing invalid-JSON category;
* `malformed_response` maps to the existing malformed-response category; and
* every other structured provider failure maps to the existing unknown category.

The result display is still produced by the PR7a and PR5 safe mappings. Raw
exception messages, HTTP bodies, provider payloads, authorization headers,
source text, prompts, and stack traces are not copied into outcomes or safe
dictionaries. A structured SDK/HTTP exception classifier is deferred to a
separate future PR, such as PR7d or v0.7; PR7b-1 and PR7c do not implement one.

## Non-Goals

PR7b-1 does not:

* provide a CLI, settings page, consent dialog, or normal-user entry point;
* create a default HTTP transport or automatically access the network;
* implement a production secret-store backend or save an API key;
* read or migrate keys from legacy configuration;
* modify the v0.5 developer smoke harness;
* implement retry, backoff, telemetry, token accounting, or cost accounting;
* generate `CardCandidate` or `HumanReview` values;
* run Quality Gate, the full orchestrator, or the review bridge;
* create an Anki note, modify `self.cards`, call a writer, or write to Anki; or
* alter note types or legacy provider/config behavior.

## Downstream Safety

The result stops at KnowledgePoint extraction. Any future product path must
still pass through Human Selection, CardCandidate generation, Quality Gate,
Human Review, Write Eligibility, duplicate checks, and final human confirmation
before any Anki write can occur.
