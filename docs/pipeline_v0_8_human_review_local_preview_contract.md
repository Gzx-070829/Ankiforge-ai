# AnkiForge AI v0.8 Local HumanReview Preview Contract

## 1. Scope

v0.8 PR2 converts a PR1 Human Review decision draft into a disposable local
`LocalHumanReviewPreview`. The preview is a UI-layer DTO, not the pipeline
`HumanReview` model, because PR2 must not imply a finalized review or write
authority.

PR2 adds no persistence, provider execution, write-eligibility calculation,
card generation, writer call, or Anki write.

## 2. Input Boundary

The adapter accepts only:

- `HumanReviewDecisionDraftViewData`, produced by the PR1 helper; and
- the matching `HumanReviewDecisionDraftInput`.

It does not accept legacy cards, provider or runtime configuration, a writer,
Anki collection, `GeneratedCard`, `WriteReadyPreviewItem`, or execution context.

The dialog preview path is:

```text
current widgets
  -> HumanReviewDecisionDraftInput
  -> build_human_review_decision_draft_view_data()
  -> build_local_human_review_preview()
  -> local UI rendering
```

## 3. Preview Content

The local preview displays:

- candidate ID;
- local review decision;
- reviewer-note excerpt and length;
- Quality Gate status;
- whether the local decision is valid;
- validation errors, if any; and
- fixed no-save/no-write status rows.

The reviewer-note excerpt is limited to 80 characters. Complete Front, Back,
Source, and reviewer-note text do not enter repr or `to_safe_dict()`.

## 4. Quality and Identity Validation

The adapter requires the draft candidate ID and decision to match the PR1 view.
Reviewer-note presence and length must also match. It verifies the PR1 fixed
safety rows before producing any preview.

`approved` with `passed` or `warning` quality can produce a valid local preview.
`approved` with `failed` or `unchecked` quality produces an invalid local
preview with the PR1 local validation error. Pending, rejected, and needs_edit
remain valid local previews regardless of failed quality.

## 5. Fixed Safety Meaning

Every generated preview says:

```text
这是本地 HumanReview 预览
尚未保存
尚未形成写入授权
尚未生成 GeneratedCard
尚未生成 WriteReadyPreviewItem
不调用 writer
不写入 Anki
关闭后丢弃
```

Local validity is not formal review finalization, write eligibility, final
confirmation, or permission to modify Anki.

## 6. UI Integration

PR2 extends the existing PR1 dialog with one hidden-until-generated group:

```text
本地 HumanReview 预览（不写入）
```

It adds one explicit command:

```text
生成本地 HumanReview 预览（不写入）
```

The existing local draft update and close commands remain. No save, apply,
provider-call, card-generation, eligibility-calculation, add-to-Anki,
approve-and-write, confirm-write, or write command is added.

Changing candidates or updating a draft clears any previously rendered local
preview so stale data cannot be mistaken for the current draft.

## 7. Isolation

The adapter imports only PR1 UI-layer draft types and `dataclasses`. It does not
import Qt, Anki, provider, network, config, secret-store, transport, executor,
writer, write bridge, or pipeline review models.

PR2 does not modify MainDialog, PR1 helper policy, provider UI, writer code,
pipeline bridge code, configuration, `self.cards`, or the Anki collection.

## 8. Automatic Tests

Pure Python tests cover supported decisions, valid and invalid approved states,
empty input, candidate/decision matching, reviewer-note safety, content safety,
fixed no-save/no-write rows, forbidden dependencies, dialog sequencing, and
the exact local-only button surface.

Tests import no Qt, Anki, provider, network, config, or writer dependency and
make no network request.

## 9. Manual Anki Acceptance

1. Open the existing `Human Review 决策草稿` entry.
2. Confirm no PR2 preview is shown before the new command is selected.
3. Select pending, rejected, and needs_edit drafts and generate local previews.
4. Confirm approved is available only for passed/warning quality.
5. Confirm failed/unchecked approved input cannot produce a valid preview.
6. Enter a long reviewer note and confirm only a short excerpt plus length is
   displayed in the local preview.
7. Confirm candidate ID, decision, quality, local validity, and fixed safety
   rows are visible.
8. Change candidate or update the draft and confirm the old preview disappears.
9. Close and reopen; confirm drafts and previews are gone.
10. Confirm no save, apply, provider, generation, eligibility, add-to-Anki,
    approve-and-write, confirm-write, or write command exists.
11. Confirm legacy candidates/settings remain unchanged, no note is created,
    and no provider or network activity occurs.

## 10. Non-Goals

PR2 does not create or persist a formal HumanReview, calculate Write
Eligibility, generate `GeneratedCard` or `WriteReadyPreviewItem`, perform
duplicate checks, modify legacy candidates, call a writer, write or edit an
Anki note, invoke a provider, access the network, change configuration, or push
to GitHub.
