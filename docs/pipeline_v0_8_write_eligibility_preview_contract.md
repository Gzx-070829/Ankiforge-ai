# AnkiForge AI v0.8 Write Eligibility Preview Contract

## 1. Scope

v0.8 PR3 converts the PR2 `LocalHumanReviewPreview` into a descriptive,
read-only `WriteEligibilityPreview`. It answers whether local review and
quality conditions appear satisfied. It does not grant write authorization or
perform any write preparation.

PR3 creates no `WriteReadyPreviewItem`, Write Plan, `GeneratedCard`, writer,
Anki note, or collection mutation.

## 2. Input Boundary

The adapter accepts only `LocalHumanReviewPreview` or `None`. It does not accept
legacy cards, a provider configuration, writer, Anki collection, runtime
context, `GeneratedCard`, or `WriteReadyPreviewItem`.

The dialog path is:

```text
current widgets
  -> PR1 decision-draft helper
  -> PR2 local HumanReview preview
  -> PR3 Write Eligibility preview
  -> local read-only rendering
```

PR3 does not call the pipeline controlled-write bridge because that bridge can
also construct write-ready preview objects. PR3 independently presents the
same high-level review/quality semantics without entering that layer.

## 3. Eligibility Status

The allowed descriptive states are:

```text
eligible
blocked
needs_review
unknown
```

The mapping is:

- approved + locally valid + passed/warning quality -> `eligible`;
- approved + failed/unchecked quality -> `blocked`;
- pending -> `needs_review`;
- rejected -> `blocked`;
- needs_edit -> `blocked`; and
- no local review preview -> `unknown`.

Blocking reasons use stable local codes such as `quality_failed`,
`quality_unchecked`, `local_review_invalid`, `review_pending`,
`review_rejected`, and `review_needs_edit`.

## 4. Defensive Validation

The adapter verifies the exact PR2 fixed safety rows and rejects forged review,
quality, or validation combinations. Approved previews are locally valid only
for passed/warning quality. Non-approved previews must retain the PR2 valid
local-review state.

`eligible` means only that the displayed local conditions are satisfied. It is
not write authorization, final confirmation, duplicate checking, a Write Plan,
or permission to touch Anki.

## 5. Safe Output

The preview displays candidate ID, review decision, quality status, local
review validity, eligibility status, blocking reasons, and fixed safety notes.

Candidate ID is excluded from repr and appears in `to_safe_dict()` only as
presence and length. Reviewer note, Front, Back, Source, and their excerpts do
not enter the PR3 DTO or safe output.

## 6. Fixed Safety Meaning

Every eligibility preview says:

```text
这是只读写入资格摘要
Write authorization：未授予
尚未生成 Write Plan
尚未生成 GeneratedCard
尚未生成 WriteReadyPreviewItem
不调用 writer
不写入 Anki
关闭后丢弃
```

## 7. UI Integration and Stale-State Handling

PR3 adds one hidden-until-generated section and one explicit command:

```text
Write Eligibility 只读摘要（不写入）
生成 Write Eligibility 只读摘要（不写入）
```

Changing decision text, reviewer note, candidate selection, PR1 draft state,
or PR2 local preview clears any old eligibility summary. Generating a new
eligibility summary always rebuilds the PR1 view and PR2 preview first.

No save, apply, provider-call, card-generation, Write Plan, add-to-Anki,
approve-and-write, confirm-write, execution, or write command is added.

## 8. Isolation

The adapter imports only the PR1 display-row type and PR2 local-preview type.
It does not import Qt, Anki, provider, network, config, secret store, transport,
executor, writer, controlled-write bridge, or pipeline write objects.

PR3 does not modify MainDialog, PR1 helper, PR2 adapter, provider UI, writer,
pipeline bridge, configuration, `self.cards`, or the Anki collection.

## 9. Automatic Tests

Pure Python tests cover empty, eligible, blocked, needs-review, and invalid
states; stable reasons; forged-state rejection; content-safe output; fixed
no-authorization/no-write rows; forbidden dependencies; adapter sequencing;
and stale-summary clearing.

Tests import no Qt, Anki, provider, network, config, or writer dependency and
make no network request.

## 10. Manual Anki Acceptance

1. Open the existing Human Review decision-draft dialog.
2. Confirm no eligibility section is visible before generation.
3. Generate pending, rejected, and needs_edit local review previews, then build
   eligibility summaries and verify needs_review/blocked states and reasons.
4. Confirm approved + passed/warning displays `eligible`.
5. Confirm failed/unchecked quality cannot yield an eligible state.
6. Confirm candidate ID, decision, quality, review validity, status, reasons,
   and all fixed safety rows are visible.
7. Change decision or reviewer note and confirm the old eligibility disappears.
8. Change candidate and confirm the old eligibility disappears.
9. Close and reopen; confirm drafts, local reviews, and eligibility summaries
   are gone.
10. Confirm no Write Plan, GeneratedCard, write-ready, save, provider,
    generation, add-to-Anki, confirmation, execution, or write command exists.
11. Confirm legacy candidates/settings remain unchanged, no note is created,
    and no provider or network activity occurs.

## 11. Non-Goals

PR3 does not grant write authorization, build a Write Plan, create
`GeneratedCard` or `WriteReadyPreviewItem`, invoke the controlled-write bridge,
perform duplicate checks, modify legacy candidates, call a writer, write or
edit an Anki note, invoke a provider, access the network, change configuration,
or push to GitHub.
