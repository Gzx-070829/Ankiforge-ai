# v0.9 PR4 beginner knowledge-point context contract

## Scope

PR4 connects material input, offline recognition, knowledge-point selection,
candidate-card preview, and review markers inside one `BeginnerFlowSession`.
The feature remains a disposable, offline, read-only walkthrough.

The Qt dialog displays session state and forwards user choices to session
methods. It does not duplicate recognition, selection, candidate construction,
or invalidation rules.

## Preview-only models

`BeginnerKnowledgePointPreview` contains an in-memory identifier, title,
explanation, and source excerpt. `BeginnerCandidateCardPreview` contains an
in-memory identifier, the source knowledge-point identifier, question and
answer previews, and a source excerpt.

These types are beginner UI previews. They are not formal pipeline card or
write-ready types, cannot carry authority, and have no writer or collection
reference. Their content fields and the session's material are excluded from
session `repr` and `to_safe_dict`; safe output exposes counts only.

## Offline recognition

`refresh_mock_recognition_from_material()` uses only the current
`material_text`. A deterministic local rule splits text on sentence, line, and
semicolon boundaries, removes blank fragments, and keeps a small bounded set.
It does not run the real pipeline or any AI service. Empty material produces no
knowledge points.

The Step 2 user-facing statement is:

> 当前使用离线演练识别，不会联网，也不会调用 AI。

## Context continuity

The session stores recognized knowledge points and selected IDs. Candidate
previews are built by looking up only those selected IDs in the current
recognition result. Each candidate retains its originating knowledge-point ID,
so Step 4 can be audited against Step 3.

When no IDs are selected, Step 4 shows:

> 还没有选择知识点。请先回到上一步选择你想制卡的内容。

When candidates exist, Step 4 explains:

> 这些候选卡来自你刚才选择的知识点。

Review markers are disposable session state. They do not mean approval,
eligibility, readiness, consent, or authorization.

## Invalidation rules

- A material change clears recognition results, selected IDs, candidate
  previews, review markers, eligibility preview state, write-plan preview
  state, and final-confirmation preview state.
- A knowledge-point selection change clears candidate previews, review
  markers, and every later preview state.
- A candidate review change clears eligibility, write-plan, and
  final-confirmation preview state.
- Closing the dialog clears material, recognition, selection, candidates,
  review markers, and every later state. Nothing is persisted.

## Non-goals and safety boundary

PR4 does not call a Provider, read an API key, use the network, save material or
choices, write configuration, run the real pipeline, execute duplicate checks,
access an Anki collection, construct formal card/write-ready pipeline outputs,
call a writer, or create an Anki note.

The endpoint remains exactly:

> 演练完成，尚未写入 Anki

No preview state grants write authorization. In particular, approved,
eligible, ready-preview, and future-confirmation-readiness concepts remain
explanatory only.
