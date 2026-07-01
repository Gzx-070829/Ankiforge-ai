# v0.9 PR5 beginner review progressive-disclosure contract

## Scope

PR5 turns Step 4 and Step 5 into plain-language beginner pages. The underlying
v0.8 ideas remain visible only through optional, read-only explanations. The Qt
layer renders copy and calls `BeginnerFlowSession`; it does not reproduce review
policy or gain any execution capability.

## Step 4: candidate review

Each candidate preview comes from the knowledge points selected in Step 3. The
page shows its front preview, back preview, and source excerpt, followed by one
of three disposable choices:

- 看起来可以
- 需要修改
- 暂时不要

The choices are stored only in the current `BeginnerFlowSession`. Every
candidate needs one choice before the primary “继续” action advances. A choice
is a review draft, not approval or write authorization.

The page states:

> 你的选择只用于本次离线演练，不会写入 Anki。

With no candidates it states:

> 还没有候选卡。请先回到上一步选择知识点。

## Step 5: future conditions

Step 5 first gives the plain-language summary:

> 当前只是离线演练。即使你已经审核候选卡，也不会写入 Anki。

It then lists target deck, note type, field mapping, duplicate checking, and
final confirmation. Every item has the status “未来需要确认”. No item is shown
as ready, authorized, or completed.

## Progressive disclosure

“继续” is the single default primary action. “查看技术详情” is a flat,
secondary control and the details are collapsed by default. Expanding it shows
the plain-Chinese mappings for human review, future write-condition
eligibility, future write-plan preview, and the future final-confirmation
contract. Each technical explanation explicitly denies write authorization.

Reading technical details is never required to complete the walkthrough.

## Invalidation and disposal

- Changing material clears recognition, selection, candidates, review choices,
  and every later preview.
- Changing the selection clears candidates, review choices, and every later
  preview.
- Changing candidates clears review choices and every later preview.
- Changing a review choice clears eligibility, write-plan, and
  final-confirmation previews.
- Closing the dialog discards the whole session.

## Safety boundary

PR5 does not call a Provider, read an API key, use the network, persist user
content or choices, write configuration, execute duplicate checking, access an
Anki collection, construct formal card or write-ready output models, call a
writer, or create an Anki note.

The endpoint remains exactly:

> 演练完成，尚未写入 Anki
