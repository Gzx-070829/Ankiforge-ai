# AnkiForge AI v0.8 Final Write Confirmation Preview Contract

## 1. Scope

PR5 adds a read-only preview of the gates that a future final write
confirmation flow would require. It is a local explanatory contract, not a
confirmation request, consent record, write authorization, duplicate check,
or executable write plan.

The preview is discarded when the Human Review draft dialog closes.

## 2. Input Boundary

The adapter accepts only a PR4 `ReadOnlyWritePlanPreview` or `None`.

It does not accept candidate content, reviewer notes, legacy `self.cards`, a
writer object, Anki collection, provider configuration, `GeneratedCard`,
`WriteReadyPreviewItem`, confirmation token, consent record, or runtime
execution context.

The adapter verifies that the input still carries PR4's fixed mappings, tags,
unbound note type/deck text, safety rows, status relationships, and bounded
blocking-reason vocabulary. A forged or weakened input is rejected.

## 3. Output

`FinalWriteConfirmationPreview` exposes only:

- candidate presence for safe serialization; the candidate ID itself is
  hidden from `repr` and `to_safe_dict()`;
- Write Plan preview status;
- eligibility status;
- review decision;
- final contract status;
- duplicate-check state and requirement;
- duplicate result state;
- final-confirmation state;
- write-authorization state;
- write-execution state;
- fixed future steps;
- bounded blocking-reason codes;
- fixed safety rows.

It does not copy Front, Back, Source, reviewer-note content, or any credential.

## 4. Status Mapping

The final contract status is derived without side effects:

| Write Plan preview | Final contract status |
| --- | --- |
| `ready_preview` | `ready_for_future_confirmation` |
| `blocked` | `blocked` |
| `needs_review` | `needs_review` |
| `unknown` or missing | `unknown` |

`ready_for_future_confirmation` means only that the preceding local preview
chain is structurally ready to explain the future gates. It is not user
confirmation and grants no write authority.

## 5. Fixed Non-Execution State

Every output, including the safe empty state, fixes these values:

```text
duplicate_check_status: not_run
duplicate_check_requirement: required_before_write
duplicate_result: unknown
final_confirmation_status: not_requested
write_authorization: not_granted
write_execution: will_not_execute
```

PR5 never runs a duplicate check and never reads a real deck, note, note type,
or collection.

## 6. Required Future Steps

The preview lists stable explanatory steps:

1. Re-display and confirm candidate content.
2. Bind a real Anki note type and deck.
3. Run duplicate checking only inside a separately authorized future flow.
4. Display the duplicate-check result.
5. Request a separate final user confirmation.
6. Recalculate write authorization only after that confirmation.

Listing a future step does not execute, authorize, or persist it.

## 7. Safety Rows

The UI must clearly show:

```text
Source: 只读 Write Plan 预览
Preview meaning: 这是最终确认契约预览
User confirmation: 这不是用户确认
Duplicate check: 尚未执行
Anki collection: 尚未绑定真实 Anki collection
Write authorization: 不是写入授权；未授予
Write execution: 不会执行
Persistence: 未保存
GeneratedCard: 尚未生成 GeneratedCard
WriteReadyPreviewItem: 尚未生成 WriteReadyPreviewItem
Writer: 不调用 writer
Anki write: 不写入 Anki
Lifetime: 仅当前弹窗，关闭后丢弃
```

## 8. Dialog Flow

The existing Human Review draft dialog adds one button:

```text
生成最终确认契约预览（不写入）
```

Clicking it rebuilds the local chain in memory:

```text
review draft
  -> local HumanReview preview
  -> Write Eligibility preview
  -> read-only Write Plan preview
  -> final confirmation contract preview
```

The final preview is cleared whenever the candidate, decision, reviewer note,
local HumanReview preview, eligibility preview, or Write Plan preview changes.
It is not retained between dialog instances.

The final preview remains inside the existing scrollable content area. The
command rows stay outside the scroll area and remain reachable.

## 9. Forbidden UI and Runtime Actions

PR5 adds no command to:

- write or add a note to Anki;
- save, apply, approve-and-write, or confirm a write;
- run duplicate checking;
- create `GeneratedCard` or `WriteReadyPreviewItem`;
- call a writer, provider, transport, executor, or network client;
- access an Anki collection;
- save a plan, confirmation, consent record, or authorization.

The allowed button contains “不写入” to state its non-action explicitly; it
does not invoke a write path.

## 10. Dependency Isolation

The adapter is pure Python. Its only project inputs are the PR4 read-only DTO
and the existing display-row value type. It imports no Qt, Anki, provider,
network, configuration, secret store, transport, executor, writer,
controlled-write bridge, or pipeline write model.

PR5 does not modify MainDialog, PR1–PR4 adapters, provider UI, writer code,
pipeline write bridge, configuration, `self.cards`, or Anki collection logic.

## 11. Automated Tests

Pure-Python tests cover:

- missing and unknown Write Plan previews;
- ready, blocked, and needs-review mappings;
- fixed duplicate-check and confirmation states;
- fixed future steps and safety notes;
- safe serialization without candidate or user content;
- rejection of forged Write Plan state;
- absence of runtime write objects and forbidden dependencies;
- dialog adapter sequencing, stale-preview clearing, and button allowlist.

The tests require no Qt, Anki, provider, writer, collection, or network.

## 12. Manual Anki Acceptance

1. Confirm only one AnkiForge AI menu entry exists.
2. Open the Human Review decision draft dialog.
3. Confirm all PR1–PR4 local previews still work.
4. Generate the final confirmation contract for ready, blocked,
   needs-review, and unknown states.
5. Confirm duplicate check is `not_run`, required before write, and has an
   unknown result.
6. Confirm final confirmation is `not_requested` and authorization is
   `not_granted`.
7. Confirm execution is `will_not_execute`.
8. Change candidate, decision, note, or an upstream preview and confirm the old
   final preview disappears.
9. Confirm no write, add-to-Anki, execute, save, apply, duplicate-check,
   confirm-write, approve-and-write, provider, or API-key control exists.
10. Close and reopen the dialog; confirm the local draft and previews are gone.
11. Confirm no note, collection mutation, provider/network activity, or Anki
    user-data change occurs.

## 13. Non-Goals

PR5 does not perform duplicate detection, request or store user consent,
authorize a write, create a write-ready object, bind real Anki targets, call a
writer, create or update a note, invoke a provider, access the network, or
modify configuration. Those remain outside the v0.8 read-only preview chain.
