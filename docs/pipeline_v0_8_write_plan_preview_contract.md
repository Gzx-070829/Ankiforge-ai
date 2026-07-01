# AnkiForge AI v0.8 Read-Only Write Plan Preview Contract

## 1. Scope

v0.8 PR4 converts the PR3 Write Eligibility summary into a read-only field-
mapping preview. It explains how a future write might map fields while granting
no authority and performing no preparation or execution.

The preview is not a saved or executable plan. PR4 creates no
`GeneratedCard`, `WriteReadyPreviewItem`, Anki note, writer, or collection
mutation.

## 2. Input Boundary

The adapter accepts only `WriteEligibilityPreview` or `None`. Candidate identity,
review decision, and quality status come from that already-safe projection.
Front, Back, Source, reviewer note, legacy cards, provider config, writer, Anki
collection, and runtime context are not accepted.

The dialog path is:

```text
current widgets
  -> PR1 decision draft
  -> PR2 local HumanReview preview
  -> PR3 Write Eligibility summary
  -> PR4 read-only Write Plan preview
  -> local rendering
```

## 3. Plan Status

The allowed states are:

```text
ready_preview
blocked
needs_review
unknown
```

Eligibility maps deterministically:

- eligible -> `ready_preview`;
- blocked -> `blocked` with preserved reasons;
- needs_review -> `needs_review` with preserved reasons; and
- unknown or no input -> `unknown` safe empty state.

`ready_preview` means only that a fixed mapping can be displayed. It is not
write authorization, duplicate clearance, final confirmation, or execution.

## 4. Fixed Mapping Preview

PR4 displays these fixed source-to-target mappings:

```text
Front -> Front
Back -> Back
Source -> Source
```

The fixed tag preview is:

```text
AnkiForgeAI
pipeline-preview
human-reviewed
```

No actual note-type or deck lookup occurs. The target labels are:

```text
未绑定真实 Anki note type，仅预览
未绑定真实 Anki deck，仅预览
```

## 5. Safe Output

The preview includes candidate ID, eligibility, review and quality states, plan
status, blocking reasons, fixed target labels, field mappings, tags, and safety
notes.

Candidate ID is excluded from repr and enters `to_safe_dict()` only as presence
and length. Front, Back, Source, reviewer note, and their excerpts never enter
the PR4 DTO or safe output.

## 6. Fixed Safety Meaning

Every preview states:

```text
这是只读 Write Plan 预览
Duplicate check：未执行
尚未绑定真实 Anki collection
Write authorization：未授予
Write execution：不会执行
Persistence：未保存
尚未生成 GeneratedCard
尚未生成 WriteReadyPreviewItem
不调用 writer
不写入 Anki
关闭后丢弃
```

## 7. UI and Stale-State Handling

PR4 adds one hidden-until-generated section and one command:

```text
只读 Write Plan 预览（不写入）
生成只读 Write Plan 预览（不写入）
```

The fixed bottom command area is split into two rows to avoid horizontal
overflow. Both rows remain outside the scrollable content.

Changing candidate, decision, reviewer note, PR1 draft, PR2 review preview, or
PR3 eligibility summary clears any old Write Plan preview. Generating a plan
always rebuilds every upstream local projection first.

No save, apply, provider-call, card-generation, plan execution, add-to-Anki,
approve-and-write, confirm-write, or write command is added.

## 8. Isolation

The adapter imports only the shared UI display-row type and PR3 eligibility
type. It does not import Qt, Anki, provider, network, config, secret store,
transport, executor, writer, controlled-write bridge, or pipeline write models.

PR4 does not modify MainDialog, PR1 helper, PR2 adapter, PR3 adapter, provider
UI, writer, pipeline bridge, configuration, `self.cards`, or Anki collection.

## 9. Automatic Tests

Pure Python tests cover empty, ready, blocked, needs-review, and unknown plans;
fixed mappings and tags; unbound targets; safe output; safety rows; forged-state
rejection; forbidden dependencies; adapter sequencing; stale-plan clearing; and
the exact local-only button surface.

Tests import no Qt, Anki, provider, network, config, or writer dependency and
make no network request.

## 10. Manual Anki Acceptance

1. Open the existing Human Review decision-draft dialog.
2. Confirm no Write Plan section appears before generation.
3. Build an eligible summary and confirm the plan status is `ready_preview`.
4. Build blocked and needs-review summaries and confirm their plan states and
   reasons are preserved.
5. Confirm unknown/no eligibility displays a safe unknown state.
6. Confirm fixed field mappings, fixed tags, and unbound target labels appear.
7. Confirm duplicate check is unexecuted and write authorization is not granted.
8. Change decision, note, candidate, local review, or eligibility and confirm
   the old Write Plan disappears.
9. Close and reopen; confirm all draft/review/eligibility/plan state is gone.
10. Confirm no save, provider, generation, execution, add-to-Anki,
    approve-and-write, confirm-write, or write command exists.
11. Confirm legacy candidates/settings remain unchanged, no note is created,
    and no provider or network activity occurs.

## 11. Non-Goals

PR4 does not authorize, save, or execute a Write Plan; run duplicate checks;
bind a real note type, deck, or collection; create `GeneratedCard` or
`WriteReadyPreviewItem`; modify legacy candidates; call a writer; write or edit
an Anki note; invoke a provider; access the network; change configuration; or
push to GitHub.
