# AnkiForge AI v0.11 AnkiWeb 描述草稿

Add-on code：`1227582295`

以下两段分别用于 AnkiWeb 中文与英文描述。发布时可按页面格式合并使用。

## 中文描述

AnkiForge AI

这是 Anki 插件，不是共享牌组。不要在 Shared Decks 里搜索。

安装入口是 Anki 桌面端：工具 → 插件 → 获取插件。输入插件代码：1227582295。

它不是网页服务。它不提供现成卡组。它用于把你自己的 Markdown / 文本 / 笔记转换为可审核的 Anki 卡片。

主要功能：

- 粘贴 Markdown / 文本学习材料
- 使用 OpenAI-compatible Provider 生成候选卡片，默认支持 DeepSeek
- 审核、编辑、保留或丢弃 AI 生成的卡片
- 选择牌组、笔记类型和字段映射
- 写入前检查重复项
- 中英文界面

v0.11 新增：

- Markdown / TXT 导入
- 拖拽导入
- 基础 DOCX 文本提取（图片、公式和复杂排版不会保留）
- PDF 友好提示：当前安装包不包含 PDF 解析器或 OCR，请复制可选文本，或先转换为 TXT / Markdown
- 更清晰的导入状态、Provider 配置和 Anki 写入区域

安全说明：

- AI 生成卡片后必须由用户审核，确认后才会写入
- API key 仅会话内使用，不保存
- 不会自动调用 AI，也不会自动写入 Anki
- 可能重复的卡片默认跳过
- 不修改已有卡片、牌组或笔记类型

建议先使用独立测试牌组体验，并确认所用 AI Provider 的隐私政策。

## English description

AnkiForge AI

This is an Anki add-on, not a shared deck. Install it from Anki Desktop: Tools → Add-ons → Get Add-ons.

Add-on code: 1227582295.

It does not run as a web app. It does not include pre-made cards. It helps convert your own Markdown / text / notes into reviewable Anki cards.

Main features:

- Paste Markdown or text study material
- Generate candidate cards with OpenAI-compatible providers, with DeepSeek support by default
- Review, edit, keep, or discard AI-generated cards
- Choose the deck, note type, and field mapping
- Check for duplicates before writing
- Chinese and English interface

New in v0.11:

- Markdown / TXT import
- Drag-and-drop import
- Basic DOCX text extraction (images, formulas, and complex layout are not preserved)
- PDF fallback guidance: the package does not include a PDF parser or OCR; copy selectable text or convert the file to TXT / Markdown first
- Clearer import feedback, provider settings, and Anki write configuration

Safety:

- AI-generated cards must be reviewed by the user before writing
- API key is session-only and is not saved
- The add-on never calls AI or writes to Anki automatically
- Possible duplicate cards are skipped by default
- Existing notes, decks, and note types are not modified

Please test with a separate deck first and review the privacy policy of your chosen AI provider.
