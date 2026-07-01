# AnkiForge AI v0.9 Beginner Entry and Mode Isolation Contract

## 1. Scope

PR2 adds a clear mode choice at the top of `MainDialog`:

- `新手模式（推荐）`
- `旧版工作台（高级）`

It adds only entry isolation and explanatory UI. PR2 does not implement the
interactive five-step walkthrough, material handling, knowledge-point context,
or candidate-review integration planned for later PRs.

## 2. Default Beginner Entry

The beginner choice is visually prominent and uses this description:

```text
离线只读演练：带你理解从学习材料到候选卡审核的流程。本模式不会联网、不会调用 AI 服务、不会写入 Anki。
```

Its action is `开始新手模式`. The action opens an independent read-only dialog
and does not build or expose the legacy workbench.

The dialog reads its stable step order, step copy, safety status, and completion
title from the PR1 `beginner_flow_models` module. Qt does not duplicate those
core policy values.

## 3. Beginner Overview Dialog

The dialog title is `新手模式（离线只读演练）`. It displays the five explanatory
steps and the fixed safety statements from PR1:

- 当前为离线只读演练
- 不会联网
- 不会调用 Provider
- 不会读取 API Key
- 不会执行 duplicate check
- 不会访问 Anki collection
- 不会写入 Anki
- 关闭后本次演练丢弃

It also displays the future safe endpoint:

```text
演练完成，尚未写入 Anki
```

Displaying that endpoint does not mark a session complete. PR2 has no
interactive session progression.

## 4. Legacy Isolation

The existing workbench is placed inside a container that is hidden by default.
It is built lazily only after the user explicitly selects `打开旧版工作台`.
This prevents the default beginner choice from causing legacy configuration or
credential fields to be read while preserving the existing legacy behavior
after the advanced entry is opened.

The advanced entry is labeled `旧版工作台（高级）` and warns:

```text
这里保留开发/调试功能，可能包含真实 Provider 设置或旧版添加到 Anki 入口。请确认你理解风险后再进入。
```

The PR1 advanced-workbench warning remains attached to this isolated group.

PR2 does not remove, rewrite, or relax the existing legacy add-to-Anki action.
It changes when the legacy controls are constructed and shown, not what their
commands do after the user explicitly opens the workbench.

## 5. Handler Boundary

`show_beginner_mode` only constructs and opens `BeginnerModeDialog`.
`show_legacy_workbench` only requests lazy workbench construction, reveals its
container, and disables the one-way open button.

Neither new handler directly reads configuration, invokes a provider, runs a
pipeline, touches `self.cards`, calls a writer, performs duplicate checking,
accesses an Anki collection, creates a note, or writes to Anki.

The legacy builder retains pre-existing configuration, provider, candidate, and
write controls. Those controls remain isolated behind the explicit advanced
entry and are not part of beginner mode.

## 6. Copy Boundary

Beginner action labels do not say save, apply, execute, run, generate cards,
add to Anki, or write. Terms such as Provider, API Key, duplicate check,
collection, and Anki write appear in the beginner dialog only in fixed negative
safety statements.

The UI does not claim that content is ready to write, can be written directly,
was written successfully, completed writing, or has already been written.
`approved`, `eligible`, and `ready_preview` retain the PR1 explanation that they
are not write authorization.

## 7. Dependency and Side-Effect Boundary

The beginner dialog imports Qt display classes and PR1 copy models only. It
does not import configuration, provider, writer, collection, pipeline,
transport, executor, secret-store, or network modules.

Opening beginner mode must not:

- load or save `config.json`;
- read an API key;
- call a provider or network client;
- run a pipeline or duplicate check;
- access an Anki collection;
- create or update a note;
- modify legacy candidate state; or
- sync an installed add-on.

## 8. Automatic Tests

Static and pure-Python tests verify entry copy, PR1 model reuse, fixed safety
copy, completion language, safe button labels, advanced labeling, lazy legacy
construction, isolated new handlers, non-authorization meanings, and the
absence of new runtime or network dependencies. Tests do not start a Qt event
loop, Anki, a provider, or a network operation.

## 9. Non-Goals

PR2 does not implement the five-step controller, persist a beginner session,
process a material, select knowledge points, generate or review cards, invoke a
provider, perform duplicate checking, request final confirmation, grant write
authorization, modify writer code, change the behavior of legacy write
commands, or write to Anki.
