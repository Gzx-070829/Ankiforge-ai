# Write Safety and Traceability

写入是独立于 AI 生成的受控动作。生成成功不代表批准，更不代表允许写入。

## 七道写入 gate

只有同时满足以下条件，写入才可进入最终执行：

1. 至少有一张用户明确保留的卡；
2. blocking 卡没有进入计划写入列表；
3. Front / Back 字段映射完整，Cloze 兼容性满足；
4. duplicate check 已针对当前内容完成；
5. 用户查看写入摘要并执行最终确认；
6. 目标牌组、笔记类型和字段仍然合法；
7. AI 生成流程已经结束，没有并行生成任务。

任一上游内容变化都会使 duplicate preview 和 final confirmation 失效。可能重复的卡默认跳过，不能绕过重复硬 gate。

## 写入前摘要

摘要应显示：计划写入数量、跳过重复数量、质量提醒数量、不能写入数量、目标牌组、笔记类型、字段映射、Tags 和安全来源标签。普通 UI 不显示完整本地路径、raw note IDs、内部对象名或 traceback。

字段映射只选择已有字段。AnkiForge AI 不自动新增字段、修改笔记类型或重构牌组。

Front、Back 和 Source 在审核/session/写入命令中保持纯文本，只在 writer 赋值边界统一换行、转义 HTML 一次并把换行转换为 `<br>`。重复检查把候选纯文本与已有 Anki HTML 都转换到同一 canonical plain-text key，因此 escaped 特殊字符和 `<br>` 不会造成漏判，也不会把已渲染字段再次送入 writer。高级 HTML/Markdown 渲染延期。

## 写入后报告

报告记录 written、skipped duplicate 和 failed 数量，以及牌组、笔记类型、Tags、来源标签、时间和 batch ID。内部 note IDs 仅用于当前窗口的批次记录，不在普通 UI 中展示。

失败必须逐项汇总，不能把部分成功误报为全部成功。报告不等于可以安全删除写入结果。

## Source labels and tags

来源字段只使用短标签，例如 `Pasted text`、`Markdown import`、`TXT import` 或 `Imported from DOCX`，不写完整路径。Tags 经过规范化、长度限制和安全字符处理，只添加到本次确认创建的 notes。

建议标签包括：

- `ankiforge`
- `ankiforge-ai`
- `mode-{card_mode}`
- `source-{source_type}`

## Last write and Undo

当前窗口可以在内存中记录 batch ID、时间、内部 note IDs、目标、Tags、来源和计数；普通 UI 只显示类似“上次写入：3 张到 Test Deck”的摘要。关闭窗口后不保留该会话记录。

**Full undo deferred.** 当前不提供自动删除按钮。安全 Undo 必须证明只针对本批次、逐条确认卡片未被后续编辑、二次确认并报告部分失败；绝不能按 tag 或 deck 批量删除历史卡。达到这些条件前，用户应使用 Anki 自身操作并先在测试牌组验收。

写入仍在现有 Anki collection 约束内执行；PR25 不把 collection mutation 放进普通 Python 后台线程。AI 生成已后台化，但它使用 `uses_collection=False`，两条线程边界不能混为一谈。

## English summary

Writing requires kept cards, no blocking entries, complete field mapping, a current duplicate check, a valid target, a finished generation task, and final confirmation. Front, Back, and Source are rendered once as escaped plain-text Anki HTML; duplicate checking canonicalizes existing HTML and candidate text through the same rules. Collection mutation is not moved to an ordinary worker thread. The add-on creates only confirmed new notes and does not automatically modify or delete existing notes/cards, decks, note types, or fields. Full Undo and advanced HTML/Markdown rendering remain deferred.
