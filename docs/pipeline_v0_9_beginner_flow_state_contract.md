# AnkiForge AI v0.9 Beginner Flow State and Copy Contract

## 1. Scope

PR1 defines pure-Python state and copy models for a future beginner mode. It
does not add or modify any Qt UI. The mode is an offline, read-only walkthrough
that helps a newcomer understand the pipeline without adding execution
capabilities.

The stable walkthrough is:

```text
select_material
  -> inspect_recognition
  -> choose_knowledge_points
  -> review_candidate_cards
  -> check_before_write
  -> completed_no_write
```

The completion title is exactly:

```text
演练完成，尚未写入 Anki
```

It must not be replaced by copy that claims writing completed, succeeded, or is
immediately ready.

## 2. Pure In-Memory Session

`BeginnerFlowSession` stores only navigation state, non-sensitive counts,
revision counters, and current/cleared/empty artifact states. It deliberately
does not store source text, card fronts or backs, candidate sources, reviewer
notes, knowledge-point identifiers, or a file path.

The session contains no API key, provider configuration, write authorization,
final user confirmation, Anki collection, writer object, duplicate checker,
persisted file path, or saved draft path.

Closing a session resets all counters and artifact states, marks it closed, and
prevents reuse. Nothing in PR1 persists a session. A later Qt owner must discard
its session object when its window closes.

## 3. Fixed Safety Copy

The future beginner surface must stably explain:

- 当前为离线只读演练
- 不会联网
- 不会调用 Provider
- 不会读取 API Key
- 不会执行 duplicate check
- 不会访问 Anki collection
- 不会写入 Anki
- 关闭后本次演练丢弃

These are fixed capability boundaries, not temporary progress messages.

## 4. Plain-Language Terminology

PR1 provides these mappings:

| Technical term | Beginner copy |
| --- | --- |
| Human Review | 人工审核 |
| Write Eligibility | 是否满足未来写入条件 |
| Write Plan | 未来写入方式预览 |
| Final confirmation contract | 真正写入前还需确认什么 |
| Provider draft | AI 服务草稿 |
| GeneratedCard | 正式待写入卡片 |
| WriteReadyPreviewItem | 写入就绪对象 |

The states `approved`, `eligible`, and `ready_preview` are explanatory review
or preview states only. Each state explicitly says it is not write
authorization. None may be promoted to consent, final confirmation, duplicate
clearance, or execution permission.

## 5. Clearing Rules

The model clears downstream state rather than retaining a stale result:

- changing material clears recognition, knowledge-point selection, candidate
  review, eligibility, write-plan preview, and final-confirmation preview;
- changing the knowledge-point selection clears candidate cards, candidate
  review, and every downstream preview;
- changing candidate cards clears review and every downstream preview;
- changing a review decision clears eligibility, write-plan preview, and
  final-confirmation preview;
- navigating backward clears every result downstream of the target step; and
- closing the session discards everything.

Clearing is represented explicitly by `BeginnerArtifactState.CLEARED` while the
session remains open. A closed session resets artifacts to `EMPTY` because no
walkthrough state survives.

## 6. Completion Meaning

Completion reports all of the following:

- 未创建 note
- 未修改卡组
- 未保存本次演练
- 未联网
- 未调用 provider

Completion is therefore completion of the walkthrough only. It is not a write
result, write authorization, or claim that a future write may proceed.

## 7. Advanced Workbench Warning

PR1 prepares this exact warning without adding an entry or changing the UI:

```text
旧版工作台（高级）包含开发/调试入口，可能包含真实 Anki 写入入口。请确认你理解风险后再进入。
```

The warning describes the existing advanced surface. It does not claim that the
new pipeline calls a real provider or performs a real Anki write.

## 8. Dependency and Runtime Boundary

The PR1 model must not import Qt, Anki, provider code, configuration loaders,
secret stores, writer code, network libraries, or a pipeline write bridge. It
must not call a provider, inspect credentials, access an Anki collection,
execute duplicate checking, construct a formal write object, or write a note.

`repr` and `to_safe_dict()` expose structural state only. Because the session
accepts no source, front, back, candidate source, or review-note content, those
representations cannot reproduce complete user content.

## 9. Non-Goals

PR1 does not:

- modify `MainDialog` or another Qt dialog;
- add a beginner-mode entry or render copy;
- connect the new model to a provider or the v0.8 preview chain;
- read or modify local configuration;
- persist paths, selections, cards, reviews, or progress;
- run duplicate checking;
- access an Anki collection;
- create `GeneratedCard` or `WriteReadyPreviewItem` objects;
- call a writer or write to Anki; or
- sync an installed add-on.

## 10. Automatic Verification

Pure-Python tests cover step order, copy completeness, fixed completion
language, non-authorization explanations, clearing behavior, close/discard
semantics, safe representations, stored-field shape, and forbidden dependency
imports and runtime calls. Tests import no Qt, Anki, provider, writer, config,
or network dependency.
