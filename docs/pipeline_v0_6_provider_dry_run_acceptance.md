# AnkiForge AI v0.6 Provider Dry-Run Acceptance

## 1. Scope

PR7c closes the documentation and manual-acceptance work for the PR7a,
PR7b-1, and PR7b-2 provider dry-run path. It is a documentation PR, not a
feature PR.

The current capability is developer-only. It is not an ordinary-user UI, a
formal provider-settings feature, a production key-storage solution, or an
Anki-writing feature.

## 2. Current Capability Boundary

The supported real-provider path is limited to:

```text
developer-only harness
-> consent-gated request
-> real-provider dry-run executor
-> KnowledgePoint extraction
```

It stops before `CardCandidate`, Quality Gate, `HumanReview`, Write
Eligibility, the Anki writer, or any Anki note creation. It does not modify
`self.cards`.

Any future product path must still pass through Human Selection,
`CardCandidate` generation, Quality Gate, Human Review, Write Eligibility,
duplicate checks, and final human confirmation before an Anki write can be
considered.

## 3. End-to-End Safety Chain

The developer-only path is:

```text
CLI developer-only harness
-> UserProviderProfile
-> ProviderSelection
-> ProviderConsentRecord
-> ProviderSecretRef
-> ProviderDryRunRequest
-> ProviderDryRunExecutionInput
-> PR7a execution boundary
-> PR7b-1 real-provider executor
-> secret-store load
-> single reveal boundary
-> explicit transport
-> safe provider wrapper
-> AIKnowledgePointExtractor
-> KnowledgePoint extraction result
-> ProviderDryRunExecutionResult
```

`ProviderDryRunExecutionResult` never continues into `CardCandidate`,
`HumanReview`, a writer, or Anki.

## 4. Consent Boundary

`--confirm-send` is the explicit human confirmation for the developer-only
harness. Without it, the harness must not read the key, create a transport,
create an executor, or access the network.

Endpoints on `localhost` or `127.0.0.1` do not bypass consent. An affirmative
consent record authorizes only sending the supplied short preview to the
selected provider for KnowledgePoint extraction. It does not authorize card
generation or Anki writing.

## 5. Secret Boundary

The API key does not enter `UserProviderProfile`, `ProviderSelection`,
`ProviderDryRunRequest`, `ProviderDryRunExecutionResult`, or a preview DTO. It
must not appear in `repr`, safe dictionaries, error displays, documentation
fixtures, or command output.

PR7b-1 has one reveal boundary. PR7b-2 reads the key from a temporary
developer environment variable and places it in a private one-shot adapter.
Neither the environment variable nor that adapter is a production secret
store.

This boundary minimizes credential lifetime; it is not encryption. Python
strings cannot be reliably cleared from memory, and debuggers or crash dumps
may still observe runtime values. The developer must remove the environment
variable after a manual run.

## 6. Source Preview Boundary

PR7b-2 sends only the short preview supplied through `--text`. The maximum
length is 500 characters. Input over that limit must fail; it must not be
truncated and sent.

The harness does not read a full source, file, Anki deck, UI field, clipboard,
or Obsidian vault. The source preview is excluded from safe dictionaries and
error displays. The length limit is data minimization, not anonymization; a
preview can still contain private material.

## 7. Transport and Network Boundary

PR7b-1 does not create a default HTTP transport. PR7b-2 may explicitly create
one only after `--confirm-send` and the required key checks pass.

Automatic tests are entirely offline. They require no real API key and must
not contact a real provider, public endpoint, or local server. A real request
can occur only when a developer deliberately runs the manual harness with all
required arguments and confirmation.

## 8. Error Display Boundary

User-visible failure information is represented by `ProviderErrorDisplay`.
PR7c does not implement a structured SDK or HTTP exception classifier.

The dry-run output must not parse or display a raw provider body, raw exception
message, stack trace, authorization data, API key, prompt, or source text. If a
structured exception classifier is needed, it must be implemented in a
separate future PR, such as PR7d or v0.7, after an independent privacy review.

## 9. Manual Acceptance Checklist

### 9.1 Missing Confirmation

- Run without `--confirm-send`.
- Expect a refusal before the key is read.
- Confirm no transport or executor is created and no network access occurs.

### 9.2 Missing Temporary Key

- Run with `--confirm-send` but without `ANKIFORGE_DEV_API_KEY`.
- Expect a safe failure before a provider request.
- Confirm the output contains no credential or raw diagnostic data.

### 9.3 Oversized Preview

- Supply `--text` with more than 500 characters.
- Expect a safe validation failure.
- Confirm the preview is neither truncated nor sent.

### 9.4 Offline Automatic Tests

- Run the full automatic test suite without a real key.
- Confirm fake transports are used and all network access remains blocked.

### 9.5 Valid Manual Provider Dry Run

- Use a short, non-private preview and an explicitly selected provider.
- Confirm the result reports only KnowledgePoint extraction status and count.
- Confirm no raw provider body is printed and no Anki write occurs.

### 9.6 Provider Failure

- Exercise a provider failure in a controlled developer environment.
- Confirm only the safe `ProviderErrorDisplay` projection is shown.
- Confirm no raw response, stack trace, source preview, or key is printed.

### 9.7 Run Completion

- Confirm the repository worktree gained no generated files.
- Confirm no Anki note was created and no existing note was changed.
- Remove the temporary environment variable.

## 10. Developer Runbook

Run this only in a developer environment. Never run a real-provider smoke test
in CI.

Set a temporary placeholder value through a protected local prompt or an
equivalent developer-only mechanism:

```powershell
$env:ANKIFORGE_DEV_API_KEY = "<your-dev-api-key>"
```

Then run the harness with explicit provider settings and confirmation:

```powershell
python -m scripts.dev_real_provider_smoke `
  --provider-id "manual-provider" `
  --provider-name "Manual Provider" `
  --model-name "manual-model" `
  --base-url "https://provider.example/v1" `
  --text "Short non-private learning preview." `
  --confirm-send
```

Do not paste output into an issue if it might contain user material. After the
run, remove the temporary environment variable:

```powershell
Remove-Item Env:ANKIFORGE_DEV_API_KEY
```

The more defensive hidden-prompt setup remains documented in
`docs/dev_real_provider_smoke.md`.

## 11. Non-Goals

PR7c does not:

- add an ordinary-user UI, provider-settings UI, or consent-dialog UI;
- add a production key-storage backend or migrate legacy keys;
- add a provider catalog or preset;
- add token or cost accounting;
- add retry or backoff;
- add a structured SDK or HTTP exception classifier;
- generate `CardCandidate` or `HumanReview` values;
- write to Anki, call the writer, or modify `self.cards`;
- change an Anki note type; or
- publish an AnkiWeb release.

## 12. Deferred Work

Possible later work includes a privacy-reviewed structured SDK/HTTP exception
classifier in PR7d or v0.7, read-only provider settings and preview UI in v0.7,
and a consent-dialog UI in v0.7.

A more mature `CardCandidate`, Quality Gate, and controlled Anki-write path may
be considered in v0.8. None of these items is implemented or authorized by
PR7c.
