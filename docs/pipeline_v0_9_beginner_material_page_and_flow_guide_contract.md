# AnkiForge AI v0.9 Beginner Material Page and Flow Guide Contract

## 1. Scope

PR3 upgrades the isolated beginner dialog into a disposable five-step guide. It
adds a welcome area, a plain-language offline safety bar, five-step navigation,
a current-step explanation, an in-memory material page, a bounded material
preview, and the existing safe completion message.

PR3 remains explanatory. It does not analyze material, identify real knowledge
points, create candidate cards, perform review, calculate eligibility, build a
write plan, request final confirmation, or write to Anki.

## 2. Surface Steps

The five visible steps are exactly:

1. 选择学习材料
2. 查看系统识别了什么
3. 选择要制卡的知识点
4. 审核候选卡
5. 查看距离真正写入还缺哪些条件

The sixth internal state is the safe guide endpoint:

```text
演练完成，尚未写入 Anki
```

Reaching it means only that the user viewed every explanation.

## 3. In-Memory Material

`BeginnerFlowSession.material_text` holds pasted or typed learning material for
the lifetime of one open dialog. No file path is requested and no material is
written to disk, configuration, a log, Anki, or another service.

The model provides:

- `material_char_count` for local UI feedback;
- `material_preview(max_chars=300)` for a bounded preview;
- `update_material(text)` for in-memory replacement and downstream clearing;
- `clear_material()` for explicit removal and downstream clearing; and
- `close()` for complete session disposal.

The material field is excluded from `repr`. `to_safe_dict()` reports only
whether material exists and its character count; it never includes material
text or a material preview.

## 4. Downstream Clearing

When material changes, the session returns to `select_material`, invalidates the
old recognition state, and clears knowledge-point selection, candidate cards,
candidate review, eligibility, write-plan preview, and final-confirmation
preview states. Clearing material applies the same rule and removes the text.

This behavior is present even though PR3 has no real downstream data or UI. It
prevents later PRs from accidentally retaining results derived from older
material.

## 5. Explanatory Navigation

`advance_guide()` changes only the current explanatory step. It does not mark
recognition, knowledge selection, candidate review, eligibility, write-plan, or
final-confirmation artifacts current.

Step 2 displays only the bounded material preview and explicitly says the
material has not been analyzed and real knowledge points have not been
identified. Steps 3–5 likewise explain future concepts without fabricating
selection, review, readiness, confirmation, consent, or authorization.

Back navigation uses the existing clearing rules. Editing material always
returns the guide to Step 1.

## 6. Safety Status

The guide reads this compact status copy from the pure-Python model:

- 当前是离线只读演练
- 不会联网
- 不会调用 AI
- 不会写入 Anki
- 关闭后丢弃本次内容

The beginner dialog contains navigation-only actions: `继续`, `上一步`,
`清空材料`, `结束演练`, and `关闭`.

## 7. Close and Reopen Behavior

Both the close button and the window close event clear the text widget and call
`BeginnerFlowSession.close()`. Closing resets the material, counters, revisions,
artifact states, and navigation state. `MainDialog` creates a new guide dialog
for each open action, so a reopened guide cannot recover earlier material.

## 8. Authorization Meaning

The meanings of `approved`, `eligible`, `ready_preview`, and
`ready_for_future_confirmation` remain explicit: each is a draft, condition, or
preview state and is not write authorization. PR3 does not create any of these
states; it only preserves their safe language for future explanatory UI.

## 9. Dependency and Execution Boundary

The beginner dialog imports Qt display classes and the pure-Python beginner
model only. It does not import or call provider, transport, network,
configuration, secret-store, pipeline, duplicate-check, collection, note, or
writer code.

PR3 does not:

- send material over a network;
- accept or inspect credentials;
- read or write `config.json`;
- access an Anki collection;
- perform duplicate checking;
- create `GeneratedCard` or `WriteReadyPreviewItem` objects;
- call a provider or writer;
- create or modify an Anki note; or
- change the isolated legacy workbench behavior.

## 10. Verification

Pure-Python and static tests cover material storage, bounded preview, character
count, downstream clearing, session disposal, safe representations, exact step
titles, explanatory-only navigation, model-copy reuse, safe action labels, and
forbidden dependencies. Tests do not start Qt, Anki, a provider, or a network
operation.
