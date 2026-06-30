# AnkiForge AI v0.8 Human Review Decision Draft UI Contract

## 1. Scope

v0.8 PR1 adds an independent, in-memory Human Review decision-draft UI for
new-pipeline CardCandidate previews. It lets a user describe a possible review
decision without creating a formal `HumanReview`, calculating write authority,
generating a legacy card, or writing to Anki.

## 2. Entry and Data Source

The MainDialog places `Human Review 决策草稿` beside the existing offline mock
pipeline preview and KnowledgePoint-selection entries. It is not placed near
the legacy `添加到 Anki` command.

With no selected Markdown file, the entry opens a safe empty state. With an
explicitly selected file, the handler runs only the existing offline mock
pipeline and adapts its CardCandidates and Quality Gate results into existing
`CardCandidatePreviewItem` values. It does not read legacy `self.cards`, legacy
provider settings, or provider credentials.

## 3. Local Draft Fields

The dialog displays the current candidate ID, short Front/Back/Source
summaries, Quality Gate status, and quality issues. It allows only these local
decision values:

```text
pending
approved
rejected
needs_edit
```

It also accepts a reviewer note owned only by the current dialog. Candidate
drafts live in a private in-memory mapping and disappear when the dialog
closes.

## 4. Approval Policy

`approved` is available only when the existing preview state says Quality Gate
is `passed` or `warning`, approval is allowed, and no quality error exists.
`failed` and `unchecked` candidates cannot form an approved draft.

The helper rejects mismatched candidate IDs and forged inconsistent quality or
approval states. Qt does not duplicate the approval policy; it asks the pure
helper for the allowed decision choices.

## 5. Fixed Safety Meaning

Every empty or populated state displays these boundaries:

```text
仅审核草稿
尚未形成正式 HumanReview
尚未计算写入授权
不生成 GeneratedCard
不修改 legacy 候选卡
不调用 writer
不写入 Anki
关闭后丢弃
```

An approved draft is still only a draft. It is not a formal review, write
eligibility, final confirmation, or Anki-write authorization.

## 6. Safe Output

The UI may display a maximum 120-character summary of candidate Front, Back,
Source, and quality issue messages. Draft input and display values are excluded
from dataclass repr.

`to_safe_dict()` records only presence, lengths, fixed labels, the local
decision, and fixed safety metadata. It does not copy complete Front, Back,
Source, reviewer note, or issue text. No logging or persistence is added.

## 7. Runtime Isolation

PR1 does not import or call a provider, network client, config loader, secret
store, transport, executor, writer, Anki collection API, or note API from the
new helper/dialog path. It does not create `HumanReview`, `GeneratedCard`, or
`WriteReadyPreviewItem` objects.

The MainDialog handler does not reference `self.cards`, `add_to_anki`, legacy
provider controls, API key input, `self.config`, writer helpers, or `mw.col`.
The pre-existing legacy paths remain unchanged and separate.

## 8. UI Surface

The dialog title is `Human Review 决策草稿`. Its only commands are:

```text
更新审核草稿（仅本地）
关闭
```

It has no save, apply, send, run, provider-call, card-generation,
approve-and-write, confirm-write, add-to-Anki, write-to-Anki, or API key
control. The top safety notice and bottom commands remain outside the
scrollable middle content area.

## 9. Automatic Tests

Pure Python tests cover safe empty state, all four draft decisions, approval
policy, candidate-ID matching, forged-state rejection, short display summaries,
safe repr/dictionary output, fixed no-write semantics, forbidden imports and
calls, the exact dialog button surface, and MainDialog handler isolation.

Tests do not import Qt, Anki, provider, writer, config, or network modules and
make no network request.

## 10. Manual Anki Acceptance

1. Confirm Anki shows one AnkiForge AI menu item and the main window opens.
2. Open `Human Review 决策草稿` without selecting a file and confirm the safe
   empty state appears without reading legacy candidates.
3. Select a small Markdown fixture and reopen the dialog.
4. Confirm candidate ID, short candidate summaries, quality status, and issues
   are visible.
5. Confirm pending, rejected, and needs_edit can be stored as local drafts.
6. For passed/warning quality, confirm approved is available as a local draft.
7. For a failed-quality fixture, confirm approved is unavailable.
8. Enter a distinctive reviewer note, switch candidates, and confirm drafts
   remain only in the currently open dialog.
9. Close and reopen; confirm all review decisions and reviewer notes are gone.
10. Confirm the middle content scrolls and update/close remain visible.
11. Confirm no save, provider, generation, approval-and-write, confirmation, or
    Anki-write command exists.
12. Confirm legacy candidates and settings are unchanged, no note is created,
    and no provider or network activity occurs.

## 11. Non-Goals

PR1 does not finalize a HumanReview, compute Write Eligibility, create a write
plan, perform duplicate checks, create a GeneratedCard, modify `self.cards`,
call a writer, write or edit an Anki note, persist a decision, call a provider,
access the network, modify configuration, or push to GitHub.
