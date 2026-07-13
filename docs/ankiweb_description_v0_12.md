# AnkiWeb Description v0.12

## 简体中文

AnkiForge AI v0.12.0 Public Preview

这是 Anki 插件，不是共享牌组。不要在 Shared Decks 里搜索。

安装入口：Anki 桌面端 → 工具 → 插件 → 获取插件

插件代码：1227582295

它不是网页服务，也不提供现成卡组。AnkiForge AI 用于把你自己的 Markdown、TXT、DOCX 或粘贴文本转换成可审核的 Anki 卡片。

v0.12 新增：

- concept / definition / exam / quick_review 四种卡片模式
- 卡片数量、答案长度和输出语言设置
- 本地 card quality warnings 和修改建议
- 更明确的逐张审核流程
- 写入前 summary
- 安全 Tags 与 Source traceability
- 最后一次写入批次的内存记录（不提供删除/Undo 按钮）

安全边界：

- 只有点击生成后，当前材料才会发送给用户配置的 AI Provider
- API key 仅会话内使用，不保存
- AI 生成卡片后必须由用户人工审核
- 写入 Anki 前必须再次确认
- 可能重复的卡默认跳过
- 不修改已有 notes/cards、牌组或笔记类型

质量检查只是辅助规则，不能保证 AI 内容绝对正确。请检查每张卡，并建议先使用测试牌组。

v0.12 支持 Markdown / TXT 导入、拖拽导入和基础 DOCX 文本提取。PDF 仍是 fallback guidance，不是完整解析，也不支持 OCR。

## English

AnkiForge AI v0.12.0 Public Preview

This is an Anki add-on, not a shared deck. Install it from Anki Desktop: Tools → Add-ons → Get Add-ons.

Add-on code: 1227582295

It is not a web app and does not include pre-made cards. AnkiForge AI helps convert your own Markdown, text, and notes into reviewable Anki cards.

New in v0.12:

- concept, definition, exam, and quick_review card modes
- card count, answer length, and output-language settings
- local card quality warnings and suggestions
- an explicit per-card review workflow
- a clearer pre-write summary
- safe tags and source traceability
- in-memory last-write batch tracking (no delete/Undo button)

Safety:

- Your material is sent to your configured AI Provider only after you click Generate Cards
- The API key is session-only and is not saved
- AI-generated cards must be reviewed by the user
- Every Anki write requires confirmation
- Possible duplicates are skipped by default
- Existing notes/cards, decks, and note types are not modified

Quality checks are assistive heuristics and cannot guarantee that AI content is correct. Review every card and start with a test deck.

v0.12 supports Markdown / TXT import, drag-and-drop import, and basic DOCX text extraction. PDF remains fallback guidance, not full parsing, and OCR is not included.
