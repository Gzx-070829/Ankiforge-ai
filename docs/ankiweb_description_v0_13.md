# AnkiWeb Description v0.13 Draft

> Draft only. Do not paste or save on AnkiWeb until the final candidate package passes manual Anki acceptance and the user separately authorizes publication.

## 简体中文

AnkiForge AI `v0.13.0-product-grade-preview`

这是 Anki 插件，不是共享牌组。不要在 Shared Decks 里搜索；它也不是网页服务，不提供现成卡组。

安装入口：Anki Desktop → 工具 → 插件 → 获取插件

插件代码：`1227582295`

AnkiForge AI 用于把你自己的 Markdown、TXT、DOCX 或粘贴文本变成可审核的 Anki 候选卡。PDF 当前只提供 fallback 指引，不做 OCR 或完整解析。

v0.13 重点：

- 线性的 Create → Review → Write 工作台；
- AI Provider / Model / API key 收入独立设置窗口；
- 多种学习目标模式和模板；
- 本地、确定性的质量提示与多学科 regression benchmark；
- 更完整的编辑、复制、还原、保留/丢弃和统计；
- Front / Back / Source 字段建议；
- 可解释的重复检查、写入摘要、来源/Tags 和写入报告；
- 内置示例、帮助与中英文界面。

安全边界：

- API key 仅会话内使用，不保存；
- 不自动调用 AI，只有点击生成后才发送当前材料；
- AI 生成后必须人工审核；
- 不自动写入 Anki，查重和最终确认不可跳过；
- 可能重复的卡默认跳过；
- 不自动修改或删除已有卡片、牌组、笔记类型或字段；
- 完整 Undo 暂不提供。

本地质量规则只是辅助，不能保证内容正确或适合你的学习目标。你需要对最终卡片负责，建议先使用独立测试牌组。

## English

AnkiForge AI `v0.13.0-product-grade-preview`

This is an Anki add-on, not a shared deck. It runs inside Anki Desktop, is not a web app, and does not include pre-made decks.

Install from Anki Desktop: **Tools → Add-ons → Get Add-ons**

Add-on code: `1227582295`

AnkiForge AI turns your own pasted text, Markdown, TXT, and DOCX material into reviewable Anki card candidates. PDF remains fallback guidance; this version does not perform OCR or full PDF text extraction.

Highlights:

- A linear Create → Review → Write workbench
- Provider, model, and API key in a dedicated session dialog
- Learning-goal card modes and templates
- Local deterministic quality feedback and multidisciplinary regression benchmarks
- Edit, copy, restore, keep/discard, bulk actions, and review statistics
- Front / Back / optional Source field suggestions
- Explainable duplicate checks, write summaries, source/tags, and reports
- Built-in examples, help, and Chinese/English UI

Safety:

- The API key is session-only and is not saved
- No automatic AI calls; material is sent only after you click Generate
- AI-generated candidates always require manual review
- No automatic Anki writes; duplicate checking and final confirmation are hard gates
- Possible duplicates are skipped by default
- Existing notes/cards, decks, note types, and fields are not automatically modified or deleted
- Full Undo is not exposed

Local quality checks are assistive heuristics, not a correctness guarantee. You are responsible for the final cards. Start with a separate test deck.
