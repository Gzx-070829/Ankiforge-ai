# AnkiForge AI v0.6 Provider User Flow and Release Checklist

## 1. Scope

PR8 closes the v0.6 provider user-flow documentation and release checklist.
It is a documentation PR, not a feature PR.

PR8 does not add UI, an exception classifier, an Anki write path, a production
key-storage backend, or any v0.7 implementation.

## 2. v0.6 Outcome Summary

v0.6 established the following provider safety components:

- a non-secret provider profile and runtime-secret boundary;
- the `ProviderSecretStore` contract without a production backend;
- provider selection and explicit-consent models;
- a consent-gated provider dry-run request model;
- a fixed safe provider error-display mapping;
- a read-only provider preview model;
- a provider dry-run execution boundary;
- a real-provider-capable executor boundary with an injected transport;
- a developer-only, consent-gated real-provider dry-run harness; and
- provider dry-run manual-acceptance documentation.

These components establish boundaries for future product work. They do not
expose a normal-user real-provider feature.

## 3. Current Capability

The current real-provider capability is limited to:

```text
developer-only manual real-provider dry run
-> explicit consent
-> short preview only
-> KnowledgePoint extraction only
```

It is not an ordinary-user UI, a complete provider-settings flow, formal API
key storage, automatic card generation, or an Anki write path.

## 4. End-to-End Safety Model

The v0.6 model is:

```text
UserProviderProfile
-> ProviderSelection
-> ProviderConsentRecord
-> ProviderSecretRef
-> ProviderDryRunRequest
-> ReadOnlyProviderPreview
-> ProviderDryRunExecutionInput
-> ProviderDryRunExecutor
-> ProviderDryRunExecutionResult
-> KnowledgePoint extraction result
```

The read-only preview is a safe projection, not execution authorization. The
execution result stops at KnowledgePoint extraction. v0.6 does not
automatically continue into Human Selection, `CardCandidate` generation,
Quality Gate, Human Review, Write Eligibility, final user confirmation, or an
Anki writer.

## 5. Ordinary User Explanation

Before information is sent to an AI provider, a user should know which
provider will receive it and must explicitly agree to send it.

v0.6 does not yet provide that normal-user interface. Its real-provider dry
run is a developer-only verification path. Even when the provider succeeds,
the result is only a set of knowledge points. It does not automatically create
cards or write anything to Anki.

Any future Anki write must remain behind human review and a final user
confirmation.

## 6. Developer Explanation

The PR7b-2 harness is manual-only and requires `--confirm-send`. It accepts a
temporary key only through `ANKIFORGE_DEV_API_KEY`. The environment variable
and the harness's private one-shot adapter are not production key storage.

Automatic tests must remain offline, and CI must never invoke a real provider.
Do not paste real-provider output or user material into an issue. Remove the
temporary environment variable after every manual run.

Detailed commands and failure scenarios are documented in
`docs/pipeline_v0_6_provider_dry_run_acceptance.md` and
`docs/dev_real_provider_smoke.md`.

## 7. Secret Boundary Checklist

- [ ] No API key is stored in `UserProviderProfile`.
- [ ] No API key is stored in `ProviderSelection`.
- [ ] No API key is stored in `ProviderDryRunRequest`.
- [ ] No API key is stored in a preview DTO.
- [ ] No API key is stored in `ProviderDryRunExecutionResult`.
- [ ] No API key appears in `repr` output.
- [ ] No API key appears in a safe dictionary.
- [ ] No API key appears in `ProviderErrorDisplay`.
- [ ] No real API key appears in a documentation fixture.
- [ ] No real API key appears in a test fixture.
- [ ] No API key appears in logs.
- [ ] Secret reveal remains confined to the PR7b-1 narrow boundary.
- [ ] Reviewers acknowledge that Python strings cannot be reliably cleared;
      the implementation only minimizes credential lifetime.

## 8. Consent Boundary Checklist

- [ ] No consent means no provider request.
- [ ] `--confirm-send` remains a developer-only manual confirmation.
- [ ] `localhost` and `127.0.0.1` do not bypass consent.
- [ ] Consent authorizes only sending the short preview to the selected
      provider for KnowledgePoint extraction.
- [ ] Consent does not authorize writing to Anki.
- [ ] Consent does not authorize creating a final Anki note.

## 9. Source Preview Boundary Checklist

- [ ] Only the explicitly supplied short preview is sent.
- [ ] The preview limit remains 500 characters.
- [ ] Input over the limit fails.
- [ ] Oversized input is not silently truncated and sent.
- [ ] The harness does not read a complete source.
- [ ] The harness does not read files.
- [ ] The harness does not read an Anki deck.
- [ ] The harness does not read UI text.
- [ ] The harness does not read the clipboard.
- [ ] The harness does not read an Obsidian vault.
- [ ] Source preview text is excluded from safe dictionaries and error
      displays.

## 10. Error Display Boundary Checklist

- [ ] User-visible failures use `ProviderErrorDisplay`.
- [ ] Raw exceptions are not displayed.
- [ ] Raw provider bodies are not displayed.
- [ ] Stack traces are not displayed.
- [ ] Authorization data is not displayed.
- [ ] API keys are not displayed.
- [ ] Prompts are not displayed.
- [ ] Source text is not displayed.
- [ ] A structured SDK/HTTP exception classifier remains deferred to a
      separate future PR.

## 11. No-Write Checklist

- [ ] The dry run does not generate `CardCandidate` values.
- [ ] The dry run does not generate `HumanReview` values.
- [ ] The dry run does not create an Anki note.
- [ ] The dry run does not modify `self.cards`.
- [ ] The dry run does not call a writer.
- [ ] The dry run does not write to Anki.
- [ ] The dry run does not modify an Anki note type.
- [ ] The dry run does not bypass Human Selection.
- [ ] The dry run does not bypass Quality Gate.
- [ ] The dry run does not bypass Human Review.
- [ ] The dry run does not bypass Write Eligibility.

## 12. v0.6 Closing Checklist

- [ ] The full unittest suite passes.
- [ ] `python -m compileall .` passes.
- [ ] `git diff --check` passes.
- [ ] The release worktree is clean.
- [ ] Documentation and fixture scans contain no real credentials.
- [ ] Automatic tests remain entirely offline.
- [ ] No Anki write occurs during automatic or manual dry-run verification.
- [ ] Documentation does not claim that normal-user provider UI exists.
- [ ] The developer harness still requires `--confirm-send`.
- [ ] A missing temporary key fails safely before provider execution.
- [ ] A preview over 500 characters fails without being sent.
- [ ] Provider failures produce only the safe error display.
- [ ] A successful manual dry run stops at KnowledgePoint extraction.

## 13. Release Checklist

- [ ] `main` is clean before and after the release merge.
- [ ] All tests pass on the release commit.
- [ ] Compileall and diff checks pass on the release commit.
- [ ] Documentation and tests contain no real secret or API key fixture.
- [ ] The provider dry-run path has no route to Anki writing.
- [ ] Ordinary-user documentation does not overclaim v0.6 capability.
- [ ] The real-provider harness is clearly labeled developer-only.
- [ ] Proposed v0.7 next steps are documented as future work.

## 14. Proposed v0.7 Transition

The project should not remain indefinitely at contract boundaries. Proposed
v0.7 productization work includes:

- a read-only provider-settings and preview UI;
- an explicit consent-dialog UI;
- a controlled dry-run UI entry point that still stops at KnowledgePoint
  extraction;
- improved KnowledgePoint selection UI;
- an ordinary-user usage and privacy guide; and
- AnkiWeb readiness documentation.

These items are proposed future work, not v0.6 features. A more complete new
pipeline Anki-write path should not be evaluated before v0.8. That later work
would need `CardCandidate` generation improvements, Quality Gate improvements,
a Human Review workbench, a Write Eligibility-to-controlled-write bridge, and
final user confirmation before any Anki write.

## 15. Non-Goals

PR8 does not:

- add an ordinary-user UI, provider-settings UI, or consent-dialog UI;
- add a production key-storage backend or migrate an old key;
- add a provider catalog or preset;
- add token or cost accounting;
- add retry or backoff;
- add a structured SDK/HTTP exception classifier;
- generate `CardCandidate` or `HumanReview` values;
- write to Anki or modify an Anki note type;
- publish an AnkiWeb release; or
- implement v0.7 or v0.8 work.
