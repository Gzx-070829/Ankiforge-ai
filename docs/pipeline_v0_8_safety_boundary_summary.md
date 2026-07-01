# AnkiForge AI v0.8 Safety Boundary Summary

## 1. What v0.8 Is

v0.8 is a local, non-persistent explanation of the path from a card candidate
to a possible future write decision:

```text
Human Review decision draft
  -> local HumanReview preview
  -> Write Eligibility summary
  -> read-only Write Plan preview
  -> duplicate readiness and final-confirmation contract preview
```

Each arrow is an in-memory projection. The chain stops before duplicate
checking, final user confirmation, write authorization, and execution.

## 2. What Each Stage Means

- A Human Review decision is a local draft, not a saved formal review.
- Approved means the local draft and Quality Gate allow an approved preview;
  it does not authorize writing.
- Write Eligibility describes whether local prerequisites appear satisfied; it
  does not authorize writing.
- A Write Plan preview explains fixed field mappings, tags, and hypothetical
  targets; it is not a real Write Plan and cannot execute.
- Duplicate readiness says duplicate checking remains required and has not run.
- A final-confirmation contract preview explains what a future confirmation
  would need; it is not a user confirmation, consent record, or authorization.

## 3. Hard Technical Boundary

The v0.8 chain does not:

- call a provider or access the network;
- accept an API key or inspect credential state;
- persist review drafts, previews, plans, confirmations, or authorizations;
- generate a formal `GeneratedCard` or `WriteReadyPreviewItem`;
- execute duplicate checking;
- read a real Anki collection, deck, note type, or note;
- create or update an Anki note;
- call a writer;
- modify `self.cards`; or
- expose a real write, add-to-Anki, execute, duplicate-check, confirm-write, or
  approve-and-write command.

Safe serialization excludes candidate identifiers and complete user content.
Runtime UI may display the current candidate identifier and bounded local
summaries solely inside the open dialog.

## 4. Configuration and Repository Boundary

- Local `ankiforge_ai/config.json` is ignored and not tracked.
- `ankiforge_ai/config.example.json` is a tracked sanitized template; its
  credential-bearing value remains empty.
- Add-on runtime sync must never copy or overwrite local `config.json`.
- The rollback backup remains in `Anki2/addon_backups`, outside `addons21`.
- The GitHub remote is configured, but local work after `534f2ed` remains
  unpushed until the user gives separate explicit authorization.

## 5. Why v0.8 Stops Here

The current UI proves the review and planning concepts while keeping every
irreversible or privacy-sensitive operation absent. This separates “the UI can
explain a future write” from “the program may write.” Those are different
capabilities and require different authorization.

No v0.8 status can be promoted by interpretation:

```text
approved != write authorization
eligible != write authorization
ready_preview != executable Write Plan
ready_for_future_confirmation != final user confirmation
```

## 6. Recommended v0.9 Theme

The recommended v0.9 theme is a beginner-friendly UI, newcomer mode, and
workflow guidance. The current developer terminology should be translated into
a process ordinary users can understand:

1. Choose material.
2. Preview what AI would do.
3. Check the proposed cards.
4. Confirm the risks and what data/actions are involved.
5. Decide whether writing to Anki should be considered.

This work should emphasize plain language, progressive disclosure, safe empty
states, and a visible distinction between preview, validation, confirmation,
authorization, and execution.

## 7. v0.9 Still Must Not Default to Real Writing

Beginner-friendly wording must not weaken the technical boundary. v0.9 should
not enable a real write path by default, infer consent from UI navigation, or
treat an approved review as permission to mutate Anki.

Any real-writing capability must be delivered through a separate PR with:

- explicit scope and user authorization;
- a concrete duplicate-check design;
- exact note type, deck, field, and tag review;
- a final confirmation tied to the exact content;
- transactional and rollback behavior;
- isolated automated tests;
- separate manual Anki acceptance; and
- an explicit decision about whether and when it may be enabled.

The real-writer PR must not be smuggled into newcomer-mode work or inferred
from this v0.8 release seal.

## 8. Seal Statement

v0.8 is complete when PR1 through PR6 are merged locally, all automated and
manual acceptance checks pass, the repository is clean, local configuration
and backup remain intact, and no unauthorized push occurs.

That seal certifies the read-only review and planning boundary only. It grants
no permission to run providers, duplicate checks, writers, or Anki mutations.
